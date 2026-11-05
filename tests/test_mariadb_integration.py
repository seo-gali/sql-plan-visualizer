import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from sqlpvi.db.mariadb import collect_mariadb
from sqlpvi.db.safety import DatabaseError

TEST_URL = os.environ.get("SQLPVI_TEST_MARIADB_URL", "")
if TEST_URL:
    import pymysql
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_URL, reason="isolated MariaDB URL not set"),
]


@pytest.mark.parametrize(
    "filename",
    ["simple-select.sql", "join.sql", "aggregate.sql", "cte.sql", "subquery.sql"],
)
def test_real_mariadb_plan(filename):
    sql = (Path(__file__).parent.parent / "fixtures/sql" / filename).read_text(
        encoding="utf-8"
    )
    plan = collect_mariadb(sql, TEST_URL)
    assert plan.vendor == "mariadb" and plan.mode == "ESTIMATED"
    assert plan.root.operation == "query_block"
    assert plan.root.children


def test_actual_read_only_and_timeout():
    url = urlsplit(TEST_URL)
    with (
        pymysql.connect(
            host=url.hostname,
            port=url.port or 3306,
            user=unquote(url.username or ""),
            password=unquote(url.password or ""),
            database=unquote(url.path.lstrip("/")),
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("START TRANSACTION READ ONLY")
        cursor.execute("SELECT COUNT(*) FROM customers WHERE active")
        before = cursor.fetchone()[0]
        with pytest.raises(pymysql.MySQLError):
            cursor.execute("UPDATE customers SET active = false")
        connection.rollback()
        cursor.execute("SELECT COUNT(*) FROM customers WHERE active")
        assert cursor.fetchone()[0] == before
        cursor.execute("SET SESSION max_statement_time = 0.05")
        with pytest.raises(pymysql.MySQLError) as error:
            cursor.execute("SELECT SLEEP(0.2)")
        assert error.value.args[0] == 1969


@pytest.mark.parametrize(
    "user",
    [
        "root",
        "sqlpvi_schema_writer",
        "sqlpvi_table_writer",
        "sqlpvi_column_writer",
        "sqlpvi_grantable",
    ],
)
def test_privileged_accounts_are_rejected(user):
    with pytest.raises(DatabaseError, match="least-privilege"):
        collect_mariadb("SELECT 1", f"mariadb://{user}@127.0.0.1:53306/sqlpvi")


def test_sql_and_authentication_errors_are_masked():
    with pytest.raises(DatabaseError, match="DATABASE_ERROR") as error:
        collect_mariadb("SELECT missing_fixture_column FROM customers", TEST_URL)
    assert "missing_fixture_column" not in str(error.value)
    with pytest.raises(DatabaseError) as error:
        collect_mariadb(
            "SELECT 1",
            "mariadb://sqlpvi_nonexistent:private-fixture-value@127.0.0.1:53306/sqlpvi",
        )
    assert "private-fixture-value" not in str(error.value)


def test_read_only_transaction_blocks_even_a_privileged_account():
    with (
        pymysql.connect(
            host="127.0.0.1", port=53306, user="root", database="sqlpvi"
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("START TRANSACTION READ ONLY")
        with pytest.raises(pymysql.MySQLError) as error:
            cursor.execute("UPDATE customers SET active = false")
        assert error.value.args[0] == 1792
        connection.rollback()


def test_collector_lock_timeout():
    with (
        pymysql.connect(
            host="127.0.0.1", port=53306, user="root", database="sqlpvi"
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("LOCK TABLES customers WRITE")
        try:
            with pytest.raises(DatabaseError, match="OperationalError"):
                collect_mariadb("SELECT id FROM customers", TEST_URL)
        finally:
            cursor.execute("UNLOCK TABLES")
