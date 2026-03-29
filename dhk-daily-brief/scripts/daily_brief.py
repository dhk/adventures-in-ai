#!/usr/bin/env python3
"""
DHK Daily Brief — End-to-End Pipeline
From Inbox to Earbuds in one command.

Finds today's reading-list NotebookLM notebooks, downloads their audio
overviews via the nlm CLI, and uploads them to element.fm.

Usage:
    python3 daily_brief.py                  # today
    python3 daily_brief.py --date 2026-03-19
    python3 daily_brief.py --download-only  # skip element.fm upload
    python3 daily_brief.py --upload-only    # skip nlm download (files already exist)
    python3 daily_brief.py --dry-run        # show what would happen, do nothing
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, date
from pathlib import Path

# Local imports (same directory)
from elementfm_client import ElementFmClient, ElementFmConfig
from podcast_config import (
    CATEGORY_SLUGS,
    CATEGORY_TITLES,
    STATE_DIR,
    elementfm_episode_description,
    manifest_path_for_date,
    parse_audio_filename,
    parse_episode_title_from_filename,
    parse_reading_list_notebook_title,
    slug_for_category_title,
    resolve_audio_dir,
    resolve_audio_format,
)
from subprocess_utils import run_with_retries

# ── Config ─────────────────────────────────────────────────────────────────────

SCRIPTS_DIR  = Path(__file__).parent
NLM_CLI      = "nlm"

API_KEY      = os.environ.get("CLAUDE_ELEMENT_FM_KEY")
WORKSPACE_ID = "b08a0951-94a4-441d-a446-81cc7950749c"
SHOW_ID      = "d5be8d71-5fe3-4d2c-b641-0cd7343e4e36"
BASE_URL     = f"https://app.element.fm/api/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}"

# ── Utilities ──────────────────────────────────────────────────────────────────

def header(text):
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def ok(msg):
    print(f"  ✓  {msg}")


def warn(msg):
    print(f"  ⚠️  {msg}")


def fail(msg):
    print(f"  ❌  {msg}")


def wait_for_audio_files(
    *,
    audio_dir: Path,
    target_date: str,
    slugs: list[str],
    audio_format: str,
    max_wait_minutes: float,
    poll_interval_seconds: float,
) -> list[str]:
    """
    Rolling-window wait for new audio files.

    Rules:
      1) Wait up to max_wait_minutes for a first file.
      2) Once the first file appears, reset the timer to 5 minutes for remaining files.
      3) If no new file appears within the current window, stop waiting.
    """
    header("Waiting for new audio files")
    wait_s = max(0.0, max_wait_minutes * 60.0)
    after_first_wait_s = 5.0 * 60.0  # 5 min window once first file found
    poll_s = max(1.0, poll_interval_seconds)

    seen: set[str] = set()
    deadline = time.monotonic() + wait_s
    expected = {slug: audio_dir / f"{target_date}-{slug}.{audio_format}" for slug in slugs}

    print(f"  Window: {max_wait_minutes:.1f} min (then 5 min per file), poll: {poll_s:.0f}s")
    print("  Timer resets to 5 min whenever a NEW audio file appears.")

    while time.monotonic() < deadline:
        new_files = []
        for slug, path in expected.items():
            if slug in seen:
                continue
            if path.exists() and path.stat().st_size > 0:
                seen.add(slug)
                new_files.append(slug)

        if new_files:
            for slug in new_files:
                ok(f"Detected: {target_date}-{slug}.{audio_format}")
            if seen == set(expected.keys()):
                ok("All expected files found.")
                break
            deadline = time.monotonic() + after_first_wait_s
            continue

        time.sleep(poll_s)

    if seen:
        ok(f"Quiet period reached; proceeding with {len(seen)} detected file(s).")
    else:
        warn("No new files detected before timeout window; proceeding.")
    return list(seen)


def _json_walk_status_values(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == "status" and isinstance(v, str):
                yield v.lower()
            yield from _json_walk_status_values(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _json_walk_status_values(item)


def _audio_completed_from_status_payload(payload: object) -> bool:
    """
    Best-effort check for completed audio artifacts in nlm studio status JSON.
    """
    if payload is None:
        return False
    # Conservative heuristic:
    # - If any status is explicitly in-progress/pending/processing, not ready.
    # - Ready when at least one status is completed/succeeded/done.
    statuses = list(_json_walk_status_values(payload))
    if not statuses:
        return False
    if any(s in {"in_progress", "pending", "processing", "running"} for s in statuses):
        return False
    return any(s in {"completed", "succeeded", "success", "done"} for s in statuses)


def wait_for_studio_audio_ready(
    *,
    notebooks: dict[str, str],
    max_wait_minutes: float,
    poll_interval_seconds: float,
) -> list[str]:
    """
    Poll `nlm studio status <notebook_id> --json` until audio is ready.
    Returns slugs that appear ready before timeout.
    """
    header("Waiting for NotebookLM studio audio readiness")
    wait_s = max(0.0, max_wait_minutes * 60.0)
    poll_s = max(1.0, poll_interval_seconds)
    deadline = time.monotonic() + wait_s
    ready: set[str] = set()

    while time.monotonic() < deadline and len(ready) < len(notebooks):
        for slug, notebook_id in notebooks.items():
            if slug in ready:
                continue
            result = run_with_retries(
                [NLM_CLI, "studio", "status", notebook_id, "--json"],
                timeout_s=45,
                retries=1,
            )
            if result.returncode != 0:
                continue
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                continue
            if _audio_completed_from_status_payload(payload):
                ready.add(slug)
                ok(f"Studio ready: {slug}")

        if len(ready) < len(notebooks):
            time.sleep(poll_s)

    not_ready = [slug for slug in notebooks.keys() if slug not in ready]
    if not_ready:
        warn(f"Studio not ready before timeout: {', '.join(not_ready)}")
    return list(ready)


def wait_for_notebooks_for_date(
    *,
    target_date: str,
    max_wait_minutes: float,
    poll_interval_seconds: float,
) -> dict[str, str]:
    """
    Wait for reading-list notebooks for target date to appear.
    """
    header("Waiting for notebooks to appear")
    wait_s = max(0.0, max_wait_minutes * 60.0)
    poll_s = max(1.0, poll_interval_seconds)
    deadline = time.monotonic() + wait_s

    while time.monotonic() < deadline:
        notebooks = find_notebooks_for_date(target_date)
        if notebooks:
            return notebooks
        time.sleep(poll_s)

    return {}


def fetch_studio_titles(notebooks: dict[str, str]) -> dict[str, str]:
    """
    Fetch the renamed studio artifact titles set by Phase 1.
    Returns {slug: rich_title} for slugs where a title was found.
    """
    header("Fetching studio artifact titles")
    titles: dict[str, str] = {}
    for slug, notebook_id in notebooks.items():
        result = run_with_retries(
            [NLM_CLI, "studio", "status", notebook_id, "--json"],
            timeout_s=45,
            retries=1,
        )
        if result.returncode != 0:
            warn(f"Could not fetch studio status for {slug}")
            continue
        try:
            payload = json.loads(result.stdout)
            artifacts = payload if isinstance(payload, list) else payload.get("artifacts", [])
            for artifact in artifacts if isinstance(artifacts, list) else []:
                t = artifact.get("title") or artifact.get("name")
                if t and t.strip():
                    titles[slug] = t.strip()
                    ok(f"{slug}: {t[:80]}")
                    break
        except (json.JSONDecodeError, AttributeError):
            continue
    return titles


def _parse_iso_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def cleanup_old_items(*, audio_dir: Path, cutoff_date_str: str, apply: bool) -> int:
    """
    Cleanup mode (dry-run by default).

    Deletes local podcast audio files older than cutoff_date in the expected naming scheme.
    Deletes NotebookLM reading-list notebooks older than cutoff_date ONLY if a downloaded audio
    file exists for that (date, category slug).
    """
    header(f"Cleanup mode (cutoff: {cutoff_date_str})")
    if not audio_dir.exists():
        warn(f"Audio directory not found: {audio_dir}")
        return 1

    cutoff_date = _parse_iso_date(cutoff_date_str)

    # 1) Audio files (local)
    supported_exts = {"mp3", "m4a"}
    allowed_slugs = set(CATEGORY_SLUGS.values())

    audio_deletions: list[tuple[Path, str, str]] = []  # (path, dt, slug)
    audio_keys: set[tuple[str, str]] = set()  # (dt, slug)
    audio_kept_wrong_slug: list[tuple[Path, str, str]] = []
    audio_kept_wrong_ext: list[tuple[Path, str, str]] = []

    for path in audio_dir.iterdir():
        if not path.is_file():
            continue
        parsed = parse_audio_filename(path.name)
        if not parsed:
            continue
        dt, slug, ext = parsed
        if _parse_iso_date(dt) < cutoff_date:
            if slug in allowed_slugs and ext in supported_exts:
                audio_deletions.append((path, dt, slug))
                audio_keys.add((dt, slug))
            elif slug not in allowed_slugs:
                audio_kept_wrong_slug.append((path, dt, slug))
            elif ext not in supported_exts:
                audio_kept_wrong_ext.append((path, dt, slug))

    # 2) Notebooks (NotebookLM)
    nlm_result = run_with_retries(
        [NLM_CLI, "notebook", "list", "--json"],
        timeout_s=60,
        retries=2,
        initial_backoff_s=1.0,
    )
    if nlm_result.returncode != 0:
        warn(f"nlm notebook list failed: {nlm_result.stderr.strip() or nlm_result.stdout.strip()}")
        return 1

    try:
        notebooks_payload = json.loads(nlm_result.stdout)
    except json.JSONDecodeError:
        warn("Could not parse nlm output as JSON.")
        return 1

    notebooks = notebooks_payload.get("notebooks", []) if isinstance(notebooks_payload, dict) else notebooks_payload

    notebook_deletions: list[tuple[str, str, str]] = []  # (nb_id, dt, slug)
    notebook_kept_no_audio: list[tuple[str, str, str]] = []

    for nb in notebooks:
        title = nb.get("title", "")
        nb_id = nb.get("id", "")
        if not isinstance(title, str) or not isinstance(nb_id, str):
            continue
        parsed = parse_reading_list_notebook_title(title)
        if not parsed:
            continue
        dt, _nn, category_title = parsed
        slug = slug_for_category_title(category_title)
        if not slug:
            continue
        nb_dt = _parse_iso_date(dt)
        if nb_dt >= cutoff_date:
            continue
        if (dt, slug) in audio_keys:
            notebook_deletions.append((nb_id, dt, slug))
        else:
            notebook_kept_no_audio.append((nb_id, dt, slug))

    print(f"  Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print(f"  Audio deletions:    {len(audio_deletions)}")
    print(f"  Notebook deletions: {len(notebook_deletions)}")
    print(f"  Notebooks kept (no audio): {len(notebook_kept_no_audio)}")
    print(f"  Audio kept (wrong slug): {len(audio_kept_wrong_slug)}")
    print(f"  Audio kept (wrong ext):  {len(audio_kept_wrong_ext)}")

    if audio_deletions:
        print("\n  Audio to delete:")
        for path, dt, slug in sorted(audio_deletions, key=lambda x: (x[1], x[2], str(x[0]))):
            print(f"    - {path}  ({dt} / {slug})")

    if notebook_deletions:
        print("\n  Notebooks to delete:")
        for nb_id, dt, slug in sorted(notebook_deletions, key=lambda x: (x[1], x[2], x[0])):
            print(f"    - {nb_id}  ({dt} / {slug})")

    if notebook_kept_no_audio:
        print("\n  Notebooks kept (no matching audio):")
        for nb_id, dt, slug in sorted(notebook_kept_no_audio, key=lambda x: (x[1], x[2], x[0])):
            print(f"    - {nb_id}  ({dt} / {slug})")

    if audio_kept_wrong_slug:
        print("\n  Audio kept (filename matches pattern but slug not one of ours):")
        for path, dt, slug in sorted(audio_kept_wrong_slug, key=lambda x: (x[1], x[2], str(x[0]))):
            print(f"    - {path}  ({dt} / {slug})")

    if audio_kept_wrong_ext:
        print("\n  Audio kept (filename matches pattern but ext is not mp3/m4a):")
        for path, dt, slug in sorted(audio_kept_wrong_ext, key=lambda x: (x[1], x[2], str(x[0]))):
            print(f"    - {path}  ({dt} / {slug})")

    if not apply:
        print("\nDry-run complete. No deletions performed.")
        return 0

    ok("Applying deletions...")

    audio_errors = 0
    for path, _dt, _slug in audio_deletions:
        try:
            path.unlink()
        except Exception as e:
            audio_errors += 1
            warn(f"Audio delete failed: {path} ({e})")

    notebook_errors = 0
    for nb_id, _dt, _slug in notebook_deletions:
        del_res = run_with_retries(
            [NLM_CLI, "notebook", "delete", "--confirm", nb_id],
            timeout_s=60,
            retries=0,
        )
        if del_res.returncode != 0:
            notebook_errors += 1
            warn(f"Notebook delete failed: {nb_id} ({del_res.stderr.strip() or del_res.stdout.strip()})")

    if audio_errors or notebook_errors:
        warn(f"Cleanup completed with errors: audio_errors={audio_errors}, notebook_errors={notebook_errors}")
        return 1

    ok("Cleanup complete.")
    return 0


# ── NotebookLM: Find notebooks for date ────────────────────────────────────────

def find_notebooks_for_date(target_date: str) -> dict:
    """
    Scan NotebookLM for reading-list notebooks matching the given date.
    Returns {slug: notebook_id} e.g. {"news": "abc123", "think": "def456"}
    """
    header(f"Finding notebooks for {target_date}")

    result = run_with_retries(
        [NLM_CLI, "notebook", "list", "--json"],
        timeout_s=45,
        retries=2,
    )
    if result.returncode != 0:
        fail(f"nlm notebook list failed: {result.stderr.strip() or result.stdout.strip()}")
        sys.exit(1)

    try:
        notebooks = json.loads(result.stdout)
    except json.JSONDecodeError:
        fail(f"Could not parse nlm output: {result.stdout[:200]}")
        sys.exit(1)

    # Handle both list and {"notebooks": [...]} formats
    if isinstance(notebooks, dict):
        notebooks = notebooks.get("notebooks", [])

    prefix = f"reading-list-{target_date}"
    best: dict[str, tuple[int, str]] = {}  # slug -> (nn, notebook_id)
    best_titles: dict[str, str] = {}

    for nb in notebooks:
        title = nb.get("title", "")
        nb_id = nb.get("id", "")
        if not isinstance(title, str) or not title.startswith(prefix):
            continue
        parsed = parse_reading_list_notebook_title(title)
        if not parsed:
            continue
        dt, nn, category_title = parsed
        if dt != target_date:
            continue

        slug = slug_for_category_title(category_title)
        if slug:
            prev = best.get(slug)
            if prev is None or nn > prev[0]:
                best[slug] = (nn, nb_id)
                best_titles[slug] = title
        else:
            warn(f"Unrecognized reading-list category (no slug): {title!r}")

    found = {slug: nb_id for slug, (_nn, nb_id) in best.items()}
    for slug, nb_id in found.items():
        ok(f"{slug:15s} → {nb_id}  ({best_titles.get(slug,'')})")

    if not found:
        warn(f"No reading-list notebooks found for {target_date}")
        warn("Has the reading-list-builder skill been run for this date?")

    return found


# ── NotebookLM: Download audio ─────────────────────────────────────────────────

def download_audio(notebook_id: str, output_path: Path, dry_run: bool, *, output_format: str) -> bool:
    """Download audio overview via nlm CLI. Returns True on success."""
    if dry_run:
        print(f"  [dry-run] nlm download audio {notebook_id} --output {output_path.name}")
        return True

    if output_path.exists():
        ok(f"Already exists, skipping: {output_path.name}")
        return True

    print(f"  Downloading {output_path.name} ...", end=" ", flush=True)
    # NotebookLM currently emits m4a; convert to mp3 when requested.
    if output_format == "mp3":
        with tempfile.TemporaryDirectory() as td:
            m4a_tmp = Path(td) / f"{output_path.stem}.m4a"
            result = run_with_retries(
                [NLM_CLI, "download", "audio", notebook_id, "--output", str(m4a_tmp)],
                timeout_s=180,
                retries=3,
                initial_backoff_s=2.0,
            )
            if result.returncode != 0:
                print()
                warn(f"Download failed (attempts={result.attempts}): {result.stderr.strip() or result.stdout.strip()}")
                return False
            convert_to_mp3(m4a_tmp, output_path)
            ok(f"Saved to {output_path.name}")
            return True
    else:
        result = run_with_retries(
            [NLM_CLI, "download", "audio", notebook_id, "--output", str(output_path)],
            timeout_s=180,
            retries=3,
            initial_backoff_s=2.0,
        )
    if result.returncode != 0:
        print()
        warn(f"Download failed (attempts={result.attempts}): {result.stderr.strip() or result.stdout.strip()}")
        return False

    ok(f"Saved to {output_path.name}")
    return True


# ── element.fm API ─────────────────────────────────────────────────────────────

def _is_real_mp3(path: Path) -> bool:
    """Return True only if the file's magic bytes indicate actual MP3 content."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        # ID3 tag (most MP3s) or sync word FF FB/FA/F3/F2 (raw MPEG frame)
        if header[:3] == b"ID3":
            return True
        if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
            return True
        return False
    except OSError:
        return False


