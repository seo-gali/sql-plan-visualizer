import os
import sys

import pytest
from html_document import Document

from sqlpvi import cli


def test_watch_rebuilds_only_changed_content_and_recovers(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "query.sql"
    output = source.with_suffix(".sqlpvi.html")
    original = "SELECT 1 AS value"
    source.write_text(original, encoding="utf-8")
    initial_stat = source.stat()
    monkeypatch.setattr(sys, "argv", ["sqlpvi", "analyze", str(source), "--watch"])
    written = []
    real_analyze = cli.analyze

    def analyze(sql, *args):
        written.append(sql)
        return real_analyze(sql, *args)

    monkeypatch.setattr(cli, "analyze", analyze)
    ticks = iter(range(6))

    def tick(seconds):
        step = next(ticks)
        if step == 0:
            assert Document(output.read_text(encoding="utf-8")).source == original
        elif step == 1:
            assert written == [original]
            source.write_text("SELECT 2 AS value", encoding="utf-8")
            os.utime(source, ns=(initial_stat.st_atime_ns, initial_stat.st_mtime_ns))
        elif step == 2:
            assert "SELECT 2 AS value" in output.read_text(encoding="utf-8")
            source.write_text("SELECT * FROM (((", encoding="utf-8")
        elif step == 3:
            assert "SELECT 2 AS value" in output.read_text(encoding="utf-8")
            source.unlink()
        elif step == 4:
            source.write_text("SELECT 3 AS value", encoding="utf-8")
        else:
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "sleep", tick)
    assert cli.main() == 0
    assert written == [
        original,
        "SELECT 2 AS value",
        "SELECT * FROM (((",
        "SELECT 3 AS value",
    ]
    assert Document(output.read_text(encoding="utf-8")).source == "SELECT 3 AS value"
    messages = capsys.readouterr()
    assert "SQL_PARSE_ERROR" in messages.err and "report not updated" in messages.err
    assert "stopped" in messages.out


@pytest.mark.parametrize(
    "option", [["--database"], ["--format", "json"], ["--database", "--runtime"]]
)
def test_watch_rejects_database_execution_and_json(monkeypatch, tmp_path, option):
    source = tmp_path / "query.sql"
    source.write_text("SELECT 1", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["sqlpvi", "analyze", str(source), "--watch", *option]
    )
    monkeypatch.setattr(cli, "collect_database", lambda *args: pytest.fail("DB called"))
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert not source.with_suffix(".sqlpvi.html").exists()


def test_watch_rechecks_input_overwrite_protection(tmp_path, monkeypatch):
    source = tmp_path / "query.sql"
    source.write_text("SELECT 1", encoding="utf-8")
    output = tmp_path / "report.html"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sqlpvi", "analyze", str(source), "--output", str(output), "--watch"],
    )
    refreshed = False

    def tick(seconds):
        nonlocal refreshed
        if refreshed:
            raise KeyboardInterrupt
        refreshed = True
        output.unlink()
        os.link(source, output)
        source.write_text("SELECT 2", encoding="utf-8")

    monkeypatch.setattr(cli, "sleep", tick)
    assert cli.main() == 0
    assert source.read_text(encoding="utf-8") == "SELECT 2"
