# DHK Daily Brief — System Context Document

**Owner:** Dave Holmes-Kinsella (davehk@gmail.com)
**Last updated:** March 24, 2026
**Purpose:** Share this document with another LLM to provide full context on the DHK Daily Brief system — what it is, how it works, and how to operate it.

---

## What This Is

The **DHK Daily Brief** is a personal podcast system that automatically converts Dave's starred Gmail newsletters into categorized, AI-generated audio episodes (~12 minutes each). It runs daily, either manually via Claude.ai or on a schedule via Claude Code + cron.

The podcast is published at:
- **RSS feed:** `https://cdn.element.fm/b08a0951-94a4-441d-a446-81cc7950749c/d5be8d71-5fe3-4d2c-b641-0cd7343e4e36/rss.xml`
- **Show page:** `https://shows.element.fm/show/daily-thinking`
- **Hosting platform:** Element.fm
- **Listed in:** Apple Podcasts (show title: "DHK Daily Brief")

---

## How It Works — End to End

The pipeline has two distinct phases:

1. **Email triage + audio generation** — handled by the `reading-list-builder` Claude skill (interactive or cron)
2. **Audio download + Element.fm publishing** — handled by `scripts/daily_brief.py` (separate Python script)

---

### Phase 1: Email Triage → NotebookLM (reading-list-builder skill)

#### Step 1: Email Triage (Gmail → Classification)

The workflow fetches all starred emails from Gmail for today (or a specified date range):
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

Each email is read in full, then classified into one of four categories:

| Category | Icon | Destination |
|---|---|---|
| News & Current Affairs | 📰 | NotebookLM notebook |
| Things to Think About | 🧠 | NotebookLM notebook |
| Professional Reading | 💼 | NotebookLM notebook |
| To-Do | 📋 | Todoist Today Pile |

**To-Do signals:** action requests, replies needed, deadlines, SENT emails starred for follow-up, receipts/invoices, subject patterns like "Re:", "Action required", "Following up".

**Ambiguity rule:** Default to To-Do if any action is implied, even loosely.

When run interactively (via Claude.ai), a triage table is shown for user approval before anything is created. The user can reclassify items. When run automated (via cron), the triage step is skipped and the workflow proceeds directly.

#### Step 2: To-Dos → Todoist

To-do emails are added as a **single grouped task** to the "Today Pile" project in Todoist:

```
add-tasks([{
  content: "📬 Email triage — YYYY-MM-DD",
  projectId: <Today Pile ID>,
  description: "• \"<subject>\" — <sender/note>\n• ...",
  dueString: "today",
  priority: "p3"
}])
```

If the Today Pile project doesn't exist, it's created automatically (orange, favorited).

#### Step 3: To-Reads → NotebookLM

One NotebookLM notebook is created per non-empty read category, named:
- `reading-list-YYYY-MM-DD-01 📰 News & Current Affairs`
- `reading-list-YYYY-MM-DD-02 🧠 Things to Think About`
- `reading-list-YYYY-MM-DD-03 💼 Professional Reading`

Each email is added as a text source (`source_add`, `wait=True`). Bodies are truncated to ~8,000 characters if very long.

After all sources are loaded, an audio overview is generated for each notebook:
```
studio_create(
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="Open with the 3-5 most important ideas or takeaways across all the
    sources — give me the signal first. Then go deeper on each piece in turn. Close
    with any commentary, opinions, or open questions raised in the material. Prioritize
    insight over summary. Target roughly 12 minutes of content."
)
```

#### Step 4: Download Audio to iCloud

After audio generation completes (polled via `studio_status`), each audio file is downloaded to the iCloud Personal Podcast folder:

```
~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/
```

Filename convention: `YYYY-MM-DD-<slug>.mp3`
- `2026-03-21-news.mp3`
- `2026-03-21-think.mp3`
- `2026-03-21-professional.mp3`

Category slugs: `news`, `think`, `professional`

---

### Phase 2: Element.fm Publishing (daily_brief.py)

The `scripts/daily_brief.py` script handles downloading audio from NotebookLM via the `nlm` CLI and uploading to Element.fm. It runs separately from the skill — either manually or via cron after audio generation completes.

**Basic usage:**
```bash
python3 scripts/daily_brief.py                   # full pipeline for today
python3 scripts/daily_brief.py --date 2026-03-19 # specific date
python3 scripts/daily_brief.py --download-only   # nlm download only, skip upload
python3 scripts/daily_brief.py --upload-only     # upload only (files already exist)
python3 scripts/daily_brief.py --dry-run         # preview without doing anything
```

**Key behaviors:**
- Waits for NotebookLM notebooks to appear (`--wait-for-studio-status`, on by default)
- Polls `nlm studio status` until audio generation completes
- Rolling-window file wait for downloaded audio before uploading
- Idempotent: per-date manifest at `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json` tracks episode IDs, upload and publish status — safe to re-run
- Auto-converts m4a → mp3 via ffmpeg if needed

