import json
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from sqlpvi.analyze import analyze
from sqlpvi.cli import main
from sqlpvi.render import render_html


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.source = ""
        self.in_source = False
        self.scripts = 0
        self.external = []
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "pre" and attrs.get("id") == "sql-source":
            self.in_source = True
        if tag == "script":
            self.scripts += 1
        for name in ("src", "href"):
            if attrs.get(name, "").startswith(("http:", "https:", "//")):
                self.external.append(attrs[name])

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_source = False

    def handle_data(self, data):
        if self.in_source:
            self.source += data


@pytest.mark.parametrize(
    "filename", ["join.sql", "cte.sql", "subquery.sql", "unsafe-strings.sql"]
)
def test_safe_standalone_html(filename):
    sql = (Path(__file__).parent.parent / "fixtures/sql" / filename).read_text(
        encoding="utf-8"
    )
    report = analyze(sql, "</title><script>window.filenameInjected=true</script>")
    content = render_html(report)
    document = Document(content)
    assert document.source == sql
    assert document.scripts == 1
    assert not document.external
    assert "<script>window.filenameInjected" not in content
    assert "<script>window.sqlpviInjected" not in content
    assert "innerHTML" not in content
    assert 'id="flow-edges"' in content
    assert all(f'id="{node.id}"' in content for node in report.flow.nodes)


def test_default_html_cli_and_hardlink_input_protection(tmp_path):
    path = tmp_path / "query.sql"
    sql = "SELECT c.id FROM customers c"
    path.write_text(sql, encoding="utf-8")
    command = [sys.executable, "-m", "sqlpvi", "analyze", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert (
        path.with_suffix(".sqlpvi.html")
        .read_text(encoding="utf-8")
        .startswith("<!doctype html>")
    )
    output = tmp_path / "hardlink.html"
    os.link(path, output)
    result = subprocess.run(
        command + ["--output", str(output)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert path.read_text(encoding="utf-8") == sql
    result = subprocess.run(
        command + ["--runtime"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert "requires --database" in result.stderr


@pytest.mark.parametrize("format", ["html", "json"])
def test_cli_creates_nested_output_folder(tmp_path, monkeypatch, capsys, format):
    path = tmp_path / "query.sql"
    sql = "SELECT c.id FROM customers AS c"
    path.write_text(sql, encoding="utf-8")
    output = tmp_path / "new" / "reports" / f"query.{format}"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sqlpvi", "analyze", str(path), "--format", format, "--output", str(output)],
    )
    assert main() == 0, capsys.readouterr().err
    content = output.read_text(encoding="utf-8")
    assert (
        Document(content).source if format == "html" else json.loads(content)["sql"]
    ) == sql
    assert path.read_text(encoding="utf-8") == sql


def test_output_folder_errors_preserve_input(tmp_path, monkeypatch, capsys):
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1", encoding="utf-8")
    blocker = tmp_path / "file"
    blocker.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["sqlpvi", "analyze", str(path), "--output", str(blocker / "report.html")],
    )
    assert main() == 1
    assert capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == "SELECT 1"
    assert blocker.read_text(encoding="utf-8") == "keep"


def test_invalid_sql_does_not_create_output_folder(tmp_path, monkeypatch, capsys):
    path = tmp_path / "query.sql"
    path.write_text("SELECT 1; SELECT 2", encoding="utf-8")
    output = tmp_path / "new" / "report.html"
    monkeypatch.setattr(
        sys, "argv", ["sqlpvi", "analyze", str(path), "--output", str(output)]
    )
    assert main() == 1
    assert capsys.readouterr().err
    assert not output.parent.exists()
