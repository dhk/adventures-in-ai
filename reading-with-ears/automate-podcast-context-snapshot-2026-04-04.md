# DHK Daily Brief — System Context Document

**Owner:** Dave Holmes-Kinsella (davehk@gmail.com)
**Last updated:** April 4, 2026
**Purpose:** Share this document with another LLM to provide full context on the DHK Daily Brief system — what it is, how it works, and how to operate it.

---

## Revision notes (April 2026)

- **Gmail intake:** Production automation uses **Gmail labels** as the primary gate (`newsletter/news`, `newsletter/think`, `newsletter/pro`). Starred-email search remains for to-do triage and edge cases. See `process-overview.md` for the label → sender mapping table.
- **Headless MCP:** Scheduled runs use `claude -p --strict-mcp-config --mcp-config reading-with-ears/automation/mcp-headless.json` (not inline JSON in the shell script).
- **Multi-feed upload:** `scripts/publish_episodes.py` reads **`workspace_id` + per-slug `elementfm_show_id`** from `feeds.json` (`load_feeds_publish_config()` in `podcast_config.py`; prefers `~/.config/reading-with-ears/feeds.json`, else bundled `config/feeds.json`). Each slug uploads to its own Element.fm show. Legacy manifests are migrated so think/professional are not stuck on the old single-show episode IDs.
- **Operations:** Audio files living under **iCloud Drive** can cause **`TimeoutError` on `read_bytes()`** during upload if the OS has not fully materialized the file locally. A category with **no notebook** (empty bucket or title mismatch) produces warnings like *No NotebookLM notebook matched* / *No notebook found for slug* and that slug is skipped for the day.
- **Todoist removed:** To-do mail is **not** exported to Todoist or any task app — triage + final report only. **Authoritative doc:** `docs/current-design.md`.

---

## What This Is

The **DHK Daily Brief** is a personal podcast system that automatically converts Dave's labeled (and selectively starred) Gmail newsletters into categorized, AI-generated audio episodes (~12 minutes each). It runs daily, either manually via Claude.ai or on a schedule via Claude Code + launchd.

The podcasts are published on **Element.fm** (one show per daily slug). Example RSS pattern: `https://cdn.element.fm/b08a0951-94a4-441d-a446-81cc7950749c/<SHOW_ID>/rss.xml` — use the UUIDs in `config/feeds.json` (news / think / professional). Apple Podcasts: one listing per show (e.g. **News: Signal from Noise**, **Thinking: Threads & Deep Dives**, **Professional: The Stack**).

---

## How It Works — End to End

The pipeline has two distinct phases:

1. **Email triage + audio generation** — handled by the `reading-with-ears` Claude skill (interactive or launchd)
2. **Audio download + Element.fm publishing** — handled by `scripts/publish_episodes.py` (Python; can also be invoked as `rwe-publish` from `~/bin` after install)

---

### Phase 1: Email Triage → NotebookLM (reading-with-ears skill)

#### Step 1: Email Triage (Gmail → Classification)

The workflow fetches eligible emails for the target date. **Primary path:** `gmail_search_messages` for messages with the category labels (`newsletter/news`, `newsletter/think`, `newsletter/pro`). **Fallback / to-dos:** starred messages may still be searched where the skill needs to catch action items or unlabeled mail.

Each email is read in full, then classified into one of four categories:

| Category | Icon | Destination |
|---|---|---|
| News & Current Affairs | 📰 | NotebookLM notebook |
| Things to Think About | 🧠 | NotebookLM notebook |
| Professional Reading | 💼 | NotebookLM notebook |
| To-Do | 📋 | Report only (closing summary; handle in Gmail) |

**To-Do signals:** action requests, replies needed, deadlines, SENT emails starred for follow-up, receipts/invoices, subject patterns like "Re:", "Action required", "Following up".

**Ambiguity rule:** Default to To-Do if any action is implied, even loosely.

When run interactively (via Claude.ai), a triage table is shown for user approval before anything is created. The user can reclassify items. When run automated (via launchd), the skill is instructed with `AUTOMATED_MODE` to proceed without waiting for user confirmation.

**To-dos:** Do **not** call Todoist or any task MCP — list items in the triage table and Step 7 report only.

#### Step 2: To-Reads → NotebookLM

