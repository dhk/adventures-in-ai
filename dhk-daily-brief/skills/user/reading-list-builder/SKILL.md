---
name: reading-list-builder
description: >
  Triages labeled Gmail newsletters into to-reads and to-dos. To-reads go into dated
  NotebookLM notebooks (split by category) each with an audio overview. To-dos get
  added to the "Today Pile" project in Todoist as a single grouped task. Use this
  skill whenever the user says anything like "process my starred emails", "triage my
  inbox", "build my reading list", "add starred emails to NotebookLM", "sort my starred
  emails", "run my email triage", "what do I need to do from my emails", or "check my
  starred emails from the last few days". Triggers any time starred emails need to be
  sorted, routed, or acted on — including multi-day ranges.
compatibility: "Requires: Gmail MCP (gmail_search_messages, gmail_read_message), notebooklm MCP (notebook_create, source_add, studio_create, studio_status, notebook_describe), Todoist MCP (search, add-projects, add-tasks)"
---

# Reading List Builder & Email Triage

Fetches labeled Gmail newsletters (today or a date range), classifies them, shows a triage
table for user approval, then routes to-reads into categorised NotebookLM notebooks with
audio overviews, and to-dos into the Today Pile in Todoist. After audio is generated,
fetches the notebook summary and renames each episode with a bullet-point description
and sources list.

---

## Newsletter Label System

Known newsletters are tagged in Gmail with one of three labels. These labels serve as
an eligibility gate — only labeled emails are treated as newsletter reads.
Starred emails without a newsletter label (receipts, event invites, personal emails)
are classified as **To-Do** regardless of content.

| Label | Sender addresses covered |
|---|---|
| `newsletter/news` | sanfrancisco@axios.com, email@washingtonpost.com, dailydigest@email.join1440.com, hello@newsletter.thedispatch.com, newsletters@theatlantic.com |
| `newsletter/think` | noahpinion@substack.com, yaschamounk@substack.com, persuasion1+francis-fukuyama@substack.com, opinionatedintelligence@substack.com, post+the-weekender@substack.com |
| `newsletter/pro` | ai.plus@axios.com, dan@tldrnewsletter.com, pragmaticengineer+deepdives@substack.com, lenny@substack.com, newsletter@towardsdatascience.com, hello@mindstream.news, thecode@mail.joinsuperhuman.ai, marketing-team@motherduck.com, info@theinformation.com, marcussawyerr@substack.com |

**Label hint for classification:** If an email has a `newsletter/news` label, default
its category to 📰 News & Current Affairs. If `newsletter/think`, default to 🧠 Things
to Think About. If `newsletter/pro`, default to 💼 Professional Reading. These are
defaults — the content-based classifier can still override if the issue is clearly
better suited to a different category (e.g. a longform Dispatch essay may fit better
in 🧠 even though the sender is in `newsletter/news`).

---

## Step 1: Determine Date Range & Fetch Emails

If the user says "today" or gives no date, use today only. If the user gives a range
("back to 3/15", "last few days", "this week"), use the earliest day as the start.

**Primary search — labeled newsletters (no star required):**
```
gmail_search_messages(q="(label:newsletter/news OR label:newsletter/think OR label:newsletter/pro) after:YYYY/MM/DD")
```

**Fallback — catch unlabeled starred emails (for to-do triage):**
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

Run both searches. Deduplicate by messageId. Any starred email that does NOT have a
newsletter label should be treated as a potential **To-Do** — don't route it to
NotebookLM unless the content clearly warrants it and you flag the exception to the user.

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
- 📰 **News & Current Affairs** — dispatches, news digests, current events newsletters
- 🧠 **Things to Think About** — opinion, analysis, ideas, philosophy, economics, culture
- 💼 **Professional Reading** — industry-specific, technical, career-relevant content
- 📋 **To-Do** — anything requiring action, reply, decision, or follow-up

### To-Do signals:
- Email does NOT have a newsletter label (`newsletter/news`, `newsletter/think`, `newsletter/pro`)
- Someone is waiting for a reply or decision
- Contains an action request, question, or deadline
- Sent emails (SENT label) that you starred to track — treat as follow-up items
- Subject patterns: "Re:", "Action required", "Please", "Can you", "Following up", receipts/invoices

