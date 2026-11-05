"""MariaDB EXPLAIN JSON is preserved as MariaDB operations and fields."""

import json
from itertools import count
from urllib.parse import unquote, urlsplit

from sqlpvi.db.safety import DatabaseError, safe_query
from sqlpvi.models import ExecutionPlan, PlanNode


def mariadb_plan(raw: object) -> ExecutionPlan:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("query_block"), dict)
        or not raw["query_block"]
    ):
        raise DatabaseError("DATABASE_PLAN_ERROR: expected MariaDB query_block")
    sequence = count()

    def convert(node, operation):
        identifier = f"plan-{next(sequence)}"
        children = []
        details = {}
        for key, value in node.items():
            if isinstance(value, dict):
                children.append(convert(value, key))
            elif isinstance(value, list) and any(
                isinstance(item, dict) for item in value
            ):
                children.extend(
                    convert(item, key) for item in value if isinstance(item, dict)
                )
            else:
                details[key] = value
        return PlanNode(
            identifier,
            operation,
            node.get("table_name"),
            node.get("access_type"),
            node.get("rows"),
            node.get("cost"),
            children,
            details,
        )

    return ExecutionPlan(
        "mariadb", "ESTIMATED", convert(raw["query_block"], "query_block")
    )


def collect_mariadb(
    sql: str, dsn: str, dialect: str = "mysql", runtime: bool = False
) -> ExecutionPlan:
    if runtime:
        raise DatabaseError("DATABASE_CONFIG_ERROR: MariaDB runtime is unsupported")
    if dialect != "mysql":
        raise DatabaseError("DATABASE_CONFIG_ERROR: MariaDB requires mysql dialect")
    query = safe_query(sql, dialect)
    try:
        import pymysql
    except ImportError:
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: install the locked PyMySQL dependency for MariaDB"
        ) from None
    try:
        url = urlsplit(dsn)
        if (
            url.scheme not in ("mysql", "mariadb")
            or not url.hostname
            or not url.path.strip("/")
            or url.query
            or url.fragment
        ):
            raise DatabaseError("DATABASE_CONFIG_ERROR: set a MariaDB connection URL")
        with (
            pymysql.connect(
                host=url.hostname,
                port=url.port or 3306,
                user=unquote(url.username or ""),
                password=unquote(url.password or ""),
                database=unquote(url.path.lstrip("/")),
                charset="utf8mb4",
                connect_timeout=5,
                read_timeout=6,
                write_timeout=5,
                autocommit=False,
                local_infile=False,
            ) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SET SESSION max_statement_time = 5")
            cursor.execute("SET SESSION lock_wait_timeout = 1")
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 1")
            cursor.execute("SET ROLE NONE")
            cursor.execute("START TRANSACTION READ ONLY")
            cursor.execute(
                " UNION ALL ".join(
                    f"SELECT PRIVILEGE_TYPE, IS_GRANTABLE FROM information_schema.{table}"
                    for table in (
                        "USER_PRIVILEGES",
                        "SCHEMA_PRIVILEGES",
                        "TABLE_PRIVILEGES",
                        "COLUMN_PRIVILEGES",
                    )
                )
            )
            if any(
                privilege not in ("USAGE", "SELECT", "SHOW VIEW") or grantable != "NO"
                for privilege, grantable in cursor.fetchall()
            ):
                raise DatabaseError(
                    "DATABASE_PERMISSION_ERROR: use a least-privilege reader account"
                )
            cursor.execute("EXPLAIN FORMAT=JSON " + query)
            return mariadb_plan(json.loads(cursor.fetchone()[0]))
    except DatabaseError:
        raise
    except (pymysql.MySQLError, OSError, ValueError, TypeError, IndexError) as exc:
        raise DatabaseError(
            f"DATABASE_ERROR: MariaDB plan unavailable ({type(exc).__name__})"
        ) from None
