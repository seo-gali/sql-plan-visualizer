import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sqlpvi import cli
from sqlpvi.analyze import analyze
from sqlpvi.models import ExecutionPlan, PlanNode
from sqlpvi.recommend import recommend
from sqlpvi.render import render_html

SORT_PATH = Path(__file__).parent.parent / "fixtures/sql/sort.sql"


@pytest.fixture
def report():
    report = analyze(SORT_PATH.read_text(encoding="utf-8"))
    report.plan = ExecutionPlan(
        "postgres",
        "RUNTIME",
        PlanNode(
            "plan-0",
            "Sort",
            None,
            None,
            10000,
            1,
            [],
            {"Sort Space Type": "Disk", "Sort Space Used": 256},
            actual_rows=10000,
            actual_loops=1,
        ),
    )
    return report


def test_evidence_is_traceable_and_recommendations_are_pure(report):
    before = asdict(report)
    candidates = recommend(report)
    assert candidates == recommend(report)
    assert asdict(report) == before
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.basis == "RECOMMENDATION"
    assert candidate.evidence[0].target_id == report.plan.root.id
    assert candidate.evidence[0].id == "evidence-plan-0"
    assert candidate.evidence[0].basis == "DATABASE"
    assert "Sort Space Used=256" in candidate.evidence[0].observation
    assert all(
        (
            candidate.reason,
            candidate.conditions,
            candidate.limitations,
            candidate.verification,
        )
    )
    assert (
        candidate.suggested_sql
        == "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + report.sql
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("mode", "ESTIMATED"),
        ("basis", "STATIC"),
        ("vendor", "mariadb"),
        ("vendor", "sqlserver"),
    ],
)
def test_insufficient_or_other_vendor_evidence_is_ignored(report, field, value):
    setattr(report.plan, field, value)
    assert recommend(report) == []


def test_static_input_has_no_candidates(report):
    report.plan = None
    assert recommend(report) == []


@pytest.mark.parametrize("status", ["AMBIGUOUS", "UNRESOLVED"])
def test_uncertain_column_references_have_no_candidates(report, status):
    next(ref for ref in report.references if ref.kind == "COLUMN").status = status
    assert recommend(report) == []


def test_small_table_seq_scan_does_not_trigger_index_advice(report):
    report.plan.root.operation = "Seq Scan"
    report.plan.root.relation = "customers"
    report.plan.root.actual_rows = 10
    report.plan.root.details = {"Relation Name": "customers"}
    assert recommend(report) == []


def test_high_cost_memory_sort_does_not_trigger_advice(report):
    report.plan.root.estimated_cost = 1e100
    report.plan.execution_time_ms = 1e100
    report.plan.root.details["Sort Space Type"] = "Memory"
    assert recommend(report) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("space", None),
        ("space", 0),
        ("space", -1),
        ("space", "256"),
        ("space", True),
        ("space", float("inf")),
        ("space", float("nan")),
        ("actual_rows", None),
        ("actual_rows", 0),
        ("actual_loops", None),
        ("actual_loops", 0),
    ],
)
def test_incomplete_or_unexecuted_metrics_do_not_trigger_advice(report, field, value):
    if field == "space":
        report.plan.root.details["Sort Space Used"] = value
    else:
        setattr(report.plan.root, field, value)
    assert recommend(report) == []


def test_multiple_observed_sorts_share_one_candidate(report):
    report.plan.root.children.append(
        PlanNode(
            "plan-1",
            "Sort",
            None,
            None,
            10000,
            1,
            [],
            {"Sort Space Type": "Disk", "Sort Space Used": 128},
            actual_rows=10000,
            actual_loops=1,
        )
    )
    candidates = recommend(report)
    assert len(candidates) == 1
    assert {e.target_id for e in candidates[0].evidence} == {"plan-0", "plan-1"}


