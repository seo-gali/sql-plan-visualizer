"""Shared statement boundary; each vendor adds its transaction protections."""

from sqlglot import exp

from sqlpvi.parser import parse_sql


class DatabaseError(ValueError):
    """A safe user-facing database error, never a driver exception string."""


def safe_query(sql: str, dialect: str = "postgres") -> str:
    ast = parse_sql(sql, dialect)
    prohibited = (exp.DML, exp.DDL, exp.Command, exp.Into, exp.Lock)
    allowed_table_hints = {"NOLOCK", "READUNCOMMITTED", "FORCESEEK", "FORCESCAN"}
    allowed_functions = {
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COALESCE",
        "NULLIF",
        "LOWER",
        "UPPER",
        "ABS",
        "ROUND",
        "CAST",
        "TRY_CAST",
        "CASE",
        "IF",
        "EXISTS",
        "AND",
        "OR",
    }
    for node in ast.walk():
        if isinstance(node, prohibited):
            raise DatabaseError(
                "DATABASE_UNSAFE_SQL: writes and locking are prohibited"
            )
        if isinstance(node, exp.WithTableHint) and (
            dialect != "tsql"
            or not node.expressions
            or any(
                not isinstance(hint, exp.Var)
                or hint.name.upper() not in allowed_table_hints
                for hint in node.expressions
            )
        ):
            raise DatabaseError(
                "DATABASE_UNSAFE_SQL: table hint is outside the allowlist"
            )
        if isinstance(node, exp.Func):
            name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
            if name.upper() not in allowed_functions or isinstance(
                node.parent, exp.Dot
            ):
                raise DatabaseError(
                    "DATABASE_UNSAFE_SQL: function is outside the allowlist"
                )
        if (
            isinstance(node, exp.DataType)
            and node.this == exp.DataType.Type.USERDEFINED
        ):
            raise DatabaseError("DATABASE_UNSAFE_SQL: custom type casts are prohibited")
    return ast.sql(dialect=dialect, comments=False)
