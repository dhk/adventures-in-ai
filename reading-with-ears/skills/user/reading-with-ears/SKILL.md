---
name: reading-with-ears
description: >
  Triages labeled Gmail newsletters into to-reads and to-dos. To-reads go into dated
  NotebookLM notebooks (split by category) each with an audio overview. To-dos are
  listed in the triage table and final report only (no external task app). Use this
  skill whenever the user says anything like "process my starred emails", "triage my
  inbox", "build my reading list", "add starred emails to NotebookLM", "sort my starred
  emails", "run my email triage", "what do I need to do from my emails", or "check my
  starred emails from the last few days". Triggers any time starred emails need to be
  sorted, routed, or acted on — including multi-day ranges.
compatibility: "Requires: Gmail MCP (gmail_search_messages, gmail_read_message), notebooklm MCP (notebook_create, source_add, studio_create, studio_status, notebook_describe)"
---

# Reading with Ears — reading list & email triage

Fetches labeled Gmail newsletters (today or a date range), classifies them, shows a triage
table for user approval, then routes to-reads into categorised NotebookLM notebooks with
audio overviews. **To-do items are not synced to Todoist or any task system** — they appear
only in the triage output and the closing report so the user can handle them in Gmail.
After audio is generated, fetches the notebook summary and renames each episode with a
bullet-point description and sources list.

---

## Multi-show feeds (`config/feeds.json`)

**Before any Gmail or NotebookLM step**, read **`config/feeds.json`** relative to this repo
(`reading-with-ears/config/feeds.json` when the project root is on your path). If the user
has **`~/.config/reading-with-ears/feeds.json`**, prefer that content when the skill can read
it; otherwise the bundled file in the repo is the source of truth for automation.

1. Consider only feeds where **`"enabled": true`** (omit or treat as disabled when `"enabled": false`).
2. Sort those feeds by **`notebook_order`** (ascending). This order defines the **`nn`**
   suffix in notebook titles (`01`, `02`, …) for the target date.
3. For each enabled feed, note: **`slug`**, **`notebook_category`** (full title suffix),
   **`notebook_emoji`**, **`gmail_labels`** (array), **`audio_focus_prompt`**.

**Primary Gmail search — union of all Gmail labels** on enabled feeds (skip feeds with
an empty `gmail_labels` list for the OR query only — they still get notebooks if mail is
classified into them another way, e.g. manual triage):

- Build `label:foo OR label:bar OR …` for every distinct label across enabled feeds.
- Example when news / think / pro / healthcare / ai-everybody are all enabled:
```
gmail_search_messages(q="(label:newsletter/news OR label:newsletter/think OR label:newsletter/pro OR label:newsletter/healthcare OR label:newsletter/ai-everybody) after:YYYY/MM/DD")
```

**Classification hint:** If an email carries a label that appears in feed `gmail_labels`,
default its read category to that feed’s **`notebook_category`**. The content classifier
may still override when clearly wrong. Starred mail **without** any of those labels is a
potential **To-Do** (report only).

**Sender registry:** Keep `reading-with-ears/data/newsletter_sender_registry.json` updated;
add new senders under the right category when you adopt new labels.

---

## Step 1: Determine Date Range & Fetch Emails

If the user says "today" or gives no date, use today only. If the user gives a range
("back to 3/15", "last few days", "this week"), use the earliest day as the start.

**Primary search** — use the **OR-of-labels** query built from **enabled** feeds’
`gmail_labels` (see above). If no enabled feed defines any label, report that misconfiguration
and stop (or fall back to starred search only if the user explicitly asks).

**Fallback — unlabeled starred emails (to-do triage):**
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

Run both searches when applicable. Deduplicate by messageId. Starred email that does **not**
carry any **newsletter** label from the feeds config should be treated as a potential **To-Do**.

If no emails are found at all, tell the user and stop.

---

## Step 2: Fetch Full Content

For each email returned, fetch the full message:
```
gmail_read_message(messageId=<id>)
```

**Fetch ALL emails before doing anything else.** This keeps tool calls front-loaded
and avoids hitting the per-turn tool call limit mid-workflow.

**HTML-only emails**: Some emails return an empty plain-text body with a note to view
the HTML version. When this happens:
- Use the subject line and snippet to create a minimal source entry
- Note in the title that the body was not accessible: `"<subject> — <sender> [body unavailable]"`
- Include whatever context is available from the snippet

