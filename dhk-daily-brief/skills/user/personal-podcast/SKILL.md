---
name: personal-podcast
description: >
  Upload NotebookLM audio overviews to element.fm as podcast episodes. Use when
  the user says anything like "upload my podcasts", "publish to element.fm",
  "upload the audio to my podcast", "push the reading list audio to element.fm",
  or "publish today's episodes". Triggers any time downloaded NotebookLM audio
  files need to be published to the "DHK Daily Brief" show on element.fm.
compatibility: "Requires: CLAUDE_ELEMENT_FM_KEY env var, ffmpeg, ~/scripts/upload_to_elementfm.py"
---

# Personal Podcast Pipeline

Uploads NotebookLM audio overviews to element.fm and publishes them as episodes
on the "DHK Daily Brief — From Inbox to Earbuds" show. Audio files are converted
from .m4a to .mp3 via ffmpeg before upload.

---

## Pipeline Overview

```
Starred Gmail
     ↓
NotebookLM notebooks (per category)
     ↓
Audio Overview generated
     ↓
nlm CLI download → ~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/
     ↓
upload_to_elementfm.py → element.fm "Daily Thinking" show
     ↓
Overcast / Apple Podcasts (via RSS feed)
```

---

## Key Config

| Item | Value |
|------|-------|
| Show | DHK Daily Brief — From Inbox to Earbuds |
| Show ID | `d5be8d71-5fe3-4d2c-b641-0cd7343e4e36` |
| Workspace ID | `b08a0951-94a4-441d-a446-81cc7950749c` |
| API Auth | `Authorization: Token $CLAUDE_ELEMENT_FM_KEY` |
| API Base | `https://app.element.fm/api/workspaces/{workspace_id}/shows/{show_id}` |
| Audio folder | `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/` |
| Upload script | `~/scripts/upload_to_elementfm.py` |
| nlm CLI | `nlm download audio <notebook_id> --output <path>` |

---

## Filename Convention

Downloaded audio files follow this naming pattern:

| Filename | Category | Episode Title |
|----------|----------|---------------|
| `YYYY-MM-DD-news.m4a` | 📰 News & Current Affairs | "📰 News & Current Affairs — Mon DD, YYYY" |
| `YYYY-MM-DD-think.m4a` | 🧠 Things to Think About | "🧠 Things to Think About — Mon DD, YYYY" |
| `YYYY-MM-DD-professional.m4a` | 💼 Professional Reading | "💼 Professional Reading — Mon DD, YYYY" |

---

## Upload Script Usage

```bash
# Single file upload
python3 ~/scripts/upload_to_elementfm.py \
  "/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/YYYY-MM-DD-news.m4a"

# With custom title
python3 ~/scripts/upload_to_elementfm.py \
  "/path/to/file.m4a" --title "Custom Episode Title"

# Dry run (preview without uploading)
python3 ~/scripts/upload_to_elementfm.py \
  "/path/to/file.m4a" --dry-run
```

The script will:
1. Convert `.m4a` → `.mp3` via ffmpeg
2. POST to `/episodes` to create the episode
3. POST audio file to `/episodes/{id}/audio`
4. POST to `/episodes/{id}/publish`

---

## element.fm API Reference

All endpoints require `Authorization: Token $CLAUDE_ELEMENT_FM_KEY`.

```
GET    /episodes                          → list episodes
POST   /episodes                          → create episode {title, season_number, episode_number}
GET    /episodes/{id}                     → get episode
PATCH  /episodes/{id}                     → update episode
POST   /episodes/{id}/audio              → upload audio (multipart, field: "audio", MP3 only)
POST   /episodes/{id}/publish            → publish episode
```

---

## Download via nlm CLI

If audio needs to be downloaded from NotebookLM first:

```bash
# Download by notebook ID
nlm download audio "<notebook-id>" \
  --output "/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/YYYY-MM-DD-news.m4a"
```

Note: The MCP `download_artifact` tool currently fails due to Google auth cookie
requirements. Use the `nlm` CLI directly from Terminal instead.

---

## Full Day Upload (all three categories)

```bash
DATE="2026-03-21"
BASE="/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast"

for cat in news think professional; do
  python3 ~/scripts/upload_to_elementfm.py "$BASE/${DATE}-${cat}.m4a"
done
```

---

## Listening

- **Overcast**: Subscribe via the element.fm RSS feed URL (find in show settings)
- **Apple Podcasts**: Submit the RSS feed at podcasters.apple.com (one-time setup)
- Once subscribed, new episodes appear automatically after publishing

---

## Edge Cases

- **MP3 only**: element.fm rejects non-MP3 files. The upload script handles conversion automatically via ffmpeg (`/opt/homebrew/bin/ffmpeg`)
- **Episode numbering**: Script auto-increments by fetching current episode count
- **Publish fails**: Usually means show author name is missing — add in element.fm show settings
- **Key not set**: Ensure `export CLAUDE_ELEMENT_FM_KEY='...'` is in `~/.zshrc` with no leading space, then `source ~/.zshrc`
- **Path spaces**: Always wrap the audio file path in double quotes
