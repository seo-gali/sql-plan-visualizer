import ssl
import sys
from base64 import b64encode
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from html_document import Document

from sqlpvi import cli
from sqlpvi.analyze import analyze
from sqlpvi.db.mariadb import collect_mariadb
from sqlpvi.db.postgres import collect_postgres
from sqlpvi.db.safety import DatabaseError
from sqlpvi.db.sqlserver import collect_sqlserver
from sqlpvi.render import render_html
from tools.update_html_csp import update


def test_report_allows_only_its_trusted_script_and_style_hashes():
    document = Document(render_html(analyze("SELECT '<script>untrusted()</script>'")))
    policy = document.meta["content-security-policy"]
    assert "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy
    directives = {
        entry.split()[0]: entry.split()[1:]
        for entry in policy.split(";")
        if entry.strip()
    }
    assert directives["default-src"] == ["'none'"]
    assert directives["base-uri"] == directives["form-action"] == ["'none'"]
    for kind, blocks in [
        ("script-src", document.scripts),
        ("style-src", document.styles),
    ]:
        assert blocks
        hashes = {
            "'sha256-" + b64encode(sha256(block.encode()).digest()).decode() + "'"
            for block in blocks
        }
        assert hashes == set(directives[kind])
    assert document.meta["referrer"] == "no-referrer"


@pytest.mark.parametrize(
    "path", sorted((Path(__file__).parent.parent / "docs").rglob("*.html"))
)
def test_public_html_pages_have_matching_hash_policies(path):
    document = Document(path.read_text(encoding="utf-8"))
    policy = document.meta["content-security-policy"]
    assert "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy
    for block in document.scripts + document.styles:
        token = "'sha256-" + b64encode(sha256(block.encode()).digest()).decode() + "'"
        assert token in policy
    assert document.meta["referrer"] == "no-referrer"


def test_static_policy_update_preserves_content_and_rejects_inline_handlers(tmp_path):
    path = tmp_path / "page.html"
    body = "<body><p>Original text</p><script>window.trusted = true;</script></body>"
    path.write_text(
        "<html><head><style>p{color:navy}</style></head>" + body + "</html>",
        encoding="utf-8",
    )
    update(path)
    result = path.read_text(encoding="utf-8")
    assert body in result and "content-security-policy" in Document(result).meta
    update(path)
    assert path.read_text(encoding="utf-8") == result
    unsafe = '<html><head></head><body onload="untrusted()"></body></html>'
    path.write_text(unsafe, encoding="utf-8")
    with pytest.raises(ValueError, match="addEventListener"):
        update(path)
    assert path.read_text(encoding="utf-8") == unsafe


def test_large_sql_is_rejected_without_replacing_the_report(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "large.sql"
    output = tmp_path / "report.html"
    sql = "SELECT '" + "x" * 64 + "'"
    source.write_text(sql, encoding="utf-8")
    output.write_text("previous report", encoding="utf-8")
    monkeypatch.setattr(cli, "MAX_SQL_BYTES", 32)
    monkeypatch.setattr(
        sys, "argv", ["sqlpvi", "analyze", str(source), "--output", str(output)]
    )
    assert cli.main() == 1
    assert "1 MiB limit" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "previous report"
    assert source.read_text(encoding="utf-8") == sql


def test_watch_recovers_after_an_oversized_file_is_replaced(tmp_path, monkeypatch):
    source = tmp_path / "large.sql"
    source.write_text("x" * 64, encoding="utf-8")
    output = source.with_suffix(".sqlpvi.html")
    monkeypatch.setattr(cli, "MAX_SQL_BYTES", 32)
    monkeypatch.setattr(sys, "argv", ["sqlpvi", "analyze", str(source), "--watch"])
    changed = False

    def tick(seconds):
        nonlocal changed
        if changed:
            raise KeyboardInterrupt
        assert not output.exists()
        changed = True
        source.write_text("SELECT 1", encoding="utf-8")

    monkeypatch.setattr(cli, "sleep", tick)
    assert cli.main() == 0
    assert Document(output.read_text(encoding="utf-8")).source == "SELECT 1"


def test_bounded_read_keeps_bom_and_universal_newline_handling(tmp_path, monkeypatch):
    source = tmp_path / "query.sql"
    source.write_bytes(b"\xef\xbb\xbfSELECT 1\r\nWHERE 1=1;\r\n")
    monkeypatch.setattr(sys, "argv", ["sqlpvi", "analyze", str(source)])
    assert cli.main() == 0
    assert (
        Document(source.with_suffix(".sqlpvi.html").read_text(encoding="utf-8")).source
        == "SELECT 1\nWHERE 1=1;\n"
    )


@pytest.mark.parametrize(
    ("parameters", "environment", "remote"),
    [
        ({"host": "db.example.test", "sslmode": "disable"}, {}, True),
        ({"host": "localhost", "hostaddr": "192.0.2.10"}, {}, True),
        ({"host": "127.0.0.1,db.example.test"}, {}, True),
        ({}, {"PGHOST": "db.example.test"}, True),
        ({}, {"PGSERVICE": "configured-service"}, True),
        ({"host": "localhost"}, {"PGHOSTADDR": "192.0.2.10"}, True),
        ({"host": "127.0.0.1"}, {}, False),
        ({"host": "::1"}, {}, False),
        ({"host": "/var/run/postgresql"}, {}, False),
    ],
)
def test_postgres_requires_verified_tls_for_remote_or_indirect_targets(
    monkeypatch, parameters, environment, remote
):
    for key in ("PGHOST", "PGHOSTADDR", "PGSERVICE"):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)

    class ConnectionFailure(Exception):
        pass

    connect = MagicMock(side_effect=ConnectionFailure)
    driver = SimpleNamespace(
        connect=connect,
        Error=ConnectionFailure,
        conninfo=SimpleNamespace(conninfo_to_dict=lambda dsn: parameters),
    )
    monkeypatch.setitem(sys.modules, "psycopg", driver)
    with pytest.raises(DatabaseError):
        collect_postgres("SELECT 1", "postgresql://reader@db.example.test/db")
    kwargs = connect.call_args.kwargs
    if remote:
        assert kwargs["sslmode"] == "verify-full" and kwargs["gssencmode"] == "disable"
        assert kwargs["ssl_min_protocol_version"] == "TLSv1.2"
    else:
        assert "sslmode" not in kwargs


