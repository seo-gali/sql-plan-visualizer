"""Command line entry point; analysis lives in the core."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from sqlpvi.analyze import analyze
from sqlpvi.database import VENDOR_DIALECTS, DatabaseError, collect_database
from sqlpvi.parser import AnalysisError
from sqlpvi.recommend import recommend
from sqlpvi.render import render_html


def main() -> int:
    parser = argparse.ArgumentParser(prog="sqlpvi")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("analyze", help="Analyze one SQL query")
    command.add_argument("file", type=Path)
    command.add_argument("--dialect")
    command.add_argument("--vendor", choices=tuple(VENDOR_DIALECTS), default="postgres")
    command.add_argument("--output", type=Path)
    command.add_argument("--format", choices=("html", "json"), default="html")
    command.add_argument(
        "--database",
        action="store_true",
        help="Collect a read-only estimated plan for the selected vendor",
    )
    command.add_argument(
        "--runtime",
        action="store_true",
        help="Execute the read-only query to measure its plan",
    )
    args = parser.parse_args()
    if args.runtime and not args.database:
        parser.error("--runtime requires --database")
    if args.runtime and args.vendor != "postgres":
        parser.error("--runtime is supported only for PostgreSQL")
    try:
        output = args.output
        if args.format == "html" and output is None:
            output = args.file.with_suffix(".sqlpvi.html")
        if output and (
            output.resolve() == args.file.resolve()
            or (output.exists() and output.samefile(args.file))
        ):
            raise AnalysisError("OUTPUT_ERROR: output must not overwrite the SQL input")
        sql = args.file.read_text(encoding="utf-8-sig")
        dialect = args.dialect or VENDOR_DIALECTS[args.vendor]
        report = analyze(sql, str(args.file), dialect)
        if args.database:
            if args.runtime:
                print(
                    "RUNTIME: the read-only query will execute with timeouts.",
                    file=sys.stderr,
                )
                report.warnings.append(
                    "Runtime mode executed the read-only query; actual metrics are environment-dependent."
                )
            report.plan = collect_database(report, args.vendor, args.runtime)
        report.recommendations = recommend(report)
        result = (
            render_html(report)
            if args.format == "html"
            else json.dumps(asdict(report), ensure_ascii=False, indent=2)
        )
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(result, encoding="utf-8")
            print(output)
        else:
            print(result)
        return 0
    except (OSError, UnicodeError, AnalysisError, DatabaseError, RecursionError) as exc:
        print(f"sqlpvi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