def test_recommendation_html_links_evidence_and_escapes_sql(report):
    unsafe = analyze(
        "SELECT '<script>window.recommendInjected=true</script>' AS payload"
    )
    unsafe.plan = report.plan
    unsafe.recommendations = recommend(unsafe)
    html = render_html(unsafe)
    assert 'id="recommendations-title"' in html
    assert ">RECOMMENDATION</span>" in html
    assert 'href="#plan-0"' in html and 'id="plan-0"' in html
    assert "&lt;script&gt;window.recommendInjected=true&lt;/script&gt;" in html
    assert "<script>window.recommendInjected" not in html
    assert html.count("<script>") == 1


def test_cli_collects_once_and_preserves_input(monkeypatch, capsys, report):
    observed = []
    before = SORT_PATH.read_bytes()

    def collect(current, vendor, runtime):
        observed.append((current.sql, vendor, runtime))
        return report.plan

    monkeypatch.setattr(cli, "collect_database", collect)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sqlpvi",
            "analyze",
            str(SORT_PATH),
            "--database",
            "--runtime",
            "--format",
            "json",
        ],
    )
    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["recommendations"]) == 1
    assert observed == [(before.decode("utf-8"), "postgres", True)]
    assert SORT_PATH.read_bytes() == before


@pytest.fixture
def hash_report(report):
    report.plan.root.operation = "Hash"
    report.plan.root.details = {"Hash Batches": 8}
    report.plan.root.buffers = {"Temp Written Blocks": 32}
    return report


def test_hash_spill_requires_traceable_runtime_evidence(hash_report):
    before = asdict(hash_report)
    candidates = recommend(hash_report)
    assert asdict(hash_report) == before
    assert candidates == recommend(hash_report)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.id == "recommendation-hash-spill"
    assert candidate.evidence[0].target_id == "plan-0"
    assert "Hash Batches=8" in candidate.evidence[0].observation
    assert "Temp Written Blocks=32" in candidate.evidence[0].observation
    assert all(
        (
            candidate.reason,
            candidate.conditions,
            candidate.limitations,
            candidate.verification,
        )
    )
    assert (
        candidate.suggested_sql
        == "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + hash_report.sql
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("batches", value)
        for value in (None, 0, 1, -1, True, "8", float("inf"), float("nan"))
    ]
    + [
        ("written", value)
        for value in (None, 0, -1, True, "32", float("inf"), float("nan"))
    ]
    + [("actual_rows", None), ("actual_rows", 0), ("actual_loops", 0)],
)
def test_hash_without_complete_spill_metrics_has_no_advice(hash_report, field, value):
    if field == "batches":
        hash_report.plan.root.details["Hash Batches"] = value
    elif field == "written":
        hash_report.plan.root.buffers["Temp Written Blocks"] = value
    else:
        setattr(hash_report.plan.root, field, value)
    assert recommend(hash_report) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("mode", "ESTIMATED"),
        ("vendor", "mariadb"),
        ("vendor", "sqlserver"),
        ("basis", "STATIC"),
    ],
)
def test_hash_spill_ignores_other_evidence_sources(hash_report, field, value):
    setattr(hash_report.plan, field, value)
    assert recommend(hash_report) == []


def test_hash_spill_with_uncertain_references_has_no_advice(hash_report):
    next(
        ref for ref in hash_report.references if ref.kind == "COLUMN"
    ).status = "UNRESOLVED"
    assert recommend(hash_report) == []


def test_sort_and_hash_spills_have_separate_linked_candidates(report):
    report.plan.root.children.append(
        PlanNode(
            "plan-1",
            "Hash",
            None,
            None,
            10000,
            1,
            [],
            {"Hash Batches": 8},
            actual_rows=10000,
            actual_loops=1,
            buffers={"Temp Written Blocks": 32},
        )
    )
    report.recommendations = recommend(report)
    assert [candidate.id for candidate in report.recommendations] == [
        "recommendation-disk-sort",
        "recommendation-hash-spill",
    ]
    assert [
        candidate.evidence[0].target_id for candidate in report.recommendations
    ] == ["plan-0", "plan-1"]
    html = render_html(report)
    assert 'href="#plan-0"' in html and 'href="#plan-1"' in html
