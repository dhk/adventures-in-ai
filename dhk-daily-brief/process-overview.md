# DHK Daily Brief — Process Overview

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Starred Gmail emails | Gmail MCP | Fetched for today (or a date range) |
| Date | CLI arg or default (today) | Controls which notebooks and audio files are targeted |
| `CLAUDE_ELEMENT_FM_KEY` | `~/.zshrc` | Required for Element.fm upload |
| `~/.config/dhk-daily-brief/config.json` | Config file | Sets `audio_dir` and `audio_format` |
| `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json` | State file | Idempotency — tracks what's been uploaded/published |

---

## Phase 1 — Email Triage + Audio Generation (reading-list-builder skill)

Runs via Claude (`claude -p`) with Gmail, Todoist, and NotebookLM MCPs.

### Steps

1. **Fetch emails** — `gmail_search_messages` for starred emails on the target date
2. **Read each email** — `gmail_read_message` for full content
3. **Classify** each email into one of four categories:
   - 📰 News & Current Affairs → NotebookLM
   - 🧠 Things to Think About → NotebookLM
   - 💼 Professional Reading → NotebookLM
   - 📋 To-Do → Todoist
4. **Show triage table** and wait for confirmation *(interactive only — skipped in automated/cron mode)*
5. **Create Todoist task** — one grouped task in "Today Pile" for all to-dos
6. **Create NotebookLM notebooks** — one per non-empty read category, named `reading-list-YYYY-MM-DD-NN 📰 Category`
7. **Add sources** — each email body added as a text source (`source_add`)
8. **Generate audio** — `studio_create` per notebook with:
   - `audio_format: deep_dive`
   - `audio_length: long`
   - Focus prompt targeting ~12 minutes
9. **Poll for completion** — `studio_status` until done
10. **Download audio** — `download_artifact` to iCloud Personal Podcast folder

### Outputs

- Up to 3 NotebookLM notebooks
- Up to 3 audio files in `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/`
  - Named `YYYY-MM-DD-news.mp3`, `YYYY-MM-DD-think.mp3`, `YYYY-MM-DD-professional.mp3`
- 1 Todoist task in Today Pile (if any to-dos)
- Updated `dhk-daily-brief/data/newsletter_sender_registry.json`

---

## Phase 2 — Upload to Element.fm (daily_brief.py)

Runs as a Python script after Phase 1 completes.

### Steps

1. **Check manifest** — skip any slugs already published
2. **Find notebooks** — `nlm notebook list`, match by date and category name
3. **Wait for studio audio** — polls `nlm studio status` until ready (up to 15 min)
4. **Download audio** — `nlm download audio` to iCloud folder (skips if file exists)
5. **Wait for files** — rolling-window file watch before uploading
6. **Upload to Element.fm** — per episode:
   - Create episode (or reuse existing by title)
   - Upload MP3
   - Set description
   - Publish

### Outputs

- Up to 3 published episodes on Element.fm / DHK Daily Brief podcast
- Updated manifest at `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json`

---

## Automation

- **Trigger:** launchd at 6:00am PT daily
- **Script:** `~/bin/run-reading-list.sh`
- **Guard:** checks manifest before running — exits early if all 3 episodes already published
- **Skill sync:** copies `SKILL.md` and all Python scripts from repo to `~/.local/share/` and `~/.config/` at start of each run (launchd can't read `~/Documents` directly)
- **Logs:** `~/logs/reading-list/YYYY-MM-DD.log`

---

## Key Parameters

| Parameter | Current value | Where set |
|---|---|---|
| Audio format | `deep_dive` | SKILL.md |
| Audio length | `long` | SKILL.md |
| Target duration | ~12 minutes | SKILL.md focus prompt |
| Output file format | `mp3` | `~/.config/dhk-daily-brief/config.json` |
| Audio output dir | iCloud Personal Podcast | `~/.config/dhk-daily-brief/config.json` |
| Slugs processed | `news`, `think`, `professional` | `daily_brief.py` default |
| Max wait for studio | 15 minutes | `daily_brief.py` default |
| Poll interval | 20 seconds | `daily_brief.py` default |
| Element.fm show | DHK Daily Brief | hardcoded in `daily_brief.py` |

---

## Category → Slug Mapping

| Category | Emoji | Slug | Notebook suffix |
|---|---|---|---|
| News & Current Affairs | 📰 | `news` | `-01` |
| Things to Think About | 🧠 | `think` | `-02` |
| Professional Reading | 💼 | `professional` | `-03` |
