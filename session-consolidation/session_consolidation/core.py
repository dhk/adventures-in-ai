"""Core sweep/cluster/classify/propose/archive logic for session-consolidation.

Plain functions, no MCP/CLI/web dependencies. The CLI and the MCP server both
import this module directly so the logic lives in exactly one place. See
docs/session-consolidation-design.md in the repo root for the design this
implements.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_ARCHIVE_DIR = Path.home() / ".claude" / "projects-archive"
DEFAULT_MANIFEST_PATH = Path.home() / ".claude" / "session-consolidation-log.jsonl"

STALE_DAYS = 14
CLUSTER_WINDOW_DAYS = 14

TIER_SAFE = "safe_to_archive"
TIER_DECISION = "needs_a_decision"
TIER_KEEP = "keep_as_is"

_KEYWORD_STOPWORDS = {
    "this", "that", "with", "have", "from", "they", "will", "would", "there",
    "their", "what", "about", "which", "when", "make", "like", "time", "just",
    "know", "take", "into", "your", "some", "could", "them", "then", "than",
    "look", "only", "come", "over", "also", "back", "after", "should", "session",
    "sessions", "want", "need", "help", "please", "thanks", "okay",
}


@dataclass
class Session:
    session_id: str
    path: str
    project_dir: Optional[str]
    git_branch: Optional[str]
    first_user_message: str
    last_message: str
    message_count: int
    start_time: Optional[str]
    end_time: Optional[str]
    files_touched: list = field(default_factory=list)
    git_commands: list = field(default_factory=list)
    committed: bool = False


@dataclass
class Cluster:
    cluster_id: str
    project_dir: Optional[str]
    sessions: list  # list[Session]


@dataclass
class ClassifiedSession:
    cluster_id: str
    session: Session
    classification: str
    reason: str


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def _iter_records(path: Path):
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _parse_ts(ts: Optional[str]) -> Optional[float]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _keywords(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower())
    return {w for w in words if w not in _KEYWORD_STOPWORDS}


def parse_session(path: Path) -> Optional[Session]:
    """Parse a single .jsonl transcript into a Session summary, or None if empty."""
    session_id = path.stem
    project_dir = None
    git_branch = None
    first_user_message = ""
    last_message = ""
    message_count = 0
    start_time = None
    end_time = None
    files_touched = set()
    git_commands = []
    committed = False

    for record in _iter_records(path):
        rtype = record.get("type")
        if rtype not in ("user", "assistant"):
            continue
        message_count += 1

        ts = record.get("timestamp")
        if ts:
            if start_time is None:
                start_time = ts
            end_time = ts

        if project_dir is None and record.get("cwd"):
            project_dir = record["cwd"]
        if git_branch is None and record.get("gitBranch"):
            git_branch = record["gitBranch"]

        message = record.get("message") or {}
        content = message.get("content")

        if rtype == "user" and not first_user_message:
            text = _extract_text(content)
            if text:
                first_user_message = text

        if rtype == "assistant":
            text = _extract_text(content)
            if text:
                last_message = text
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    tool_input = block.get("input") or {}
                    if name in ("Edit", "Write", "NotebookEdit"):
                        file_path = tool_input.get("file_path")
                        if file_path:
                            files_touched.add(file_path)
                    elif name == "Bash":
                        cmd = (tool_input.get("command") or "").strip()
                        if not cmd:
                            continue
                        if "git commit" in cmd:
                            committed = True
                        if cmd.startswith("git ") or " git " in cmd:
                            git_commands.append(cmd[:200])

    if message_count == 0:
        return None

    return Session(
        session_id=session_id,
        path=str(path),
        project_dir=project_dir,
        git_branch=git_branch,
        first_user_message=first_user_message.strip()[:500],
        last_message=last_message.strip()[:500],
        message_count=message_count,
        start_time=start_time,
        end_time=end_time,
        files_touched=sorted(files_touched),
        git_commands=git_commands[-10:],
        committed=committed,
    )


def sweep(projects_dir: Path = DEFAULT_PROJECTS_DIR, since_days: Optional[int] = 30) -> list:
    """Find and parse session transcripts under projects_dir.

    Returns [] (not an error) when the directory is absent -- expected on
    cloud/ephemeral environments with no local session history.
    """
    projects_dir = Path(projects_dir)
    if not projects_dir.exists():
        return []

    cutoff = None
    if since_days is not None:
        cutoff = time.time() - since_days * 86400

    sessions = []
    for path in sorted(projects_dir.glob("*/*.jsonl")):
        if cutoff is not None and path.stat().st_mtime < cutoff:
            continue
        session = parse_session(path)
        if session:
            sessions.append(session)
    return sessions


def cluster(sessions: list) -> list:
    """Group sessions plausibly split across sessions: same project, recency,
    and shared touched files or first-message keywords."""
    by_project = {}
    for s in sessions:
        key = s.project_dir or "(unknown project)"
        by_project.setdefault(key, []).append(s)

    clusters = []
    for project_dir, group in by_project.items():
        group = sorted(group, key=lambda s: _parse_ts(s.start_time) or 0)
        used = [False] * len(group)
        for i, s in enumerate(group):
            if used[i]:
                continue
            used[i] = True
            member_idxs = [i]
            acc_keywords = _keywords(s.first_user_message)
            acc_files = set(s.files_touched)
            acc_time = _parse_ts(s.start_time) or 0

            for j in range(i + 1, len(group)):
                if used[j]:
                    continue
                other = group[j]
                other_time = _parse_ts(other.start_time) or 0
                if other_time and acc_time and other_time - acc_time > CLUSTER_WINDOW_DAYS * 86400:
                    continue
                other_keywords = _keywords(other.first_user_message)
                other_files = set(other.files_touched)
                shares_file = bool(acc_files & other_files)
                shares_keywords = len(acc_keywords & other_keywords) >= 2
                if shares_file or shares_keywords:
                    member_idxs.append(j)
                    used[j] = True
                    acc_files |= other_files
                    acc_keywords |= other_keywords
                    acc_time = max(acc_time, other_time)

            members = [group[k] for k in member_idxs]
            cluster_id = f"{project_dir}::{members[0].session_id[:8]}"
            clusters.append(Cluster(cluster_id=cluster_id, project_dir=project_dir, sessions=members))

    return clusters


def _classify_one(session: Session, now: float, stale_days: int):
    end_ts = _parse_ts(session.end_time)
    age_days = (now - end_ts) / 86400 if end_ts else None
    is_recent = age_days is not None and age_days <= stale_days
    idle = f"idle {int(age_days)} day(s)" if age_days is not None else "idle for an unknown period"

    if is_recent:
        return "active", f"activity within the last {int(age_days)} day(s)"
    if session.committed:
        return "completed", "includes a git commit"
    if session.files_touched:
        return "orphaned", f"touched {len(session.files_touched)} file(s), no commit found, {idle}"
    return "stale", f"no file changes or commits, {idle}"


def classify(clusters: list, now: Optional[float] = None, stale_days: int = STALE_DAYS) -> list:
    """Classify every session in every cluster. Active and orphaned sessions
    are never silently marked superseded -- only completed/stale ones are,
    when a later session in the same cluster carries the work forward."""
    if now is None:
        now = time.time()

    results = []
    for c in clusters:
        base = [(s, *_classify_one(s, now, stale_days)) for s in c.sessions]
        if len(c.sessions) > 1:
            latest = max(c.sessions, key=lambda s: _parse_ts(s.end_time) or 0)
            for idx, (s, cls, reason) in enumerate(base):
                if s is not latest and cls in ("completed", "stale"):
                    base[idx] = (
                        s,
                        "superseded",
                        f"{reason}; superseded by a later session in the same cluster ({latest.session_id[:8]})",
                    )
        for s, cls, reason in base:
            results.append(ClassifiedSession(cluster_id=c.cluster_id, session=s, classification=cls, reason=reason))
    return results


def tier_for(classification: str) -> str:
    if classification in ("stale", "superseded"):
        return TIER_SAFE
    if classification == "orphaned":
        return TIER_DECISION
    return TIER_KEEP  # active, completed


def build_report(
    projects_dir: Path = DEFAULT_PROJECTS_DIR,
    since_days: Optional[int] = 30,
    stale_days: int = STALE_DAYS,
) -> dict:
    """Run the full sweep -> cluster -> classify -> propose pipeline and
    return one JSON-serializable report -- the shape the CLI writes and the
    web viewer reads."""
    sessions = sweep(projects_dir, since_days)
    clusters = cluster(sessions)
    classified = classify(clusters, stale_days=stale_days)

    by_cluster = {}
    for cs in classified:
        by_cluster.setdefault(cs.cluster_id, []).append(cs)

    tier_counts = {TIER_SAFE: 0, TIER_DECISION: 0, TIER_KEEP: 0}
    cluster_reports = []
    for c in clusters:
        session_reports = []
        for cs in by_cluster.get(c.cluster_id, []):
            tier = tier_for(cs.classification)
            tier_counts[tier] += 1
            s = cs.session
            session_reports.append(
                {
                    "session_id": s.session_id,
                    "path": s.path,
                    "classification": cs.classification,
                    "reason": cs.reason,
                    "tier": tier,
                    "first_user_message": s.first_user_message,
                    "last_message": s.last_message,
                    "message_count": s.message_count,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "git_branch": s.git_branch,
                    "files_touched": s.files_touched,
                    "committed": s.committed,
                }
            )
        # Most recently active session first within a cluster.
        session_reports.sort(key=lambda r: r["end_time"] or "", reverse=True)
        cluster_reports.append(
            {
                "cluster_id": c.cluster_id,
                "project_dir": c.project_dir,
                "session_count": len(session_reports),
                "sessions": session_reports,
            }
        )

    cluster_reports.sort(key=lambda c: (c["project_dir"] or "", -c["session_count"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "projects_dir": str(projects_dir),
        "since_days": since_days,
        "stale_days": stale_days,
        "summary": {
            "total_sessions": len(sessions),
            "total_clusters": len(clusters),
            TIER_SAFE: tier_counts[TIER_SAFE],
            TIER_DECISION: tier_counts[TIER_DECISION],
            TIER_KEEP: tier_counts[TIER_KEEP],
        },
        "clusters": cluster_reports,
    }


def archive_sessions(
    session_paths: list,
    archive_dir: Path = DEFAULT_ARCHIVE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    reason: str = "",
) -> list:
    """Move approved session transcripts to a mirrored path under archive_dir
    (never delete) and append one manifest entry per move for auditability."""
    archive_dir = Path(archive_dir)
    manifest_path = Path(manifest_path)
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for raw_path in session_paths:
        src = Path(raw_path)
        if not src.exists():
            results.append({"session_id": src.stem, "status": "missing", "path": str(src)})
            continue

        dest_dir = archive_dir / src.parent.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        shutil.move(str(src), str(dest))

        entry = {
            "session_id": src.stem,
            "from": str(src),
            "to": str(dest),
            "reason": reason,
            "archived_at": datetime.now(timezone.utc).isoformat(),
        }
        with manifest_path.open("a") as mf:
            mf.write(json.dumps(entry) + "\n")

        results.append({"session_id": src.stem, "status": "archived", "path": str(dest)})

    return results
