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
    manifest_path_for_date,
    parse_episode_title_from_filename,
    parse_reading_list_notebook_title,
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
      2) Every time a NEW file appears, reset the timer for max_wait_minutes.
      3) If no new file appears within the current window, stop waiting.
    """
    header("Waiting for new audio files")
    wait_s = max(0.0, max_wait_minutes * 60.0)
    poll_s = max(1.0, poll_interval_seconds)

    seen: set[str] = set()
    deadline = time.monotonic() + wait_s
    expected = {slug: audio_dir / f"{target_date}-{slug}.{audio_format}" for slug in slugs}

    print(f"  Window: {max_wait_minutes:.1f} min, poll: {poll_s:.0f}s")
    print("  Timer resets whenever a NEW audio file appears.")

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
            deadline = time.monotonic() + wait_s
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

        for expected_category, slug in CATEGORY_SLUGS.items():
            if expected_category == category_title or expected_category in category_title:
                prev = best.get(slug)
                if prev is None or nn > prev[0]:
                    best[slug] = (nn, nb_id)
                    best_titles[slug] = title

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


def upload_to_elementfm(client: ElementFmClient, audio_path: Path, *, dry_run: bool, manifest: dict) -> bool:
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

    # Convert if needed
    if audio_path.suffix.lower() != ".mp3":
        print(f"      Converting to mp3 ...", end=" ", flush=True)
        with tempfile.TemporaryDirectory() as td:
            mp3_path = Path(td) / (audio_path.stem + ".mp3")
            convert_to_mp3(audio_path, mp3_path)
            print("✓")

            return _upload_and_publish_mp3(client, mp3_path, title, episode_number, entry)
    else:
        mp3_path = audio_path
        return _upload_and_publish_mp3(client, mp3_path, title, episode_number, entry)

def _upload_and_publish_mp3(client: ElementFmClient, mp3_path: Path, title: str, episode_number: int, entry: dict) -> bool:
    episode_id = entry.get("episode_id")

    if not episode_id:
        # Create episode
        print(f"      Creating episode ...", end=" ", flush=True)
        episode = client.create_episode(title=title, season_number=1, episode_number=episode_number)
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

    # Publish
    if not entry.get("published"):
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
    parser.add_argument("--download-only", action="store_true",
                        help="Download audio only, skip element.fm upload")
    parser.add_argument("--upload-only", action="store_true",
                        help="Upload to element.fm only (audio files must already exist)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without doing anything")
    parser.add_argument("--slugs", default="news,think,professional",
                        help="Comma-separated slugs to process (default: news,think,professional)")
    parser.add_argument("--audio-dir", default=None,
                        help="Audio directory (overrides config). Default: iCloud Personal Podcast")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="HTTP timeout in seconds (default: 30)")
    parser.add_argument("--audio-format", choices=["mp3", "m4a"], default=None,
                        help="Saved output format (default from config, fallback: mp3)")
    parser.add_argument("--wait-for-audio", action="store_true",
                        help="In upload-only mode, wait for new audio files to appear before uploading")
    parser.add_argument("--wait-for-studio-status", action="store_true",
                        help="In non-upload-only mode, poll `nlm studio status` before download")
    parser.add_argument("--max-wait-minutes", type=float, default=15.0,
                        help="Wait window in minutes (default: 15)")
    parser.add_argument("--poll-interval-seconds", type=float, default=20.0,
                        help="Polling interval while waiting (default: 20)")
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

    # ── Step 1: Find notebooks ──────────────────────────────────────────────
    notebooks = {}
    if not args.upload_only:
        notebooks = find_notebooks_for_date(target_date)
        if not notebooks:
            sys.exit(1)
        if args.wait_for_studio_status and not args.dry_run:
            # Keep only notebooks whose studio artifacts are ready by timeout.
            ready_slugs = set(
                wait_for_studio_audio_ready(
                    notebooks=notebooks,
                    max_wait_minutes=args.max_wait_minutes,
                    poll_interval_seconds=args.poll_interval_seconds,
                )
            )
            notebooks = {slug: nb_id for slug, nb_id in notebooks.items() if slug in ready_slugs}
            if not notebooks:
                warn("No notebooks became ready within the wait window.")
                sys.exit(1)
    else:
        waited_found = []
        if args.wait_for_audio:
            waited_found = wait_for_audio_files(
                audio_dir=audio_dir,
                target_date=target_date,
                slugs=slugs,
                audio_format=audio_format,
                max_wait_minutes=args.max_wait_minutes,
                poll_interval_seconds=args.poll_interval_seconds,
            )

        # In upload-only mode, infer from existing files
        for slug in slugs:
            audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
            if slug in waited_found or audio_path.exists():
                notebooks[slug] = None  # no notebook id needed

    # ── Step 2: Download audio ──────────────────────────────────────────────
    downloaded = []
    if not args.upload_only:
        header("Downloading audio overviews")
        for slug in slugs:
            nb_id = notebooks.get(slug)
            if not nb_id:
                warn(f"No notebook found for slug: {slug} — skipping")
                continue
            output_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
            success = download_audio(nb_id, output_path, args.dry_run, output_format=audio_format)
            if success:
                downloaded.append(slug)
    else:
        # Check which files exist
        for slug in slugs:
            audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
            if audio_path.exists():
                downloaded.append(slug)
            else:
                warn(f"File not found, skipping: {audio_path.name}")

    if args.download_only:
        header("Done (download-only mode)")
        print(f"  Downloaded: {', '.join(downloaded) or 'none'}")
        print(f"  Files in: {audio_dir}\n")
        return

    # Optional second guard: after studio-status gating + download, apply rolling
    # quiet-window file wait before upload to catch late-arriving files.
    if args.wait_for_studio_status and args.wait_for_audio and not args.upload_only and not args.dry_run:
        pre_upload_found = wait_for_audio_files(
            audio_dir=audio_dir,
            target_date=target_date,
            slugs=slugs,
            audio_format=audio_format,
            max_wait_minutes=args.max_wait_minutes,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        for slug in pre_upload_found:
            if slug not in downloaded:
                downloaded.append(slug)

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
    )

    for slug in downloaded:
        audio_path = audio_dir / f"{target_date}-{slug}.{audio_format}"
        if not audio_path.exists():
            warn(f"File not found after download: {audio_path.name}")
            failed.append(slug)
            continue
        success = upload_to_elementfm(client, audio_path, dry_run=args.dry_run, manifest=manifest)
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
    print(f"  Downloaded: {len(downloaded)} — {', '.join(downloaded) or 'none'}")
    print(f"  Uploaded:   {len(uploaded)} — {', '.join(uploaded) or 'none'}")
    if failed:
        print(f"  Failed:     {len(failed)} — {', '.join(failed)}")
    if not args.dry_run and uploaded:
        print(f"\n  🎧 Episodes live in Overcast and Apple Podcasts")
        print(f"  View show: https://app.element.fm/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}")
    print()


if __name__ == "__main__":
    main()