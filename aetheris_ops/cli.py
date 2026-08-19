"""
Command line interface for aetheris-ops.

Commands:
  check      - quick summary of the host health and optimization findings
  report     - full markdown/JSON report (used by the GitHub workflow)
  updates    - list pending package updates

Exit codes: 0 = clean, 1 = warnings or pending updates, 2 = critical findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .collectors import collect, current_time
from .optimizations import evaluate, grade
from .report import render_json, render_markdown, write_report
from .updates import detect_all

_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def _worst_severity(findings: list) -> str:
    """Return the most severe finding level present, defaulting to 'info'."""
    worst = "info"
    for finding in findings:
        rank = _SEVERITY_RANK.get(finding.severity, 0)
        if rank > _SEVERITY_RANK[worst]:
            worst = finding.severity
    return worst


def _exit_for(findings: list, updates: list, include_updates: bool = True) -> int:
    """Map findings/updates to the documented exit code contract."""
    worst = _worst_severity(findings)
    if worst == "critical":
        return 2
    if worst == "warning" or (include_updates and updates):
        return 1
    return 0


def _print_findings_table(findings: list) -> None:
    if not findings:
        print("  No optimization opportunities detected.")
        return
    for finding in findings:
        severity = finding.severity.upper().ljust(8)
        print(f"  [{severity}] {finding.title}")
        print(f"          {finding.detail}")
        if finding.fix:
            print(f"          fix: {finding.fix}")
        print()


def cmd_check(args: argparse.Namespace) -> int:
    metrics = collect()
    findings, score = evaluate(metrics)
    updates = [] if args.no_updates else detect_all()

    print(f"Aetheris host report - {current_time()}")
    print(f"Host: {metrics.get('hostname')} ({metrics.get('platform')} {metrics.get('release')})")
    print(f"Score: {score}/100 (grade {grade(score)})")
    print()
    print("Optimizations:")
    _print_findings_table(findings)
    if updates:
        print(f"Pending updates: {len(updates)}")
        for update in updates[:10]:
            print(f"  [{update.manager}] {update.package}: {update.current} -> {update.available}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")
    else:
        print("Pending updates: none detected")

    return _exit_for(findings, updates)


def cmd_report(args: argparse.Namespace) -> int:
    metrics = collect()
    findings, score = evaluate(metrics)
    updates = [] if args.no_updates else detect_all()

    if args.json:
        print(json.dumps(render_json(metrics, findings, updates, score), indent=2))
    elif args.markdown or not (args.out_md or args.out_json):
        # Default to markdown on stdout when no output file was requested.
        print(render_markdown(metrics, findings, updates, score))
    else:
        write_report(
            metrics,
            findings,
            updates,
            score,
            markdown_path=args.out_md,
            json_path=args.out_json,
        )
        print(f"Report written. Score: {score}/100 (grade {grade(score)}).")

    return _exit_for(findings, updates)


def cmd_updates(args: argparse.Namespace) -> int:
    updates = detect_all()
    if not updates:
        print("No pending package updates detected.")
        return 0
    print(f"{len(updates)} pending update(s):")
    for update in updates:
        print(f"  [{update.manager}] {update.package}: {update.current} -> {update.available}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aetheris-ops",
        description="System optimization scanner and update manager for Aetheris hosts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_check = subparsers.add_parser("check", help="quick host health summary")
    parser_check.add_argument("--no-updates", action="store_true", help="skip update detection")
    parser_check.set_defaults(func=cmd_check)

    parser_report = subparsers.add_parser("report", help="full markdown/JSON report")
    output_group = parser_report.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="print JSON report to stdout")
    output_group.add_argument("--markdown", action="store_true", help="print markdown report to stdout")
    parser_report.add_argument("--out-md", default=None, help="write markdown report to this file")
    parser_report.add_argument("--out-json", default=None, help="write JSON report to this file")
    parser_report.add_argument("--no-updates", action="store_true", help="skip update detection")
    parser_report.set_defaults(func=cmd_report)

    parser_updates = subparsers.add_parser("updates", help="list pending package updates")
    parser_updates.set_defaults(func=cmd_updates)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
