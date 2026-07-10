# adventures-in-ai — Project Context

## What this repo is

A personal collection of Claude Code skills and analytics tooling. Skills live
in `skills/` (repo-level). The reading/audio pipeline (reading-with-ears) was
extracted to its own repo, [dhk/reading-with-ears](https://github.com/dhk/reading-with-ears),
on 2026-07-10 — see "Former reading-with-ears pipeline" below.

## Local environment

- User's repos all live at `~/Documents/dev/<repo-name>` locally (e.g.
  `~/Documents/dev/adventures-in-ai`, `~/Documents/dev/skill-map`). Use this
  path when giving local checkout/install commands instead of a placeholder.

## Skills in this repo

Every skill installs the same way: put its directory into
`~/.claude/skills/<name>/`. Claude Code picks it up automatically — no
restart needed. Symlink from this repo rather than copying, so there's one
source of truth and no drift when the skill is updated:

```bash
ln -s ~/Documents/dev/adventures-in-ai/<path> ~/.claude/skills/<name>
```

| Skill | Path | Notes |
|---|---|---|
| `run-analytics` | `skills/user/run-analytics/` | Has its own INSTALL.md with a curl one-shot |
| `redpen` | `skills/redpen/` | Has its own INSTALL.md with a curl one-shot; `--tickets`/`--pr` require GitHub MCP connected |
| `git-push-handoff` | `skills/user/git-push-handoff/` | — |
| `review-document` | `skills/user/review-document/` | Must include `reference/` — SKILL.md links to it, symlinking the whole directory (not just SKILL.md) covers this. Built via PR #31 if you want the backstory. |

`multi-model-review`, `personal-podcast`, and `reading-list-builder` moved
with the reading-with-ears pipeline extraction — see
[dhk/reading-with-ears](https://github.com/dhk/reading-with-ears)`/skills/user/`.

## review-document (most recently added)

Two-mode document reviewer: review → score → offer severity-tiered edits →
apply only on confirmation.

- **Mode A — single document** (`skills/user/review-document/reference/rubric.md`):
  one report/proposal/memo/README/spec, scored on 6 axes.
- **Mode B — doc package** (`skills/user/review-document/reference/doc-package-rubric.md`):
  a whole repo's documentation surface, scored against 4 audience journeys
  (encounter/understand/use/extend-maintain-develop) plus a hygiene pass. The
  hygiene checks (duplicate canonical docs, stale committed artifacts, broken
  links, missing index, drifted numbers) are derived directly from the
  `dhk/skill-map` docs cleanup done in this session (see PR #15 there).

Declares `allowed-tools: Read, Grep, Glob, Edit, Write` — Mode B needs Grep/Glob
to survey a repo and Write to create a new index file if one is missing.

Not for source code (`redpen`) or a Claude Agent Skill's own `SKILL.md`
(`skill-doctor`, in `dhk/skill-map`).

## run-analytics

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

## Former reading-with-ears pipeline

Extracted to [dhk/reading-with-ears](https://github.com/dhk/reading-with-ears)
on 2026-07-10 (full git history preserved via `git-filter-repo`). Pulls
newsletter emails via Gmail MCP → NotebookLM notebooks → audio overview →
Element.fm podcast. No longer lives in this repo — `reading-with-ears/`,
`bin/rwe-*`, and `dhkondata/reading-db/` were removed here.

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
