import pytest

from sqlpvi import database
from sqlpvi.analyze import analyze
from sqlpvi.database import DatabaseError


def test_postgres_url_precedence_and_legacy_compatibility(monkeypatch):
    monkeypatch.setenv("SQLPVI_DATABASE_URL", "legacy-fixture-url")
    monkeypatch.setenv("SQLPVI_POSTGRES_URL", "new-fixture-url")
    observed = []

    def collect(sql, dsn, dialect, report, runtime):
        observed.append((dsn, dialect, runtime))

    monkeypatch.setattr(database, "collect_postgres", collect)
    report = analyze("SELECT 1")
    database.collect_database(report, runtime=True)
    assert observed[-1] == ("new-fixture-url", "postgres", True)
    monkeypatch.delenv("SQLPVI_POSTGRES_URL")
    database.collect_database(report)
    assert observed[-1] == ("legacy-fixture-url", "postgres", False)


def test_unsupported_vendor_and_mismatched_dialect():
    with pytest.raises(DatabaseError, match="unsupported vendor"):
        database.collect_database(analyze("SELECT 1"), "unknown")
    with pytest.raises(DatabaseError, match="do not match"):
        database.collect_database(analyze("SELECT 1", dialect="mysql"))


def test_mariadb_url_routing_and_runtime_rejection(monkeypatch):
    observed = []
    monkeypatch.setenv("SQLPVI_MARIADB_URL", "mariadb-fixture-url")
    monkeypatch.setattr(
        database, "collect_mariadb", lambda *args: observed.append(args)
    )
    report = analyze("SELECT 1", dialect="mysql")
    database.collect_database(report, "mariadb")
    assert observed == [(report.sql, "mariadb-fixture-url", "mysql")]
    with pytest.raises(DatabaseError, match="runtime"):
        database.collect_database(report, "mariadb", runtime=True)
    monkeypatch.delenv("SQLPVI_MARIADB_URL")
    with pytest.raises(DatabaseError, match="set SQLPVI_MARIADB_URL"):
        database.collect_database(report, "mariadb")


def test_sqlserver_routing_and_runtime_rejection(monkeypatch):
    observed = []
    monkeypatch.setenv("SQLPVI_SQLSERVER_URL", "sqlserver-fixture-url")
    monkeypatch.setattr(
        database, "collect_sqlserver", lambda *args: observed.append(args)
    )
    report = analyze("SELECT 1", dialect="tsql")
    database.collect_database(report, "sqlserver")
    assert observed == [(report.sql, "sqlserver-fixture-url", "tsql")]
    with pytest.raises(DatabaseError, match="runtime"):
        database.collect_database(report, "sqlserver", runtime=True)
    monkeypatch.delenv("SQLPVI_SQLSERVER_URL")
    with pytest.raises(DatabaseError, match="set SQLPVI_SQLSERVER_URL"):
        database.collect_database(report, "sqlserver")