def test_mariadb_remote_tls_requires_a_valid_certificate_and_hostname(monkeypatch):
    class ConnectionFailure(Exception):
        pass

    connect = MagicMock(side_effect=ConnectionFailure)
    monkeypatch.setitem(
        sys.modules,
        "pymysql",
        SimpleNamespace(
            connect=connect, MySQLError=ConnectionFailure, VERSION=(1, 2, 3)
        ),
    )
    with pytest.raises(DatabaseError):
        collect_mariadb("SELECT 1", "mariadb://reader@db.example.test/db")
    context = connect.call_args.kwargs["ssl"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname


@pytest.mark.parametrize("version", [(1, 1, 1), (1, 2, 2), ()])
def test_remote_mariadb_rejects_old_unsynced_drivers_before_connect(
    monkeypatch, version
):
    connect = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "pymysql",
        SimpleNamespace(connect=connect, MySQLError=RuntimeError, VERSION=version),
    )
    with pytest.raises(DatabaseError, match="requires PyMySQL 1.2.3"):
        collect_mariadb("SELECT 1", "mariadb://reader@db.example.test/db")
    connect.assert_not_called()


@pytest.mark.parametrize(
    "host", ["db.example.test", "192.0.2.10", "localhost.example.test"]
)
def test_sqlserver_rejects_remote_credentials_before_connect(monkeypatch, host):
    connect = MagicMock()
    monkeypatch.setitem(
        sys.modules, "pymssql", SimpleNamespace(connect=connect, Error=RuntimeError)
    )
    with pytest.raises(DatabaseError, match="remote certificate verification"):
        collect_sqlserver("SELECT 1", f"sqlserver://reader@{host}/db")
    connect.assert_not_called()


@pytest.mark.parametrize(
    "role_flags,permissions,allowed",
    [
        ((False, False, False, False, False), (False,), True),
        ((False, False, False, True, False), (False,), False),
        ((False, False, False, False, True), (False,), False),
        ((False, False, False, False, False), (True,), False),
        ((False, False, False, False, False), None, False),
        ((False, False, False, False, False), (None,), False),
    ],
)
def test_postgres_checks_role_and_effective_write_permissions_before_explain(
    monkeypatch, role_flags, permissions, allowed
):
    driver = MagicMock()
    driver.Error = RuntimeError
    driver.conninfo.conninfo_to_dict.return_value = {"host": "127.0.0.1"}
    connection = driver.connect.return_value.__enter__.return_value
    statements = []

    def execute(statement, *parameters, **kwargs):
        assert connection.read_only is True
        statements.append(statement)
        if "rolsuper, rolcreatedb" in statement:
            assert "SET LOCAL search_path TO pg_catalog, public" in statements[:-1]
            row = role_flags
        elif "has_database_privilege" in statement:
            assert "has_any_column_privilege" in statement
            assert "has_sequence_privilege" in statement and "pg_has_role" in statement
            row = permissions
        elif statement.startswith("EXPLAIN"):
            assert kwargs.get("prepare") is True
            row = (
                [{"Plan": {"Node Type": "Result", "Plan Rows": 1, "Total Cost": 0}}],
            )
        else:
            row = None
        return SimpleNamespace(fetchone=lambda: row)

    connection.execute.side_effect = execute
    monkeypatch.setitem(sys.modules, "psycopg", driver)
    if allowed:
        assert (
            collect_postgres("SELECT 1", "postgresql://reader@127.0.0.1/db").mode
            == "ESTIMATED"
        )
    else:
        with pytest.raises(DatabaseError, match="least-privilege"):
            collect_postgres("SELECT 1", "postgresql://reader@127.0.0.1/db")
        assert not any(statement.startswith("EXPLAIN") for statement in statements)
