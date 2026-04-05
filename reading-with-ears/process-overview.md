# DHK Daily Brief — Process Overview

Authoritative architecture and repo↔machine policy: **[docs/current-design.md](docs/current-design.md)** (5 Apr 2026).

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Labeled Gmail emails | Gmail MCP | Fetched by label (`newsletter/news`, `newsletter/think`, `newsletter/pro`) — no star required |
| Starred Gmail emails | Gmail MCP | Fallback search for unlabeled starred emails (to-do triage only) |
| Date | CLI arg or default (today) | Controls which notebooks and audio files are targeted |
| `CLAUDE_ELEMENT_FM_KEY` | `~/.zshrc` | Required for Element.fm upload |
| `~/.config/reading-with-ears/config.json` | Config file | Sets `audio_dir`, `audio_format`, optional `repo_root`, `sync_mode` (`symlink` default in repo example / script fallback, or `copy`) |
| `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json` | State file | Idempotency — tracks what's been uploaded/published |

---

## Newsletter Label System

Gmail filters auto-label incoming newsletters. **Canonical labels per show** live in [`config/feeds.json`](config/feeds.json) under each feed’s `gmail_labels`. Only feeds with **`"enabled": true`** participate in automation; Phase 2 processes the same feeds’ **`slug`** values (see `enabled_slugs_ordered()` in `podcast_config.py`). Adding a show (e.g. **AI is for Everybody**) = add/update a feed entry, set `enabled`, ensure `gmail_labels` and `elementfm_show_id`, then run the pipeline — no hardcoded slug list in code.

These labels are the primary eligibility gate — no starring required.

| Label | Senders |
|---|---|
| `newsletter/news` | sanfrancisco@axios.com, email@washingtonpost.com, dailydigest@email.join1440.com, hello@newsletter.thedispatch.com, newsletters@theatlantic.com |
| `newsletter/think` | noahpinion@substack.com, yaschamounk@substack.com, persuasion1+francis-fukuyama@substack.com, opinionatedintelligence@substack.com, post+the-weekender@substack.com |
| `newsletter/pro` | ai.plus@axios.com, dan@tldrnewsletter.com, pragmaticengineer+deepdives@substack.com, lenny@substack.com, newsletter@towardsdatascience.com, hello@mindstream.news, thecode@mail.joinsuperhuman.ai, marketing-team@motherduck.com, info@theinformation.com, marcussawyerr@substack.com |

To add a new newsletter: create a Gmail filter for its sender, apply the appropriate label, and add it to the registry at `reading-with-ears/data/newsletter_sender_registry.json`.

---

## Phase 1 — Email Triage + Audio Generation (reading-with-ears skill)

Runs via Claude (`claude -p`) with **Gmail** and **NotebookLM** MCPs.

### Steps

1. **Fetch emails** — primary: `gmail_search_messages` for labeled emails on the target date; fallback: `gmail_search_messages` for starred emails (for triage / to-do classification, not exported to a task app)
2. **Read each email** — `gmail_read_message` for full content
3. **Classify** each email into one of four categories:
   - 📰 News & Current Affairs → NotebookLM (label hint: `newsletter/news`)
   - 🧠 Things to Think About → NotebookLM (label hint: `newsletter/think`)
   - 💼 Professional Reading → NotebookLM (label hint: `newsletter/pro`)
   - 📋 To-Do → **report only** in triage and closing summary (unlabeled starred emails default here; no Todoist or other task integration)
4. **Show triage table** and wait for confirmation *(interactive only — skipped in automated/cron mode)*
5. **Create NotebookLM notebooks** — one per non-empty read category, named `reading-list-YYYY-MM-DD-NN 📰 Category`
6. **Add sources** — each email body added as a text source (`source_add`)
7. **Generate audio** — `studio_create` per notebook with:
   - `audio_format: deep_dive`
   - `audio_length: long`
   - Focus prompt: *"This episode should run approximately 12 minutes. Open with the 3-5 most important ideas or takeaways across all the sources — give me the signal first. Then go deeper on each piece in turn. Close with any commentary, opinions, or open questions raised in the material. Prioritize insight over summary."*
8. **Poll for completion** — `studio_status` until done
9. **Title & describe each episode** — `notebook_describe` to get AI summary, then `studio_status(action="rename")` to set title with bullet-point key ideas and sources line
10. **Download audio** — `download_artifact` to iCloud Personal Podcast folder

### Outputs

- Up to 3 NotebookLM notebooks
- Up to 3 audio files in `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/`
  - Named `YYYY-MM-DD-news.mp3`, `YYYY-MM-DD-think.mp3`, `YYYY-MM-DD-professional.mp3`
- Each audio episode titled with: NotebookLM auto-title + 3-5 insight bullets + sources line
- To-do items listed in the skill output only (handle in Gmail)
- Updated `reading-with-ears/data/newsletter_sender_registry.json`