One NotebookLM notebook is created per non-empty read category, named:
- `reading-list-YYYY-MM-DD-01 📰 News & Current Affairs`
- `reading-list-YYYY-MM-DD-02 🧠 Things to Think About`
- `reading-list-YYYY-MM-DD-03 💼 Professional Reading`

Each email is added as a text source (`source_add`, `wait=True`). Bodies are truncated to ~8,000 characters if very long.

After all sources are loaded, an audio overview is generated for each notebook (focus prompt may be unified or per-feed as the skill evolves; `config/feeds.json` holds per-slug prompts for the multi-feed target state):

```
studio_create(
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="… ~12 minutes, insight-first …"
)
```

#### Step 3: Download Audio to iCloud

After audio generation completes (polled via `studio_status`), each audio file is downloaded to the iCloud Personal Podcast folder:

```
~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/
```

Filename convention: `YYYY-MM-DD-<slug>.mp3`
- `2026-04-04-news.mp3`
- `2026-04-04-think.mp3`
- `2026-04-04-professional.mp3`

Category slugs: `news`, `think`, `professional`

---

### Phase 2: Element.fm Publishing (publish_episodes.py)

The `scripts/publish_episodes.py` script handles downloading audio from NotebookLM via the `nlm` CLI and uploading to Element.fm. It runs separately from the skill — manually, via `rwe-publish`, or at the end of `rwe-run.sh`.

**Basic usage:**
```bash
python3 scripts/publish_episodes.py                   # full pipeline for today
python3 scripts/publish_episodes.py --date 2026-04-04 # specific date
python3 scripts/publish_episodes.py --download-only   # nlm download only, skip upload
python3 scripts/publish_episodes.py --upload-only     # upload only (files already exist)
python3 scripts/publish_episodes.py --dry-run         # preview without doing anything
# After `install-local.sh --install-bin`:
rwe-publish
rwe-publish --show-status
```

**Key behaviors:**
- Waits for NotebookLM notebooks to appear (`--wait-for-studio-status`, on by default)
- Polls `nlm studio status` until audio generation completes
- Rolling-window file wait for downloaded audio before uploading
- Idempotent: per-date manifest at `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json` tracks episode IDs, upload and publish status — safe to re-run
- Auto-converts m4a → mp3 via ffmpeg if needed

**Important RSS note:** Each episode must have a unique `<itunes:episode>` number. Duplicate episode numbers cause Apple Podcasts to suppress episodes from the directory listing. The script handles this automatically via `get_next_episode_number()`.

After publishing, force Apple Podcasts to re-crawl at:
`https://podcastsconnect.apple.com` → find the show → Refresh Feed.

**Element.fm API credentials:**
- Env var: `CLAUDE_ELEMENT_FM_KEY`
- Workspace + per-slug show UUIDs: **`config/feeds.json`** (or `~/.config/reading-with-ears/feeds.json`)
- **`publish_episodes.py`:** one `ElementFmClient` per slug during upload; episode numbers are per show

---

## Supporting Scripts

### `scripts/elementfm_client.py`
REST client for the Element.fm API. Handles authentication, retries with exponential backoff, multipart audio upload, episode create/patch/publish. Used by `publish_episodes.py`.

### `scripts/podcast_config.py`
Configuration, parsing, and utility functions shared across scripts:
- `resolve_audio_dir()` — config precedence: CLI > `~/.config/reading-with-ears/config.json` > env var `RWE_AUDIO_DIR` > iCloud default
- `resolve_audio_format()` — same precedence, default `mp3`
- `load_feeds_publish_config()` — `(workspace_id, slug → elementfm_show_id)` for enabled feeds
- `migrate_manifest_episodes_for_per_show_uploads()` — clears stale episode state when moving slugs to their own shows
- `parse_episode_title_from_filename()` — e.g. `2026-03-21-news.mp3` → display title
- `parse_reading_list_notebook_title()` — extracts date, nn, category from notebook name
- `manifest_path_for_date()` — `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json`

### `scripts/subprocess_utils.py`
Subprocess wrapper with configurable timeout and exponential-backoff retries. Returns a `RunResult` dataclass (returncode, stdout, stderr, attempts, elapsed).

### `scripts/upload_to_elementfm.py`
Standalone script to upload a single audio file to Element.fm (useful for one-off uploads or re-uploads). Wraps `elementfm_client.py`.

### `scripts/suggest_gmail_label_filters.py`
Reads `data/newsletter_sender_registry.json` and generates Gmail filter query suggestions ranked by frequency. Supports `--preferred-category`, `--min-count`, `--top`, `--emit-or-query`. Useful for migrating from starred-based workflow to label-based.

