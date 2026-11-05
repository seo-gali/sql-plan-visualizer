"""PostgreSQL vendor adapter, preserving its estimates and runtime fields."""

from itertools import count

import psycopg

from sqlpvi.db.safety import DatabaseError, safe_query
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
        raise DatabaseError("DATABASE_CONFIG_ERROR: set SQLPVI_DATABASE_URL")
    try:
        with psycopg.connect(
            dsn,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=1000",
        ) as connection:
            connection.read_only = True
            roles = connection.execute(
                "SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
            if roles is None or any(roles):
                raise DatabaseError(
                    "DATABASE_PERMISSION_ERROR: use a least-privilege reader account"
                )
            connection.execute("SET LOCAL search_path TO pg_catalog, public")
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
