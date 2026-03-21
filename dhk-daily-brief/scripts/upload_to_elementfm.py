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
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY      = os.environ.get("CLAUDE_ELEMENT_FM_KEY")
WORKSPACE_ID = "b08a0951-94a4-441d-a446-81cc7950749c"
SHOW_ID      = "d5be8d71-5fe3-4d2c-b641-0cd7343e4e36"
BASE_URL     = f"https://app.element.fm/api/workspaces/{WORKSPACE_ID}/shows/{SHOW_ID}"

# ── Helpers ───────────────────────────────────────────────────────────────────

def api(method, path, **kwargs):
    """Make an authenticated API call, return parsed JSON."""
    import urllib.request, urllib.error
    url = BASE_URL + path
    data = kwargs.get("data")
    files = kwargs.get("files")

    if files:
        # Multipart upload
        boundary = "----ElementFMBoundary"
        body_parts = []
        for name, (filename, filedata, content_type) in files.items():
            body_parts.append(
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f'Content-Type: {content_type}\r\n\r\n'.encode() +
                filedata +
                b'\r\n'
            )
        body = b''.join(
            p if isinstance(p, bytes) else p.encode()
            for p in body_parts
        ) + f'--{boundary}--\r\n'.encode()
        headers = {
            "Authorization": f"Token {API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
    elif data:
        body = json.dumps(data).encode()
        headers = {
            "Authorization": f"Token {API_KEY}",
            "Content-Type": "application/json",
        }
    else:
        body = None
        headers = {"Authorization": f"Token {API_KEY}"}

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return json.loads(err)
        except Exception:
            print(f"  HTTP {e.code}: {err[:200]}")
            sys.exit(1)


def parse_title(filename):
    """Turn '2026-03-21-news.m4a' into a readable episode title."""
    stem = Path(filename).stem
    parts = stem.split("-")
    category_map = {
        "news":         "📰 News & Current Affairs",
        "think":        "🧠 Things to Think About",
        "professional": "💼 Professional Reading",
    }
    if len(parts) >= 4:
        try:
            date = datetime.strptime(f"{parts[0]}-{parts[1]}-{parts[2]}", "%Y-%m-%d")
            slug = parts[3].lower()
            category = category_map.get(slug, " ".join(parts[3:]).title())
            return f"{category} — {date.strftime('%b %d, %Y')}"
        except ValueError:
            pass
    return stem.replace("-", " ").replace("_", " ").title()


def get_next_episode_number():
    """Get current episode count and return next number."""
    result = api("GET", "/episodes")
    return result.get("total_episodes", 0) + 1


def convert_to_mp3(input_path, output_path):
    """Convert audio file to MP3 using ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-codec:a", "libmp3lame", "-qscale:a", "3",
        "-loglevel", "error",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload audio to element.fm")
    parser.add_argument("audio_file", help="Path to audio file (.m4a or .mp3)")
    parser.add_argument("--title", help="Episode title (auto-generated from filename if not set)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, don't upload")
    args = parser.parse_args()

    if not API_KEY:
        print("❌ CLAUDE_ELEMENT_FM_KEY environment variable not set")
        sys.exit(1)

    audio_path = Path(args.audio_file).expanduser()
    if not audio_path.exists():
        print(f"❌ File not found: {audio_path}")
        sys.exit(1)

    title = args.title or parse_title(audio_path.name)
    episode_number = get_next_episode_number()

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
        mp3_path = Path(tempfile.mkdtemp()) / (audio_path.stem + ".mp3")
        convert_to_mp3(audio_path, mp3_path)
        print("✓")
    else:
        mp3_path = audio_path

    # Step 2: Create episode
    print("  Creating episode ...", end=" ", flush=True)
    episode = api("POST", "/episodes", data={
        "title": title,
        "season_number": 1,
        "episode_number": episode_number,
    })
    episode_id = episode["id"]
    print(f"✓ ({episode_id})")

    # Step 3: Upload audio
    print("  Uploading audio ...", end=" ", flush=True)
    with open(mp3_path, "rb") as f:
        audio_data = f.read()

    result = api("POST", f"/episodes/{episode_id}/audio", files={
        "audio": (mp3_path.name, audio_data, "audio/mpeg")
    })
    if "error" in result:
        print(f"\n  ❌ Upload failed: {result['error']}")
        sys.exit(1)
    print("✓")

    # Step 4: Publish
    print("  Publishing ...", end=" ", flush=True)
    result = api("POST", f"/episodes/{episode_id}/publish")
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

    # Cleanup temp mp3 if we created one
    if audio_path.suffix.lower() != ".mp3" and mp3_path.exists():
        mp3_path.unlink()


if __name__ == "__main__":
    main()
