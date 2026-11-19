import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from html_document import Document

BLOCK_DRIVERS = """
import importlib.abc
import sys
class BlockDrivers(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'psycopg', 'pymysql', 'pymssql'}:
            raise ModuleNotFoundError('database driver unavailable: ' + fullname)
sys.meta_path.insert(0, BlockDrivers())
"""


@pytest.mark.parametrize("vendor", ["postgres", "mariadb", "sqlserver"])
@pytest.mark.parametrize("format", ["json", "html"])
def test_static_cli_runs_without_any_database_driver(tmp_path, format, vendor):
    path = tmp_path / "query.sql"
    sql = "SELECT o.amount FROM orders o"
    path.write_text(sql, encoding="utf-8")
    output = tmp_path / f"report.{format}"
    program = (
        BLOCK_DRIVERS
        + """
from sqlpvi.cli import main
raise SystemExit(main())
"""
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            "analyze",
            str(path),
            "--vendor",
            vendor,
            "--format",
            format,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    if format == "json":
        payload = json.loads(content)
        assert payload["sql"] == sql and payload["plan"] is None
    else:
        assert Document(content).source == sql
    assert path.read_text(encoding="utf-8") == sql


def test_core_test_collection_needs_no_database_drivers():
    program = (
        BLOCK_DRIVERS
        + """
import os
import pytest
for vendor in ('POSTGRES','MARIADB','SQLSERVER'):
    os.environ['SQLPVI_TEST_' + vendor + '_URL'] = 'fixture-only-for-collection'
raise SystemExit(pytest.main(['tests', '--collect-only', '-m', 'not integration', '-q', '-p', 'no:cacheprovider']))
"""
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_development_and_database_dependencies_are_optional():
    config = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    )

    def names(specifiers):
        return {re.match(r"[\w.-]+", value).group().lower() for value in specifiers}

    runtime = names(config["project"]["dependencies"])
    assert not runtime & {"pytest", "ruff", "psycopg", "pymysql", "pymssql"}
    assert {"pytest", "ruff"} <= names(config["dependency-groups"]["dev"])
    extras = config["project"]["optional-dependencies"]
    for extra, driver in [
        ("postgres", "psycopg"),
        ("mariadb", "pymysql"),
        ("sqlserver", "pymssql"),
    ]:
        assert driver in names(extras[extra])
