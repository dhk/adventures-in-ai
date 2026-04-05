# DHK Daily Brief — System Context Document

**Owner:** Dave Holmes-Kinsella (davehk@gmail.com)
**Last updated:** April 1, 2026
**Purpose:** Share this document with another LLM to provide full context on the DHK Daily Brief system — what it is, how it works, and how to operate it.

**Stale:** Todoist integration and some MCP details were removed or superseded after this snapshot — see **`docs/current-design.md`**.

---

## What This Is

The **DHK Daily Brief** pipeline turns **labeled Gmail newsletters** (plus starred non-newsletter mail for to-do triage) into up to **three category-specific NotebookLM audio overviews** (~12 minutes each), then downloads MP3s and publishes to **Element.fm**.

**Primary eligibility:** Gmail labels `newsletter/news`, `newsletter/think`, `newsletter/pro` (no star required). **Fallback:** starred threads for to-do classification.

The repo lives under **reading-with-ears** (`reading-with-ears/`). **Source of truth:** git; **deployed copies:** `~/.local/share/reading-with-ears/` (skill + Python), optional `~/bin` wrappers — refreshed by `scripts/install-local.sh` and at the start of each `rwe-run.sh` run.

---

## Element.fm — Workspace and Shows

**Workspace ID:** `b08a0951-94a4-441d-a446-81cc7950749c`

**API token:** env var `CLAUDE_ELEMENT_FM_KEY` (e.g. in `~/.zshrc`).

Canonical feed + show metadata for all podcasts: **[`config/feeds.json`](config/feeds.json)** in the repo (mirror to `~/.config/reading-with-ears/feeds.json` when multi-feed upload is wired).

| Editorial title | Slug | Element.fm show ID |
|---|---|---|
| News: Signal from Noise | `news` | `d5be8d71-5fe3-4d2c-b641-0cd7343e4e36` |
| Thinking: Threads & Deep Dives | `think` | `626ef543-291a-4919-8712-ae685dd55b26` |
| Professional: The Stack | `professional` | `01a6981c-6888-4d51-9471-f3258a98b13e` |
| AI is for Everybody | `ai-everybody` | `4bd34c62-f7d3-45bc-82ac-9b63a00751cd` |

The fourth feed is **disabled** in `feeds.json` until Gmail/skill routing exists.

**RSS (per show):** `https://cdn.element.fm/b08a0951-94a4-441d-a446-81cc7950749c/<SHOW_ID>/rss.xml`

**Upload routing:** `scripts/publish_episodes.py` loads **`workspace_id` and per-slug `elementfm_show_id`** from [`config/feeds.json`](config/feeds.json) (or `~/.config/reading-with-ears/feeds.json` if present). Each of `news`, `think`, and `professional` uploads to its own show. Legacy manifests (everything on the old news show) are **migrated** on load so think/professional get fresh episode IDs on the correct shows.

