import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sqlpvi.analyze import analyze
from sqlpvi.cli import main
from sqlpvi.db.safety import DatabaseError, safe_query
from sqlpvi.db.sqlserver import collect_sqlserver, sqlserver_plan
from sqlpvi.parser import AnalysisError
from sqlpvi.render import render_html

XML = (Path(__file__).parent.parent / "fixtures/plans/sqlserver-select.xml").read_text(
    encoding="utf-8"
)
URL = "sqlserver://reader:private-fixture-value@127.0.0.1:14330/sqlpvi"


def test_namespace_hierarchy_and_vendor_fields():
    plan = sqlserver_plan(XML)
    assert (
        plan.vendor == "sqlserver"
        and plan.basis == "DATABASE"
        and plan.mode == "ESTIMATED"
    )
    assert plan.root.operation == "Nested Loops" and plan.root.relation is None
    assert len(plan.root.children) == 2
    scan, seek = plan.root.children
    assert scan.relation == "[dbo].[customers]" and seek.relation == "[dbo].[orders]"
    assert seek.access_method == "Index Seek" and seek.estimated_rows == 20
    assert seek.details["Objects"][0]["Index"] == "[orders_customer_idx]"
    assert plan.root.details["LogicalOp"] == "Inner Join"
    assert {node.id for node in [plan.root, scan, seek]} == {
        "plan-0",
        "plan-1",
        "plan-2",
    }


@pytest.mark.parametrize(
    "raw",
    [
        None,
        XML.encode("utf-16"),
        "",
        "<broken>",
        XML.replace(
            "http://schemas.microsoft.com/sqlserver/2004/07/showplan",
            "https://example.invalid",
        ),
        XML.replace('StatementType="SELECT"', 'StatementType="UPDATE"'),
        XML.replace('EstimateRows="500"', 'EstimateRows="NaN"'),
        XML.replace(
            'EstimatedTotalSubtreeCost="0.1"', 'EstimatedTotalSubtreeCost="-1"'
        ),
        XML.replace('PhysicalOp="Index Seek"', ""),
        '<!DOCTYPE x SYSTEM "file:///private-fixture-value"><x/>',
        '<!DOCTYPE x [<!ENTITY secret SYSTEM "http://example.invalid/private">]><x>&secret;</x>',
    ],
)
def test_malformed_and_external_entity_xml_rejected(raw):
    with pytest.raises(DatabaseError, match="DATABASE_PLAN_ERROR"):
        sqlserver_plan(raw)


def test_select_without_query_preserves_missing_estimates():
    raw = """<ShowPlanXML xmlns="http://schemas.microsoft.com/sqlserver/2004/07/showplan">
      <BatchSequence><Batch><Statements>
        <StmtSimple StatementType="SELECT WITHOUT QUERY" StatementText="SELECT 1"/>
      </Statements></Batch></BatchSequence></ShowPlanXML>"""
    plan = sqlserver_plan(raw)
    assert plan.root.operation == "SELECT WITHOUT QUERY"
    assert plan.root.estimated_rows is None and plan.root.estimated_cost is None
    assert plan.root.children == []


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE customers SET active = 0",
        "SELECT 1; SELECT 2",
        "SELECT * INTO backup FROM customers",
        "EXEC xp_cmdshell 'whoami'",
        "SELECT * FROM customers WITH (UPDLOCK)",
        "SELECT * FROM customers WITH (TABLOCKX)",
        "SELECT * FROM customers WITH (NOLOCK, UPDLOCK)",
        "SELECT * FROM customers WITH (HOLDLOCK)",
        "SELECT * FROM customers WITH (XLOCK)",
        "SELECT * FROM customers WITH (ROWLOCK)",
        "SELECT * FROM customers WITH (UNKNOWN_HINT)",
        "SELECT * FROM customers WITH (INDEX(PK_customers))",
        "SELECT * FROM customers WITH (FORCESEEK(PK_customers(id)))",
        "SELECT NEXT VALUE FOR sequence_fixture",
        "SELECT dbo.sum(1)",
    ],
)
def test_statement_boundary_before_driver_import(monkeypatch, sql):
    monkeypatch.setitem(sys.modules, "pymssql", None)
    with pytest.raises((DatabaseError, AnalysisError)) as error:
        collect_sqlserver(sql, URL)
    assert "install" not in str(error.value)


