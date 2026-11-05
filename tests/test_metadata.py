from sqlpvi.analyze import analyze
from sqlpvi.metadata import bind_catalog


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
