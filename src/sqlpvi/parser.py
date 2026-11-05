"""Keep SQLGlot details on the analysis side of the report boundary."""

from itertools import count

import sqlglot
from sqlglot import exp
from sqlglot.errors import ErrorLevel, ParseError, TokenError
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers

from sqlpvi.models import AstNode, SourceRange


class AnalysisError(ValueError):
    """An input cannot be represented by the supported analysis contract."""


def parse_sql(sql: str, dialect: str) -> exp.Query:
    try:
        statements = [
            node
            for node in sqlglot.parse(sql, read=dialect, error_level=ErrorLevel.RAISE)
            if node is not None
        ]
    except (ParseError, TokenError, ValueError) as exc:
        raise AnalysisError(f"SQL_PARSE_ERROR: {exc}") from exc
    if len(statements) != 1:
        raise AnalysisError("SQL_INPUT_ERROR: provide exactly one SQL statement")
    if not isinstance(statements[0], exp.Query):
        raise AnalysisError("SQL_UNSUPPORTED: only query statements are supported")
    return normalize_identifiers(statements[0], dialect=dialect)


def source_range(node: exp.Expression) -> SourceRange | None:
    leaf = node if node.meta else node.this
    if not isinstance(leaf, exp.Expression):
        return None
    meta = leaf.meta
    if not all(key in meta for key in ("start", "end", "line", "col")):
        return None
    return SourceRange(meta["start"], meta["end"] + 1, meta["line"], meta["col"])


def ast_model(node: exp.Expression, dialect: str, counter=None) -> AstNode:
    if counter is None:
        counter = count()
    return AstNode(
        id=f"ast-{next(counter)}",
        kind=type(node).__name__,
        label=node.sql(dialect=dialect)[:160],
        source=source_range(node),
        children=[
            ast_model(child, dialect, counter) for child in node.iter_expressions()
        ],
    )
