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

### Config file (optional)

By default the scripts use the iCloud “Personal Podcast” folder:

- `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast`

You can override this by creating:

- `~/.config/dhk-daily-brief/config.json`

Example:

```json
{
  "audio_dir": "/Users/dhk/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast",
  "audio_format": "mp3"
}
```

Precedence:

- CLI `--audio-dir ...` (highest)
- `~/.config/dhk-daily-brief/config.json` `"audio_dir"`
- `DHK_DAILY_BRIEF_AUDIO_DIR` env var
- Default iCloud folder (lowest)

Audio format:

- Supported: `mp3`, `m4a`
- Default: `mp3`
- CLI override: `--audio-format mp3|m4a`

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

### `daily_brief.py`

End-to-end runner: finds NotebookLM reading-list notebooks for a date, downloads audio via `nlm`, and uploads to element.fm.

```bash
python3 scripts/daily_brief.py
python3 scripts/daily_brief.py --date 2026-03-19
python3 scripts/daily_brief.py --download-only
python3 scripts/daily_brief.py --upload-only
python3 scripts/daily_brief.py --audio-dir "/path/to/podcasts"
python3 scripts/daily_brief.py --audio-format mp3
python3 scripts/daily_brief.py --upload-only --wait-for-audio --max-wait-minutes 15 --poll-interval-seconds 20
python3 scripts/daily_brief.py --wait-for-studio-status --max-wait-minutes 20 --poll-interval-seconds 20
```

Default behavior now includes both waits:

- `--wait-for-studio-status` is ON by default
- `--wait-for-audio` is ON by default

Opt out when needed:

```bash
python3 scripts/daily_brief.py --no-wait-for-studio-status
python3 scripts/daily_brief.py --no-wait-for-audio
```

Large MP3 uploads to element.fm may need a longer timeout than JSON calls. Use `--upload-timeout` (default 900s); each upload also scales from file size up to 1 hour.

The script writes a per-date manifest for idempotency at:

- `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json`

Upload-only waiting behavior:

- `--wait-for-audio` enables rolling-window waiting for `YYYY-MM-DD-<slug>.<format>` files.
- It waits up to `--max-wait-minutes` for a first file.
- Whenever a new file appears, the timer resets for another `--max-wait-minutes`.
- If no new file appears within a window, it proceeds with files found so far.

NotebookLM status waiting (recommended when downloading in the same run):

- `--wait-for-studio-status` polls `nlm studio status <notebook_id> --json`.
- It first waits for matching `reading-list-YYYY-MM-DD-NN ...` notebooks to appear.
- It waits up to `--max-wait-minutes` for studio readiness per notebook.
- Notebooks not ready by timeout are skipped (reported in output).

Combined guard mode:

- Use both `--wait-for-studio-status` and `--wait-for-audio` in the same run.
- The pipeline first waits for NotebookLM studio readiness.
- After download, it applies the rolling quiet-window file wait before upload.

### Cleanup mode

Dry-run (show what would be deleted):

```bash
python3 scripts/daily_brief.py --cleanup-old
```

Actually delete:

```bash
python3 scripts/daily_brief.py --cleanup-old --cleanup-apply
```

Optional cutoff date (default: today):

```bash
python3 scripts/daily_brief.py --cleanup-old --cleanup-cutoff-date 2026-03-20
```

Cleanup behavior:
- Deletes local podcast audio files older than the cutoff date (matching `YYYY-MM-DD-<slug>.mp3|m4a`).
- Deletes NotebookLM `reading-list-*` notebooks older than the cutoff date only when a downloaded audio file exists for that notebook’s date+category.

Newsletter tracking for label migration:

- Sender registry file: `dhk-daily-brief/data/newsletter_sender_registry.json`
- Updated by the `reading-list-builder` skill during starred triage runs.

### `suggest_gmail_label_filters.py`

Reads the sender registry and ranks likely newsletter senders to help migrate from starred-based triage to a Gmail label workflow.

```bash
# default suggestions
python3 scripts/suggest_gmail_label_filters.py

# stricter threshold + include one copy/paste OR query
python3 scripts/suggest_gmail_label_filters.py --min-count 3 --top 20 --emit-or-query

# bias toward one listening category
python3 scripts/suggest_gmail_label_filters.py --preferred-category think
```

### `personal_podcast_rss.py`

Local RSS feed server — serves your iCloud Personal Podcast folder as a podcast
feed. Alternative to element.fm for Overcast on same WiFi.

```bash
python3 ~/scripts/personal_podcast_rss.py
# Then subscribe in Overcast to: http://<your-mac-ip>:8765/feed.rss
```

Optional overrides:

```bash
python3 ~/scripts/personal_podcast_rss.py --audio-dir "/path/to/podcasts" --port 8765
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
