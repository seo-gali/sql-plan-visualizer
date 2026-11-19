import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from sqlglot import exp

from sqlpvi.analyze import analyze
from sqlpvi.parser import AnalysisError, parse_sql, source_range

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sql"


@pytest.mark.parametrize(
    "filename",
    [
        "simple-select.sql",
        "join.sql",
        "aggregate.sql",
        "cte.sql",
        "subquery.sql",
        "clauses.sql",
    ],
)
def test_fixture_analysis(filename):
    sql = (FIXTURES / filename).read_text(encoding="utf-8")
    report = analyze(sql)
    assert report.status == "PARSED"
    assert report.sql == sql
    assert report.ast.kind == "Select"
    assert report.flow.root in {node.id for node in report.flow.nodes}
    assert all(reference.basis == "STATIC" for reference in report.references)
    json.dumps(asdict(report))
    for reference in report.references:
        if reference.source:
            fragment = sql[reference.source.start : reference.source.end]
            assert fragment.strip('"') == reference.name


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT c.id FROM customers c", "RESOLVED"),
        ("SELECT id FROM customers c", "UNRESOLVED"),
        ("SELECT id FROM customers c JOIN orders o ON c.id=o.customer_id", "AMBIGUOUS"),
        ("SELECT missing.id FROM customers c", "UNRESOLVED"),
        ("SELECT s.id FROM (SELECT c.id FROM customers c) s", "RESOLVED"),
        ("SELECT s.nope FROM (SELECT c.id FROM customers c) s", "UNRESOLVED"),
        ("SELECT s.id FROM (SELECT c.id, c.id FROM customers c) s", "AMBIGUOUS"),
    ],
)
def test_reference_status(sql, expected):
    columns = [
        reference for reference in analyze(sql).references if reference.kind == "COLUMN"
    ]
    target = min(columns, key=lambda reference: reference.source.start)
    assert target.status == expected


def test_scope_and_flow():
    report = analyze((FIXTURES / "subquery.sql").read_text(encoding="utf-8"))
    assert {node.operation for node in report.flow.nodes} >= {
        "Scan",
        "Project",
        "Filter",
        "Subquery",
    }
    correlated = [ref for ref in report.references if ref.qualifier == "s"]
    assert all(ref.status == "RESOLVED" for ref in correlated)
    report = analyze((FIXTURES / "cte.sql").read_text(encoding="utf-8"))
    assert {node.operation for node in report.flow.nodes} >= {
        "CTE",
        "Aggregate",
        "Filter",
    }
    assert not any(
        node.operation == "Scan" and node.detail == "totals AS t"
        for node in report.flow.nodes
    )


def test_identifier_normalization_and_cte_column_names():
    report = analyze("WITH X(Y) AS (SELECT c.id FROM customers C) SELECT x.y FROM X")
    assert all(ref.status == "RESOLVED" for ref in report.references)
    assert any(ref.name == "x" and ref.kind == "TABLE" for ref in report.references)
    report = analyze('SELECT "C".id FROM customers "C"')
    assert all(ref.status == "RESOLVED" for ref in report.references)
    report = analyze('SELECT c.id FROM customers "C"')
    assert (
        next(ref for ref in report.references if ref.kind == "COLUMN").status
        == "UNRESOLVED"
    )


def test_multiple_joins_have_binary_inputs():
    report = analyze("SELECT a.id FROM a JOIN b ON a.id=b.id JOIN c ON a.id=c.id")
    joins = [node for node in report.flow.nodes if node.operation == "Join"]
    assert len(joins) == 2
    assert all(len(node.inputs) == 2 for node in joins)
    assert joins[1].inputs[0] == joins[0].id


def test_duplicate_alias_is_a_controlled_error():
    with pytest.raises(AnalysisError, match="SQL_SCOPE_ERROR"):
        analyze("SELECT x.id FROM customers x JOIN orders x ON true")


def test_schema_qualifier_does_not_bind_a_different_schema():
    report = analyze("SELECT private.customers.id FROM public.customers")
    assert (
        next(ref for ref in report.references if ref.kind == "COLUMN").status
        == "UNRESOLVED"
    )


