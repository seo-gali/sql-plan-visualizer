"""Verify spill recommendations and unchanged fixture data."""

import json
import os
import sys
from pathlib import Path

import psycopg
import pytest

from sqlpvi.cli import main

TEST_URL = os.environ.get("SQLPVI_TEST_POSTGRES_URL", "")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_URL, reason="isolated PostgreSQL URL not set"),
]


@pytest.mark.parametrize("work_mem,expected", [("64kB", True), ("8MB", False)])
@pytest.mark.parametrize("filename", ["sort.sql", "hash-spill.sql"])
def test_actual_recommendation_preserves_input_data_and_indexes(
    monkeypatch, capsys, work_mem, expected, filename
):
    original_connect = psycopg.connect
    observed = []

    def connect(*args, **kwargs):
        kwargs["options"] = kwargs.get("options", "") + f" -c work_mem={work_mem}"
        if filename == "hash-spill.sql":
            kwargs["options"] += " -c enable_mergejoin=off -c enable_nestloop=off"
        observed.append(True)
        return original_connect(*args, **kwargs)

    def snapshot():
        with original_connect(TEST_URL) as connection:
            return (
                connection.execute(
                    "SELECT COUNT(*), SUM(amount) FROM orders"
                ).fetchone(),
                connection.execute(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname"
                ).fetchall(),
            )

    path = Path(__file__).parent.parent / "fixtures/sql" / filename
    original_sql = path.read_bytes()
    before = snapshot()
    monkeypatch.setattr(psycopg, "connect", connect)
    monkeypatch.setenv("SQLPVI_POSTGRES_URL", TEST_URL)
    monkeypatch.setattr(
        sys,
        "argv",
        ["sqlpvi", "analyze", str(path), "--database", "--runtime", "--format", "json"],
    )
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert bool(payload["recommendations"]) == expected
    assert len(observed) == 1

    def walk(node):
        yield node
        for child in node["children"]:
            yield from walk(child)

    nodes = {node["id"]: node for node in walk(payload["plan"]["root"])}
    for candidate in payload["recommendations"]:
        assert candidate["basis"] == "RECOMMENDATION"
        assert candidate["id"] == (
            "recommendation-disk-sort"
            if filename == "sort.sql"
            else "recommendation-hash-spill"
        )
        assert (
            candidate["conditions"]
            and candidate["limitations"]
            and candidate["verification"]
        )
        for evidence in candidate["evidence"]:
            target = nodes[evidence["target_id"]]
            assert evidence["basis"] == "DATABASE"
            if filename == "sort.sql":
                assert target["details"]["Sort Space Type"] == "Disk"
            else:
                assert target["operation"] == "Hash"
                assert target["details"]["Hash Batches"] > 1
                assert target["buffers"]["Temp Written Blocks"] > 0
            assert target["actual_loops"] > 0 and target["actual_rows"] > 0
    assert path.read_bytes() == original_sql
    assert snapshot() == before
