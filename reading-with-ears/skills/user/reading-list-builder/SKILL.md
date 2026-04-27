---
name: reading-list-builder
description: >
  Deterministic newsletter pipeline. Gmail labels are the routing truth — no LLM
  classification, no approval gate. Fetches labeled emails, creates NotebookLM notebooks
  (one per day per label), generates audio overviews with per-feed prompts, titles each
  episode with key ideas, downloads the audio, and publishes to Element.fm. Use when user
  says "process my newsletters", "run the pipeline", "build my reading list", "triage my
  inbox", or similar. Handles today or a date range.
compatibility: "Requires: Gmail MCP (gmail_search_messages, gmail_read_message), NotebookLM MCP (notebook_create, source_add, studio_create, studio_status, notebook_describe), nlm CLI, ffmpeg, CLAUDE_ELEMENT_FM_KEY env var"
---

# Reading List Builder — Deterministic Pipeline

Four phases. Each phase completes fully before the next begins.
Labels ARE the routing. No classification step. No approval gate.

---

## Step 0 — Load Feeds Config

**Before any Gmail or NotebookLM step**, read `config/feeds.json` (at
`reading-with-ears/config/feeds.json` relative to the repo root; prefer
`~/.config/reading-with-ears/feeds.json` if readable — it takes precedence).

Extract from the top level:
- **`workspace_id`** — used in every Element.fm API call
- **`audio_dir`** — local download destination (e.g. `~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast`)

For each feed where **`"enabled": true`**, sorted by **`notebook_order`** ascending,
record: `slug`, `gmail_labels` (array), `notebook_category` (full title suffix with
emoji), `notebook_emoji`, `notebook_order`, `elementfm_show_id`, `audio_focus_prompt`.

Assign `nn` (zero-padded two digits) by position in the sorted enabled list: lowest
`notebook_order` → `01`, next → `02`, etc. This determines the notebook title suffix.

Note the **state directory**: `~/.local/state/reading-with-ears/` — used for per-feed
sentinel files that guard against duplicates on retry (see Phase 2 and Phase 4).

If no feeds are enabled, report and stop.

---

## Phase 1 — Fetch

If the user gives no date, use today. For a range, use the earliest day as the start.

Search each enabled feed's labels individually (one call per label — don't merge into
a union query, so each result stays associated with its feed):

```
gmail_search_messages(q="label:<gmail_label> after:YYYY/MM/DD")
```

Fetch every label across every enabled feed **before** doing anything else.

For each message ID returned, fetch the full message:
```
gmail_read_message(messageId=<id>)
```

**Record for each email:** received date, feed slug (from the label that matched),
subject, sender, body.

**HTML-only emails** (empty plain-text body, HTML-only note): skip entirely. Log
subject + sender for the Skipped section of the final report.

If zero emails total: report and stop.

---

## Phase 2 — Notebooks + Sources

Group emails by `(received_date × feed_slug)`. For each non-empty group, before doing
anything else, **check the per-feed sentinel**:

```bash
~/.local/state/reading-with-ears/done-YYYY-MM-DD-<slug>
```

If that file exists, this feed was already fully published in a previous run — skip it
entirely (no notebook, no sources, no audio, no upload). Log it as "already done" in
the final report.

For feeds without a sentinel, create one notebook using the `nn` assigned in Step 0:

**Create notebook:**
```
notebook_create(title="reading-list-YYYY-MM-DD-nn <notebook_category>")
```
Example with four enabled feeds:
- `reading-list-2026-04-27-01 📰 News & Current Affairs`
- `reading-list-2026-04-27-02 🧠 Things to Think About`
- `reading-list-2026-04-27-03 💼 Professional Reading`
- `reading-list-2026-04-27-04 🏥 Healthcare Reading`

If a notebook with that title already exists for the date, increment the suffix
(`-01` → `-01b`).

**Add each email as a text source. Process all sources for notebook 1 before
starting notebook 2:**
```
source_add(
  notebook_id=<id>,
  source_type="text",
  title="<subject> — <sender> (<date>)",
  text="From: <sender>\nDate: <date>\n\n<body truncated to 8000 chars>",
  wait=True
)
```

---

## Phase 3 — Audio, Titles & Download

