"""Phase 0 Feasibility 검증. 각 테스트는 docs/instructions/phase0-feasibility.md
Gate 항목 하나에 대응한다. 실패하면 Gate 미통과로 취급한다."""

import html
import json
from pathlib import Path

import pytest
import sqlglot
from phase0_probe import render_probe
from sqlglot import exp

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sql"


def parse(name: str):
    sql = (FIXTURES / name).read_text(encoding="utf-8")
    return sqlglot.parse_one(sql, read="postgres")


def test_gate_parsing_simple_select():
    ast = parse("simple-select.sql")
    assert isinstance(ast, exp.Select)


def test_gate_parsing_join():
    ast = parse("join.sql")
    assert isinstance(ast, exp.Select)
    assert ast.find(exp.Join) is not None


def test_gate_parsing_aggregate():
    ast = parse("aggregate.sql")
    assert isinstance(ast, exp.Select)
    assert ast.find(exp.Sum) is not None
    assert ast.find(exp.Group) is not None
    assert ast.find(exp.Having) is not None


def test_gate_ast_traversal():
    ast = parse("join.sql")
    nodes = list(ast.walk())
    assert len(nodes) > 5


def test_gate_table_reference_extraction():
    ast = parse("join.sql")
    tables = [t.name for t in ast.find_all(exp.Table)]
    assert set(tables) == {"customers", "orders"}


def test_gate_column_reference_extraction():
    ast = parse("join.sql")
    columns = [c.name for c in ast.find_all(exp.Column)]
    assert "id" in columns
    assert "amount" in columns
    assert "customer_id" in columns


def test_gate_table_alias():
    ast = parse("join.sql")
    aliases = {t.alias: t.name for t in ast.find_all(exp.Table) if t.alias}
    assert aliases == {"c": "customers", "o": "orders"}


def test_gate_column_alias():
    ast = parse("simple-select.sql")
    select = ast.expressions
    aliased = [e for e in select if isinstance(e, exp.Alias)]
    assert any(a.alias == "customer_name" for a in aliased)


def test_gate_join_condition():
    ast = parse("join.sql")
    join = ast.find(exp.Join)
    assert join is not None
    assert join.args.get("on") is not None


def test_gate_aggregate_function():
    ast = parse("aggregate.sql")
    assert ast.find(exp.Sum) is not None
    assert ast.find(exp.Count) is not None


def test_gate_parser_error_detected():
    """실제 확인된 한계: 'SELEC * FORM x' 처럼 키워드가 오타인 SQL은
    SQLGlot이 예외를 던지지 않고 '컬럼 SELEC 곱하기 컬럼 FORM, 별칭 x'로
    조용히 재해석한다 (오탐 없음, 그러나 침묵 실패). 실제 ParseError를
    유발하려면 구조적으로 복구 불가능한 SQL이 필요하다."""
    with pytest.raises(sqlglot.errors.ParseError):
        sqlglot.parse_one("SELECT * FROM (((", read="postgres")


def test_gate_source_mapping_positions_exist():
    """실제 확인된 한계: Table 같은 상위 Expression 노드 자체의 .meta는 비어
    있다. 위치 정보(line/col/start/end)는 그 안의 Identifier 리프 노드에만
    붙는다. 따라서 Expression 단위 Source Mapping은 불완전하고,
    Identifier 단위로 범위를 좁혀야 한다."""
    ast = parse("join.sql")
    table = ast.find(exp.Table)
    assert table.meta == {}, "Table 노드 자체에는 위치 정보가 없음 (실제 확인됨)"

    identifier = table.find(exp.Identifier)
    assert identifier is not None
    assert "line" in identifier.meta and "start" in identifier.meta, (
        "Identifier 리프 노드에는 위치 정보가 있어야 함"
    )


def test_gate_html_escape_safety():
    malicious_sql = "SELECT 1 -- <script>alert(1)</script>"
    escaped = html.escape(malicious_sql)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_gate_json_serialization_safety():
    """분석 결과를 JS로 넘길 때 </script> 탈출이 안 되는지 확인."""
    payload = {"sql": "SELECT 1 -- </script><script>alert(1)</script>"}
    serialized = json.dumps(payload).replace("</", "<\\/")
    assert "</script>" not in serialized


def test_gate_minimal_standalone_html_generation(tmp_path):
    sql = (FIXTURES / "simple-select.sql").read_text(encoding="utf-8")
    out = tmp_path / "report.html"
    out.write_text(render_probe(sql), encoding="utf-8")
    content = out.read_text(encoding="utf-8")
    assert "customers" in content
    assert '<svg aria-hidden="true">' in content
    assert 'id="source-0"' in content
    assert 'href="#source-0"' in content
    assert "createElementNS" in content


def test_gate_source_mapping_preserves_original_sql():
    from html.parser import HTMLParser

    class SourceReader(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_source = False
            self.text = ""

        def handle_starttag(self, tag, attrs):
            if tag == "pre":
                self.in_source = True

        def handle_endtag(self, tag):
            if tag == "pre":
                self.in_source = False

        def handle_data(self, data):
            if self.in_source:
                self.text += data

    sql = 'SELECT "한글", c.id FROM customers c; -- <script>alert(1)</script> <>&"\''
    content = render_probe(sql)
    reader = SourceReader()
    reader.feed(content)
    assert reader.text == sql
    assert "<script>alert(1)</script>" not in content
