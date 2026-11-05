"""Render only the report contract; no SQLGlot or vendor plan objects."""

from importlib.resources import files

from jinja2 import Environment, PackageLoader, select_autoescape

from sqlpvi.models import AstNode, Report, SourceRange


def _ast_ranges(node: AstNode):
    if node.source:
        yield node.source
    for child in node.children:
        yield from _ast_ranges(child)


def range_key(source: SourceRange | None) -> str:
    return f"range-{source.start}-{source.end}" if source else ""


def render_html(report: Report) -> str:
    positions = {
        (source.start, source.end)
        for source in _ast_ranges(report.ast)
        if 0 <= source.start < source.end <= len(report.sql)
    }
    chunks = []
    cursor = 0
    for start, end in sorted(positions):
        if start < cursor:
            continue
        chunks.append((report.sql[cursor:start], ""))
        chunks.append((report.sql[start:end], f"range-{start}-{end}"))
        cursor = end
    chunks.append((report.sql[cursor:], ""))
    environment = Environment(
        loader=PackageLoader("sqlpvi", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return environment.get_template("report.html").render(
        report=report,
        chunks=chunks,
        key=range_key,
        css=files("sqlpvi").joinpath("assets/report.css").read_text(encoding="utf-8"),
        js=files("sqlpvi").joinpath("assets/report.js").read_text(encoding="utf-8"),
    )