---

## Step 3: Classify Each Email

Classify every email as one of:
- **One read bucket per enabled feed** — use that feed’s **`notebook_category`** name in the triage table (e.g. 📰 News & Current Affairs, 🧠 Things to Think About, 💼 Professional Reading, 🎙️ AI is for Everybody, …).
- 📋 **To-Do** — anything requiring action, reply, decision, or follow-up

### To-Do signals:
- Email does NOT have any label listed under **enabled feeds’** `gmail_labels`
- Someone is waiting for a reply or decision
- Contains an action request, question, or deadline
- Sent emails (SENT label) that you starred to track — treat as follow-up items
- Subject patterns: "Re:", "Action required", "Please", "Can you", "Following up", receipts/invoices

### Ambiguity rule:
Default to **to-do** if any action is implied, even loosely. Unlabeled starred emails
default to **to-do** unless content is unambiguously a newsletter read.

### Show triage table before acting:

Build one **NotebookLM** section per **enabled** feed that has at least one email (use
`notebook_category` as the heading). Example shape when four feeds are enabled:

```
📧 Triage — [date range]

📰 News & Current Affairs (→ NotebookLM):
  • …

🧠 Things to Think About (→ NotebookLM):
  • …

💼 Professional Reading (→ NotebookLM):
  • …

🎙️ AI is for Everybody (→ NotebookLM):
  • …

📋 To-Do (→ report only — not NotebookLM, no task app):
  • "Re: Resume: Dave Holmes-Kinsella" — follow up with Olivier @ Ramp
  • "It's that time of year" — reply to birthday message from G
  • "Your receipt from Gamma #2239-6502" — file the receipt

Proceed? (or tell me what to reclassify)
```

Wait for confirmation. If the user reclassifies items, re-show the updated table
and confirm again before acting.

**Skip empty categories silently** — if there are no professional reads, don't create
that notebook. **Do not call any task-manager MCP** for to-dos.

---

## Step 4: Route To-Reads → NotebookLM

Create **one notebook per non-empty enabled feed** (non-empty = at least one email in that
feed’s read bucket). **Assign `nn`** by **`notebook_order`** among enabled feeds only:
the lowest `notebook_order` gets `01`, the next `02`, etc. (pad to two digits).

Title format:
```
reading-list-YYYY-MM-DD-nn <notebook_category from feeds.json for that feed>
```

Example with four enabled feeds:
- `reading-list-2026-04-05-01 📰 News & Current Affairs`
- `reading-list-2026-04-05-02 🧠 Things to Think About`
- `reading-list-2026-04-05-03 💼 Professional Reading`
- `reading-list-2026-04-05-04 🎙️ AI is for Everybody`

If running for a date range, use the end date (today) in the name.
If a notebook with today’s date already exists, increment the numeric suffix.

### For each notebook:

**Create it** (substitute the feed’s `notebook_category`):
```
notebook_create(title="reading-list-YYYY-MM-DD-nn <notebook_category>")
```

**Add each email as a text source:**
```
source_add(
  notebook_id=<id>,
  source_type="text",
  title="<subject> — <sender> (<date>)",
  text="From: <sender>\nDate: <date>\n\n<body>",
  wait=True
)
```
- Truncate body to ~8,000 characters if very long
- For HTML-only emails with no body: use subject + snippet as the text

**Generate Audio Overview after all sources are loaded** — use that feed’s
**`audio_focus_prompt`** from `feeds.json` (verbatim). If missing, fall back to a single
generic ~12-minute insight-first prompt.
```
studio_create(
  notebook_id=<id>,
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="<audio_focus_prompt from the matching feed>",
  confirm=True
)
```

### Tool call budget awareness:
This workflow is tool-call-intensive. To stay within per-turn limits:
- Fetch all emails in Step 2 before creating any notebooks
- Create all notebooks before adding any sources
- Add sources notebook by notebook (all sources for notebook 1, then notebook 2, etc.)
- Start all audio generations last
- Run Step 5 (episode titling) after all audio is confirmed generated
- Run Step 6 (download) after all episodes are titled
- If the budget runs out mid-workflow, report exactly what was completed and what
  remains, so the user can continue in the next turn

---

## Step 5: Title & Describe Each Audio Episode

After firing all audio generations, call studio_status on each notebook to confirm
completion, then call notebook_describe to get the AI-generated summary. Use this
to rename each artifact with a rich title, bullet-point key ideas, and sources line.

