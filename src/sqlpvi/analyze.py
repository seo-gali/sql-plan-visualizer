"""Static scope analysis; SQL Flow describes syntax, never execution order."""

from sqlglot import exp
from sqlglot.errors import OptimizeError
from sqlglot.optimizer.scope import Scope, traverse_scope

from sqlpvi.models import Reference, Report, SqlFlow, SqlFlowNode
from sqlpvi.parser import AnalysisError, ast_model, parse_sql, source_range


def _visible_sources(scope: Scope) -> dict:
    # selected_sources excludes CTE definitions that this query does not read.
    return {name: source for name, (_, source) in scope.selected_sources.items()}


def _column_candidates(column: exp.Column, scope: Scope) -> tuple[str, list[str]]:
    sources = _visible_sources(scope)
    if column.table:
        current = scope
        while True:
            sources = _visible_sources(current)
            if column.table in sources:
                source = sources[column.table]
                if (column.db or column.catalog) and (
                    not isinstance(source, exp.Table)
                    or column.db != source.db
                    or column.catalog != source.catalog
                ):
                    return "UNRESOLVED", []
                if isinstance(source, Scope):
                    names = source.outer_columns or source.expression.named_selects
                    if names.count(column.name) > 1:
                        return "AMBIGUOUS", [column.table]
                    if column.name not in names or "*" in names:
                        return "UNRESOLVED", [column.table]
                return "RESOLVED", [column.table]
            if not current.can_be_correlated or current.parent is None:
                return "UNRESOLVED", []
            current = current.parent
    if len(sources) > 1:
        return "AMBIGUOUS", sorted(sources)
    # A base table's column existence requires catalog evidence.
    if len(sources) == 1:
        name, source = next(iter(sources.items()))
        if isinstance(source, Scope):
            names = source.outer_columns or source.expression.named_selects
            if names.count(column.name) == 1 and "*" not in names:
                return "RESOLVED", [name]
        return "UNRESOLVED", [name]
    return "UNRESOLVED", []


def analyze(sql: str, filename: str = "<sql>", dialect: str = "postgres") -> Report:
    ast = parse_sql(sql, dialect)
    try:
        scopes = list(traverse_scope(ast))
        sources = {id(scope): _visible_sources(scope) for scope in scopes}
    except (ValueError, KeyError, OptimizeError) as exc:
        raise AnalysisError(f"SQL_SCOPE_ERROR: {exc}") from exc
    if not scopes:
        raise AnalysisError("SQL_UNSUPPORTED: query has no supported SELECT scope")
    references = []
    flow = []
    roots = {}
    seen_columns = set()
    for number, scope in enumerate(scopes):
        scope_id = f"scope-{number}"
        inputs = []
        for alias, source in sources[id(scope)].items():
            if isinstance(source, exp.Table):
                table = source
                references.append(
                    Reference(
                        f"ref-{len(references)}",
                        "TABLE",
                        table.name,
                        table.db,
                        table.alias,
                        scope_id,
                        "RESOLVED",
                        source_range(table),
                        [table.sql(dialect=dialect)],
                        relation=".".join(
                            part.sql(dialect=dialect) for part in table.parts
                        ),
                    )
                )
                node = SqlFlowNode(
                    f"flow-{len(flow)}",
                    "Scan",
                    table.sql(dialect=dialect),
                    [],
                    source_range(table),
                )
            else:
                source_node = scope.selected_sources[alias][0]
                if isinstance(source_node, exp.Table):
                    references.append(
                        Reference(
                            f"ref-{len(references)}",
                            "TABLE",
                            source_node.name,
                            source_node.db,
                            source_node.alias,
                            scope_id,
                            "RESOLVED",
                            source_range(source_node),
                            [alias],
                        )
                    )
                node = SqlFlowNode(
                    f"flow-{len(flow)}",
                    "CTE" if source.is_cte else "Subquery",
                    alias,
                    [roots[id(source)]] if id(source) in roots else [],
                    source_range(source_node),
                )
            flow.append(node)
            inputs.append(node.id)
        for column in scope.columns:
            if id(column) in seen_columns:
                continue
            seen_columns.add(id(column))
            status, candidates = _column_candidates(column, scope)
            references.append(
                Reference(
                    f"ref-{len(references)}",
                    "COLUMN",
                    column.name,
                    column.table,
                    "",
                    scope_id,
                    status,
                    source_range(column),
                    candidates,
                )
            )
        query = scope.expression
        if isinstance(query, exp.SetOperation):
            inputs = [roots[id(child)] for child in scope.union_scopes]
            operations = [(type(query).__name__, query)]
        else:
            operations = []
            for position, join in enumerate(query.args.get("joins") or []):
                if position + 1 >= len(inputs):
                    raise AnalysisError("SQL_UNSUPPORTED: unsupported join source")
                left = flow[-1].id if position else inputs[0]
                node = SqlFlowNode(
                    f"flow-{len(flow)}",
                    "Join",
                    join.sql(dialect=dialect)[:240],
                    [left, inputs[position + 1]],
                    source_range(join),
                )
                flow.append(node)
            if query.args.get("joins"):
                inputs = [flow[-1].id]
            for child in scope.subquery_scopes:
                node = SqlFlowNode(
                    f"flow-{len(flow)}",
                    "Subquery",
                    child.expression.sql(dialect=dialect)[:240],
                    [roots[id(child)]],
                )
                flow.append(node)
                inputs.append(node.id)
            for key, operation in (
                ("where", "Filter"),
                ("group", "Aggregate"),
                ("having", "Filter"),
                ("distinct", "Distinct"),
                ("order", "Sort"),
                ("offset", "Offset"),
                ("limit", "Limit"),
            ):
                if query.args.get(key) is not None:
                    operations.append((operation, query.args[key]))
            if not query.args.get("group") and any(
                isinstance(node, exp.AggFunc)
                and node.find_ancestor(exp.Select) is query
                for node in query.walk()
            ):
                operations.insert(
                    1 if query.args.get("where") else 0, ("Aggregate", query)
                )
            operations.append(("Project", query))
        for operation, expression in operations:
            node = SqlFlowNode(
                f"flow-{len(flow)}",
                operation,
                expression.sql(dialect=dialect)[:240],
                inputs,
                source_range(expression),
            )
            flow.append(node)
            inputs = [node.id]
        roots[id(scope)] = inputs[-1]
    return Report(
        filename,
        sql,
        dialect,
        "PARSED",
        ast_model(ast, dialect),
        references,
        SqlFlow(flow, roots[id(scopes[-1])]),
        [
            "PARSED does not establish database executability or object existence.",
            "SQL Flow describes SQL structure, not the DBMS execution order.",
            "Source mapping covers parser-provided token ranges only.",
        ],
    )