### `scripts/personal_podcast_rss.py`
Optional: serves the audio folder as HTTP RSS on a port (default 8765) for LAN testing. Primary listening is Element.fm / Apple Podcasts, not a local client.

---

## Configuration

### `~/.config/reading-with-ears/config.json`
Optional JSON config file. Supported keys:
```json
{
  "audio_dir": "/path/to/audio",
  "audio_format": "mp3",
  "repo_root": "/path/to/reading-with-ears"
}
```

### `reading-with-ears/config/feeds.json` (repo; multi-feed source of truth)
Canonical feed definitions: slugs, Element.fm show IDs, Gmail labels, notebook category strings, and per-feed `audio_focus_prompt`. Optional override: `~/.config/reading-with-ears/feeds.json`. See `docs/current-design.md` and archived `docs/archive/prior-multi-feed-design-2026-04.md`.

### Environment Variables
| Variable | Purpose |
|---|---|
| `CLAUDE_ELEMENT_FM_KEY` | Element.fm API token (required for upload) |
| `RWE_AUDIO_DIR` | Override audio directory |
| `RWE_REPO` | Repo root if not inferrable from `~/bin` layout |

---

## Newsletter Sender Registry

The skill maintains a running registry at `reading-with-ears/data/newsletter_sender_registry.json`. For every non-to-do newsletter seen in triage, it tracks sender email/name, first/last seen, count, category usage, and recent subjects. Schema:

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

This workflow requires **two** MCP servers in headless config:

| Service | MCP URL / command | Used for |
|---|---|---|
| Gmail | `https://gmail.mcp.claude.com/mcp` | Fetching labeled (and starred) emails |
| Google NotebookLM | `uvx --from notebooklm-mcp-cli notebooklm-mcp` (stdio) | Creating notebooks, adding sources, generating audio |

Headless definition file (repo): `reading-with-ears/automation/mcp-headless.json`.

---

## Automation Setup (launchd)

