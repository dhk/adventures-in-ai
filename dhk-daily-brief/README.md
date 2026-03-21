# DHK Daily Brief — From Inbox to Earbuds

A personal AI-powered podcast pipeline that converts my daily reading list into
audio episodes, published to [element.fm](https://element.fm) and available in
Overcast and Apple Podcasts.

---

## How It Works

```
Starred Gmail
     ↓
NotebookLM notebooks (per category, via Claude + MCP)
     ↓
Audio Overview generated (NotebookLM)
     ↓
nlm CLI download → iCloud Personal Podcast folder
     ↓
upload_to_elementfm.py → element.fm "DHK Daily Brief" show
     ↓
Overcast / Apple Podcasts (via RSS)
```

---

## Episode Categories

| File | Category | Description |
|------|----------|-------------|
| `YYYY-MM-DD-news.m4a` | 📰 News & Current Affairs | Dispatches, news digests, current events |
| `YYYY-MM-DD-think.m4a` | 🧠 Things to Think About | Opinion, analysis, ideas, economics, culture |
| `YYYY-MM-DD-professional.m4a` | 💼 Professional Reading | Industry, technical, career-relevant content |

---

## Setup

### Prerequisites

- macOS with zsh
- Python 3
- [ffmpeg](https://ffmpeg.org) (`brew install ffmpeg`)
- [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) (`uv tool install notebooklm-mcp-cli`)
- An [element.fm](https://element.fm) account with a show created
- Claude Desktop with MCP integrations: Gmail, NotebookLM, Todoist

### Environment Variables

Add to `~/.zshrc`:

```zsh
export CLAUDE_ELEMENT_FM_KEY='your-element-fm-api-key'
```

Then reload: `source ~/.zshrc`

### Install Scripts

```bash
cp scripts/upload_to_elementfm.py ~/scripts/
cp scripts/personal_podcast_rss.py ~/scripts/
```

---

## Scripts

### `upload_to_elementfm.py`

Converts a `.m4a` audio file to `.mp3`, creates an episode on element.fm, uploads
the audio, and publishes it.

```bash
# Upload and publish
python3 ~/scripts/upload_to_elementfm.py \
  "/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/2026-03-21-news.m4a"

# Custom title
python3 ~/scripts/upload_to_elementfm.py \
  "/path/to/file.m4a" --title "Custom Episode Title"

# Dry run
python3 ~/scripts/upload_to_elementfm.py \
  "/path/to/file.m4a" --dry-run

# Upload all of today's episodes
DATE="$(date +%Y-%m-%d)"
BASE="/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast"
for cat in news think professional; do
  python3 ~/scripts/upload_to_elementfm.py "$BASE/${DATE}-${cat}.m4a"
done
```

### `personal_podcast_rss.py`

Local RSS feed server — serves your iCloud Personal Podcast folder as a podcast
feed. Alternative to element.fm for Overcast on same WiFi.

```bash
python3 ~/scripts/personal_podcast_rss.py
# Then subscribe in Overcast to: http://<your-mac-ip>:8765/feed.rss
```

---

## element.fm Config

| Setting | Value |
|---------|-------|
| Show | DHK Daily Brief — From Inbox to Earbuds |
| Show ID | `d5be8d71-5fe3-4d2c-b641-0cd7343e4e36` |
| Workspace ID | `b08a0951-94a4-441d-a446-81cc7950749c` |
| API Auth | `Authorization: Token $CLAUDE_ELEMENT_FM_KEY` |
| API Base | `https://app.element.fm/api/workspaces/{workspace_id}/shows/{show_id}` |

### element.fm API Endpoints

```
GET    /episodes                     → list episodes
POST   /episodes                     → create episode
GET    /episodes/{id}                → get episode
PATCH  /episodes/{id}                → update episode metadata
POST   /episodes/{id}/audio          → upload audio (multipart, MP3 only)
POST   /episodes/{id}/publish        → publish episode
```

---

## Audio Download (NotebookLM CLI)

MCP `download_artifact` fails due to Google auth cookie requirements.
Use the `nlm` CLI directly:

```bash
nlm download audio "<notebook-id>" \
  --output "/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/YYYY-MM-DD-news.m4a"
```

---

## Claude Skills

The `skills/` directory contains Claude skill files that drive the automated
pipeline via Claude Desktop + MCP integrations.

| Skill | Trigger | Description |
|-------|---------|-------------|
| `reading-list-builder` | "process my starred emails" | Triages Gmail → NotebookLM → Todoist |
| `personal-podcast` | "upload my podcasts" | Uploads audio to element.fm |

To install, copy the `skills/user/` directory to your Claude skills path.

---

## Listening

- **Overcast**: Subscribe via element.fm RSS feed URL (in show settings → Distribution)
- **Apple Podcasts**: Submit RSS feed at [podcasters.apple.com](https://podcasters.apple.com) (one-time, 24-48hr approval)

---

## Artwork

`docs/podcast-cover.svg` — 1400×1400 podcast cover art. Convert to PNG for upload:

```bash
# ImageMagick
magick docs/podcast-cover.svg docs/podcast-cover.png

# Or open in browser and export
```

---

## Part of: Adventures in AI

This project lives in the [adventures-in-ai](https://github.com/dhk/adventures-in-ai)
repo — a collection of personal AI workflow experiments by DHK.