### Ambiguity rule:
Default to **to-do** if any action is implied, even loosely. Unlabeled starred emails
default to **to-do** unless content is unambiguously a newsletter read.

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
  audio_length="long",
  focus_prompt="This episode should run approximately 12 minutes. Open with the 3-5 most important ideas or takeaways across all the sources — give me the signal first. Then go deeper on each piece in turn. Close with any commentary, opinions, or open questions raised in the material. Prioritize insight over summary.",
  confirm=True
)
```

### Tool call budget awareness:
This workflow is tool-call-intensive. To stay within per-turn limits:
- Fetch all emails in Step 2 before creating any notebooks
- Create all notebooks before adding any sources
- Add sources notebook by notebook (all sources for notebook 1, then notebook 2, etc.)
- Start all audio generations last
- Run Step 6 (episode titling) after all audio is confirmed generated
- Run Step 7 (download) after all episodes are titled
- If the budget runs out mid-workflow, report exactly what was completed and what
  remains, so the user can continue in the next turn

---

## Step 6: Title & Describe Each Audio Episode

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
- If audio is still in_progress when Step 6 runs, poll studio_status until completed

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

## Step 7: Download Audio Files

After all episodes are titled, download each completed audio file to the iCloud Personal
Podcast folder so Phase 2 (Element.fm upload) can pick them up.

```
download_artifact(
  notebook_id=<id>,
  artifact_id=<artifact_id>,
  output_path="~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast/YYYY-MM-DD-<slug>.mp3"
)
```

### Slug mapping:
| Category | Slug | Filename |
|---|---|---|
| 📰 News & Current Affairs | `news` | `YYYY-MM-DD-news.mp3` |
| 🧠 Things to Think About | `think` | `YYYY-MM-DD-think.mp3` |
| 💼 Professional Reading | `professional` | `YYYY-MM-DD-professional.mp3` |

- Skip download if the file already exists at that path (idempotency)
- If download fails, report the error and continue — Phase 2 will retry via manifest

---

## Step 8: Report Back

```
✅ Done — [date range]

📚 NotebookLM — 3 notebooks created:
  • "reading-list-2026-03-26-01 📰 News & Current Affairs" → 4 sources
    🎧 "How Algorithms Lost Their Legal Shield" → 📥 2026-03-26-news.mp3
  • "reading-list-2026-03-26-02 🧠 Things to Think About" → 2 sources
    🎧 "How Power Profits From Manufactured Chaos" → 📥 2026-03-26-think.mp3
  • "reading-list-2026-03-26-03 💼 Professional Reading" → 5 sources
    🎧 "Uber AI Minions and the Liability Sponge" → 📥 2026-03-26-professional.mp3

📋 Todoist — Today Pile:
  → 1 grouped task added with 3 to-dos

Nothing was deleted or archived in Gmail.
Audio files downloaded to iCloud Personal Podcast — ready for Phase 2 (Element.fm upload).
```

---

## Edge Cases

- **No labeled emails in range**: Fall back to starred search; tell user labels aren't set up if both return nothing
- **All to-reads, no to-dos**: Skip Todoist, mention it
- **All to-dos, no to-reads**: Skip NotebookLM, mention it
- **HTML-only email body**: Use subject + snippet, note body was unavailable
- **Unlabeled starred email looks like a newsletter**: Flag it in the triage table with a note, let user decide
- **Gmail MCP unavailable**: Tell user to check Settings → Connectors
- **Today Pile missing**: Create it automatically (orange, favorited), note in summary
- **Duplicate notebook name**: Increment nn suffix (01 → 02 → 03)
- **User reclassifies**: Re-show full triage table with changes, re-confirm before acting
- **Tool call limit hit mid-run**: Report what's done, what's pending, continue next turn
- **Audio still in_progress at Step 6**: Poll studio_status until completed, then rename
- **Audio file already exists at download path**: Skip download, note it in report-back
- **Download fails**: Report error, continue with remaining notebooks — Phase 2 will retry
- **New newsletter not yet labeled**: Add it to the label system table above and note the gap to the user