**Status as of April 2026:** Configured per `docs/install.md` — sync from repo, launchd at 6:00am local (Pacific on Dave's Mac).

### Key files

| File | Purpose |
|---|---|
| `~/bin/rwe-run.sh` | Main script invoked by launchd |
| `~/Library/LaunchAgents/com.dhk.reading-with-ears.plist` | launchd job definition |
| `~/logs/reading-with-ears/YYYY-MM-DD.log` | Per-run output log (written by the script) |
| `~/logs/reading-with-ears/launchd.log` | stdout/stderr captured by launchd |
| `reading-with-ears/bin/rwe-run.sh` | Versioned source (copied or synced to `~/bin`) |
| `reading-with-ears/automation/mcp-headless.json` | MCP servers for `claude -p` |

### Schedule

Runs at **6:00am PT daily** via launchd. System timezone is `America/Los_Angeles`.

launchd is preferred over cron on macOS because it wakes the machine from sleep to run jobs (or catches up when the machine wakes if it missed the scheduled time).

To reload after editing the plist:
```bash
launchctl unload ~/Library/LaunchAgents/com.dhk.reading-with-ears.plist
launchctl load ~/Library/LaunchAgents/com.dhk.reading-with-ears.plist
```

To check status:
```bash
launchctl list | grep com.dhk.reading-with-ears
```

### What rwe-run.sh does

1. Sources `~/.zshrc` to pick up `CLAUDE_ELEMENT_FM_KEY` and other env vars (launchd runs with a bare environment)
2. Runs `reading-with-ears/scripts/install-local.sh` (deploys skill + Python to `~/.local/share/reading-with-ears/`)
3. **Early exit:** If today's manifest already has all three slugs (`news`, `think`, `professional`) marked published, skips Phase 1 and Phase 2
4. Runs the `reading-with-ears` skill headlessly via `claude -p --strict-mcp-config --mcp-config …/automation/mcp-headless.json`
5. Bails if the skill exits non-zero
6. Runs `publish_episodes.py` (from synced `~/.local/share/...`) to wait for studio audio, download via `nlm`, and upload to Element.fm

### Headless MCP config

**Historical note:** HTTP-based MCP servers in `~/.claude.json` did not always load in Claude Code's `-p` mode; the repo pins MCP via `--mcp-config` + `automation/mcp-headless.json`.

The notebooklm MCP binary is `notebooklm-mcp` (not `notebooklm-mcp-cli`); invoke via `uvx --from notebooklm-mcp-cli notebooklm-mcp`.

---

## Operating the Workflow Manually (Claude.ai)

To trigger the workflow in Claude.ai, say any of:
- "create today's reading list"
- "process my starred emails"
- "run my email triage"
- "build my reading list"

The skill name is **`reading-with-ears`**.

**Interactive mode behavior:**
1. Fetches and reads eligible emails (labels + starred as designed by the skill)
2. Shows a triage table grouped by category
3. Waits for user confirmation (or reclassification requests)
4. Creates NotebookLM notebooks + generates audio
5. Downloads audio to iCloud Personal Podcast folder
6. Reports back with notebook links, download status, and any to-dos as text (no task app)

Then run `publish_episodes.py` / `rwe-publish` separately to upload to Element.fm.

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
- `reading-list-2026-04-04-01 📰 News & Current Affairs`
- `reading-list-2026-04-04-02 🧠 Things to Think About`
- `reading-list-2026-04-04-03 💼 Professional Reading`

If running for a date range, the end date (today) is used. If a notebook with today's date already exists, the numeric suffix is incremented (01 → 02 → 03).

---

## Audio File Naming Convention

```
YYYY-MM-DD-<slug>.<ext>
```

Slugs: `news`, `think`, `professional`
Extensions: `mp3` (default), `m4a`

Examples: `2026-04-04-news.mp3`, `2026-04-04-think.m4a`

---

## Edge Cases & Known Behaviors

- **No eligible emails:** Report and stop. Offer to widen the date range.
- **HTML-only email body:** Use subject + snippet as source text; note "[body unavailable]" in the title.
- **All to-reads, no to-dos:** Omit the to-do section from the report.
- **All to-dos, no to-reads:** Skip NotebookLM entirely.
- **Empty read category:** No notebook for that slug → `publish_episodes.py` skips it. **`rwe-run.sh` only skips the full run when all three slugs are marked published** in today's manifest — if one category is routinely empty (e.g. no `professional` episode), that guard never fires and Phase 1 still runs each morning until the script or manifest logic is adjusted.
- **Tool call limit hit mid-run:** Report exactly what was completed and what remains so the user can continue in the next turn.
- **Duplicate episode numbers in RSS:** Causes Apple Podcasts to suppress episodes. Fix in Element.fm, then force re-crawl via Podcasts Connect.
- **Studio audio not ready:** `publish_episodes.py` will wait up to `--max-wait-minutes` (default 15) before timing out. Re-run with `--no-wait-for-studio-status` to skip the wait if audio is already ready.
- **iCloud-backed audio path:** `TimeoutError` during `read_bytes()` on upload — ensure files are downloaded locally (open folder, or move off iCloud) and retry.
- **`nlm` auth:** Session expires periodically; run `nlm login` when downloads fail.

---

## Cleanup

`publish_episodes.py` supports a cleanup mode for housekeeping:
```bash
python3 publish_episodes.py --cleanup-old                              # dry-run
python3 publish_episodes.py --cleanup-old --cleanup-apply             # apply
python3 publish_episodes.py --cleanup-old --cleanup-cutoff-date 2026-03-01
```

Deletes local audio files and NotebookLM notebooks older than the cutoff date. Notebooks are only deleted if a corresponding downloaded audio file exists (prevents data loss if a download was missed).

---

## Deeper references (repo)

- `reading-with-ears/docs/current-design.md` — authoritative architecture (as of 5 Apr 2026)
- `reading-with-ears/process-overview.md` — phases, parameters, paths, automation details
- `reading-with-ears/docs/context.md` — narrative history and current gaps
- `reading-with-ears/docs/archive/prior-multi-feed-design-2026-04.md` — archived multi-feed migration detail

---

## User Context

- **Name:** Dave (goes by DHK)
- **Email:** davehk@gmail.com
- **Work:** DHK Consulting; Substack called "dhkondata" (data topics); consulting work with Synctera
- **Stack:** Claude.ai (claude.ai), Claude Code with Gmail + NotebookLM MCP, Google NotebookLM, Element.fm (Podbean used elsewhere historically; optional future)
- **Productivity style:** Prefers concrete over vague tasks, aggressive cleanup, knock-off-and-organize mode for lighter days
- **Tone preference:** Direct, no unnecessary hedging, skip the meta-commentary
