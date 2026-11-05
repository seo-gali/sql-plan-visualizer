"""Catalog evidence can strengthen bindings; incomplete evidence cannot."""

import psycopg

from sqlpvi.models import ColumnMetadata, RelationMetadata, Report


def enrich_postgres(report: Report, connection) -> None:
    relations = {ref.relation for ref in report.references if ref.relation}
    known = {}
    for relation in sorted(relations):
        try:
            with connection.transaction():
                table = connection.execute(
                    "SELECT c.oid, n.nspname, c.relname, c.reltuples "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE c.oid=to_regclass(%s) AND has_table_privilege(c.oid, 'SELECT')",
                    (relation,),
                ).fetchone()
                if table is None:
                    report.warnings.append(f"Metadata unavailable for {relation}.")
                    continue
                oid, schema, name, rows = table
                columns = connection.execute(
                    "SELECT a.attname, format_type(a.atttypid,a.atttypmod), "
                    "NOT a.attnotnull, s.null_frac, s.n_distinct "
                    "FROM pg_attribute a LEFT JOIN pg_stats s ON "
                    "s.schemaname=%s AND s.tablename=%s AND s.attname=a.attname "
                    "WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped "
                    "ORDER BY a.attnum",
                    (schema, name, oid),
                ).fetchall()
                indexes = connection.execute(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=%s AND tablename=%s",
                    (schema, name),
                ).fetchall()
                evidence = RelationMetadata(
                    relation,
                    schema,
                    name,
                    rows,
                    [ColumnMetadata(*column) for column in columns],
                    dict(indexes),
                )
                report.metadata.append(evidence)
                known[relation] = {column.name for column in evidence.columns}
        except psycopg.Error:
            report.warnings.append(f"Metadata unavailable for {relation}.")
    bind_catalog(report, known)
    report.warnings.append("Catalog statistics are estimates and may be stale.")


def bind_catalog(report: Report, known: dict[str, set[str]]) -> None:
    sources = {}
    for reference in report.references:
        if reference.kind == "TABLE" and reference.relation:
            sources[(reference.scope, reference.alias or reference.name)] = (
                reference.relation
            )
            if reference.relation in known:
                reference.basis = "DATABASE"
    for reference in report.references:
        if reference.kind != "COLUMN" or not reference.candidates:
            continue
        candidates = {
            alias: sources.get((reference.scope, alias))
            for alias in reference.candidates
        }
        if any(relation not in known for relation in candidates.values()):
            continue
        matches = sorted(
            alias
            for alias, relation in candidates.items()
            if reference.name in known[relation]
        )
        reference.candidates = matches
        reference.status = (
            "RESOLVED"
            if len(matches) == 1
            else "AMBIGUOUS"
            if matches
            else "UNRESOLVED"
        )
        reference.basis = "DATABASE"
