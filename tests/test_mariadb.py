import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sqlpvi.analyze import analyze
from sqlpvi.cli import main
from sqlpvi.db.mariadb import collect_mariadb, mariadb_plan
from sqlpvi.db.safety import DatabaseError
from sqlpvi.parser import AnalysisError
from sqlpvi.render import render_html


def test_vendor_fields_and_access_type_are_preserved():
    plan = mariadb_plan(
        {
            "query_block": {
                "select_id": 1,
                "nested_loop": [
                    {
                        "table": {
                            "table_name": "c",
                            "access_type": "range",
                            "rows": 30,
                            "key": "PRIMARY",
                            "possible_keys": ["PRIMARY"],
                            "filtered": 20,
                            "attached_condition": "c.id > 1",
                        }
                    }
                ],
            }
        }
    )
    table = plan.root.children[0].children[0]
    assert table.access_method == "range"
    assert table.details["possible_keys"] == ["PRIMARY"]
    assert table.details["attached_condition"] == "c.id > 1"
    assert table.details["key"] == "PRIMARY"
    assert table.details["filtered"] == 20
    assert table.estimated_rows == 30
    assert table.operation == "table"


def test_runtime_and_malformed_json_are_rejected():
    with pytest.raises(DatabaseError, match="runtime"):
        collect_mariadb("SELECT 1", "", runtime=True)
    with pytest.raises(DatabaseError):
        mariadb_plan({"Plan": {}})


@pytest.mark.parametrize(
    "raw", [None, [], {}, {"query_block": []}, {"query_block": {}}]
)
def test_malformed_plan_is_rejected(raw):
    with pytest.raises(DatabaseError, match="DATABASE_PLAN_ERROR"):
        mariadb_plan(raw)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE customers SET active = false",
        "SELECT 1; SELECT 2",
        "SELECT * INTO OUTFILE '/tmp/sqlpvi.txt' FROM customers",
        "SELECT * FROM customers FOR UPDATE",
        "SELECT SLEEP(1)",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT GET_LOCK('sqlpvi', 1)",
    ],
)
def test_unsafe_query_is_rejected_before_connect(monkeypatch, sql):
    monkeypatch.setitem(sys.modules, "pymysql", None)
    with pytest.raises((DatabaseError, AnalysisError)) as error:
        collect_mariadb(sql, "mariadb://reader@127.0.0.1/sqlpvi")
    assert "install" not in str(error.value)


def test_missing_driver_has_a_safe_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymysql", None)
    with pytest.raises(DatabaseError, match="install the locked PyMySQL"):
        collect_mariadb(
            "SELECT 1", "mariadb://reader:private-fixture-value@127.0.0.1/sqlpvi"
        )


@pytest.fixture
def fake_driver(monkeypatch):
    class DriverError(Exception):
        pass

    driver = MagicMock()
    driver.MySQLError = DriverError
    connection = driver.connect.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [("USAGE", "NO"), ("SELECT", "NO")]
    cursor.fetchone.return_value = ('{"query_block": {"message": "No tables used"}}',)
    monkeypatch.setitem(sys.modules, "pymysql", driver)
    return driver, cursor


def test_collector_applies_read_only_timeouts_and_cleans_up(fake_driver):
    driver, cursor = fake_driver
    plan = collect_mariadb("SELECT 1", "mariadb://reader@127.0.0.1:53306/sqlpvi")
    assert plan.vendor == "mariadb" and plan.mode == "ESTIMATED"
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert "SET ROLE NONE" in statements
    assert "SET SESSION max_statement_time = 5" in statements
    assert "SET SESSION lock_wait_timeout = 1" in statements
    assert "SET SESSION innodb_lock_wait_timeout = 1" in statements
    assert statements.index("START TRANSACTION READ ONLY") < len(statements) - 1
    assert all(
        scope in statements[-2]
        for scope in (
            "USER_PRIVILEGES",
            "SCHEMA_PRIVILEGES",
            "TABLE_PRIVILEGES",
            "COLUMN_PRIVILEGES",
        )
    )
    assert statements[-1] == "EXPLAIN FORMAT=JSON SELECT 1"
    assert driver.connect.call_args.kwargs["local_infile"] is False
    assert driver.connect.call_args.kwargs["read_timeout"] == 6
    driver.connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("grant", [("UPDATE", "NO"), ("SELECT", "YES")])
def test_write_and_grant_privileges_are_rejected(fake_driver, grant):
    driver, cursor = fake_driver
    cursor.fetchall.return_value = [grant]
    with pytest.raises(DatabaseError, match="least-privilege"):
        collect_mariadb("SELECT 1", "mariadb://reader@127.0.0.1/sqlpvi")
    assert not any(
        call.args[0].startswith("EXPLAIN") for call in cursor.execute.call_args_list
    )
    driver.connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("stage", ["connect", "execute", "fetchone"])
def test_driver_errors_are_masked(fake_driver, stage):
    driver, cursor = fake_driver
    target = driver.connect if stage == "connect" else getattr(cursor, stage)
    target.side_effect = driver.MySQLError("password=private-fixture-value")
    with pytest.raises(DatabaseError) as error:
        collect_mariadb(
            "SELECT 1", "mariadb://reader:private-fixture-value@127.0.0.1/sqlpvi"
        )
    assert "private-fixture-value" not in str(error.value)
    if stage != "connect":
        driver.connect.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "dsn",
    [
        "",
        "postgresql://reader@localhost/db",
        "mariadb://reader@localhost/",
        "mariadb://reader@localhost:invalid/db",
        "mariadb://reader@localhost/db?option=secret",
        "mariadb://reader@localhost/db#secret",
    ],
)
def test_invalid_url_is_rejected_before_connect(fake_driver, dsn):
    driver, _ = fake_driver
    with pytest.raises(DatabaseError):
        collect_mariadb("SELECT 1", dsn)
    driver.connect.assert_not_called()


def test_database_html_preserves_and_escapes_vendor_fields():
    report = analyze("SELECT c.id FROM customers c", dialect="mysql")
    report.plan = mariadb_plan(
        {
            "query_block": {
                "table": {
                    "table_name": "customers",
                    "access_type": "range",
                    "rows": 30,
                    "key": "PRIMARY",
                    "filtered": 20,
                    "attached_condition": "</script><script>alert(1)</script>",
                }
            }
        }
    )
    html = render_html(report)
    assert '<section aria-labelledby="plan-title">' in html
    assert "<span>mariadb</span>" in html and ">DATABASE</span>" in html
    assert "PRIMARY" in html and "attached_condition" in html
    assert "&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "</script><script>alert(1)</script>" not in html


def test_mariadb_cli_static_mode_and_runtime_rejection(monkeypatch, capsys):
    path = Path(__file__).parent.parent / "fixtures/sql/join.sql"
    command = [
        "sqlpvi",
        "analyze",
        str(path),
        "--vendor",
        "mariadb",
        "--format",
        "json",
    ]
    monkeypatch.setitem(sys.modules, "pymysql", None)
    monkeypatch.setattr(sys, "argv", command)
    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dialect"] == "mysql" and report["plan"] is None
    monkeypatch.setattr(sys, "argv", command + ["--database", "--runtime"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "only for PostgreSQL" in capsys.readouterr().err
