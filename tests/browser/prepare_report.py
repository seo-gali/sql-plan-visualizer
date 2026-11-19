"""Generate a standalone browser fixture with synthetic plan evidence; no DB I/O."""

import sys
from pathlib import Path

from sqlpvi.analyze import analyze
from sqlpvi.models import ExecutionPlan, PlanNode
from sqlpvi.recommend import recommend
from sqlpvi.render import render_html


def prepare(output: Path) -> None:
    sql = """SELECT o.id,
       SUM(o.amount) OVER (PARTITION BY o.customer_id ORDER BY o.id) AS running_total,
       '<script>window.sqlpviInjected=true</script> innerHTML' AS payload
FROM orders AS o
ORDER BY o.id
LIMIT 5;
"""
    report = analyze(sql, "browser-contract.sql")
    report.warnings.append(
        "Browser fixture: synthetic runtime evidence, no DB execution."
    )
    report.plan = ExecutionPlan(
        "postgres",
        "RUNTIME",
        PlanNode(
            "browser-sort",
            "Sort",
            None,
            None,
            10000,
            1,
            [],
            {"Sort Space Type": "Disk", "Sort Space Used": 128},
            actual_rows=10000,
            actual_loops=1,
            actual_time_ms=0.5,
        ),
        execution_time_ms=1,
    )
    report.recommendations = recommend(report)
    assert len(report.recommendations) == 1
    output.mkdir(parents=True, exist_ok=True)
    (output / "query.sql").write_text(sql, encoding="utf-8", newline="\n")
    (output / "report.html").write_text(render_html(report), encoding="utf-8")


if __name__ == "__main__":
    prepare(Path(sys.argv[1]))
