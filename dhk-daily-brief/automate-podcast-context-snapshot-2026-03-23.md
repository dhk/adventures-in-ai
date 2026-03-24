# DHK Daily Brief — System Context Document

**Owner:** Dave Holmes-Kinsella (davehk@gmail.com)  
**Last updated:** March 23, 2026  
**Purpose:** Share this document with another LLM to provide full context on the DHK Daily Brief system — what it is, how it works, and how to operate it.

---

## What This Is

The **DHK Daily Brief** is a personal podcast system that automatically converts Dave's starred Gmail newsletters into categorized, AI-generated audio episodes (~15 minutes each). It runs daily, either manually via Claude.ai or on a schedule via Claude Code + cron.

The podcast is published at:
- **RSS feed:** `https://cdn.element.fm/b08a0951-94a4-441d-a446-81cc7950749c/d5be8d71-5fe3-4d2c-b641-0cd7343e4e36/rss.xml`
- **Show page:** `https://shows.element.fm/show/daily-thinking`
- **Hosting platform:** Element.fm
- **Listed in:** Apple Podcasts (show title: "DHK Daily Brief")

---

## How It Works — End to End

### Step 1: Email Triage (Gmail → Classification)

The workflow fetches all starred emails from Gmail for today (or a specified date range):
```
gmail_search_messages(q="is:starred after:YYYY/MM/DD")
```

Each email is read in full, then classified into one of four categories:

| Category | Icon | Destination |
|---|---|---|
| News & Current Affairs | 📰 | NotebookLM notebook |
| Things to Think About | 🧠 | NotebookLM notebook |
| Professional Reading | 💼 | NotebookLM notebook |
| To-Do | 📋 | Todoist Today Pile |

**To-Do signals:** action requests, replies needed, deadlines, SENT emails starred for follow-up, receipts/invoices, subject patterns like "Re:", "Action required", "Following up".

**Ambiguity rule:** Default to To-Do if any action is implied, even loosely.

When run interactively (via Claude.ai), a triage table is shown for user approval before anything is created. The user can reclassify items. When run automated (via cron), the triage step is skipped and the workflow proceeds directly.

---

### Step 2: To-Dos → Todoist

To-do emails are added as a **single grouped task** to the "Today Pile" project in Todoist:

```
add-tasks([{
  content: "📬 Email triage — YYYY-MM-DD",
  projectId: <Today Pile ID>,
  description: "• \"<subject>\" — <sender/note>\n• ...",
  dueString: "today",
  priority: "p3"
}])
```

If the Today Pile project doesn't exist, it's created automatically (orange, favorited).

---

### Step 3: To-Reads → NotebookLM

One NotebookLM notebook is created per non-empty read category, named:
- `reading-list-YYYY-MM-DD-01 📰 News & Current Affairs`
- `reading-list-YYYY-MM-DD-02 🧠 Things to Think About`
- `reading-list-YYYY-MM-DD-03 💼 Professional Reading`

Each email is added as a text source (`source_add`, `wait=True`). Bodies are truncated to ~8,000 characters if very long.

After all sources are loaded, an audio overview is generated for each notebook:
```
studio_create(
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="This is a personal podcast for one listener. Open with the 2-3
    most important ideas across all sources — give the signal first. Then go
    deeper on each piece in turn. Close with commentary and open questions.
    Prioritize insight over summary. Target roughly 15 minutes of content."
)
```

---

### Step 4: Publish to Element.fm

The generated audio files are uploaded to Element.fm and published as episodes of the DHK Daily Brief podcast. Each episode corresponds to one category notebook (e.g. one episode for News, one for Things to Think About).

**Important RSS note:** Each episode must have a unique `<itunes:episode>` number. Duplicate episode numbers cause Apple Podcasts to suppress episodes from the directory listing.

After publishing, force Apple Podcasts to re-crawl at:
`https://podcastsconnect.apple.com` → find the show → Refresh Feed.

---

## MCP Integrations Required

This workflow requires three MCP servers to be connected:

