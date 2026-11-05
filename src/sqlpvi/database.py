"""Vendor routing and URL migration; renderer and core consume only models."""

import os

from sqlpvi.db.mariadb import collect_mariadb
from sqlpvi.db.postgres import collect_postgres, postgres_plan
from sqlpvi.db.safety import DatabaseError, safe_query
from sqlpvi.db.sqlserver import collect_sqlserver
from sqlpvi.models import ExecutionPlan, Report

VENDOR_DIALECTS = {"postgres": "postgres", "mariadb": "mysql", "sqlserver": "tsql"}

__all__ = [
    "VENDOR_DIALECTS",
    "DatabaseError",
    "collect_database",
    "collect_postgres",
    "postgres_plan",
    "safe_query",
]


def collect_database(
    report: Report, vendor: str = "postgres", runtime: bool = False
) -> ExecutionPlan:
    if vendor not in VENDOR_DIALECTS:
        raise DatabaseError("DATABASE_CONFIG_ERROR: unsupported vendor")
    if report.dialect != VENDOR_DIALECTS[vendor] and not (
        vendor == "postgres" and report.dialect == "postgresql"
    ):
        raise DatabaseError("DATABASE_CONFIG_ERROR: vendor and dialect do not match")
    if vendor == "sqlserver":
        if runtime:
            raise DatabaseError(
                "DATABASE_CONFIG_ERROR: SQL Server runtime is unsupported"
            )
        dsn = os.environ.get("SQLPVI_SQLSERVER_URL", "")
        if not dsn:
            raise DatabaseError("DATABASE_CONFIG_ERROR: set SQLPVI_SQLSERVER_URL")
        return collect_sqlserver(report.sql, dsn, report.dialect)
    if vendor == "mariadb":
        if runtime:
            raise DatabaseError("DATABASE_CONFIG_ERROR: MariaDB runtime is unsupported")
        dsn = os.environ.get("SQLPVI_MARIADB_URL", "")
        if not dsn:
            raise DatabaseError("DATABASE_CONFIG_ERROR: set SQLPVI_MARIADB_URL")
        return collect_mariadb(report.sql, dsn, report.dialect)
    dsn = os.environ.get("SQLPVI_POSTGRES_URL") or os.environ.get(
        "SQLPVI_DATABASE_URL", ""
    )
    if not dsn:
        raise DatabaseError(
            "DATABASE_CONFIG_ERROR: set SQLPVI_POSTGRES_URL (legacy SQLPVI_DATABASE_URL also supported)"
        )
    return collect_postgres(report.sql, dsn, report.dialect, report, runtime)
