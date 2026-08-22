"""MCP server exposing session-consolidation's core as tools.

Thin wrapper only -- all logic lives in core.py. Register with:

    claude mcp add session-consolidation -- python3 -m session_consolidation.mcp_server

Run directly for local/manual testing:

    python3 -m session_consolidation.mcp_server
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import core

mcp = FastMCP("session-consolidation")


@mcp.tool()
def sweep_sessions(projects_dir: Optional[str] = None, since_days: Optional[int] = 30) -> dict:
    """Sweep local Claude Code session transcripts and return their metadata
    (project, first/last message, files touched, commit activity) without
    clustering or classifying them. Use for a raw inventory; prefer
    propose_actions for the full sweep -> cluster -> classify -> propose
    pipeline in one call."""
    directory = Path(projects_dir) if projects_dir else core.DEFAULT_PROJECTS_DIR
    sessions = core.sweep(directory, since_days)
    return {
        "count": len(sessions),
        "sessions": [vars(s) for s in sessions],
    }


@mcp.tool()
def propose_actions(projects_dir: Optional[str] = None, since_days: Optional[int] = 30, stale_days: int = core.STALE_DAYS) -> dict:
    """Run the full session-consolidation pipeline: sweep transcripts,
    cluster related sessions, classify each (active / completed / stale /
    orphaned / superseded), and tier them into safe_to_archive /
    needs_a_decision / keep_as_is. Returns a report; does not archive
    anything -- call archive_sessions with explicit paths after the caller
    (a human, via whatever surface is presenting this) approves."""
    directory = Path(projects_dir) if projects_dir else core.DEFAULT_PROJECTS_DIR
    return core.build_report(projects_dir=directory, since_days=since_days, stale_days=stale_days)


@mcp.tool()
def archive_sessions(session_paths: list, reason: str = "", archive_dir: Optional[str] = None) -> dict:
    """Archive (move, never delete) the given session transcript file paths
    to a mirrored location under archive_dir (default
    ~/.claude/projects-archive/), logging each move to an append-only
    manifest. Only call this with paths the user has explicitly approved --
    seeing a propose_actions report is not approval to archive it."""
    directory = Path(archive_dir) if archive_dir else core.DEFAULT_ARCHIVE_DIR
    results = core.archive_sessions(session_paths, archive_dir=directory, reason=reason)
    return {"results": results}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