**Apple Podcasts:** After publish, refresh the feed in [Podcasts Connect](https://podcastsconnect.apple.com) if episodes look stuck.

---

## How It Works — End to End

Two phases:

1. **Email triage + audio generation** — `reading-with-ears` Claude skill (interactive or headless via `claude -p`)
2. **Audio download + Element.fm publishing** — `scripts/publish_episodes.py` (Python; often chained after Phase 1 by `rwe-run.sh`)

---

### Phase 1: Email Triage → NotebookLM (`reading-with-ears` skill)

#### Step 1: Fetch and classify

**Primary (newsletters):**
```
gmail_search_messages(q="(label:newsletter/news OR label:newsletter/think OR label:newsletter/pro) after:YYYY/MM/DD")
```

**Fallback (to-dos, starred):**
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

Deduplicate by message ID. Starred mail **without** a newsletter label is treated as **To-Do** by default.

| Category | Icon | Destination |
|---|---|---|
| News & Current Affairs | 📰 | NotebookLM |
| Things to Think About | 🧠 | NotebookLM |
| Professional Reading | 💼 | NotebookLM |
| To-Do | 📋 | Todoist Today Pile |

Interactive runs show a triage table and wait for confirmation. **Automated** runs (`rwe-run.sh`): prompt instructs the model to proceed without waiting for user confirmation after internal triage.

#### Step 2: To-Dos → Todoist

Single grouped task in **Today Pile** (create project if missing: orange, favorited).

#### Step 3: To-Reads → NotebookLM

One notebook per non-empty read category. **Naming convention** (required for Phase 2 matching in `publish_episodes.py` / `podcast_config.py`):

```
reading-list-YYYY-MM-DD-NN CATEGORY_EMOJI Category Name
```

Examples:
- `reading-list-2026-03-21-01 📰 News & Current Affairs`
- `reading-list-2026-03-21-02 🧠 Things to Think About`
- `reading-list-2026-03-21-03 💼 Professional Reading`

`studio_create` uses `audio_format="deep_dive"`, `audio_length="long"`, plus the ~12-minute focus prompt in the skill.

#### Step 4: Download audio to iCloud

Target folder (configurable):  
`~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/`

**Filenames:** `YYYY-MM-DD-<slug>.<ext>` — slugs `news`, `think`, `professional`.

---

### Phase 2: Element.fm publishing (`publish_episodes.py`)

Runs after Phase 1 (or standalone). Prefers the synced copy at `~/.local/share/reading-with-ears/scripts/publish_episodes.py` when installed; wrapper **`rwe-publish`** on `PATH` does the same.

```bash
rwe-publish                              # today
rwe-publish --date 2026-03-19
rwe-publish --download-only
rwe-publish --upload-only
rwe-publish --dry-run
rwe-publish --show-status
```

**Behaviors:** wait for notebooks / studio audio (defaults), rolling file wait before upload, **manifest** at `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json` for idempotency, ffmpeg m4a→mp3 if needed, episode numbering for Apple.

**Workspace / shows in code:** `load_feeds_publish_config()` in `podcast_config.py` → `ElementFmClient` per slug during upload.

---

## Repo Layout and Automation (April 2026)

| Item | Role |
|---|---|
| [`bin/rwe-run.sh`](../bin/rwe-run.sh) | launchd/manual: `install-local.sh` → manifest short-circuit → `claude -p` → `publish_episodes.py` |
| [`bin/rwe-publish`](../bin/rwe-publish) | Invokes synced or in-tree `publish_episodes.py` |
| [`bin/rwe-common.sh`](../bin/rwe-common.sh) | Resolves repo root: `RWE_REPO`, or `repo_root` in `~/.config/reading-with-ears/config.json`, or in-repo `bin/` layout |
| [`reading-with-ears/scripts/install-local.sh`](scripts/install-local.sh) | Copies skill + `scripts/*.py` → `~/.local/share/reading-with-ears/`; `--install-bin` refreshes `~/bin` |
| [`reading-with-ears/automation/mcp-headless.json`](automation/mcp-headless.json) | MCP JSON for `claude -p --strict-mcp-config` |
| [`reading-with-ears/com.dhk.reading-with-ears.plist`](com.dhk.reading-with-ears.plist) | launchd template (`__HOME__` → replace when installing) |
| [`.githooks/post-merge`](../.githooks/post-merge), [`.githooks/post-checkout`](../.githooks/post-checkout) | Optional: run `install-local.sh` after pull / branch checkout (`git config core.hooksPath .githooks`) |

**Logs:** `~/logs/reading-with-ears/YYYY-MM-DD.log` (script tee), `~/logs/reading-with-ears/launchd.log` (plist stdio after install).

**Install / operator steps:** [`docs/install.md`](docs/install.md), design reference [`process-overview.md`](process-overview.md).

---

## Supporting Scripts

### `scripts/elementfm_client.py`
REST client for Element.fm (auth, retries, multipart upload, create/patch/publish).

### `scripts/podcast_config.py`
Audio path resolution, manifest paths, **`parse_reading_list_notebook_title()`** (expects `reading-list-YYYY-MM-DD-NN …` prefix), filename/slug parsing, episode description helpers.

### `scripts/subprocess_utils.py`
Subprocess helper with timeout and exponential backoff.

### `scripts/upload_to_elementfm.py`
One-off upload helper (same single show IDs as `publish_episodes.py` unless updated).

### `scripts/suggest_gmail_label_filters.py`
Uses `data/newsletter_sender_registry.json` to suggest Gmail filter queries.

### `scripts/personal_podcast_rss.py`
Local RSS server for the Personal Podcast folder (e.g. port 8765).

---

## Configuration

### `~/.config/reading-with-ears/config.json`
Keys include `audio_dir`, `audio_format`, and optionally **`repo_root`** (for `~/bin` wrappers when `RWE_REPO` is unset). Example: [`config/config.example.json`](config/config.example.json).

### Environment variables
| Variable | Purpose |
|---|---|
| `CLAUDE_ELEMENT_FM_KEY` | Element.fm API token |
| `RWE_REPO` | Root of reading-with-ears clone (parent of `reading-with-ears/`) |
| `RWE_AUDIO_DIR` | Override audio directory |

---

## MCP Integrations

| Service | Transport | Used for |
|---|---|---|
| Gmail | HTTP MCP | Search/read mail |
| NotebookLM | stdio via `uvx --from notebooklm-mcp-cli notebooklm-mcp` | Notebooks, sources, studio audio |
| Todoist | HTTP MCP | Today Pile tasks |

Headless runs load MCP only from **`automation/mcp-headless.json`** (not from `~/.claude.json` alone). **Known issue:** HTTP MCPs may not load in `-p` without `--mcp-config` / `--strict-mcp-config` as used in `rwe-run.sh`.

---

## Automation Setup (launchd)

**Schedule:** 6:00 **local** system time (see install doc for Pacific). **Label:** `com.dhk.reading-with-ears`. **Program:** `/bin/bash -lc 'exec "$HOME/bin/rwe-run.sh"'`.

Reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.dhk.reading-with-ears.plist
launchctl load ~/Library/LaunchAgents/com.dhk.reading-with-ears.plist
launchctl list | grep com.dhk.reading-with-ears
```

---

## Operating Manually (Claude.ai)

Triggers: e.g. “build my reading list”, “run my email triage”. Skill id: **`reading-with-ears`**.

Then run **`rwe-publish`** (or `python3 …/publish_episodes.py`) for Element.fm when audio is ready.

---

## Edge Cases & Known Behaviors

- **No matching mail:** Skill reports and stops (may suggest widening the date range).
- **HTML-only bodies:** Use subject + snippet; note `[body unavailable]` where applicable.
- **All reads or all to-dos:** Skip Todoist or NotebookLM branches as appropriate.
- **Tool call limits:** Report partial progress for follow-up turns.
- **Duplicate Apple episode numbers:** Breaks directory display; fix in Element.fm + refresh in Podcasts Connect.
- **Studio timeout:** Adjust `--max-wait-minutes` or `--no-wait-for-studio-status`.
- **`nlm` auth:** Re-login periodically when tokens expire.

---

## Cleanup

```bash
rwe-publish --cleanup-old
rwe-publish --cleanup-old --cleanup-apply
rwe-publish --cleanup-old --cleanup-cutoff-date 2026-03-01
```

Deletes old local audio and matching NotebookLM notebooks when safe (see script help).

---

## User Context

- **Name:** Dave (DHK) · **Email:** davehk@gmail.com
- **Work:** DHK Consulting; Substack “dhkondata”; Synctera-related consulting
- **Stack:** Claude.ai, Claude Code, Todoist, NotebookLM, Element.fm
- **Style:** Concrete tasks, aggressive cleanup when appropriate; direct tone, minimal meta-commentary

---

## Related Docs (repo)

- [`process-overview.md`](process-overview.md) — parameters, category ↔ slug ↔ label mapping
- [`docs/current-design.md`](docs/current-design.md) — current architecture; [`docs/archive/prior-multi-feed-design-2026-04.md`](docs/archive/prior-multi-feed-design-2026-04.md) — archived multi-feed detail
- [`docs/install.md`](docs/install.md) — prerequisites, plist install, hooks
- [`docs/context.md`](docs/context.md) — narrative history of the project