**For each notebook:**
```
studio_status(notebook_id=<id>)       # get artifact_id and confirm completed
notebook_describe(notebook_id=<id>)   # get AI summary to distill into bullets
```

Then rename:
```
studio_status(
  notebook_id=<id>,
  action="rename",
  artifact_id=<artifact_id>,
  new_title="<NotebookLM-generated title>\n\n• <key idea 1>\n• <key idea 2>\n• <key idea 3>\n\nSources: <Newsletter (topic)> · <Newsletter (topic)> · ..."
)
```

### Titling rules:
- Keep NotebookLM's auto-generated title — it's usually excellent; don't replace it
- Bullets should be punchy and insight-first, not just descriptive ("X covers Y")
- Sources line format: `Newsletter Name (topic shorthand) · Newsletter Name (topic) · ...`
- 3 bullets minimum, 5 maximum — don't pad
- If audio is still in_progress when Step 5 runs, poll studio_status until completed

### Example finished episode title:
```
How Power Profits From Manufactured Chaos

• AI companies are uniquely selling a product framed around existential risk and job displacement — yet people are buying it anyway
• The Iran war is functioning as a massive regressive global tax, hitting import-dependent nations hardest while the US gets off relatively easy
• Trump's second-term economic instability is self-generated, not inherited — a structural shift from his first term
• The White House governs through a repeating pattern: manufacture crisis → demand concessions → claim victory

Sources: Noahpinion (AI's worst sales pitch; Iran war economics) · Jonah Goldberg / The Dispatch (Two Trump economies) · The Atlantic Daily (Trump's bailout pattern)
```

---

## Step 6: Download Audio Files

After all episodes are titled, download each completed audio file to the iCloud Personal
Podcast folder so Phase 2 (Element.fm upload) can pick them up.

```
download_artifact(
  notebook_id=<id>,
  artifact_id=<artifact_id>,
  output_path="~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/YYYY-MM-DD-<slug>.mp3"
)
```

### Slug mapping (from `feeds.json`)

Use each feed’s **`slug`** field for the filename: `YYYY-MM-DD-<slug>.mp3`
(e.g. `news`, `think`, `professional`, `vital-signs`, `ai-everybody`). Phase 2 (`publish_episodes.py`) uses the
same slugs for enabled feeds.

- Skip download if the file already exists at that path (idempotency)
- If download fails, report the error and continue — Phase 2 will retry via manifest

---

## Step 7: Report Back

```
✅ Done — [date range]

📚 NotebookLM — N notebooks created (one line per enabled feed that had mail):
  • "reading-list-YYYY-MM-DD-01 …" → K sources
    🎧 "<episode title>" → 📥 YYYY-MM-DD-<slug>.mp3
  • (repeat for each feed)

📋 To-dos (handle in Gmail — not exported to a task app):
  • "Re: Resume …" — follow up
  • …

Nothing was deleted or archived in Gmail.
Audio files downloaded to iCloud Personal Podcast — ready for Phase 2 (Element.fm upload).
```

---

## Edge Cases

- **No labeled emails in range**: Fall back to starred search; tell user labels aren't set up if both return nothing
- **All to-reads, no to-dos**: Say so in the report; no task list section needed
- **All to-dos, no to-reads**: Skip NotebookLM; list to-dos in the report only
- **HTML-only email body**: Use subject + snippet, note body was unavailable
- **Unlabeled starred email looks like a newsletter**: Flag it in the triage table with a note, let user decide
- **Gmail MCP unavailable**: Tell user to check Settings → Connectors
- **Duplicate notebook name**: Increment nn suffix (01 → 02 → 03)
- **User reclassifies**: Re-show full triage table with changes, re-confirm before acting
- **Tool call limit hit mid-run**: Report what's done, what's pending, continue next turn
- **Audio still in_progress at Step 5**: Poll studio_status until completed, then rename
- **Audio file already exists at download path**: Skip download, note it in report-back
- **Download fails**: Report error, continue with remaining notebooks — Phase 2 will retry
- **New newsletter not yet labeled**: Add Gmail filter + label, add the label to the right feed’s `gmail_labels` in `feeds.json`, and note the gap to the user
- **Enabled feed with empty `gmail_labels`**: Primary search won’t catch mail; user must route content manually or add labels before relying on automation
