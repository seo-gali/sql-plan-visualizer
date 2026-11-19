import sys
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

from sqlpvi.analyze import analyze
from sqlpvi.metadata import bind_catalog, enrich_postgres


def test_catalog_resolves_only_complete_evidence():
    sql = "SELECT name FROM customers c JOIN orders o ON c.id=o.customer_id"
    report = analyze(sql)
    target = next(
        ref for ref in report.references if ref.kind == "COLUMN" and ref.name == "name"
    )
    assert target.status == "AMBIGUOUS"
    bind_catalog(report, {"customers": {"id", "name"}})
    assert target.status == "AMBIGUOUS" and target.basis == "STATIC"
    bind_catalog(report, {"customers": {"id", "name"}, "orders": {"id", "customer_id"}})
    assert target.status == "RESOLVED" and target.basis == "DATABASE"
    assert target.candidates == ["c"]


def test_virtual_relation_does_not_bind_to_same_named_database_table():
    report = analyze(
        "WITH customers AS (SELECT o.id FROM orders o) SELECT id FROM customers"
    )
    bind_catalog(report, {"customers": {"id"}, "orders": {"id"}})
    outer = next(
        ref
        for ref in report.references
        if ref.kind == "COLUMN" and ref.scope == "scope-1"
    )
    assert outer.basis == "STATIC"


def test_rebinding_a_report_uses_original_static_candidates():
    report = analyze("SELECT name FROM customers c JOIN orders o ON c.id=o.customer_id")
    original = deepcopy(report.references)
    bind_catalog(report, {"customers": {"id", "name"}, "orders": {"id", "customer_id"}})
    bind_catalog(report, {"customers": {"id"}, "orders": {"id", "customer_id", "name"}})
    target = next(
        ref for ref in report.references if ref.kind == "COLUMN" and ref.name == "name"
    )
    assert target.status == "RESOLVED" and target.candidates == ["o"]
    assert report.static_references == original
    assert all(ref.basis == "STATIC" for ref in report.static_references)
    bind_catalog(report, {"customers": {"id"}})
    assert target.status == "AMBIGUOUS" and target.candidates == ["c", "o"]
    assert target.basis == "STATIC"
    tables = {ref.name: ref.basis for ref in report.references if ref.kind == "TABLE"}
    assert tables == {"customers": "DATABASE", "orders": "STATIC"}


def test_missing_column_can_be_resolved_by_a_later_catalog():
    report = analyze("SELECT c.name FROM customers c")
    bind_catalog(report, {"customers": {"id"}})
    target = next(ref for ref in report.references if ref.kind == "COLUMN")
    assert target.status == "UNRESOLVED" and not target.candidates
    bind_catalog(report, {"customers": {"id", "name"}})
    assert target.status == "RESOLVED" and target.candidates == ["c"]


def test_catalog_refresh_replaces_old_metadata_and_warnings(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(Error=RuntimeError))
    columns = {"name"}
    visible = True

    def execute(sql, parameters):
        if "FROM pg_class" in sql:
            return SimpleNamespace(
                fetchone=lambda: (1, "public", "customers", 10) if visible else None
            )
        if "FROM pg_attribute" in sql:
            return SimpleNamespace(
                fetchall=lambda: [
                    (name, "text", True, None, None) for name in sorted(columns)
                ]
            )
        assert "FROM pg_indexes" in sql
        return SimpleNamespace(fetchall=list)

    connection = SimpleNamespace(transaction=nullcontext, execute=execute)
    report = analyze("SELECT c.name FROM customers c")
    original = deepcopy(report.static_references)
    enrich_postgres(report, connection)
    columns = {"id"}
    enrich_postgres(report, connection)
    assert len(report.metadata) == 1
    assert [column.name for column in report.metadata[0].columns] == ["id"]
    assert (
        next(ref for ref in report.references if ref.kind == "COLUMN").status
        == "UNRESOLVED"
    )
    visible = False
    enrich_postgres(report, connection)
    assert not report.metadata
    assert any(
        warning.startswith("Metadata unavailable") for warning in report.warnings
    )
    visible, columns = True, {"name"}
    enrich_postgres(report, connection)
    assert not any(
        warning.startswith("Metadata unavailable") for warning in report.warnings
    )
    assert (
        report.warnings.count("Catalog statistics are estimates and may be stale.") == 1
    )
    assert (
        next(ref for ref in report.references if ref.kind == "COLUMN").status
        == "RESOLVED"
    )
    assert report.static_references == original