def test_all_clauses_and_join():
    report = analyze((FIXTURES / "clauses.sql").read_text(encoding="utf-8"))
    assert {node.operation for node in report.flow.nodes} >= {
        "Distinct",
        "Sort",
        "Limit",
        "Offset",
        "Project",
        "Filter",
        "Scan",
    }
    report = analyze((FIXTURES / "join.sql").read_text(encoding="utf-8"))
    assert "Join" in {node.operation for node in report.flow.nodes}


@pytest.mark.parametrize(
    ("expression", "aggregate_count"),
    [
        ("SUM(amount) OVER ()", 0),
        ("SUM(amount) FILTER (WHERE amount > 0) OVER ()", 0),
        ("SUM(SUM(amount)) OVER ()", 1),
        ("SUM(amount) OVER (ORDER BY SUM(amount))", 1),
    ],
)
def test_window_and_group_aggregates_have_distinct_flow(expression, aggregate_count):
    report = analyze(f"SELECT {expression} FROM orders")
    operations = [node.operation for node in report.flow.nodes]
    assert operations.count("Window") == 1
    assert operations.count("Aggregate") == aggregate_count
    if aggregate_count:
        assert operations.index("Aggregate") < operations.index("Window")
    assert operations.index("Window") < operations.index("Project")


def test_named_window_definition_is_not_a_second_computation():
    report = analyze("SELECT ROW_NUMBER() OVER w FROM orders WINDOW w AS (ORDER BY id)")
    assert sum(node.operation == "Window" for node in report.flow.nodes) == 1
    assert not any(node.operation == "Aggregate" for node in report.flow.nodes)


def test_window_in_a_subquery_is_not_counted_again_in_the_outer_scope():
    report = analyze(
        "SELECT s.total FROM (SELECT SUM(amount) OVER () AS total FROM orders) s"
    )
    assert sum(node.operation == "Window" for node in report.flow.nodes) == 1
    assert not any(node.operation == "Aggregate" for node in report.flow.nodes)


@pytest.mark.parametrize("operator", ["UNION ALL", "INTERSECT", "EXCEPT"])
def test_set_operation_preserves_its_sort_offset_and_limit(operator):
    report = analyze(
        f"SELECT 2 AS x {operator} SELECT 1 AS x ORDER BY x LIMIT 1 OFFSET 2"
    )
    nodes = {node.id: node for node in report.flow.nodes}
    limit = nodes[report.flow.root]
    assert limit.operation == "Limit"
    offset = nodes[limit.inputs[0]]
    assert offset.operation == "Offset"
    sort = nodes[offset.inputs[0]]
    assert sort.operation == "Sort"
    combined = nodes[sort.inputs[0]]
    assert combined.operation.upper() == operator.split()[0]
    assert len(combined.inputs) == 2
    assert all(nodes[input].operation == "Project" for input in combined.inputs)


def test_source_mapping_accepts_parent_or_identifier_metadata():
    sql = "SELECT o.id FROM orders AS o"
    table = parse_sql(sql, "postgres").find(exp.Table)
    source = source_range(table)
    assert source is not None
    assert "orders" in sql[source.start : source.end]
    start = sql.index("orders")
    table.meta.update(start=start, end=len(sql) - 1, line=1, col=len(sql))
    source = source_range(table)
    assert source is not None and sql[source.start : source.end] == "orders AS o"


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "-- comment",
        "SELECT 1; SELECT 2",
        "SELECT * FROM (((",
        "DELETE FROM customers",
        "SELEC * FORM x",
    ],
)
def test_bad_input(sql):
    with pytest.raises(AnalysisError):
        analyze(sql)


def test_cli_and_input_preservation(tmp_path):
    path = tmp_path / "query.sql"
    path.write_text("SELECT c.id FROM customers c", encoding="utf-8")
    command = [sys.executable, "-m", "sqlpvi", "analyze", str(path), "--format", "json"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "PARSED"
    output = tmp_path / "result.json"
    result = subprocess.run(
        command + ["--output", str(output)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "PARSED"
    result = subprocess.run(
        command + ["--output", str(path)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert path.read_text(encoding="utf-8") == "SELECT c.id FROM customers c"
    path.write_text("SELECT * FROM (((", encoding="utf-8")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "SQL_PARSE_ERROR" in result.stderr
