"""CLI for session-consolidation. Imports core.py directly -- no MCP server
process required for sweep/report; only needed if you want other MCP hosts
to call the same logic (see mcp_server.py).

Usage:
    session-consolidation report [--since 30d] [--out report.json]
    session-consolidation archive --report report.json --approve-tier safe_to_archive --yes
    session-consolidation archive --report report.json --approve <session_id> [<session_id> ...] --yes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import core

TIER_LABELS = {
    core.TIER_SAFE: "Safe to archive",
    core.TIER_DECISION: "Needs a decision",
    core.TIER_KEEP: "Keep as-is",
}


def _parse_since(value: str):
    if value is None or value.lower() == "all":
        return None
    value = value.lower().strip()
    if value.endswith("d"):
        value = value[:-1]
    return int(value)


def _print_report_summary(report: dict, file=sys.stderr):
    summary = report["summary"]
    since_label = f"{report['since_days']}d" if report["since_days"] is not None else "all"
    print(
        f"Swept {summary['total_sessions']} session(s) across {summary['total_clusters']} "
        f"cluster(s) under {report['projects_dir']} "
        f"(since={since_label}, stale_days={report['stale_days']})",
        file=file,
    )
    for tier in (core.TIER_SAFE, core.TIER_DECISION, core.TIER_KEEP):
        print(f"  {TIER_LABELS[tier]}: {summary[tier]}", file=file)
    print(file=file)

    for c in report["clusters"]:
        print(f"Cluster {c['cluster_id']}  ({c['project_dir']}, {c['session_count']} session(s))", file=file)
        for s in c["sessions"]:
            print(
                f"  [{s['tier']}] {s['classification']:<11} {s['session_id'][:12]}  "
                f"{s['reason']}",
                file=file,
            )
            topic = s["first_user_message"].splitlines()[0][:80] if s["first_user_message"] else "(no topic captured)"
            print(f"      \"{topic}\"", file=file)
        print(file=file)


def cmd_sweep(args):
    directory = Path(args.projects_dir) if args.projects_dir else core.DEFAULT_PROJECTS_DIR
    sessions = core.sweep(directory, _parse_since(args.since))
    payload = {"count": len(sessions), "sessions": [vars(s) for s in sessions]}
    _write_json(payload, args.out)
    if args.out:
        print(f"Wrote {len(sessions)} session(s) to {args.out}", file=sys.stderr)


def cmd_report(args):
    directory = Path(args.projects_dir) if args.projects_dir else core.DEFAULT_PROJECTS_DIR
    report = core.build_report(
        projects_dir=directory,
        since_days=_parse_since(args.since),
        stale_days=args.stale_days,
    )
    if not args.quiet:
        _print_report_summary(report)
    _write_json(report, args.out)
    if args.out:
        print(f"Wrote report to {args.out}", file=sys.stderr)


def cmd_archive(args):
    report = json.loads(Path(args.report).read_text())

    by_id = {}
    for c in report["clusters"]:
        for s in c["sessions"]:
            by_id[s["session_id"]] = s

    targets = []
    if args.approve_tier:
        targets = [s for s in by_id.values() if s["tier"] == args.approve_tier]
        if args.approve_tier != core.TIER_SAFE:
            print(
                f"Refusing to bulk-approve tier '{args.approve_tier}': only "
                f"'{core.TIER_SAFE}' can be approved in bulk. Use --approve <id> "
                f"for individual sessions in other tiers.",
                file=sys.stderr,
            )
            return 1
    elif args.approve:
        missing = [sid for sid in args.approve if sid not in by_id]
        if missing:
            print(f"Unknown session id(s) in report: {', '.join(missing)}", file=sys.stderr)
            return 1
        targets = [by_id[sid] for sid in args.approve]
    else:
        print("Nothing to do: pass --approve <id...> or --approve-tier safe_to_archive", file=sys.stderr)
        return 1

    if not targets:
        print("No matching sessions to archive.", file=sys.stderr)
        return 0

    print(f"{'Archiving' if args.yes else 'Would archive'} {len(targets)} session(s):", file=sys.stderr)
    for s in targets:
        print(f"  [{s['classification']}] {s['session_id']}  {s['path']}", file=sys.stderr)

    if not args.yes:
        print("\nDry run only -- re-run with --yes to actually move these files.", file=sys.stderr)
        return 0

    archive_dir = Path(args.archive_dir) if args.archive_dir else core.DEFAULT_ARCHIVE_DIR
    results = core.archive_sessions(
        [s["path"] for s in targets],
        archive_dir=archive_dir,
        reason=args.reason or f"approved via CLI ({args.approve_tier or 'explicit ids'})",
    )
    for r in results:
        print(f"  {r['status']}: {r['session_id']} -> {r.get('path')}", file=sys.stderr)
    return 0


def _write_json(payload: dict, out: str):
    text = json.dumps(payload, indent=2)
    if out:
        Path(out).write_text(text)
    else:
        print(text)


def build_parser():
    parser = argparse.ArgumentParser(prog="session-consolidation")
    parser.add_argument("--projects-dir", default=None, help="Override ~/.claude/projects")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sweep = sub.add_parser("sweep", help="Raw session inventory, no clustering/classification")
    p_sweep.add_argument("--since", default="30d", help="e.g. 7d, 30d, all (default: 30d)")
    p_sweep.add_argument("--out", default=None, help="Write JSON here instead of stdout")
    p_sweep.set_defaults(func=cmd_sweep)

    p_report = sub.add_parser("report", help="Full sweep -> cluster -> classify -> propose pipeline")
    p_report.add_argument("--since", default="30d", help="e.g. 7d, 30d, all (default: 30d)")
    p_report.add_argument("--stale-days", type=int, default=core.STALE_DAYS)
    p_report.add_argument("--out", default=None, help="Write JSON report here (also feeds the web viewer)")
    p_report.add_argument("--quiet", action="store_true", help="Suppress the human-readable summary")
    p_report.set_defaults(func=cmd_report)

    p_archive = sub.add_parser("archive", help="Archive approved sessions from a prior report (move, never delete)")
    p_archive.add_argument("--report", required=True, help="Path to a report JSON from `report --out`")
    p_archive.add_argument("--approve", nargs="+", metavar="SESSION_ID", help="Explicit session ids to archive")
    p_archive.add_argument("--approve-tier", choices=[core.TIER_SAFE], help="Bulk-approve every session in this tier (safe_to_archive only)")
    p_archive.add_argument("--archive-dir", default=None, help="Override ~/.claude/projects-archive")
    p_archive.add_argument("--reason", default=None, help="Recorded in the archive manifest")
    p_archive.add_argument("--yes", action="store_true", help="Actually move files; omit for a dry run")
    p_archive.set_defaults(func=cmd_archive)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
