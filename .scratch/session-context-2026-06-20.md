# Session Context — 2026-06-20

## What we're working on

### 1. Reading List Builder pipeline (primary work this session)
Rewrote and rationalized the newsletter-to-podcast pipeline for the `adventures-in-ai`
repo. The pipeline: Gmail labels → NotebookLM notebooks → audio overviews → download
→ Element.fm publish.

Key decisions made:
- Replaced the old `reading-with-ears` skill (with triage table + approval gate) with a
  new deterministic `reading-list-builder` skill (labels ARE the routing, no human checkpoint)
- Skill stops at audio download — `rwe-publish` handles Element.fm (existing tool, unchanged)
- `rwe-run.sh` runs the full pipeline (skill + rwe-publish) for automation/launchd
- Added `rwe-catchup.sh` for backfilling missed days, invokable via `rwe-run.sh --catch-up`
- Added sentinel file idempotency (`done-YYYY-MM-DD`) to prevent duplicate runs
- Added skill version check in both scripts (current: v1.1 on feature branch, v2.1 on main)

**Current skill on main:** v2.1 — two modes:
- Light (Haiku): Gmail → NotebookLM → audio → download
- Deep (Sonnet, default): + URL extraction, article fetch, synthesis, HTML briefs,
  YAML reading-db at `dhkondata/reading-db/runs/YYYY-MM-DD.yaml`

### 2. Weekly synthesis feature (in design, not yet built)
"The Week That Was" — a new skill that reads the week's reading-db YAML and produces:
- A structured Markdown doc organized by fixed subject taxonomy
- A dynamic ideation layer: 2-3 angles filtered to the user's writing themes
- NotebookLM audio + separate Element.fm weekly show

**Design decisions made:**
- Input: reading-db YAML (not re-fetching Gmail)
- Fixed taxonomy (6 subject areas) + dynamic ideation on top
- Manual trigger, weekend cadence
- Separate Element.fm show (new show ID needed in feeds.json)

**In progress: writer profile interview**
The ideation layer needs to know what the user writes about so it surfaces relevant
angles, not generic ones.

- Theme established: *"The thoughtful use of AI to augment everyone's work"*
- Interview paused mid-question: what's the contrast — what version of AI adoption
  are you pushing back against? (probing "thoughtful" and "everyone's")

---

## Current status

| Item | Status |
|---|---|
| `reading-list-builder` skill | ✅ v1.1 on feature branch, v2.1 on main |
| `rwe-run.sh` | ✅ Updated (skill ref, sentinel, --catch-up, stdin fix) |
| `rwe-catchup.sh` | ✅ New script, committed |
| Old `reading-with-ears` skill | ✅ Deleted |
| Feature branch pushed | ✅ `claude/reading-list-pipeline-ahpsE` |
| Local repo synced to main (v2.1) | ✅ Pulled |
| `v1.1-updates` branch | ⏳ Not merged — has rwe-publish wiring + May 18 run |
| Weekly synthesis skill | ⏳ In design |
| Writer profile interview | ⏳ Paused mid-question |
| `claude-code-context.md` | ⚠️ Stale — predates v2.1, needs update |

**How to run the pipeline now:**
```bash
cd ~/Documents/dev/adventures-in-ai/reading-with-ears
claude --mcp-config automation/mcp-headless.json
# say: "run the pipeline"
# then: rwe-publish
```

---

## Next actions

1. **Resume writer profile interview** — answer: what are you pushing back against?
   Then: who is "everyone" specifically? Then synthesize into a writer profile config.

2. **Build `week-that-was` skill** — once writer profile is clear:
   - New skill at `reading-with-ears/skills/user/week-that-was/SKILL.md`
   - Reads `dhkondata/reading-db/runs/` for target week
   - Pre-flight: flag missing days
   - Cluster articles into fixed taxonomy
   - Generate ideation layer using writer profile
   - Output: `dhkondata/reading-db/weekly/YYYY-WNN.md`
   - NotebookLM notebook (synthesis doc as source) + audio + rwe-publish

3. **Add weekly show to feeds.json** — new slug (`weekly`), new Element.fm show ID

4. **Merge `v1.1-updates`** — rwe-publish wiring is useful, shouldn't stay on a branch

5. **Update `claude-code-context.md`** — bring it current with v2.1 reality

6. **Push feature branch or open PR** — stop hook flagging 30 unpushed commits
   on `claude/reading-list-pipeline-ahpsE`
