"""PostgreSQL vendor adapter, preserving its estimates and runtime fields."""

import os
from itertools import count

from sqlpvi.db.safety import DatabaseError, is_loopback_host, safe_query
from sqlpvi.metadata import enrich_postgres
from sqlpvi.models import ExecutionPlan, PlanNode, Report


def postgres_plan(raw: object, runtime: bool = False) -> ExecutionPlan:
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise DatabaseError("DATABASE_PLAN_ERROR: expected a PostgreSQL JSON plan")
    sequence = count()

    def convert(node):
        if not isinstance(node, dict) or not isinstance(node.get("Node Type"), str):
            raise DatabaseError("DATABASE_PLAN_ERROR: invalid PostgreSQL plan node")
        children = node.get("Plans", [])
        if not isinstance(children, list):
            raise DatabaseError("DATABASE_PLAN_ERROR: invalid PostgreSQL plan children")
        return PlanNode(
            f"plan-{next(sequence)}",
            node["Node Type"],
            node.get("Relation Name"),
            node["Node Type"] if "Scan" in node["Node Type"] else None,
            node.get("Plan Rows"),
            node.get("Total Cost"),
            [convert(child) for child in children],
            {key: value for key, value in node.items() if key != "Plans"},
            node.get("Actual Rows"),
            node.get("Actual Loops"),
            node.get("Actual Total Time"),
            {key: value for key, value in node.items() if key.endswith(" Blocks")},
        )

    plan = ExecutionPlan(
        "postgres", "RUNTIME" if runtime else "ESTIMATED", convert(raw[0].get("Plan"))
    )
    if runtime and plan.root.actual_rows is None:
        raise DatabaseError(
            "DATABASE_PLAN_ERROR: runtime plan has no actual measurements"
        )
    plan.planning_time_ms = raw[0].get("Planning Time")
    plan.execution_time_ms = raw[0].get("Execution Time")
    return plan


def collect_postgres(
    sql: str,
    dsn: str,
    dialect: str = "postgres",
    report: Report | None = None,
    runtime: bool = False,
) -> ExecutionPlan:
    if dialect not in ("postgres", "postgresql"):
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: PostgreSQL mode requires postgres dialect"
        )
    query = safe_query(sql, dialect)
    if not dsn:
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: set SQLPVI_POSTGRES_URL (legacy SQLPVI_DATABASE_URL also supported)"
        )
    try:
        import psycopg
    except ImportError:
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: install sql-plan-visualizer[postgres] for PostgreSQL"
        ) from None
    try:
        parameters = psycopg.conninfo.conninfo_to_dict(dsn)
        hosts = (parameters.get("host") or os.environ.get("PGHOST", "")).split(",")
        addresses = (
            parameters.get("hostaddr") or os.environ.get("PGHOSTADDR", "")
        ).split(",")
        local = (
            not (parameters.get("service") or os.environ.get("PGSERVICE"))
            and all(
                is_loopback_host(host) or host.startswith("/") for host in hosts if host
            )
            and all(is_loopback_host(address) for address in addresses if address)
        )
        tls = (
            {}
            if local
            else {
                "sslmode": "verify-full",
                "ssl_min_protocol_version": "TLSv1.2",
                "gssencmode": "disable",
            }
        )
        with psycopg.connect(
            dsn,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=1000",
            **tls,
        ) as connection:
            connection.read_only = True
            connection.execute("SET LOCAL search_path TO pg_catalog, public")
            roles = connection.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                "FROM pg_catalog.pg_roles WHERE rolname=current_user"
            ).fetchone()
            if roles is None or any(roles):
                raise DatabaseError(
                    "DATABASE_PERMISSION_ERROR: use a least-privilege reader account"
                )
            permissions = connection.execute("""
                SELECT
                    has_database_privilege(current_database(), 'CREATE')
                    OR EXISTS (
                        SELECT 1 FROM pg_catalog.pg_namespace AS n
                        WHERE n.nspname !~ '^pg_(toast_)?temp_'
                        AND has_schema_privilege(n.oid, 'CREATE')
                    )
                    OR EXISTS (
                        SELECT 1 FROM pg_catalog.pg_class AS c
                        JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace
                        WHERE n.nspname !~ '^pg_(toast_)?temp_'
                        AND CASE
                            WHEN c.relkind = 'S' THEN has_sequence_privilege(
                                c.oid, 'USAGE, UPDATE, SELECT WITH GRANT OPTION'
                            )
                            WHEN c.relkind IN ('r', 'p', 'v', 'm', 'f') THEN
                                has_table_privilege(c.oid,
                                    'INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER, MAINTAIN, SELECT WITH GRANT OPTION')
                                OR has_any_column_privilege(c.oid,
                                    'INSERT, UPDATE, REFERENCES, SELECT WITH GRANT OPTION')
                            ELSE false
                        END
                    )
                    OR EXISTS (
                        SELECT 1 FROM pg_catalog.pg_roles AS r
                        WHERE pg_has_role(r.oid, 'MEMBER')
                        AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                            OR r.rolreplication OR r.rolbypassrls
                            OR r.rolname IN ('pg_write_all_data', 'pg_read_server_files',
                                'pg_write_server_files', 'pg_execute_server_program',
                                'pg_signal_backend', 'pg_checkpoint', 'pg_maintain',
                                'pg_create_subscription'))
                    )
            """).fetchone()
            if permissions is None or permissions[0] is not False:
                raise DatabaseError(
                    "DATABASE_PERMISSION_ERROR: use a least-privilege reader account"
                )
            explain = (
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                if runtime
                else "EXPLAIN (FORMAT JSON) "
            )
            raw = connection.execute(explain + query, prepare=True).fetchone()[0]
            plan = postgres_plan(raw, runtime)
            if report is not None:
                enrich_postgres(report, connection)
            return plan
    except (psycopg.Error, OSError, TypeError, IndexError, KeyError) as exc:
        raise DatabaseError(
            f"DATABASE_ERROR: PostgreSQL plan unavailable ({type(exc).__name__})"
        ) from None
