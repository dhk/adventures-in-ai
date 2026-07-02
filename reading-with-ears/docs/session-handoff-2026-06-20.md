# Session Handoff — 2026-06-20

Paste this into a new Claude Code session to resume.

---

## What happened in this session

Started from a user-provided `reading-list-builder` skill draft and worked through a full
review, rewrite, and integration across the repo. Then pulled main (which had v2.1 already
merged) and moved into planning a new `week-that-was` weekly synthesis feature.

---

## Current repo state

**Branch:** `claude/reading-list-pipeline-ahpsE` (ahead of main — 30 unpushed commits,
stop hook is flagging this)

**Skill on main:** `reading-list-builder` v2.1 — two modes:
- **Light** (Haiku): Gmail → NotebookLM → audio → download
- **Deep** (Sonnet, default): + URL extraction, article fetch, synthesis, HTML briefs,
  YAML reading-db at `dhkondata/reading-db/runs/YYYY-MM-DD.yaml`

**Key files changed this session (on feature branch, not yet in main):**
- `reading-with-ears/skills/user/reading-list-builder/SKILL.md` — rewrote from draft
- `bin/rwe-run.sh` — new skill reference, sentinel guard, stdin prompt fix, `--catch-up` flag
- `bin/rwe-catchup.sh` — new: day-by-day gap backfill
- `reading-with-ears/skills/user/reading-with-ears/SKILL.md` — deleted (superseded)

**Unmerged branch:** `v1.1-updates` — two commits ahead of the v2.1 merge point:
1. Wire reading-list-builder to rwe-publish for download/publish
2. Deep pipeline run for 2026-05-18

---

## How to run the pipeline (current)

```bash
cd ~/Documents/dev/adventures-in-ai/reading-with-ears
claude --mcp-config automation/mcp-headless.json
# then say: "run the pipeline"
```

Then publish:
```bash
rwe-publish
```

Or catch-up:
```bash
rwe-run.sh --catch-up [--from YYYY-MM-DD] [--to YYYY-MM-DD]
```

**Note:** `rwe-run.sh` stdin prompt fix is on feature branch only — the `claude -p`
invocation was broken (newer CLI requires prompt via stdin, not trailing arg). If
automated runs are failing, that's why.

---

## In progress: weekly synthesis feature

**Concept:** "The Week That Was" — synthesizes a full week of reading-db output into
a Markdown doc + NotebookLM audio, published to a separate Element.fm weekly show.
For weekend reading/listening. Manual trigger.

**Design decisions made:**
- Input: reading-db YAML (not re-fetching from Gmail)
- Fixed subject taxonomy for continuity + dynamic ideation layer on top
- Output: Markdown doc + audio (NotebookLM) + Element.fm (separate weekly show)
- Cadence: manual, run Friday or weekend

**Proposed taxonomy:**
| Section | Feeds it draws from |
|---|---|
| 🤖 AI & Technology | pro, think, news |
| 💰 Economy & Markets | news, pro |
| 🏛️ Politics & Power | news, think |
| 🧬 Health & Science | healthcare, news |
| 💡 Ideas & Culture | think, news |
| 🏢 Business & Strategy | pro, think |

**Ideation layer:** Dynamic section identifying 2-3 cross-cutting angles the user
could write about, filtered against their writing themes (not a generic digest).

**Writer profile interview — in progress:**
- Q: What's the thread you return to in your writing?
- A: "The thoughtful use of AI to augment everyone's work"
- Next question asked: what's the contrast — what are you pushing back against?
- **Interview was interrupted — needs to resume here**

Key words to probe: "thoughtful" (vs. what?) and "everyone's" (who specifically?)

---

## Pending / loose ends

1. **Push the feature branch** — stop hook flagging 30 unpushed commits
2. **Merge `v1.1-updates`** — has useful rwe-publish wiring not yet in main
3. **Update `claude-code-context.md`** — predates v2.1, references old skill name
4. **Weekly synthesis skill** — resume writer profile interview, then spec + build
5. **Weekly Element.fm show** — needs a new `elementfm_show_id` in feeds.json
   or a separate weekly config

---

## Key files to know

| File | Purpose |
|---|---|
| `reading-with-ears/skills/user/reading-list-builder/SKILL.md` | Main skill (v2.1) |
| `reading-with-ears/config/feeds.json` | Feed config, show IDs, prompts |
| `dhkondata/reading-db/runs/` | Daily YAML output from deep mode |
| `dhkondata/reading-db/briefs/` | HTML article briefs |
| `bin/rwe-run.sh` | Full pipeline runner + `--catch-up` |
| `bin/rwe-catchup.sh` | Day-by-day backfill |
| `reading-with-ears/automation/mcp-headless.json` | Gmail + NotebookLM MCPs |
