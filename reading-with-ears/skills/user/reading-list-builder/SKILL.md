---
name: reading-list-builder
version: "1.1"
description: >
  Deterministic newsletter pipeline. Gmail labels are the routing truth — no LLM
  classification, no approval gate. Fetches labeled emails, creates NotebookLM notebooks
  (one per day per label), generates audio overviews, titles each episode, and downloads
  the audio. Publishing to Element.fm is handled separately by rwe-publish. Use when user
  says "process my newsletters", "run the pipeline", "build my reading list", "triage my
  inbox", or similar. Handles today or a date range.
compatibility: "Requires: Gmail MCP (gmail_search_messages, gmail_read_message), NotebookLM MCP (notebook_create, source_add, studio_create, studio_status, notebook_describe), nlm CLI, ffmpeg"
---

# Reading List Builder

Labels ARE the routing. No classification step. No approval gate.
Stops at audio download — use rwe-publish to push to Element.fm.

---

## Step 0 — Load Feeds Config

**Before any Gmail or NotebookLM step**, read `config/feeds.json` (at
`reading-with-ears/config/feeds.json` relative to the repo root; prefer
`~/.config/reading-with-ears/feeds.json` if readable — it takes precedence).

For each feed where **`"enabled": true`**, sorted by **`notebook_order`** ascending,
record: `slug`, `gmail_labels` (array), `notebook_category` (full title suffix with
emoji), `notebook_order`, `audio_dir` (top-level), `audio_focus_prompt`.

Assign `nn` (zero-padded two digits) by position in the sorted enabled list: lowest
`notebook_order` → `01`, next → `02`, etc.

If no feeds are enabled, report and stop.

---

## Step 1 — Fetch

If no date is given, use today. For a range, use the earliest day as the start.

Search each enabled feed's labels individually (one call per label):

```
gmail_search_messages(q="label:<gmail_label> after:YYYY/MM/DD")
```

**Single past date (catch-up):** add a `before:` bound to scope to exactly that day:

```
gmail_search_messages(q="label:<gmail_label> after:YYYY/MM/DD before:YYYY/MM/DD+1")
```

Fetch every label across every enabled feed before doing anything else. For each
message ID, fetch the full message:

```
gmail_read_message(messageId=<id>)
```

**HTML-only emails** (empty plain-text body): skip entirely. Log subject + sender
for the Skipped section of the report.

If zero emails total: report and stop.

---

## Step 2 — Notebooks + Sources

Group emails by `(received_date × feed_slug)`. For each non-empty group, create one
notebook:

```
notebook_create(title="reading-list-YYYY-MM-DD-nn <notebook_category>")
```

Example:
- `reading-list-2026-04-27-01 📰 News & Current Affairs`
- `reading-list-2026-04-27-02 🧠 Things to Think About`
- `reading-list-2026-04-27-03 💼 Professional Reading`
- `reading-list-2026-04-27-04 🏥 Healthcare Reading`

If a notebook with that title already exists, skip creating it and use the existing one.

Add each email as a text source. Process all sources for one notebook before starting
the next:

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

## Step 3 — Audio, Titles & Download

After all notebooks have all their sources loaded, trigger audio generation for all
notebooks in parallel:

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
(timeout: 10 minutes). Log any that time out and continue with the rest.

### Episode titling

Once complete, call `notebook_describe` then rename the artifact with a title,
3–5 insight-first bullets, and a sources line:

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
- Bullets state what something *means*, not what it *covers* — insight-first
- 3 bullets minimum, 5 maximum
- Sources: `Newsletter Name (topic shorthand) · ...`

### Download

```bash
nlm download audio <notebook_id> \
  --output "<audio_dir>/YYYY-MM-DD-<slug>.m4a"
```

Convert to MP3 if needed:
```bash
ffmpeg -i "<audio_dir>/YYYY-MM-DD-<slug>.m4a" \
  -codec:a libmp3lame -q:a 2 \
  "<audio_dir>/YYYY-MM-DD-<slug>.mp3"
```

Skip download if `<audio_dir>/YYYY-MM-DD-<slug>.mp3` already exists.

---

## Report

```
✅ Done — [date or date range]

Fetched: [N] emails across [N] feeds
Notebooks: [N] created, [N] sources loaded
Audio: [N] files downloaded to <audio_dir>

• reading-list-2026-04-27-01 📰 News & Current Affairs → YYYY-MM-DD-news.mp3
• reading-list-2026-04-27-02 🧠 Things to Think About → YYYY-MM-DD-think.mp3
…

⚠️ Skipped (HTML-only, no body):
• "<subject>" — <sender>
```

Omit the Skipped section if there are no HTML-only emails.

---

## Edge Cases

- **Zero emails in range**: Report and stop
- **Feed has no emails on a given day**: Skip that notebook silently
- **HTML-only email**: Skip, surface in report
- **Notebook already exists**: Use it, don't create a duplicate
- **`studio_status` timeout (10 min)**: Log it, continue with other notebooks
- **Audio file already exists at download path**: Skip download, note it in report
- **ffmpeg unavailable**: Skip conversion, attempt direct m4a upload via rwe-publish; flag if rejected
- **Tool call budget hit mid-run**: Report what's done and what remains; continue next turn with "proceed"