def test_runtime_dialect_and_missing_driver(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymssql", None)
    with pytest.raises(DatabaseError, match="runtime"):
        collect_sqlserver("SELECT 1", URL, runtime=True)
    with pytest.raises(DatabaseError, match="tsql"):
        collect_sqlserver("SELECT 1", URL, dialect="postgres")
    with pytest.raises(DatabaseError, match="install the locked pymssql"):
        collect_sqlserver("SELECT 1", URL)


@pytest.fixture
def fake_driver(monkeypatch):
    class DriverError(Exception):
        pass

    driver = MagicMock()
    driver.Error = DriverError
    connection = driver.connect.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.side_effect = [[("CONNECT",), ("SELECT",), ("SHOWPLAN",)], []]
    cursor.fetchone.return_value = (XML,)
    monkeypatch.setitem(sys.modules, "pymssql", driver)
    return driver, connection, cursor


def test_showplan_batches_timeouts_and_cleanup(fake_driver):
    driver, connection, cursor = fake_driver
    plan = collect_sqlserver("SELECT 1", URL)
    assert plan.vendor == "sqlserver"
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert statements[0] == "SET LOCK_TIMEOUT 1000"
    assert statements[-3:] == [
        "SET SHOWPLAN_XML ON",
        "SELECT 1",
        "SET SHOWPLAN_XML OFF",
    ]
    kwargs = driver.connect.call_args.kwargs
    assert kwargs["login_timeout"] == kwargs["timeout"] == 5
    assert kwargs["encryption"] == "require" and kwargs["read_only"] is True
    assert kwargs["autocommit"] is False
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    driver.connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "hint", ["NOLOCK", "readuncommitted", "FORCESEEK", "FORCESCAN", "NOLOCK, FORCESEEK"]
)
def test_argument_free_read_hints_reach_showplan(fake_driver, hint):
    _, connection, cursor = fake_driver
    sql = f"SELECT c.id FROM customers AS c WITH ({hint}) WHERE c.id = 1"
    plan = collect_sqlserver(sql, URL)
    assert plan.mode == "ESTIMATED"
    assert cursor.execute.call_args_list[-3].args == ("SET SHOWPLAN_XML ON",)
    assert cursor.execute.call_args_list[-2].args == (safe_query(sql, "tsql"),)
    assert hint.upper() in cursor.execute.call_args_list[-2].args[0].upper()
    connection.commit.assert_not_called()


@pytest.mark.parametrize(
    "privilege", ["UPDATE", "EXECUTE", "CONTROL SERVER", "GRANT OPTION"]
)
def test_privileges_rejected_before_showplan(fake_driver, privilege):
    driver, _, cursor = fake_driver
    cursor.fetchall.side_effect = [[(privilege,)]]
    with pytest.raises(DatabaseError, match="least-privilege"):
        collect_sqlserver("SELECT 1", URL)
    assert not any(
        call.args[0] == "SET SHOWPLAN_XML ON" for call in cursor.execute.call_args_list
    )
    driver.connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "stage",
    ["SET SHOWPLAN_XML ON", "SELECT 1", "SET SHOWPLAN_XML OFF", "fetch", "parse"],
)
def test_failure_always_attempts_showplan_off_and_rollback(fake_driver, stage):
    driver, connection, cursor = fake_driver

    def execute(statement):
        if statement == stage:
            raise driver.Error("private-fixture-value")

    cursor.execute.side_effect = execute
    if stage == "fetch":
        cursor.fetchone.side_effect = driver.Error("private-fixture-value")
    if stage == "parse":
        cursor.fetchone.return_value = ("<private-fixture-value/>",)
    with pytest.raises(DatabaseError) as error:
        collect_sqlserver("SELECT 1", URL)
    assert "private-fixture-value" not in str(error.value)
    assert cursor.execute.call_args_list[-1].args == ("SET SHOWPLAN_XML OFF",)
    connection.rollback.assert_called_once()
    driver.connect.return_value.__exit__.assert_called_once()


def test_connection_error_is_masked(fake_driver):
    driver, _, _ = fake_driver
    driver.connect.side_effect = driver.Error("password=private-fixture-value")
    with pytest.raises(DatabaseError) as error:
        collect_sqlserver("SELECT 1", URL)
    assert "private-fixture-value" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "postgresql://reader@localhost/db",
        "sqlserver://reader@localhost/",
        "sqlserver://reader@localhost:invalid/db",
        "sqlserver://reader@localhost/db?token=private",
        "sqlserver://reader@localhost/db#private",
    ],
)
def test_invalid_url_does_not_connect(fake_driver, url):
    driver, _, _ = fake_driver
    with pytest.raises(DatabaseError):
        collect_sqlserver("SELECT 1", url)
    driver.connect.assert_not_called()


def test_html_escapes_plan_identifiers():
    report = analyze("SELECT 1", dialect="tsql")
    report.plan = sqlserver_plan(
        XML.replace("[orders_customer_idx]", "&lt;script&gt;alert(1)&lt;/script&gt;")
    )
    html = render_html(report)
    assert "<span>sqlserver</span>" in html and ">DATABASE</span>" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_static_cli_without_driver_and_runtime_rejection(monkeypatch, capsys):
    path = Path(__file__).parent.parent / "fixtures/sql/join.sql"
    command = [
        "sqlpvi",
        "analyze",
        str(path),
        "--vendor",
        "sqlserver",
        "--format",
        "json",
    ]
    monkeypatch.setitem(sys.modules, "pymssql", None)
    monkeypatch.setattr(sys, "argv", command)
    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dialect"] == "tsql" and report["plan"] is None
    monkeypatch.setattr(sys, "argv", command + ["--database", "--runtime"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