| Service | MCP URL | Used for |
|---|---|---|
| Gmail | `https://gmail.mcp.claude.com/mcp` | Fetching starred emails |
| Google NotebookLM | `notebooklm-mcp-cli` (local) | Creating notebooks, adding sources, generating audio |
| Todoist | `https://ai.todoist.net/mcp` | Adding to-do tasks to Today Pile |

---

## Automation Setup (Claude Code + Cron)

The workflow can be run unattended every morning via Claude Code in headless (`-p`) mode.

**Key files:**
- `~/.claude/skills/reading-list-builder.md` — the skill/prompt that Claude Code reads
- `~/bin/run-reading-list.sh` — the shell script invoked by cron
- Logs written to `~/logs/reading-list/YYYY-MM-DD.log`

**Cron schedule (7am daily):**
```
0 7 * * * /Users/davehk/bin/run-reading-list.sh
```

On macOS, launchd is recommended over cron for reliability.

**Known issue:** As of March 2026, HTTP-based MCP servers in `~/.claude.json` don't load in Claude Code's `-p` (headless) mode (GitHub issue #34131). The run script works around this by passing `--mcp-server` flags explicitly:
```bash
claude -p "$(cat "$SKILL_FILE")" \
  --mcp-server "gmail=https://gmail.mcp.claude.com/mcp" \
  --mcp-server "todoist=https://ai.todoist.net/mcp" \
  --mcp-server "notebooklm=..." \
  --allowedTools "mcp__gmail__*,mcp__todoist__*,mcp__notebooklm__*" \
  --dangerously-skip-permissions \
  --output-format text
```

---

## Operating the Workflow Manually (Claude.ai)

To trigger the workflow in Claude.ai, say any of:
- "create today's reading list"
- "process my starred emails"
- "run my email triage"
- "build my reading list"

The skill name is **`reading-list-builder`**.

**Interactive mode behavior:**
1. Fetches and reads all starred emails
2. Shows a triage table grouped by category
3. Waits for user confirmation (or reclassification requests)
4. Creates NotebookLM notebooks + generates audio
5. Adds any to-dos to Todoist Today Pile
6. Reports back with notebook links

**User preferences established in prior sessions:**
- Audio length: ~15 minutes ("long" setting)
- Audio are referred to as "personal podcasts"
- Items can be excluded at the triage step (e.g. "cut Chuck Norris")
- Reclassification is supported — user can move items between categories before proceeding

---

## Notebook Naming Convention

```
reading-list-YYYY-MM-DD-NN CATEGORY_EMOJI Category Name
```

Examples:
- `reading-list-2026-03-21-01 📰 News & Current Affairs`
- `reading-list-2026-03-21-02 🧠 Things to Think About`
- `reading-list-2026-03-21-03 💼 Professional Reading`

If running for a date range, the end date (today) is used. If a notebook with today's date already exists, the numeric suffix is incremented (01 → 02 → 03).

---

## Edge Cases & Known Behaviors

- **No starred emails:** Report and stop. Offer to widen the date range.
- **HTML-only email body:** Use subject + snippet as source text; note "[body unavailable]" in the title.
- **All to-reads, no to-dos:** Skip Todoist entirely.
- **All to-dos, no to-reads:** Skip NotebookLM entirely.
- **Tool call limit hit mid-run:** Report exactly what was completed and what remains so the user can continue in the next turn.
- **Duplicate episode numbers in RSS:** Causes Apple Podcasts to suppress episodes. Fix in Element.fm, then force re-crawl via Podcasts Connect.

---

## User Context

- **Name:** Dave (goes by DHK)
- **Email:** davehk@gmail.com
- **Work:** DHK Consulting; Substack called "dhkondata" (data topics); consulting work with Synctera
- **Stack:** Claude.ai (claude.ai), Claude Desktop with MCP integrations, Todoist Pro, Google NotebookLM, Element.fm
- **Productivity style:** Prefers concrete over vague tasks, aggressive cleanup, knock-off-and-organize mode for lighter days
- **Tone preference:** Direct, no unnecessary hedging, skip the meta-commentary