**Important RSS note:** Each episode must have a unique `<itunes:episode>` number. Duplicate episode numbers cause Apple Podcasts to suppress episodes from the directory listing. The script handles this automatically via `get_next_episode_number()`.

After publishing, force Apple Podcasts to re-crawl at:
`https://podcastsconnect.apple.com` → find the show → Refresh Feed.

**Element.fm API credentials:**
- Env var: `CLAUDE_ELEMENT_FM_KEY`
- Workspace ID: `b08a0951-94a4-441d-a446-81cc7950749c`
- Show ID: `d5be8d71-5fe3-4d2c-b641-0cd7343e4e36`

---

## Supporting Scripts

### `scripts/elementfm_client.py`
REST client for the Element.fm API. Handles authentication, retries with exponential backoff, multipart audio upload, episode create/patch/publish. Used by `daily_brief.py`.

### `scripts/podcast_config.py`
Configuration, parsing, and utility functions shared across scripts:
- `resolve_audio_dir()` — config precedence: CLI > `~/.config/dhk-daily-brief/config.json` > env var `DHK_DAILY_BRIEF_AUDIO_DIR` > iCloud default
- `resolve_audio_format()` — same precedence, default `mp3`
- `parse_episode_title_from_filename()` — e.g. `2026-03-21-news.mp3` → `📰 News & Current Affairs — Mar 21, 2026`
- `parse_reading_list_notebook_title()` — extracts date, nn, category from notebook name
- `manifest_path_for_date()` — `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json`

### `scripts/subprocess_utils.py`
Subprocess wrapper with configurable timeout and exponential-backoff retries. Returns a `RunResult` dataclass (returncode, stdout, stderr, attempts, elapsed).

### `scripts/upload_to_elementfm.py`
Standalone script to upload a single audio file to Element.fm (useful for one-off uploads or re-uploads). Wraps `elementfm_client.py`.

### `scripts/suggest_gmail_label_filters.py`
Reads `data/newsletter_sender_registry.json` and generates Gmail filter query suggestions ranked by frequency. Supports `--preferred-category`, `--min-count`, `--top`, `--emit-or-query`. Useful for migrating from starred-based workflow to label-based.

### `scripts/personal_podcast_rss.py`
Serves the iCloud Personal Podcast folder as a local RSS feed (default port 8765). Lets Overcast subscribe to the local feed before episodes are uploaded to Element.fm.

---

## Configuration

### `~/.config/dhk-daily-brief/config.json`
Optional JSON config file. Supported keys:
```json
{
  "audio_dir": "/path/to/audio",
  "audio_format": "mp3"
}
```

### Environment Variables
| Variable | Purpose |
|---|---|
| `CLAUDE_ELEMENT_FM_KEY` | Element.fm API token (required for upload) |
| `DHK_DAILY_BRIEF_AUDIO_DIR` | Override audio directory |

---

## Newsletter Sender Registry

The skill maintains a running registry at `dhk-daily-brief/data/newsletter_sender_registry.json`. For every non-to-do newsletter seen in triage, it tracks sender email/name, first/last seen, count, category usage, and recent subjects. Schema:

```json
{
  "version": 1,
  "updated_at": "ISO-8601",
  "senders": {
    "sender@example.com": {
      "name": "Newsletter Name",
      "email": "sender@example.com",
      "first_seen": "YYYY-MM-DD",
      "last_seen": "YYYY-MM-DD",
      "count": 12,
      "categories": {"news": 7, "think": 4, "professional": 1},
      "last_subject": "...",
      "subjects": ["...", "..."]
    }
  }
}
```

Use `suggest_gmail_label_filters.py` to turn this into Gmail filter query snippets.

---

## MCP Integrations Required

This workflow requires three MCP servers to be connected:

| Service | MCP URL | Used for |
|---|---|---|
| Gmail | `https://gmail.mcp.claude.com/mcp` | Fetching starred emails |
| Google NotebookLM | `notebooklm-mcp-cli` (local) | Creating notebooks, adding sources, generating audio |
| Todoist | `https://ai.todoist.net/mcp` | Adding to-do tasks to Today Pile |

---

## Automation Setup (launchd)

**Status as of March 24, 2026: fully configured and running.**

### Key files

| File | Purpose |
|---|---|
| `~/bin/run-reading-list.sh` | Main script invoked by launchd |
| `~/Library/LaunchAgents/com.dhk.reading-list.plist` | launchd job definition |
| `~/logs/reading-list/YYYY-MM-DD.log` | Per-run output log (written by the script) |
| `~/logs/reading-list/launchd.log` | stdout/stderr captured by launchd |

### Schedule

Runs at **6:00am PT daily** via launchd. System timezone is `America/Los_Angeles`.

launchd is preferred over cron on macOS because it wakes the machine from sleep to run jobs (or catches up when the machine wakes if it missed the scheduled time).

To reload after editing the plist:
```bash
launchctl unload ~/Library/LaunchAgents/com.dhk.reading-list.plist
launchctl load ~/Library/LaunchAgents/com.dhk.reading-list.plist
```

