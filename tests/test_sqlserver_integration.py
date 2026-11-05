"""Only enable against the project's approved loopback SQL Server fixture."""

import os
from contextlib import contextmanager
from pathlib import Path

import pytest

from sqlpvi.db.safety import DatabaseError, safe_query
from sqlpvi.db.sqlserver import collect_sqlserver

TEST_URL = os.environ.get("SQLPVI_TEST_SQLSERVER_URL", "")
if TEST_URL:
    import pymssql
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_URL, reason="isolated SQL Server URL not set"),
]


def fixture_connection(user="sqlpvi_reader", timeout=5):
    return pymssql.connect(
        server="127.0.0.1",
        port="14330",
        user=user,
        database="sqlpvi",
        password="Sqlpvi-Fixture-2026!",
        login_timeout=5,
        timeout=timeout,
        encryption="require",
        autocommit=False,
    )


@pytest.mark.parametrize(
    "filename",
    ["simple-select.sql", "join.sql", "aggregate.sql", "cte.sql", "subquery.sql"],
)
def test_real_estimated_plan(filename):
    sql = (Path(__file__).parent.parent / "fixtures/sql" / filename).read_text(
        encoding="utf-8"
    )
    plan = collect_sqlserver(sql, TEST_URL)
    assert (
        plan.vendor == "sqlserver"
        and plan.mode == "ESTIMATED"
        and plan.basis == "DATABASE"
    )
    assert plan.root.operation and plan.root.estimated_rows >= 0


def test_showplan_does_not_execute_the_query():
    sql = "SELECT c.id / (c.id - c.id) FROM dbo.customers AS c"
    plan = collect_sqlserver(sql, TEST_URL)
    assert plan.root.operation
    with (
        fixture_connection() as connection,
        connection.cursor() as cursor,
        pytest.raises(pymssql.Error),
    ):
        cursor.execute(safe_query(sql, "tsql"))
        cursor.fetchall()


@pytest.mark.parametrize(
    "hint", ["NOLOCK", "READUNCOMMITTED", "FORCESEEK", "FORCESCAN"]
)
def test_real_estimated_plan_with_read_hint(hint):
    sql = f"SELECT c.id FROM customers AS c WITH ({hint}) WHERE c.id = 1"
    plan = collect_sqlserver(sql, TEST_URL)
    assert plan.vendor == "sqlserver" and plan.mode == "ESTIMATED"
    assert plan.root.operation and plan.root.actual_rows is None


@pytest.mark.parametrize(
    "user", ["sa", "sqlpvi_writer", "sqlpvi_column_writer", "sqlpvi_grantable"]
)
def test_privileged_accounts_are_rejected(user):
    with pytest.raises(DatabaseError, match="least-privilege"):
        collect_sqlserver(
            "SELECT 1",
            f"sqlserver://{user}:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi",
        )


def test_reader_cannot_write_and_data_is_preserved():
    with fixture_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*), SUM(CAST(active AS int)) FROM dbo.customers")
        before = cursor.fetchone()
        with pytest.raises(pymssql.Error):
            cursor.execute("UPDATE dbo.customers SET active = 0")
        connection.rollback()
        cursor.execute("SELECT COUNT(*), SUM(CAST(active AS int)) FROM dbo.customers")
        assert cursor.fetchone() == before


def test_permission_sql_and_authentication_errors_are_masked():
    urls = [
        "sqlserver://sqlpvi_no_showplan:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi",
        "sqlserver://nonexistent:private-fixture-value@127.0.0.1:14330/sqlpvi",
    ]
    for url in urls:
        with pytest.raises(DatabaseError, match="DATABASE_ERROR") as error:
            collect_sqlserver("SELECT id FROM customers", url)
        assert "private-fixture-value" not in str(error.value)
        assert "Sqlpvi-Fixture-2026!" not in str(error.value)
    with pytest.raises(DatabaseError) as error:
        collect_sqlserver("SELECT missing_fixture_column FROM customers", TEST_URL)
    assert "missing_fixture_column" not in str(error.value)


@pytest.mark.parametrize(
    "sql", ["SELECT 1", "SELECT missing_fixture_column FROM customers"]
)
def test_showplan_restored_and_connection_closed(monkeypatch, sql):
    original_connect = pymssql.connect
    observed = []

    @contextmanager
    def capture(**kwargs):
        with original_connect(**kwargs) as connection:
            observed.append(connection)
            try:
                yield connection
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 42")
                    assert cursor.fetchone() == (42,)

    monkeypatch.setattr(pymssql, "connect", capture)
    if "missing_fixture_column" in sql:
        with pytest.raises(DatabaseError):
            collect_sqlserver(sql, TEST_URL)
    else:
        collect_sqlserver(sql, TEST_URL)
    with pytest.raises(pymssql.Error):
        observed[0].cursor().execute("SELECT 1")


def test_actual_driver_query_timeout():
    with fixture_connection(timeout=1) as connection, connection.cursor() as cursor:
        with pytest.raises(pymssql.Error) as error:
            cursor.execute("WAITFOR DELAY '00:00:03'")
        assert "timed out" in str(error.value).lower()


def test_collector_lock_timeout():
    with fixture_connection("sa") as connection, connection.cursor() as cursor:
        cursor.execute("ALTER TABLE dbo.customers SET (LOCK_ESCALATION = TABLE)")
        try:
            with pytest.raises(DatabaseError, match="OperationalError"):
                collect_sqlserver("SELECT id FROM customers", TEST_URL)
        finally:
            connection.rollback()
