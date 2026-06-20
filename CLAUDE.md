# adventures-in-ai — Project Context

## What this repo is

A personal collection of Claude Code skills, analytics tooling, and reading/audio
pipeline experiments. Skills live in `skills/` (repo-level) and
`reading-with-ears/skills/` (reading pipeline specific).

## Skills in this repo

| Skill | Path | Install |
|---|---|---|
| `run-analytics` | `skills/user/run-analytics/` | see INSTALL.md |
| `redpen` | `skills/redpen/` | see INSTALL.md |
| `git-push-handoff` | `skills/user/git-push-handoff/` | manual copy |
| `multi-model-review` | `reading-with-ears/skills/user/multi-model-review/` | manual copy |
| `personal-podcast` | `reading-with-ears/skills/user/personal-podcast/` | manual copy |
| `reading-list-builder` | `reading-with-ears/skills/user/reading-list-builder/` | manual copy |

Skills are installed by copying their `SKILL.md` to `~/.claude/skills/<name>/SKILL.md`.
Claude Code picks them up automatically from that directory.

## run-analytics (most recently worked on)

**Status:** Merged to main (PR #19, commit `440f36e`).
**Branch:** `claude/run-analytics-meta-skill-b2mum2` — merged, feature branch still exists.

### What it does
Two-mode meta-skill for analytics studies:

- **Standard mode** (`/run-analytics`): intake interview → tool stack ID →
  connection verification → allow-list curation → writes `settings.json` →
  study brief → runs analysis
- **Discovery mode** (`/run-analytics --discover [7d|30d|90d|all]`): crawls
  `~/.claude/projects/` transcripts + SKILL.md files + CLAUDE.md for tool usage
  patterns → tiered allow-list candidates → writes `settings.json`

### Key design decisions made this session
- Dry runs reframed as **connection verification** (not permission pre-approval —
  that's a settings.json write)
- MCP tool IDs use **ToolSearch dynamically** rather than hardcoded UUIDs
- Transcript parsing uses `xargs python3` with filenames as args (`sys.argv[1:]`)
  so session identity is tracked correctly; `-mtime -N` not `-newer <(...)`
- Discovery mode detects cloud/ephemeral environments (no `~/.claude/projects/`)
  and gracefully falls back to skill/context crawl only
- Phase D scoring formula removed — raw signals (calls + sessions + source) are
  more legible than invented weighted scores
- Allow-list write distinguishes **global** (`~/.claude/settings.json`) vs
  **project** (`.claude/settings.json`) — generic tools (python3, ls, jq) go global

### Install command (on main now)
```bash
mkdir -p ~/.claude/skills/run-analytics && \
  curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/user/run-analytics/SKILL.md \
    -o ~/.claude/skills/run-analytics/SKILL.md
```

## reading-with-ears pipeline

Lives in `reading-with-ears/`. Pulls newsletter emails via Gmail MCP →
NotebookLM notebooks → audio overview → Element.fm podcast. Config in
`reading-with-ears/config/feeds.json`. Data store in
`dhkondata/reading-db/`.

## MCP servers connected in typical sessions

- Gmail (`mcp__Gmail__*`)
- Google Calendar (`mcp__Google_Calendar__*`)
- Google Drive (`mcp__Google_Drive__*`)
- Todoist (`mcp__ToDoist__*`)
- Twilio (`mcp__Twilio__*`)
- GitHub (`mcp__github__*`)

## Notes for next session

- `save-context` and `ivy-archive` skills referenced by user do not exist in
  this container — likely installed only on local machine. Ask user to share
  or install if needed.
- No `.claude/settings.json` exists in this repo yet — the run-analytics skill
  will create it on first allow-list write.