To check status:
```bash
launchctl list | grep com.dhk.reading-list
```

### What run-reading-list.sh does

1. Sources `~/.zshrc` to pick up `CLAUDE_ELEMENT_FM_KEY` and other env vars (cron/launchd run with a bare environment)
2. Runs the `reading-list-builder` skill headlessly via `claude -p`, passing MCP servers via `--mcp-config` inline JSON
3. Bails if the skill exits non-zero
4. Runs `daily_brief.py` to wait for studio audio, download via `nlm`, and upload to Element.fm

### MCP config (inline JSON in the run script)

**Known issue:** As of March 2026, HTTP-based MCP servers in `~/.claude.json` don't load in Claude Code's `-p` (headless) mode (GitHub issue #34131). The run script works around this by passing `--mcp-config` explicitly:

```json
{
  "mcpServers": {
    "gmail":      { "type": "http", "url": "https://gmail.mcp.claude.com/mcp" },
    "todoist":    { "type": "http", "url": "https://ai.todoist.net/mcp" },
    "notebooklm": { "type": "stdio", "command": "uvx", "args": ["--from", "notebooklm-mcp-cli", "notebooklm-mcp"] }
  }
}
```

The notebooklm MCP binary is `notebooklm-mcp` (not `notebooklm-mcp-cli`); invoke via `uvx --from notebooklm-mcp-cli notebooklm-mcp`.

---

## Operating the Workflow Manually (Claude.ai)

To trigger the workflow in Claude.ai, say any of:
- "create today's reading list"
- "process my starred emails"
- "run my email triage"
- "build my reading list"

The skill name is **`reading-list-builder`**.

**Interactive mode behavior:**
1. Fetches and reads all starred emails
2. Shows a triage table grouped by category
3. Waits for user confirmation (or reclassification requests)
4. Creates NotebookLM notebooks + generates audio
5. Adds any to-dos to Todoist Today Pile
6. Downloads audio to iCloud Personal Podcast folder
7. Reports back with notebook links and download status

Then run `daily_brief.py` separately to upload to Element.fm.

**User preferences established in prior sessions:**
- Audio length: ~12 minutes ("long" setting)
- Audio are referred to as "personal podcasts"
- Items can be excluded at the triage step (e.g. "cut Chuck Norris")
- Reclassification is supported — user can move items between categories before proceeding

---

## Notebook Naming Convention

```
reading-list-YYYY-MM-DD-NN CATEGORY_EMOJI Category Name
```

Examples:
- `reading-list-2026-03-21-01 📰 News & Current Affairs`
- `reading-list-2026-03-21-02 🧠 Things to Think About`
- `reading-list-2026-03-21-03 💼 Professional Reading`

If running for a date range, the end date (today) is used. If a notebook with today's date already exists, the numeric suffix is incremented (01 → 02 → 03).

---

## Audio File Naming Convention

```
YYYY-MM-DD-<slug>.<ext>
```

Slugs: `news`, `think`, `professional`
Extensions: `mp3` (default), `m4a`

Examples: `2026-03-21-news.mp3`, `2026-03-21-think.m4a`

---

## Edge Cases & Known Behaviors

- **No starred emails:** Report and stop. Offer to widen the date range.
- **HTML-only email body:** Use subject + snippet as source text; note "[body unavailable]" in the title.
- **All to-reads, no to-dos:** Skip Todoist entirely.
- **All to-dos, no to-reads:** Skip NotebookLM entirely.
- **Tool call limit hit mid-run:** Report exactly what was completed and what remains so the user can continue in the next turn.
- **Duplicate episode numbers in RSS:** Causes Apple Podcasts to suppress episodes. Fix in Element.fm, then force re-crawl via Podcasts Connect.
- **Studio audio not ready:** `daily_brief.py` will wait up to `--max-wait-minutes` (default 15) before timing out. Re-run with `--no-wait-for-studio-status` to skip the wait if audio is already ready.

---

## Cleanup

`daily_brief.py` supports a cleanup mode for housekeeping:
```bash
python3 daily_brief.py --cleanup-old                              # dry-run
python3 daily_brief.py --cleanup-old --cleanup-apply             # apply
python3 daily_brief.py --cleanup-old --cleanup-cutoff-date 2026-03-01
```

Deletes local audio files and NotebookLM notebooks older than the cutoff date. Notebooks are only deleted if a corresponding downloaded audio file exists (prevents data loss if a download was missed).

---

## User Context

- **Name:** Dave (goes by DHK)
- **Email:** davehk@gmail.com
- **Work:** DHK Consulting; Substack called "dhkondata" (data topics); consulting work with Synctera
- **Stack:** Claude.ai (claude.ai), Claude Desktop with MCP integrations, Todoist Pro, Google NotebookLM, Element.fm
- **Productivity style:** Prefers concrete over vague tasks, aggressive cleanup, knock-off-and-organize mode for lighter days
- **Tone preference:** Direct, no unnecessary hedging, skip the meta-commentary
