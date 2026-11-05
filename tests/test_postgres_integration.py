"""Set SQLPVI_TEST_POSTGRES_URL only for the approved isolated fixture DB."""

import os
from pathlib import Path

import psycopg
import pytest

from sqlpvi.analyze import analyze
from sqlpvi.database import DatabaseError, collect_postgres
from sqlpvi.metadata import enrich_postgres

TEST_URL = os.environ.get("SQLPVI_TEST_POSTGRES_URL", "")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_URL, reason="isolated PostgreSQL test URL not set"),
]


@pytest.mark.parametrize(
    "filename",
    ["simple-select.sql", "join.sql", "aggregate.sql", "cte.sql", "subquery.sql"],
)
def test_real_estimated_plan(filename):
    sql = (Path(__file__).parent.parent / "fixtures/sql" / filename).read_text(
        encoding="utf-8"
    )
    plan = collect_postgres(sql, TEST_URL)
    assert plan.mode == "ESTIMATED" and plan.vendor == "postgres"
    assert plan.root.operation
    assert plan.root.estimated_rows is not None
    assert "Actual Rows" not in plan.root.details


def test_actual_reader_permissions_and_timeouts():
    with psycopg.connect(TEST_URL) as connection:
        assert connection.execute("SHOW transaction_read_only").fetchone()[0] == "on"
        before = connection.execute(
            "SELECT COUNT(*) FROM customers WHERE active"
        ).fetchone()[0]
        with pytest.raises(psycopg.Error):
            connection.execute("UPDATE customers SET active = false")
        connection.rollback()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM customers WHERE active"
            ).fetchone()[0]
            == before
        )
        connection.execute("SET LOCAL statement_timeout = 50")
        with pytest.raises(psycopg.errors.QueryCanceled):
            connection.execute("SELECT pg_sleep(0.2)")


def test_privileged_account_is_rejected():
    with pytest.raises(DatabaseError, match="least-privilege"):
        collect_postgres("SELECT 1", "postgresql://postgres@127.0.0.1:55432/sqlpvi")


def test_collector_lock_timeout_is_enforced():
    with psycopg.connect("postgresql://postgres@127.0.0.1:55432/sqlpvi") as locker:
        locker.execute("LOCK TABLE customers IN ACCESS EXCLUSIVE MODE")
        with pytest.raises(DatabaseError, match="LockNotAvailable"):
            collect_postgres("SELECT c.id FROM customers c", TEST_URL)


def test_catalog_schema_and_permission_boundaries():
    sql = "SELECT name FROM alternate.customers"
    report = analyze(sql)
    collect_postgres(sql, TEST_URL, report=report)
    assert report.metadata[0].schema == "alternate"
    assert report.metadata[0].name == "customers"
    assert (
        next(ref for ref in report.references if ref.kind == "COLUMN").basis
        == "DATABASE"
    )
    report = analyze("SELECT r.id FROM restricted_fixture r")
    with psycopg.connect(TEST_URL) as connection:
        enrich_postgres(report, connection)
    assert report.metadata == []
    assert any("Metadata unavailable" in warning for warning in report.warnings)
    assert all(ref.basis == "STATIC" for ref in report.references)
    report = analyze("SELECT id FROM unanalyzed_fixture")
    collect_postgres(report.sql, TEST_URL, report=report)
    assert report.metadata[0].columns[0].distinct_estimate is None
    assert any("may be stale" in warning for warning in report.warnings)


@pytest.mark.parametrize("filename", ["simple-select.sql", "join.sql", "aggregate.sql"])
def test_real_runtime_plan(filename):
    sql = (Path(__file__).parent.parent / "fixtures/sql" / filename).read_text(
        encoding="utf-8"
    )
    plan = collect_postgres(sql, TEST_URL, runtime=True)
    assert plan.mode == "RUNTIME"
    assert plan.root.actual_rows >= 0 and plan.root.actual_loops >= 1
    assert plan.root.actual_time_ms >= 0
    assert plan.execution_time_ms >= 0
    assert "Shared Hit Blocks" in plan.root.buffers


def test_runtime_timeout_and_data_preservation():
    with psycopg.connect(TEST_URL) as connection:
        before = connection.execute(
            "SELECT COUNT(*), SUM(amount) FROM orders"
        ).fetchone()
    query = "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i+1 FROM n WHERE i<1000000000) SELECT SUM(i) FROM n"
    with pytest.raises(DatabaseError, match="QueryCanceled"):
        collect_postgres(query, TEST_URL, runtime=True)
    with psycopg.connect(TEST_URL) as connection:
        assert (
            connection.execute("SELECT COUNT(*), SUM(amount) FROM orders").fetchone()
            == before
        )


def test_real_catalog_enrichment():
    sql = "SELECT name FROM customers c JOIN orders o ON c.id=o.customer_id"
    report = analyze(sql)
    report.plan = collect_postgres(sql, TEST_URL, report=report)
    target = next(
        ref for ref in report.references if ref.kind == "COLUMN" and ref.name == "name"
    )
    assert target.status == "RESOLVED" and target.basis == "DATABASE"
    assert {metadata.schema for metadata in report.metadata} == {"public"}
    assert any(
        "orders_customer_idx" in metadata.indexes for metadata in report.metadata
    )
    assert any(
        column.distinct_estimate is not None
        for metadata in report.metadata
        for column in metadata.columns
    )
