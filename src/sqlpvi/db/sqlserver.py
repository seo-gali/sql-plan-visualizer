"""SQL Server estimated SHOWPLAN, with no execution of the supplied query."""

import math
from itertools import count
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from sqlpvi.db.safety import DatabaseError, safe_query
from sqlpvi.models import ExecutionPlan, PlanNode

SHOWPLAN_NS = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}"


def sqlserver_plan(raw: str) -> ExecutionPlan:
    if (
        not isinstance(raw, str)
        or "<!DOCTYPE" in raw.upper()
        or "<!ENTITY" in raw.upper()
    ):
        raise DatabaseError("DATABASE_PLAN_ERROR: unsafe SQL Server XML")
    try:
        root = ET.fromstring(raw)
        statements = root.findall(f".//{SHOWPLAN_NS}StmtSimple")
        if (
            root.tag != SHOWPLAN_NS + "ShowPlanXML"
            or len(statements) != 1
            or statements[0].get("StatementType")
            not in ("SELECT", "SELECT WITHOUT QUERY")
        ):
            raise ValueError("expected one SELECT plan")
        if statements[0].get("StatementType") == "SELECT WITHOUT QUERY":
            return ExecutionPlan(
                "sqlserver",
                "ESTIMATED",
                PlanNode(
                    "plan-0",
                    "SELECT WITHOUT QUERY",
                    None,
                    None,
                    None,
                    None,
                    [],
                    dict(statements[0].attrib),
                ),
            )
        plans = statements[0].findall(f"{SHOWPLAN_NS}QueryPlan/{SHOWPLAN_NS}RelOp")
        if len(plans) != 1:
            raise ValueError("expected one plan root")
        sequence = count()

        def convert(node):
            identifier = f"plan-{next(sequence)}"
            children = []
            objects = []
            details = dict(node.attrib)

            def visit(element):
                for child in element:
                    if child.tag == SHOWPLAN_NS + "RelOp":
                        children.append(convert(child))
                    else:
                        if child.tag == SHOWPLAN_NS + "Object":
                            objects.append(dict(child.attrib))
                        visit(child)

            visit(node)
            rows = float(node.attrib["EstimateRows"])
            cost = float(node.attrib["EstimatedTotalSubtreeCost"])
            if not all(math.isfinite(value) and value >= 0 for value in (rows, cost)):
                raise ValueError("invalid estimates")
            operation = node.attrib["PhysicalOp"]
            if not operation:
                raise ValueError("missing operation")
            relation = None
            if objects:
                details["Objects"] = objects
                relation = (
                    ".".join(
                        objects[0][key]
                        for key in ("Schema", "Table")
                        if key in objects[0]
                    )
                    or None
                )
            return PlanNode(
                identifier,
                operation,
                relation,
                operation if objects else None,
                rows,
                cost,
                children,
                details,
            )

        return ExecutionPlan("sqlserver", "ESTIMATED", convert(plans[0]))
    except (ET.ParseError, ValueError, KeyError, OverflowError):
        raise DatabaseError(
            "DATABASE_PLAN_ERROR: invalid SQL Server SHOWPLAN XML"
        ) from None


def collect_sqlserver(
    sql: str, dsn: str, dialect: str = "tsql", runtime: bool = False
) -> ExecutionPlan:
    if runtime:
        raise DatabaseError("DATABASE_CONFIG_ERROR: SQL Server runtime is unsupported")
    if dialect != "tsql":
        raise DatabaseError("DATABASE_CONFIG_ERROR: SQL Server requires tsql dialect")
    query = safe_query(sql, dialect)
    try:
        import pymssql
    except ImportError:
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: install the locked pymssql dependency for SQL Server"
        ) from None
    try:
        url = urlsplit(dsn)
        if (
            url.scheme not in ("sqlserver", "mssql")
            or not url.hostname
            or not url.path.strip("/")
            or url.query
            or url.fragment
        ):
            raise DatabaseError(
                "DATABASE_CONFIG_ERROR: set a SQL Server connection URL"
            )
        with (
            pymssql.connect(
                server=url.hostname,
                port=str(url.port or 1433),
                user=unquote(url.username or ""),
                password=unquote(url.password or ""),
                database=unquote(url.path.lstrip("/")),
                login_timeout=5,
                timeout=5,
                charset="UTF-8",
                appname="SQLPVI",
                encryption="require",
                read_only=True,
                autocommit=False,
            ) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SET LOCK_TIMEOUT 1000")
            cursor.execute("""
                SELECT permission_name FROM sys.fn_my_permissions(NULL, 'SERVER')
                UNION ALL
                SELECT permission_name FROM sys.fn_my_permissions(NULL, 'DATABASE')
                UNION ALL
                SELECT p.permission_name FROM sys.objects AS o
                CROSS APPLY sys.fn_my_permissions(
                    QUOTENAME(SCHEMA_NAME(o.schema_id)) + '.' + QUOTENAME(o.name), 'OBJECT'
                ) AS p WHERE o.is_ms_shipped = 0 AND o.parent_object_id = 0
                UNION ALL
                SELECT 'GRANT OPTION' FROM sys.database_permissions
                WHERE state = 'W' AND grantee_principal_id IN (
                    SELECT principal_id FROM sys.user_token
                )
                UNION ALL
                SELECT 'GRANT OPTION' FROM sys.server_permissions
                WHERE state = 'W' AND grantee_principal_id IN (
                    SELECT principal_id FROM sys.login_token
                )
            """)
            allowed = {
                "CONNECT",
                "CONNECT SQL",
                "SELECT",
                "SHOWPLAN",
                "VIEW DEFINITION",
                "VIEW ANY DATABASE",
                "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
                "VIEW ANY COLUMN MASTER KEY DEFINITION",
            }
            if any(row[0] not in allowed for row in cursor.fetchall()):
                raise DatabaseError(
                    "DATABASE_PERMISSION_ERROR: use a least-privilege reader account"
                )
            try:
                cursor.execute("SET SHOWPLAN_XML ON")
                cursor.execute(query)
                row = cursor.fetchone()
                cursor.fetchall()
                return sqlserver_plan(row[0])
            finally:
                try:
                    cursor.execute("SET SHOWPLAN_XML OFF")
                finally:
                    connection.rollback()
    except DatabaseError:
        raise
    except (pymssql.Error, OSError, ValueError, TypeError, IndexError) as exc:
        raise DatabaseError(
            f"DATABASE_ERROR: SQL Server plan unavailable ({type(exc).__name__})"
        ) from None