def convert_to_mp3(input_path: Path, output_path: Path):
    """Convert audio to MP3 via ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-codec:a", "libmp3lame", "-qscale:a", "3",
        "-loglevel", "error",
        str(output_path)
    ]
    result = run_with_retries(cmd, timeout_s=180, retries=0)
    if result.returncode != 0:
        fail(f"ffmpeg error: {result.stderr.strip()}")
        sys.exit(1)


def upload_to_elementfm(client: ElementFmClient, audio_path: Path, *, dry_run: bool, manifest: dict, rich_description: str | None = None) -> bool:
    """Convert, upload, and publish one episode. Returns True on success."""
    title = parse_episode_title_from_filename(audio_path.name)

    # Idempotency: if we already recorded an episode_id, reuse it; otherwise look up by title.
    slug = audio_path.stem.split("-")[3] if len(audio_path.stem.split("-")) >= 4 else audio_path.stem
    entry = manifest.setdefault("episodes", {}).setdefault(slug, {})
    episode_id = entry.get("episode_id")
    existing = None
    if not episode_id:
        existing = client.find_episode_by_title(title)
        if existing and existing.get("id"):
            episode_id = existing["id"]
            entry["episode_id"] = episode_id
            entry["found_existing_by_title"] = True

    episode_number = entry.get("episode_number")
    if not isinstance(episode_number, int):
        episode_number = client.get_next_episode_number()
        entry["episode_number"] = episode_number

    print(f"\n  📤  {audio_path.name}")
    print(f"      Title:   {title}")
    print(f"      Episode: #{episode_number}")

    if dry_run:
        print("      [dry-run] would upload and publish")
        return True

    # Convert if needed — check actual file content, not just extension
    # (Phase 1 skill may save M4A files with a .mp3 extension)
    needs_convert = audio_path.suffix.lower() != ".mp3" or not _is_real_mp3(audio_path)
    if needs_convert:
        print(f"      Converting to mp3 ...", end=" ", flush=True)
        with tempfile.TemporaryDirectory() as td:
            mp3_path = Path(td) / (audio_path.stem + ".mp3")
            convert_to_mp3(audio_path, mp3_path)
            print("✓")
            return _upload_and_publish_mp3(client, mp3_path, title, episode_number, entry, rich_description)
    else:
        return _upload_and_publish_mp3(client, audio_path, title, episode_number, entry, rich_description)

def _upload_and_publish_mp3(client: ElementFmClient, mp3_path: Path, title: str, episode_number: int, entry: dict, rich_description: str | None = None) -> bool:
    episode_id = entry.get("episode_id")

    if not episode_id:
        # Create episode
        print(f"      Creating episode ...", end=" ", flush=True)
        desc = elementfm_episode_description(title, rich_description)
        episode = client.create_episode(
            title=title,
            season_number=1,
            episode_number=episode_number,
            description=desc,
        )
        if "error" in episode:
            fail(f"Create failed: {episode['error']}")
            entry["create_error"] = episode.get("error")
            return False
        episode_id = episode.get("id")
        if not episode_id:
            fail("Create failed: missing episode id")
            entry["create_error"] = "missing episode id"
            return False
        entry["episode_id"] = episode_id
        print(f"✓ ({str(episode_id)[:8]}...)")
    else:
        ok(f"Reusing existing episode_id: {str(episode_id)[:8]}...")

    # Upload audio
    if not entry.get("audio_uploaded"):
        print(f"      Uploading audio ...", end=" ", flush=True)
        result = client.upload_audio(episode_id=str(episode_id), mp3_path=mp3_path)
        if "error" in result:
            fail(f"Upload failed: {result['error']}")
            entry["upload_error"] = result.get("error")
            return False
        entry["audio_uploaded"] = True
        print("✓")
    else:
        ok("Audio already uploaded (per manifest), skipping upload")

    # Publish (element.fm requires a non-empty episode description)
    if not entry.get("published"):
        desc = elementfm_episode_description(title, rich_description)
        patch = client.patch_episode(episode_id=str(episode_id), data={"description": desc})
        if "error" in patch:
            warn(f"Set description failed: {patch['error']} — publish may still fail")
        print(f"      Publishing ...", end=" ", flush=True)
        result = client.publish_episode(episode_id=str(episode_id))
        if "error" in result:
            warn(f"Publish failed: {result['error']} — publish manually in element.fm")
            entry["publish_error"] = result.get("error")
            return True
        entry["published"] = True
        print("✓")
    else:
        ok("Already published (per manifest), skipping publish")

    return True


# ── Status ─────────────────────────────────────────────────────────────────────

SLUGS_ALL = ["news", "think", "professional"]


def _manifest_status_line(slug: str, entry: dict) -> str:
    if not entry:
        return "  —  not started"
    if entry.get("published"):
        ep = entry.get("episode_number")
        ep_str = f"  (#{ep})" if isinstance(ep, int) else ""
        return f"  ✓  published{ep_str}"
    if entry.get("upload_error") or entry.get("create_error"):
        err = entry.get("upload_error") or entry.get("create_error")
        return f"  ✗  error: {err}"
    if entry.get("audio_uploaded"):
        return "  ↑  uploaded (not yet published)"
    if entry.get("episode_id"):
        return "  …  episode created (not uploaded)"
    return "  —  in progress"


def _is_complete(manifest: dict) -> bool:
    eps = manifest.get("episodes", {})
    return all(eps.get(s, {}).get("published") for s in SLUGS_ALL)


def _print_manifest(manifest: dict, audio_dir: Path, audio_format: str):
    target_date = manifest.get("date", "?")
    eps = manifest.get("episodes", {})
    for slug in SLUGS_ALL:
        entry = eps.get(slug, {})
        audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
        file_str = "  📁 file ready" if audio_path.exists() else ""
        print(f"  {slug:14s}{_manifest_status_line(slug, entry)}{file_str}")


def show_status(target_date: str, audio_dir: Path, audio_format: str):
    # ── Today ──────────────────────────────────────────────────────────────
    header(f"Status — {target_date}")
    today_path = manifest_path_for_date(target_date)
    if today_path.exists():
        try:
            today_manifest = json.loads(today_path.read_text(encoding="utf-8"))
        except Exception:
            today_manifest = {}
    else:
        today_manifest = {}

    files_on_disk: set[str] = set()
    for slug in SLUGS_ALL:
        for ext in (audio_format, "mp3", "m4a"):
            if (audio_dir / f"{target_date}-{slug}.{ext}").exists():
                files_on_disk.add(slug)
                break

    if today_manifest:
        _print_manifest(today_manifest, audio_dir, audio_format)
        all_published = _is_complete(today_manifest)
        eps = today_manifest.get("episodes", {})
        has_error = any(
            eps.get(s, {}).get("upload_error") or eps.get(s, {}).get("create_error")
            for s in SLUGS_ALL
        )
        any_unpublished = not all_published
    else:
        print("  No manifest yet — checking for audio files on disk:")
        for slug in SLUGS_ALL:
            if slug in files_on_disk:
                path = next(
                    audio_dir / f"{target_date}-{slug}.{ext}"
                    for ext in (audio_format, "mp3", "m4a")
                    if (audio_dir / f"{target_date}-{slug}.{ext}").exists()
                )
                size_mb = path.stat().st_size / 1_048_576
                print(f"  {slug:14s}  📁 {path.name}  ({size_mb:.1f} MB)")
            else:
                print(f"  {slug:14s}  —  no file found")
        all_published = False
        has_error = False
        any_unpublished = True

    # ── Last completed ─────────────────────────────────────────────────────
    header("Last completed run")
    manifests = sorted(STATE_DIR.glob("manifest-*.json"), reverse=True)
    last_complete = None
    for path in manifests:
        date_str = path.stem.replace("manifest-", "")
        if date_str == target_date:
            continue
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _is_complete(m):
            last_complete = m
            break

    if last_complete:
        print(f"  Date: {last_complete.get('date', '?')}")
        _print_manifest(last_complete, audio_dir, audio_format)
    else:
        print("  No completed runs found in history.")

    # ── Next step ──────────────────────────────────────────────────────────
    header("Next step")
    if all_published:
        print("  ✓  All episodes published — nothing to do.")
    elif has_error:
        print("  ✗  Some episodes errored. Retry:")
        print("     daily-brief --upload-only")
    elif files_on_disk and not today_manifest:
        print("  Files are ready but not uploaded. Run:")
        print("     daily-brief --upload-only")
    elif files_on_disk and any_unpublished:
        print("  Some episodes not yet published. Run:")
        print("     daily-brief --upload-only")
    elif not files_on_disk:
        print("  No audio files found. Run the full pipeline:")
        print("     daily-brief")
    else:
        print("  Run the full pipeline:")
        print("     daily-brief")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DHK Daily Brief — end-to-end pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 daily_brief.py                     # run full pipeline for today
  python3 daily_brief.py --date 2026-03-19   # run for a specific date
  python3 daily_brief.py --download-only     # nlm download only, skip upload
  python3 daily_brief.py --upload-only       # element.fm upload only (files must exist)
  python3 daily_brief.py --dry-run           # preview without doing anything
        """
    )
    parser.add_argument("--date", default=date.today().strftime("%Y-%m-%d"),
                        help="Date to process (YYYY-MM-DD, default: today)")
    parser.add_argument("--show-status", action="store_true",
                        help="Show pipeline status for today and the last completed run, then exit")
    parser.add_argument("--download-only", action="store_true",
                        help="Download audio from NotebookLM only, skip element.fm upload")
    parser.add_argument("--upload-only", action="store_true",
                        help="Upload to element.fm only (audio files must already exist)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without doing anything")
    parser.add_argument("--slugs", default="news,think,professional",
                        help="Comma-separated slugs to process (default: news,think,professional)")
    parser.add_argument("--audio-dir", default=None,
                        help="Audio directory (overrides config). Default: iCloud Personal Podcast")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="HTTP timeout for JSON API calls in seconds (default: 30)")
    parser.add_argument("--upload-timeout", type=float, default=900.0,
                        help="Minimum per-attempt timeout for MP3 uploads in seconds; actual may be higher from file size (default: 900)")
    parser.add_argument("--audio-format", choices=["mp3", "m4a"], default=None,
                        help="Saved output format (default from config, fallback: mp3)")
    parser.add_argument("--wait-for-audio", dest="wait_for_audio", action=argparse.BooleanOptionalAction, default=True,
                        help="Wait for new audio files before upload (default: on; disable with --no-wait-for-audio)")
    parser.add_argument("--wait-for-studio-status", dest="wait_for_studio_status", action=argparse.BooleanOptionalAction, default=True,
                        help="Poll `nlm studio status` before download (default: on; disable with --no-wait-for-studio-status)")
    parser.add_argument("--max-wait-minutes", type=float, default=15.0,
                        help="Wait window in minutes (default: 15)")
    parser.add_argument("--poll-interval-seconds", type=float, default=20.0,
                        help="Polling interval while waiting (default: 20)")
    parser.add_argument("--cleanup-old", action="store_true",
                        help="Cleanup mode: delete downloaded audio + matching reading-list notebooks older than cutoff date (dry-run by default).")
    parser.add_argument("--cleanup-apply", action="store_true",
                        help="In cleanup mode, actually perform deletions (default is dry-run).")
    parser.add_argument("--cleanup-cutoff-date", default=date.today().strftime("%Y-%m-%d"),
                        help="Cutoff date for cleanup (YYYY-MM-DD). Older than this are eligible (default: today).")
    args = parser.parse_args()

    target_date = args.date
    slugs = [s.strip() for s in args.slugs.split(",")]
    audio_dir = resolve_audio_dir(cli_audio_dir=args.audio_dir)
    audio_format = resolve_audio_format(cli_audio_format=args.audio_format)
    manifest_path = manifest_path_for_date(target_date)

    print(f"""
╔══════════════════════════════════════════════════╗
║       DHK Daily Brief Pipeline                  ║
║       From Inbox to Earbuds                     ║
╚══════════════════════════════════════════════════╝
  Date:     {target_date}
  Mode:     {"dry-run" if args.dry_run else "download-only" if args.download_only else "upload-only" if args.upload_only else "full pipeline"}
  Slugs:    {", ".join(slugs)}
  Format:   {audio_format}
  Audio dir: {audio_dir}
  Manifest:  {manifest_path}
""")

    # Validate
    if args.show_status:
        audio_dir = resolve_audio_dir(cli_audio_dir=args.audio_dir)
        audio_format = resolve_audio_format(cli_audio_format=args.audio_format)
        show_status(target_date, audio_dir, audio_format)
        sys.exit(0)

    if args.cleanup_old:
        sys.exit(
            cleanup_old_items(
                audio_dir=audio_dir,
                cutoff_date_str=args.cleanup_cutoff_date,
                apply=args.cleanup_apply,
            )
        )

    if not args.dry_run and not args.download_only:
        if not API_KEY:
            fail("CLAUDE_ELEMENT_FM_KEY not set. Run: source ~/.zshrc")
            sys.exit(1)

    if not audio_dir.exists():
        fail(f"Audio directory not found: {audio_dir}")
        fail("Create it, or set ~/.config/dhk-daily-brief/config.json audio_dir, or pass --audio-dir")
        sys.exit(1)

    # Load manifest (idempotency)
    manifest = {"date": target_date, "episodes": {}}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {"date": target_date, "episodes": {}}

    # ── Step 1: Find notebooks + wait for studio readiness ─────────────────
    notebooks = {}
    if not args.dry_run:
        if args.upload_only:
            notebooks = {}  # audio files already on disk; no need to query nlm
        elif args.wait_for_studio_status:
            notebooks = wait_for_notebooks_for_date(
                target_date=target_date,
                max_wait_minutes=args.max_wait_minutes,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        else:
            notebooks = find_notebooks_for_date(target_date)

        if not args.upload_only and not notebooks:
            warn("No notebooks found before timeout/discovery step.")
            sys.exit(1)

        missing_nb = [s for s in slugs if s not in notebooks]
        if missing_nb:
            warn(
                "No NotebookLM notebook matched for: "
                + ", ".join(missing_nb)
                + " (skill may have skipped an empty category, or the notebook title/category differs)."
            )

        if args.wait_for_studio_status and notebooks:
            before_studio = dict(notebooks)
            ready_slugs = set(
                wait_for_studio_audio_ready(
                    notebooks=notebooks,
                    max_wait_minutes=args.max_wait_minutes,
                    poll_interval_seconds=args.poll_interval_seconds,
                )
            )
            notebooks = {slug: nb_id for slug, nb_id in notebooks.items() if slug in ready_slugs}
            dropped = set(before_studio.keys()) - set(notebooks.keys())
            if dropped:
                warn(
                    "Studio audio not ready in time (skipped these slugs — "
                    "re-run with --no-wait-for-studio-status or increase --max-wait-minutes): "
                    + ", ".join(sorted(dropped))
                )
            if not args.upload_only and not notebooks:
                warn("No notebooks became ready within the wait window.")
                sys.exit(1)

    # ── Step 2: Fetch rich titles from studio artifacts ─────────────────────
    # Phase 1 renames each artifact with the NotebookLM title + bullets + sources.
    # We use that as the Element.fm episode description.
    rich_titles: dict[str, str] = {}
    if notebooks and not args.dry_run:
        rich_titles = fetch_studio_titles(notebooks)

    # ── Step 3: Download audio from NotebookLM (if not upload-only) ─────────
    if not args.upload_only:
        header("Downloading audio overviews")
        for slug in slugs:
            nb_id = notebooks.get(slug)
            if not nb_id:
                warn(f"No notebook found for slug: {slug} — skipping")
                continue
            output_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
            download_audio(nb_id, output_path, args.dry_run, output_format=audio_format)

    if args.download_only:
        header("Done (download-only mode)")
        print(f"  Files in: {audio_dir}\n")
        return

    # ── Step 4: Wait for audio files then check what's available ────────────
    if args.wait_for_audio and not args.dry_run:
        wait_for_audio_files(
            audio_dir=audio_dir,
            target_date=target_date,
            slugs=slugs,
            audio_format=audio_format,
            max_wait_minutes=args.max_wait_minutes,
            poll_interval_seconds=args.poll_interval_seconds,
        )

    available = []
    for slug in slugs:
        audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
        if audio_path.exists() or args.dry_run:
            available.append(slug)
        else:
            warn(f"File not found, skipping: {audio_path.name}")

    # ── Step 3: Upload to element.fm ────────────────────────────────────────
    header("Uploading to element.fm — DHK Daily Brief")
    uploaded = []
    failed = []

    client = ElementFmClient(
        ElementFmConfig(
            api_key=API_KEY or "",
            workspace_id=WORKSPACE_ID,
            show_id=SHOW_ID,
            base_url=BASE_URL,
        ),
        timeout_s=args.timeout,
        upload_timeout_s=args.upload_timeout,
    )

    for slug in available:
        audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
        if not audio_path.exists() and not args.dry_run:
            warn(f"File not found: {audio_path.name}")
            failed.append(slug)
            continue
        success = upload_to_elementfm(client, audio_path, dry_run=args.dry_run, manifest=manifest, rich_description=rich_titles.get(slug))
        try:
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass
        if success:
            uploaded.append(slug)
        else:
            failed.append(slug)

    # ── Summary ─────────────────────────────────────────────────────────────
    header("Summary")
    print(f"  Date:       {target_date}")
    print(f"  Available:  {len(available)} — {', '.join(available) or 'none'}")
    print(f"  Uploaded:   {len(uploaded)} — {', '.join(uploaded) or 'none'}")
    if failed:
        print(f"  Failed:     {len(failed)} — {', '.join(failed)}")
    if not args.dry_run and uploaded:
        print(f"\n  🎧 Episodes live in Overcast and Apple Podcasts")
        print(f"  View show: https://app.element.fm/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}")
    print()


if __name__ == "__main__":
    main()