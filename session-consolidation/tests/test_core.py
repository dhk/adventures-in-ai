import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from session_consolidation import core  # noqa: E402


def _ts(days_ago: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat().replace("+00:00", "Z")


def _write_session(
    project_dir: Path,
    session_id: str,
    project_cwd: str,
    first_message: str,
    start_days_ago: float,
    end_days_ago: float,
    files_touched=(),
    committed=False,
):
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{session_id}.jsonl"
    lines = [
        {
            "type": "user",
            "message": {"role": "user", "content": first_message},
            "timestamp": _ts(start_days_ago),
            "cwd": project_cwd,
            "gitBranch": "main",
        }
    ]
    content = []
    for fp in files_touched:
        content.append({"type": "tool_use", "name": "Edit", "input": {"file_path": fp}})
    if committed:
        content.append({"type": "tool_use", "name": "Bash", "input": {"command": "git commit -m 'done'"}})
    content.append({"type": "text", "text": "wrapping up"})
    lines.append(
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": content},
            "timestamp": _ts(end_days_ago),
            "cwd": project_cwd,
        }
    )
    with path.open("w") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


def test_sweep_returns_empty_list_when_projects_dir_missing(tmp_path):
    assert core.sweep(tmp_path / "does-not-exist") == []


def test_parse_session_extracts_expected_fields(tmp_path):
    path = _write_session(
        tmp_path / "proj",
        "abc123",
        "/home/user/repo",
        "fix the login bug in auth.py",
        start_days_ago=1,
        end_days_ago=1,
        files_touched=["/home/user/repo/auth.py"],
        committed=True,
    )
    session = core.parse_session(path)
    assert session.session_id == "abc123"
    assert session.project_dir == "/home/user/repo"
    assert session.committed is True
    assert session.files_touched == ["/home/user/repo/auth.py"]
    assert "login bug" in session.first_user_message


def test_cluster_groups_by_project_and_shared_file(tmp_path):
    proj = tmp_path / "proj"
    _write_session(proj, "s1", "/home/user/repo", "fix the login bug in auth.py",
                    start_days_ago=5, end_days_ago=5, files_touched=["/home/user/repo/auth.py"])
    _write_session(proj, "s2", "/home/user/repo", "continue fixing the login bug",
                    start_days_ago=2, end_days_ago=2, files_touched=["/home/user/repo/auth.py"])
    _write_session(proj, "s3", "/home/user/other-repo", "unrelated work on a different repo",
                    start_days_ago=2, end_days_ago=2, files_touched=["/home/user/other-repo/x.py"])

    sessions = core.sweep(tmp_path, since_days=None)
    assert len(sessions) == 3
    clusters = core.cluster(sessions)
    # s1/s2 share project + file -> one cluster; s3 is a different project -> its own cluster
    sizes = sorted(len(c.sessions) for c in clusters)
    assert sizes == [1, 2]


def test_classify_marks_older_completed_session_as_superseded(tmp_path):
    proj = tmp_path / "proj"
    _write_session(proj, "old", "/home/user/repo", "add the export feature",
                    start_days_ago=18, end_days_ago=18, files_touched=["/home/user/repo/export.py"], committed=True)
    _write_session(proj, "new", "/home/user/repo", "finish the export feature",
                    start_days_ago=5, end_days_ago=5, files_touched=["/home/user/repo/export.py"], committed=True)

    sessions = core.sweep(tmp_path, since_days=None)
    clusters = core.cluster(sessions)
    assert len(clusters) == 1
    classified = core.classify(clusters, stale_days=14)
    by_id = {cs.session.session_id: cs for cs in classified}
    assert by_id["new"].classification == "active"
    assert by_id["old"].classification == "superseded"


def test_classify_orphaned_never_marked_superseded(tmp_path):
    proj = tmp_path / "proj"
    _write_session(proj, "old_orphan", "/home/user/repo", "start the export feature",
                    start_days_ago=18, end_days_ago=18, files_touched=["/home/user/repo/export.py"], committed=False)
    _write_session(proj, "new", "/home/user/repo", "finish the export feature",
                    start_days_ago=5, end_days_ago=5, files_touched=["/home/user/repo/export.py"], committed=True)

    sessions = core.sweep(tmp_path, since_days=None)
    clusters = core.cluster(sessions)
    classified = core.classify(clusters, stale_days=14)
    by_id = {cs.session.session_id: cs for cs in classified}
    # orphaned (uncommitted touched files) must always surface for a human decision,
    # never get silently swept into "superseded" alongside stale/completed sessions.
    assert by_id["old_orphan"].classification == "orphaned"
    assert core.tier_for(by_id["old_orphan"].classification) == core.TIER_DECISION


def test_build_report_tier_counts_and_shape(tmp_path):
    proj = tmp_path / "proj"
    _write_session(proj, "stale1", "/home/user/repo", "an abandoned experiment",
                    start_days_ago=40, end_days_ago=40)
    report = core.build_report(projects_dir=tmp_path, since_days=None, stale_days=14)
    assert report["summary"]["total_sessions"] == 1
    assert report["summary"][core.TIER_SAFE] == 1
    assert report["clusters"][0]["sessions"][0]["classification"] == "stale"


def test_archive_moves_file_and_writes_manifest(tmp_path):
    proj = tmp_path / "proj"
    path = _write_session(proj, "stale1", "/home/user/repo", "an abandoned experiment",
                           start_days_ago=40, end_days_ago=40)
    archive_dir = tmp_path / "archive"
    manifest_path = tmp_path / "manifest.jsonl"

    results = core.archive_sessions([str(path)], archive_dir=archive_dir, manifest_path=manifest_path, reason="stale, no commit")

    assert results[0]["status"] == "archived"
    assert not path.exists()
    dest = Path(results[0]["path"])
    assert dest.exists()
    assert dest.parent.name == "proj"

    manifest_lines = manifest_path.read_text().strip().splitlines()
    assert len(manifest_lines) == 1
    entry = json.loads(manifest_lines[0])
    assert entry["session_id"] == "stale1"
    assert entry["reason"] == "stale, no commit"


def test_archive_reports_missing_file_without_raising(tmp_path):
    results = core.archive_sessions(
        [str(tmp_path / "gone.jsonl")],
        archive_dir=tmp_path / "archive",
        manifest_path=tmp_path / "manifest.jsonl",
    )
    assert results[0]["status"] == "missing"