---

## Phase 2 — Upload to Element.fm (publish_episodes.py)

Runs as a Python script after Phase 1 completes.

### Steps

1. **Check manifest** — skip any slugs already published
2. **Find notebooks** — `nlm notebook list`, match by date and category name
3. **Wait for studio audio** — polls `nlm studio status` until ready (up to 15 min)
4. **Download audio** — `nlm download audio` to iCloud folder (skips if file exists)
5. **Wait for files** — rolling-window file watch before uploading
6. **Upload to Element.fm** — per episode, **each slug goes to its own show** (UUIDs in [`config/feeds.json`](config/feeds.json), overridable via `~/.config/reading-with-ears/feeds.json`):
   - Create episode (or reuse existing by title) on that slug’s show
   - Upload MP3
   - Set description (uses episode title with bullets and sources from Phase 1)
   - Publish

### Outputs

- Up to 3 published episodes across **three Element.fm shows** (news / think / professional)
- Updated manifest at `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json`

---

## Automation

- **Trigger:** launchd at 6:00am local time daily (see [`docs/install.md`](docs/install.md) — use Pacific timezone on the Mac for 6am PT)
- **Script:** `~/bin/rwe-run.sh` (versioned under repo [`bin/rwe-run.sh`](../bin/rwe-run.sh))
- **Guard:** checks manifest before running — exits early if all 3 episodes already published
- **Skill sync:** [`scripts/install-local.sh`](scripts/install-local.sh) deploys `SKILL.md` and all `scripts/*.py` to `~/.local/share/reading-with-ears/` by **symlink** (default) or **copy** (`sync_mode` / `--copy`); runs at the start of each `rwe-run.sh` and optionally from git hooks after pull
- **Headless MCP config:** [`automation/mcp-headless.json`](automation/mcp-headless.json) (passed to `claude -p --strict-mcp-config`)
- **Repo resolution for `~/bin` copies:** `RWE_REPO` or `repo_root` in `~/.config/reading-with-ears/config.json` (see [`config/config.example.json`](config/config.example.json))
- **Optional git hooks:** repo [`.githooks/`](../.githooks/) — set `git config core.hooksPath .githooks` to run sync after pull/checkout
- **Logs:** `~/logs/reading-with-ears/YYYY-MM-DD.log` (and `launchd.log` for launchd stdout/stderr)

---

## Key Parameters

| Parameter | Current value | Where set |
|---|---|---|
| Audio format | `deep_dive` | SKILL.md |
| Audio length | `long` | SKILL.md |
| Target duration | ~12 minutes | SKILL.md focus prompt |
| Output file format | `mp3` | `~/.config/reading-with-ears/config.json` |
| Audio output dir | iCloud Personal Podcast | `~/.config/reading-with-ears/config.json` |
| Slugs processed | `news`, `think`, `professional` | `publish_episodes.py` default |
| Max wait for studio | 15 minutes | `publish_episodes.py` default |
| Poll interval | 20 seconds | `publish_episodes.py` default |
| Element.fm shows | One UUID per slug | [`config/feeds.json`](config/feeds.json) (`load_feeds_publish_config` in `podcast_config.py`) |

---

## Category → Slug Mapping

| Category | Emoji | Slug | Notebook suffix | Gmail label |
|---|---|---|---|---|
| News & Current Affairs | 📰 | `news` | `-01` | `newsletter/news` |
| Things to Think About | 🧠 | `think` | `-02` | `newsletter/think` |
| Professional Reading | 💼 | `professional` | `-03` | `newsletter/pro` |

---

## File Locations

| File | Path |
|---|---|
| Repo (source of truth) | `…/reading-with-ears/reading-with-ears/` |
| Bin entrypoints (source of truth) | `…/reading-with-ears/bin/rwe-run.sh`, `…/reading-with-ears/bin/rwe-publish`, `…/reading-with-ears/bin/rwe-common.sh` |
| Sync script | `reading-with-ears/scripts/install-local.sh` |
| launchd plist template | `reading-with-ears/com.dhk.reading-with-ears.plist` (`__HOME__` → install with `sed`) |
| Live skill (deployed by sync) | `~/.local/share/reading-with-ears/skills/user/reading-with-ears/SKILL.md` |
| Live Python (deployed by sync) | `~/.local/share/reading-with-ears/scripts/*.py` |
| Installed bin (optional copy) | `~/bin/rwe-run.sh`, `~/bin/rwe-publish`, `~/bin/rwe-common.sh` |
| Config | `~/.config/reading-with-ears/config.json` |
| Manifest | `~/.local/state/reading-with-ears/manifest-YYYY-MM-DD.json` |
| Logs | `~/logs/reading-with-ears/YYYY-MM-DD.log` |
| Audio output | `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/` |
| Sender registry | `reading-with-ears/data/newsletter_sender_registry.json` (in repo) |
