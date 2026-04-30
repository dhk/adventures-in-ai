# Reading with Ears — context for Claude Code

**Purpose:** Paste this file or `@`-reference it when working in this repo in Claude Code. It complements **`docs/current-design.md`** (architecture) and **`docs/install.md`** (setup).

**Product:** **Reading with Ears** — *Your newsletter inbox, as a podcast.* Labeled Gmail → NotebookLM (per feed) → audio → **`publish_episodes.py`** → Element.fm. Listening: RSS in any podcast app.

---

## Repo layout (typical)

- **`reading-with-ears/`** — project root *inside* a parent monorepo clone (e.g. `adventures-in-ai/reading-with-ears/`) **or** a standalone `reading-with-ears` clone. Parent contains **`bin/`** (`rwe-run.sh`, `rwe-publish`, `rwe-common.sh`) when using the bundled layout.
- **`reading-with-ears/config/feeds.json`** — `workspace_id`, optional defaults, **`feeds[]`**: `slug`, `enabled`, `show_name`, `elementfm_show_id`, `gmail_labels`, `notebook_category`, `notebook_order`, `audio_focus_prompt`.
- **`reading-with-ears/skills/user/reading-with-ears/SKILL.md`** — Claude skill **`reading-with-ears`**: Phase 1 (Gmail + NotebookLM MCPs). **In scope:** labeled newsletter mail only (OR of `gmail_labels` on enabled feeds). **Out of scope:** task apps, Todoist, to-do triage buckets — do not extend the skill there.
- **`reading-with-ears/scripts/`** — `publish_episodes.py`, `podcast_config.py`, `install-local.sh`, `elementfm_client.py`, etc.
- **`reading-with-ears/automation/mcp-headless.json`** — MCP config for **`claude -p --strict-mcp-config`** (scheduled runs).

---

## Two phases

| Phase | What | How |
|-------|------|-----|
| **1** | Triage + NotebookLM notebooks + studio audio + download to disk | **`reading-with-ears`** skill via **`claude -p`** (see `bin/rwe-run.sh` for exact flags). Uses Gmail + NotebookLM MCPs. |
| **2** | Wait/download via **`nlm`**, MP3 sanity, upload/publish to Element.fm | **`publish_episodes.py`** (plain Python, no MCP). Reads **`feeds.json`** (override: `~/.config/reading-with-ears/feeds.json`). |

**Episode filenames:** `YYYY-MM-DD-<slug>.mp3` in configured `audio_dir` (often iCloud “Personal Podcast”).

**Element.fm episode titles (current behavior):** **`{show_name} - YYYY-MM-DD`** from each feed’s **`show_name`** in `feeds.json` — *not* `reading list - <slug> - <date>`. Slugs with hyphens (e.g. `vital-signs`) are parsed as a whole slug.

---

## Operations you’ll touch

- **Sync skill + scripts to the machine:**  
  `reading-with-ears/scripts/install-local.sh`  
  Optional: `…/install-local.sh --install-bin` → `~/bin/rwe-run.sh`, `rwe-publish`, etc. Default deploy is **symlink** into the clone (`sync_mode` / `RWE_SYNC_MODE`).

- **Full daily run (Phase 1 + 2):**  
  `~/bin/rwe-run.sh` (runs `install-local.sh`, optional manifest short-circuit, `claude -p` with skill prompt + `mcp-headless.json`, then `publish_episodes.py`). **Do not** rely on sourcing `~/.zshrc` from bash for this script — PATH for `claude` / `python3` / `nlm` must work non-interactively (`~/.profile`, launchd `EnvironmentVariables`, etc.).

- **Phase 2 only:**  
  `rwe-publish` or `python3 …/publish_episodes.py` (see `install.md`).

- **Logs / state:**  
  `~/logs/reading-with-ears/` · manifests `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json`

---

## Config precedence (short)

- **`~/.config/reading-with-ears/config.json`** — `repo_root`, `audio_dir`, `audio_format`, `sync_mode`.
- **`~/.config/reading-with-ears/feeds.json`** — if present, overrides bundled **`reading-with-ears/config/feeds.json`** for feeds + `workspace_id`.
- **Env:** `CLAUDE_ELEMENT_FM_KEY` (Element.fm API), optional `RWE_REPO`, `RWE_SYNC_MODE`, `RWE_AUDIO_DIR`.

---

## Code pointers

- **Which slugs run:** `podcast_config.enabled_slugs_ordered()` — driven by **`"enabled": true`** feeds with a slug.
- **Slug ↔ show / title:** `slug_to_show_name`, `parse_episode_title_from_filename`, `parse_date_and_slug_from_stem`, `parse_slug_date_from_episode_title` in **`podcast_config.py`**.
- **Tidy old Element.fm titles:** `scripts/tidy_elementfm_shows.py` (dry-run / `--apply`).

---

## External prerequisites

- **Claude Code CLI** + OAuth for Gmail MCP (user scope for headless) and whatever NotebookLM MCP your stack uses.
- **`nlm login`** for NotebookLM CLI (token expires periodically).
- **ffmpeg** for MP3 conversion when uploads need real MP3.

---

## Authoritative docs (deeper detail)

1. **`docs/current-design.md`** — symlink vs copy, GitHub vs laptop, parameterization, architecture sketch.  
2. **`docs/install.md`** — launchd plist, MCP registration, migration from old `dhk-daily-brief` names.  
3. **`process-overview.md`** — operational narrative (may lag slightly; trust **`current-design.md`** + code for numbers).  
4. **`README.md`** (under `reading-with-ears/`) — quick orientation.

When changing behavior, update the **skill** and **`podcast_config` / `publish_episodes`** together if titles, slugs, or feeds are involved.
