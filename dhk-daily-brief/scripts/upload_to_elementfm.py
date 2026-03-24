#!/usr/bin/env python3
"""
Upload NotebookLM audio to element.fm
Converts m4a → mp3, creates episode, uploads audio, publishes.

Usage:
    python3 upload_to_elementfm.py <audio_file> [--title "Episode Title"] [--dry-run]

Examples:
    python3 upload_to_elementfm.py 2026-03-21-news.m4a
    python3 upload_to_elementfm.py 2026-03-21-think.m4a --title "Things to Think About — Mar 21"
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Local imports (same directory)
from elementfm_client import ElementFmClient, ElementFmConfig
from podcast_config import elementfm_episode_description, parse_episode_title_from_filename
from subprocess_utils import run_with_retries

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY      = os.environ.get("CLAUDE_ELEMENT_FM_KEY")
WORKSPACE_ID = "b08a0951-94a4-441d-a446-81cc7950749c"
SHOW_ID      = "d5be8d71-5fe3-4d2c-b641-0cd7343e4e36"
BASE_URL     = f"https://app.element.fm/api/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}"

# ── Helpers ───────────────────────────────────────────────────────────────────

def convert_to_mp3(input_path, output_path):
    """Convert audio file to MP3 using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-codec:a", "libmp3lame", "-qscale:a", "3",
        "-loglevel", "error",
        str(output_path)
    ]
    result = run_with_retries(cmd, timeout_s=180, retries=0)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr.strip()}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload audio to element.fm")
    parser.add_argument("audio_file", help="Path to audio file (.m4a or .mp3)")
    parser.add_argument("--title", help="Episode title (auto-generated from filename if not set)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, don't upload")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout for JSON calls in seconds (default: 30)")
    parser.add_argument("--upload-timeout", type=float, default=900.0, help="Minimum upload timeout in seconds (default: 900)")
    args = parser.parse_args()

    if not API_KEY:
        print("❌ CLAUDE_ELEMENT_FM_KEY environment variable not set")
        sys.exit(1)

    audio_path = Path(args.audio_file).expanduser()
    if not audio_path.exists():
        print(f"❌ File not found: {audio_path}")
        sys.exit(1)

    title = args.title or parse_episode_title_from_filename(audio_path.name)
    client = ElementFmClient(
        ElementFmConfig(
            api_key=API_KEY,
            workspace_id=WORKSPACE_ID,
            show_id=SHOW_ID,
            base_url=BASE_URL,
        ),
        timeout_s=args.timeout,
        upload_timeout_s=args.upload_timeout,
    )
    episode_number = client.get_next_episode_number()

    print(f"""
┌─────────────────────────────────────────────┐
│  element.fm Upload                          │
└─────────────────────────────────────────────┘
  File:     {audio_path.name}
  Title:    {title}
  Episode:  #{episode_number}
  Dry run:  {args.dry_run}
""")

    if args.dry_run:
        print("  Dry run — stopping here.")
        return

    # Step 1: Convert to MP3 if needed
    if audio_path.suffix.lower() != ".mp3":
        print(f"  Converting {audio_path.suffix} → .mp3 ...", end=" ", flush=True)
        with tempfile.TemporaryDirectory() as td:
            mp3_path = Path(td) / (audio_path.stem + ".mp3")
            convert_to_mp3(audio_path, mp3_path)
            print("✓")
            _create_upload_publish(client, title, episode_number, mp3_path)
            return
    else:
        mp3_path = audio_path
        _create_upload_publish(client, title, episode_number, mp3_path)


def _create_upload_publish(client: ElementFmClient, title: str, episode_number: int, mp3_path: Path) -> None:
    # Step 2: Create episode
    print("  Creating episode ...", end=" ", flush=True)
    desc = elementfm_episode_description(title)
    episode = client.create_episode(
        title=title,
        season_number=1,
        episode_number=episode_number,
        description=desc,
    )
    if "error" in episode:
        print(f"\n  ❌ Create failed: {episode['error']}")
        sys.exit(1)
    episode_id = episode.get("id")
    if not episode_id:
        print("\n  ❌ Create failed: missing episode id")
        sys.exit(1)
    print(f"✓ ({episode_id})")

    # Step 3: Upload audio
    print("  Uploading audio ...", end=" ", flush=True)
    result = client.upload_audio(episode_id=episode_id, mp3_path=mp3_path)
    if "error" in result:
        print(f"\n  ❌ Upload failed: {result['error']}")
        sys.exit(1)
    print("✓")

    # Step 4: Description + publish (element.fm requires description)
    patch = client.patch_episode(episode_id=episode_id, data={"description": desc})
    if "error" in patch:
        print(f"\n  ⚠️  Could not set description: {patch['error']}")

    print("  Publishing ...", end=" ", flush=True)
    result = client.publish_episode(episode_id=episode_id)
    if "error" in result:
        print(f"\n  ⚠️  Publish failed: {result['error']}")
        print("     Episode created and audio uploaded — publish manually in element.fm")
    else:
        print("✓")

    print(f"""
  ✅ Done!
  Episode: {title}
  View at: https://app.element.fm/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}/episodes/{episode_id}
""")


if __name__ == "__main__":
    main()
