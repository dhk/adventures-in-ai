# DHK Daily Brief — Process Overview

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Labeled Gmail emails | Gmail MCP | Fetched by label (`newsletter/news`, `newsletter/think`, `newsletter/pro`) — no star required |
| Starred Gmail emails | Gmail MCP | Fallback search for unlabeled starred emails (to-do triage only) |
| Date | CLI arg or default (today) | Controls which notebooks and audio files are targeted |
| `CLAUDE_ELEMENT_FM_KEY` | `~/.zshrc` | Required for Element.fm upload |
| `~/.config/dhk-daily-brief/config.json` | Config file | Sets `audio_dir` and `audio_format` |
| `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json` | State file | Idempotency — tracks what's been uploaded/published |

---

## Newsletter Label System

Gmail filters auto-label incoming newsletters into three categories. These labels are the primary eligibility gate — no starring required.

| Label | Senders |
|---|---|
| `newsletter/news` | sanfrancisco@axios.com, email@washingtonpost.com, dailydigest@email.join1440.com, hello@newsletter.thedispatch.com, newsletters@theatlantic.com |
| `newsletter/think` | noahpinion@substack.com, yaschamounk@substack.com, persuasion1+francis-fukuyama@substack.com, opinionatedintelligence@substack.com, post+the-weekender@substack.com |
| `newsletter/pro` | ai.plus@axios.com, dan@tldrnewsletter.com, pragmaticengineer+deepdives@substack.com, lenny@substack.com, newsletter@towardsdatascience.com, hello@mindstream.news, thecode@mail.joinsuperhuman.ai, marketing-team@motherduck.com, info@theinformation.com, marcussawyerr@substack.com |

To add a new newsletter: create a Gmail filter for its sender, apply the appropriate label, and add it to the registry at `dhk-daily-brief/data/newsletter_sender_registry.json`.

---

## Phase 1 — Email Triage + Audio Generation (reading-list-builder skill)

Runs via Claude (`claude -p`) with Gmail, Todoist, and NotebookLM MCPs.

### Steps

1. **Fetch emails** — primary: `gmail_search_messages` for labeled emails on the target date; fallback: `gmail_search_messages` for starred emails (to-do triage only)
2. **Read each email** — `gmail_read_message` for full content
3. **Classify** each email into one of four categories:
   - 📰 News & Current Affairs → NotebookLM (label hint: `newsletter/news`)
   - 🧠 Things to Think About → NotebookLM (label hint: `newsletter/think`)
   - 💼 Professional Reading → NotebookLM (label hint: `newsletter/pro`)
   - 📋 To-Do → Todoist (unlabeled starred emails default here)
4. **Show triage table** and wait for confirmation *(interactive only — skipped in automated/cron mode)*
5. **Create Todoist task** — one grouped task in "Today Pile" for all to-dos
6. **Create NotebookLM notebooks** — one per non-empty read category, named `reading-list-YYYY-MM-DD-NN 📰 Category`
7. **Add sources** — each email body added as a text source (`source_add`)
8. **Generate audio** — `studio_create` per notebook with:
   - `audio_format: deep_dive`
   - `audio_length: long`
   - Focus prompt: *"This episode should run approximately 12 minutes. Open with the 3-5 most important ideas or takeaways across all the sources — give me the signal first. Then go deeper on each piece in turn. Close with any commentary, opinions, or open questions raised in the material. Prioritize insight over summary."*
9. **Poll for completion** — `studio_status` until done
10. **Title & describe each episode** — `notebook_describe` to get AI summary, then `studio_status(action="rename")` to set title with bullet-point key ideas and sources line
11. **Download audio** — `download_artifact` to iCloud Personal Podcast folder

### Outputs

- Up to 3 NotebookLM notebooks
- Up to 3 audio files in `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/`
  - Named `YYYY-MM-DD-news.mp3`, `YYYY-MM-DD-think.mp3`, `YYYY-MM-DD-professional.mp3`
- Each audio episode titled with: NotebookLM auto-title + 3-5 insight bullets + sources line
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
   - Set description (uses episode title with bullets and sources from Phase 1)
   - Publish

### Outputs

- Up to 3 published episodes on Element.fm / DHK Daily Brief podcast
- Updated manifest at `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json`

---

## Automation

- **Trigger:** launchd at 6:00am local time daily (see [`docs/install.md`](docs/install.md) — use Pacific timezone on the Mac for 6am PT)
- **Script:** `~/bin/run-reading-list.sh` (versioned under repo [`bin/run-reading-list.sh`](../bin/run-reading-list.sh))
- **Guard:** checks manifest before running — exits early if all 3 episodes already published
- **Skill sync:** [`scripts/sync-to-local.sh`](scripts/sync-to-local.sh) copies `SKILL.md` and all `scripts/*.py` from the repo to `~/.local/share/dhk-daily-brief/` at the start of each run (and can be run manually or from git hooks)
- **Headless MCP config:** [`automation/mcp-headless.json`](automation/mcp-headless.json) (passed to `claude -p --strict-mcp-config`)
- **Repo resolution for `~/bin` copies:** `DHK_DAILY_BRIEF_REPO` or `repo_root` in `~/.config/dhk-daily-brief/config.json` (see [`config/config.example.json`](config/config.example.json))
- **Optional git hooks:** repo [`.githooks/`](../.githooks/) — set `git config core.hooksPath .githooks` to run sync after pull/checkout
- **Logs:** `~/logs/reading-list/YYYY-MM-DD.log` (and `launchd.log` for launchd stdout/stderr)

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

| Category | Emoji | Slug | Notebook suffix | Gmail label |
|---|---|---|---|---|
| News & Current Affairs | 📰 | `news` | `-01` | `newsletter/news` |
| Things to Think About | 🧠 | `think` | `-02` | `newsletter/think` |
| Professional Reading | 💼 | `professional` | `-03` | `newsletter/pro` |

---

## File Locations

| File | Path |
|---|---|
| Repo (source of truth) | `…/adventures-in-ai/dhk-daily-brief/` |
| Bin entrypoints (source of truth) | `…/adventures-in-ai/bin/run-reading-list.sh`, `…/adventures-in-ai/bin/daily-brief`, `…/adventures-in-ai/bin/dhk-common.sh` |
| Sync script | `dhk-daily-brief/scripts/sync-to-local.sh` |
| launchd plist template | `dhk-daily-brief/com.dhk.reading-list.plist` (`__HOME__` → install with `sed`) |
| Live skill (deployed by sync) | `~/.local/share/dhk-daily-brief/skills/user/reading-list-builder/SKILL.md` |
| Live Python (deployed by sync) | `~/.local/share/dhk-daily-brief/scripts/*.py` |
| Installed bin (optional copy) | `~/bin/run-reading-list.sh`, `~/bin/daily-brief`, `~/bin/dhk-common.sh` |
| Config | `~/.config/dhk-daily-brief/config.json` |
| Manifest | `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json` |
| Logs | `~/logs/reading-list/YYYY-MM-DD.log` |
| Audio output | `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/` |
| Sender registry | `dhk-daily-brief/data/newsletter_sender_registry.json` (in repo) |
