import json
import sys
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from sqlpvi.database import DatabaseError, collect_postgres, postgres_plan, safe_query
from sqlpvi.parser import AnalysisError


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM customers",
        "SELECT 1; SELECT 2",
        "SELECT * INTO backup FROM customers",
        "SELECT * FROM customers FOR UPDATE",
        "WITH x AS (DELETE FROM customers RETURNING *) SELECT * FROM x",
        "SELECT pg_sleep(1)",
        "SELECT nextval('seq')",
        "SELECT public.sum(1)",
        "SELECT 1::custom_type",
    ],
)
def test_database_allowlist(sql):
    with pytest.raises((DatabaseError, AnalysisError)):
        safe_query(sql)


def test_aggregate_and_subquery_allowed():
    assert "SUM" in safe_query("SELECT SUM(o.amount) FROM orders o")
    assert "EXISTS" in safe_query("SELECT 1 WHERE EXISTS (SELECT 1 FROM customers)")


def test_postgres_adapter_keeps_vendor_details():
    plan = postgres_plan(
        [
            {
                "Plan": {
                    "Node Type": "Aggregate",
                    "Plan Rows": 1,
                    "Total Cost": 10,
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "orders",
                            "Plan Rows": 12,
                            "Total Cost": 8,
                            "Filter": "amount > 1",
                        }
                    ],
                }
            }
        ]
    )
    assert plan.basis == "DATABASE" and plan.mode == "ESTIMATED"
    assert plan.root.children[0].relation == "orders"
    assert plan.root.children[0].details["Filter"] == "amount > 1"
    assert json.loads(json.dumps(asdict(plan)))["vendor"] == "postgres"


@pytest.mark.parametrize(
    "raw", [{}, [], [{"Plan": {}}], [{"Plan": {"Node Type": "Scan", "Plans": {}}}]]
)
def test_bad_plan(raw):
    with pytest.raises(DatabaseError):
        postgres_plan(raw)


def test_driver_error_does_not_expose_credentials(monkeypatch):
    class OperationalError(Exception):
        pass

    def fail(*args, **kwargs):
        raise OperationalError("password=private-test-value host=private-host")

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(
            connect=fail,
            Error=OperationalError,
            conninfo=SimpleNamespace(
                conninfo_to_dict=lambda dsn: {"host": "private-host"}
            ),
        ),
    )
    with pytest.raises(DatabaseError) as error:
        collect_postgres(
            "SELECT 1", "postgresql://test:private-test-value@private-host/db"
        )
    assert "private" not in str(error.value)
    assert "OperationalError" in str(error.value)


def test_postgres_missing_driver_is_a_configuration_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", None)
    with pytest.raises(DatabaseError, match=r"sql-plan-visualizer\[postgres\]"):
        collect_postgres("SELECT 1", "postgresql://reader@localhost/db")
    with pytest.raises((DatabaseError, AnalysisError), match="UNSUPPORTED"):
        collect_postgres("DELETE FROM customers", "postgresql://reader@localhost/db")


def test_runtime_adapter_requires_actual_measurements():
    raw = [{"Plan": {"Node Type": "Result", "Plan Rows": 1}}]
    with pytest.raises(DatabaseError, match="actual measurements"):
        postgres_plan(raw, runtime=True)


def test_missing_configuration_and_wrong_dialect():
    with pytest.raises(DatabaseError, match="set SQLPVI_POSTGRES_URL"):
        collect_postgres("SELECT 1", "")
    with pytest.raises(DatabaseError, match="dialect"):
        collect_postgres("SELECT 1", "", "mysql")
