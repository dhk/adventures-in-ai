---
name: reading-list-builder
description: >
  Triages starred Gmail emails into to-reads and to-dos. To-reads go into dated
  NotebookLM notebooks (split by category) each with an audio overview. To-dos get
  added to the "Today Pile" project in Todoist as a single grouped task. Use this
  skill whenever the user says anything like "process my starred emails", "triage my
  inbox", "build my reading list", "add starred emails to NotebookLM", "sort my starred
  emails", "run my email triage", "what do I need to do from my emails", or "check my
  starred emails from the last few days". Triggers any time starred emails need to be
  sorted, routed, or acted on — including multi-day ranges.
compatibility: "Requires: Gmail MCP (gmail_search_messages, gmail_read_message), notebooklm MCP (notebook_create, source_add, studio_create, studio_status), Todoist MCP (search, add-projects, add-tasks)"
---

# Reading List Builder & Email Triage

Fetches starred Gmail emails (today or a date range), classifies them, shows a triage
table for user approval, then routes to-reads into categorised NotebookLM notebooks with
audio overviews, and to-dos into the Today Pile in Todoist.

---

## Step 1: Determine Date Range

If the user says "today" or gives no date, use today only:
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

If the user gives a range ("back to 3/15", "last few days", "this week"), use:
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```
where the date is the earliest day requested. The search returns all starred emails
from that date forward.

If no starred emails are found, tell the user and stop.

---

## Step 2: Fetch Full Content

For each email returned, fetch the full message:
```
gmail_read_message(messageId=<id>)
```

**Fetch ALL emails before doing anything else.** This keeps tool calls front-loaded
and avoids hitting the per-turn tool call limit mid-workflow.

While fetching each email, also capture sender metadata for tracking:
- sender display name (if available)
- sender email (if available)
- subject
- message id
- date

**HTML-only emails**: Some emails (e.g. JournalClub.io) return an empty plain-text
body with a note to view the HTML version. When this happens:
- Use the subject line and snippet to create a minimal source entry
- Note in the title that the body was not accessible: `"<subject> — <sender> [body unavailable]"`
- Include whatever context is available from the snippet

---

## Step 3: Classify Each Email

Classify every email as one of:
- 📰 **News & Current Affairs** — dispatches, news digests, current events newsletters
- 🧠 **Things to Think About** — opinion, analysis, ideas, philosophy, economics, culture
- 💼 **Professional Reading** — industry-specific, technical, career-relevant content
- 📋 **To-Do** — anything requiring action, reply, decision, or follow-up

### To-Do signals:
- Someone is waiting for a reply or decision
- Contains an action request, question, or deadline
- Sent emails (SENT label) that you starred to track — treat as follow-up items
- Subject patterns: "Re:", "Action required", "Please", "Can you", "Following up", receipts/invoices

### Ambiguity rule:
Default to **to-do** if any action is implied, even loosely.

### Newsletter sender tracking (for migration to Gmail labels)

Maintain a running sender registry at:

`dhk-daily-brief/data/newsletter_sender_registry.json`

For every non-to-do newsletter item seen in starred triage, update sender stats:
- increment `count`
- update `last_seen`
- preserve `first_seen`
- append category usage counters (`news`, `think`, `professional`)
- store `last_subject`
- maintain a small set/list of representative `subjects` (cap at 20)

If sender email is unavailable, use sender display name as fallback key.

Schema guidance:
```
{
  "version": 1,
  "updated_at": "ISO-8601",
  "senders": {
    "sender_key": {
      "name": "...",
      "email": "...",
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

### Show triage table before acting:

```
📧 Triage — [date range]

📰 News & Current Affairs (→ NotebookLM):
  • "Domestic Terror on the Rise" — The Morning Dispatch
  • "J.D. Vance learns what Mike Pence knows" — The Atlantic

🧠 Things to Think About (→ NotebookLM):
  • "What AI Hypists Miss" — Francis Fukuyama / Persuasion
  • "Roundup #79: The revenge of macroeconomics" — Noahpinion

💼 Professional Reading (→ NotebookLM):
  • "Are AI agents actually slowing us down?" — The Pragmatic Engineer
  • "Tiny Machine Learning (TinyML)" — JournalClub.io

📋 To-Do (→ Today Pile):
  • "Re: Resume: Dave Holmes-Kinsella" — follow up with Olivier @ Ramp
  • "It's that time of year" — reply to birthday message from G
  • "Your receipt from Gamma #2239-6502" — file the receipt

Proceed? (or tell me what to reclassify)
```

Wait for confirmation. If the user reclassifies items, re-show the updated table
and confirm again before acting.

**Skip empty categories silently** — if there are no professional reads, don't create
that notebook. If there are no to-dos, skip Todoist.

---

## Step 4: Route To-Dos → Today Pile (Todoist)

Check if "Today Pile" project exists:
```
search(query="Today Pile")
```

If it doesn't exist, create it:
```
add-projects([{name: "Today Pile", color: "orange", isFavorite: true, viewStyle: "list"}])
```

Add a **single grouped task** for this batch — not one task per email:
```
add-tasks([{
  content: "📬 Email triage — <date or date range>",
  projectId: <Today Pile project ID>,
  description: "• \"<subject>\" — <sender/note>\n• ...",
  dueString: "today",
  priority: "p3"
}])
```

Format the description as plain bullets with subject + sender + one-line action note.

---

## Step 5: Route To-Reads → NotebookLM

Create one notebook per non-empty category. Use this naming convention:
- `reading-list-YYYY-MM-DD-01 📰 News & Current Affairs`
- `reading-list-YYYY-MM-DD-02 🧠 Things to Think About`
- `reading-list-YYYY-MM-DD-03 💼 Professional Reading`

If running for a date range, use the end date (today) in the name.
If a notebook with today's date already exists, increment the numeric suffix.

### For each notebook:

**Create it:**
```
notebook_create(title="reading-list-YYYY-MM-DD-nn 📰 News & Current Affairs")
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

**Generate Audio Overview after all sources are loaded:**
```
studio_create(
  notebook_id=<id>,
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="default",
  focus_prompt="Open with the 3-5 most important ideas or takeaways across all the sources — give me the signal first. Then go deeper on each piece in turn. Close with any commentary, opinions, or open questions raised in the material. Prioritize insight over summary.",
  confirm=True
)
```

### Tool call budget awareness:
This workflow is tool-call-intensive. To stay within per-turn limits:
- Fetch all emails in Step 2 before creating any notebooks
- Create all notebooks before adding any sources
- Add sources notebook by notebook (all sources for notebook 1, then notebook 2, etc.)
- Start all audio generations last
- If the budget runs out mid-workflow, report exactly what was completed and what
  remains, so the user can continue in the next turn

---

## Step 6: Download Audio Overviews to iCloud

After audio generation is confirmed complete (via `studio_status`), download each
audio file to the Personal Podcast iCloud folder.

**Poll for completion first:**
```
studio_status(notebook_id=<id>)
```
Wait until status is `completed` before downloading. If still `in_progress`, note it
in the report and tell the user they can re-run the download step once ready.

**Download each audio artifact:**
```
download_artifact(
  notebook_id=<id>,
  artifact_type="audio",
  output_path="~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/<filename>.mp3"
)
```

**Filename convention:**
```
<YYYY-MM-DD>-<category-slug>.mp3
```
Examples:
- `2026-03-21-news.mp3`
- `2026-03-21-think.mp3`
- `2026-03-21-professional.mp3`

Category slugs:
- 📰 News & Current Affairs → `news`
- 🧠 Things to Think About → `think`
- 💼 Professional Reading → `professional`

**If download fails** (audio not yet ready): note which notebooks are still generating
and remind the user the files will be available once the overviews complete (typically
2–3 minutes after generation starts).

---

## Step 7: Report Back

```
✅ Done — [date range]

📚 NotebookLM — 3 notebooks created:
  • "reading-list-2026-03-18-01 📰 News & Current Affairs" → 3 sources
    [link]
  • "reading-list-2026-03-18-02 🧠 Things to Think About" → 3 sources
    [link]
  • "reading-list-2026-03-18-03 💼 Professional Reading" → 2 sources
    [link]

🎧 Personal Podcast (iCloud):
  • 2026-03-18-news.mp3 ✅
  • 2026-03-18-think.mp3 ✅
  • 2026-03-18-professional.mp3 ⏳ still generating — download when ready

📋 Todoist — Today Pile:
  → 1 grouped task added with 3 to-dos

🧾 Sender registry:
  • `dhk-daily-brief/data/newsletter_sender_registry.json` updated
  • Include top senders touched today (name/email + count)

Nothing was deleted or archived in Gmail.
Files saved to ~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast
```

---

## Edge Cases

- **No starred emails in range**: Tell user, offer to widen the date range
- **All to-reads, no to-dos**: Skip Todoist, mention it
- **All to-dos, no to-reads**: Skip NotebookLM, mention it
- **HTML-only email body**: Use subject + snippet, note body was unavailable
- **Gmail MCP unavailable**: Tell user to check Settings → Connectors
- **Today Pile missing**: Create it automatically (orange, favorited), note in summary
- **Duplicate notebook name**: Increment nn suffix (01 → 02 → 03)
- **User reclassifies**: Re-show full triage table with changes, re-confirm before acting
- **Tool call limit hit mid-run**: Report what's done, what's pending, continue next turn
- **Audio still generating at download time**: Note which files are pending, remind user they can ask "download my reading list audio" once ready
- **iCloud folder missing**: Remind user to run `mkdir -p ~/Library/Mobile\ Documents/com\~apple\~CloudDocs/Personal\ Podcast` before retrying