After **all** notebooks have **all** their sources loaded, trigger audio generation
for all notebooks in parallel (one `studio_create` per notebook; don't wait between calls):

```
studio_create(
  notebook_id=<id>,
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="<audio_focus_prompt from feeds.json for this feed>",
  confirm=True
)
```

Poll each notebook with `studio_status` every 30 seconds until `status == "complete"`
(timeout: 10 minutes per notebook). Log any that time out and continue with the rest.

### Episode titling

Once a notebook's audio is complete, call `notebook_describe` to get the AI-generated
summary, then rename the artifact with a rich title, 3–5 insight-first bullets, and a
sources line:

```
notebook_describe(notebook_id=<id>)

studio_status(
  notebook_id=<id>,
  action="rename",
  artifact_id=<artifact_id>,
  new_title="<NotebookLM-generated title>\n\n• <key idea 1>\n• <key idea 2>\n• <key idea 3>\n\nSources: <Newsletter (topic)> · <Newsletter (topic)> · ..."
)
```

**Titling rules:**
- Keep NotebookLM's auto-generated title — don't replace it
- Bullets should state what something *means*, not what it *covers* — insight-first, not descriptive
- 3 bullets minimum, 5 maximum — don't pad
- Sources line: `Newsletter Name (topic shorthand) · ...`
- If audio is still `in_progress` when titling begins, poll `studio_status` until complete

### Download

After titling each episode, download via the `nlm` CLI to `audio_dir` from feeds.json:

```bash
nlm download audio <notebook_id> \
  --output "<audio_dir>/YYYY-MM-DD-<slug>.m4a"
```

Convert to MP3 if the file is `.m4a`:
```bash
ffmpeg -i "<audio_dir>/YYYY-MM-DD-<slug>.m4a" \
  -codec:a libmp3lame -q:a 2 \
  "<audio_dir>/YYYY-MM-DD-<slug>.mp3"
```

Skip download if `<audio_dir>/YYYY-MM-DD-<slug>.mp3` already exists (idempotency).

---

## Phase 4 — Publish to Element.fm

For each downloaded MP3, publish to the feed's own Element.fm show. Pull
`elementfm_show_id` and `workspace_id` from feeds.json per feed. Upload one at a time.

**Step 1 — Create episode** (JSON body):
```bash
curl -s -X POST \
  "https://app.element.fm/api/workspaces/<workspace_id>/shows/<elementfm_show_id>/episodes" \
  -H "Authorization: Token $CLAUDE_ELEMENT_FM_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "<notebook title>", "season_number": 1, "episode_number": <next>}'
```
Capture the returned `id` as `<episode_id>`. For `episode_number`, fetch
`GET /episodes` first and use `total_episodes + 1`.

**Step 2 — Upload audio** (multipart, MP3 only):
```bash
curl -s -X POST \
  "https://app.element.fm/api/workspaces/<workspace_id>/shows/<elementfm_show_id>/episodes/<episode_id>/audio" \
  -H "Authorization: Token $CLAUDE_ELEMENT_FM_KEY" \
  -F "audio=@<path-to-mp3>"
```

**Step 3 — Publish:**
```bash
curl -s -X POST \
  "https://app.element.fm/api/workspaces/<workspace_id>/shows/<elementfm_show_id>/episodes/<episode_id>/publish" \
  -H "Authorization: Token $CLAUDE_ELEMENT_FM_KEY"
```

Capture the episode URL from the publish response for the final report.

**After a successful publish for this feed**, write the per-feed sentinel:
```bash
mkdir -p ~/.local/state/reading-with-ears
touch ~/.local/state/reading-with-ears/done-YYYY-MM-DD-<slug>
```

This ensures a retry after a partial failure skips already-published feeds rather than
creating duplicates.

---

## Final Report

```
✅ Pipeline complete — [date or date range]

Phase 1 — Fetched: [N] emails across [N] feeds
Phase 2 — Notebooks: [N] created, [N] sources loaded
Phase 3 — Audio: [N] files downloaded
Phase 4 — Published: [N] episodes on Element.fm

Episodes:
• reading-list-2026-04-27-01 📰 News & Current Affairs → [element.fm episode url]
• reading-list-2026-04-27-02 🧠 Things to Think About → [element.fm episode url]
…

Already published (skipped):
• news, think

⚠️ Skipped (HTML-only, no body):
• "<subject>" — <sender>
```

Omit "Already published" if no feeds were skipped. Omit "Skipped" if no HTML-only emails.

---

## Edge Cases

- **Zero emails in range**: Report and stop after Phase 1
- **Feed has no emails on a given day**: Skip that notebook silently
- **HTML-only email**: Skip, surface in final report Skipped section
- **`studio_status` timeout (10 min)**: Log which notebooks timed out, continue with others
- **Audio file already exists at download path**: Skip download, note it in report
- **ffmpeg unavailable**: Skip m4a→mp3 conversion; attempt direct m4a upload; flag if Element.fm rejects
- **Element.fm 4xx on upload**: Log error + filename, continue with remaining files
- **`CLAUDE_ELEMENT_FM_KEY` not set**: Report and skip Phase 4 entirely; audio files are still downloaded
- **Partial previous run (some feeds done, some not)**: Per-feed sentinels skip completed feeds; only remaining feeds are processed — no duplicates
- **Tool call budget hit mid-run**: Report last completed phase and what remains; user continues with "proceed"
