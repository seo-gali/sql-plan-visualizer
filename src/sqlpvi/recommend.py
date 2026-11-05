"""Conservative recommendations from measured evidence; no database calls."""

import math

from sqlpvi.models import Evidence, Recommendation, Report


def _positive_metrics(*values: object) -> bool:
    return all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
        for value in values
    )


def recommend(report: Report) -> list[Recommendation]:
    plan = report.plan
    if (
        plan is None
        or plan.basis != "DATABASE"
        or plan.vendor != "postgres"
        or plan.mode != "RUNTIME"
        or any(
            ref.kind == "COLUMN" and ref.status != "RESOLVED"
            for ref in report.references
        )
    ):
        return []
    sort_evidence = []
    hash_evidence = []
    pending = [plan.root]
    while pending:
        node = pending.pop()
        pending.extend(reversed(node.children))
        if not _positive_metrics(node.actual_rows, node.actual_loops):
            continue
        space = node.details.get("Sort Space Used")
        if (
            node.operation == "Sort"
            and node.details.get("Sort Space Type") == "Disk"
            and _positive_metrics(space)
        ):
            sort_evidence.append(
                Evidence(
                    f"evidence-{node.id}",
                    node.id,
                    f"Sort Space Type=Disk; Sort Space Used={space}; Actual Rows={node.actual_rows}; Actual Loops={node.actual_loops}",
                )
            )
        batches = node.details.get("Hash Batches")
        written = node.buffers.get("Temp Written Blocks")
        if (
            node.operation == "Hash"
            and _positive_metrics(batches, written)
            and batches > 1
        ):
            hash_evidence.append(
                Evidence(
                    f"evidence-{node.id}",
                    node.id,
                    f"Hash Batches={batches}; Temp Written Blocks={written}; Actual Rows={node.actual_rows}; Actual Loops={node.actual_loops}",
                )
            )
    candidates = []
    if sort_evidence:
        candidates.append(
            Recommendation(
                "recommendation-disk-sort",
                "Review disk sorting",
                sort_evidence,
                "The measured sort used disk storage. Review sort input size and per-session work_mem.",
                "Use a representative workload, preserve result semantics, and account for concurrent queries.",
                "A disk sort alone does not prove a problem or justify an index or a global memory increase.",
                "Compare sort space, output rows, buffers, and timings in an isolated read-only test session.",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + report.sql,
            )
        )
    if hash_evidence:
        candidates.append(
            Recommendation(
                "recommendation-hash-spill",
                "Review hash spilling",
                hash_evidence,
                "The measured hash used multiple batches and wrote temporary blocks. Review hash input size and per-session memory settings.",
                "Use a representative workload, preserve result semantics, and account for concurrent queries.",
                "Hash spilling alone does not prove a problem or justify an index or a global memory increase.",
                "Compare hash batches, temporary blocks, output rows, and timings in an isolated read-only test session.",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)\n" + report.sql,
            )
        )
    return candidates
