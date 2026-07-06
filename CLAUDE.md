# adventures-in-ai — Project Context

## What this repo is

A personal collection of Claude Code skills, analytics tooling, and reading/audio
pipeline experiments. Skills live in `skills/` (repo-level) and
`reading-with-ears/skills/` (reading pipeline specific).

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

| Skill | Path | Status | Notes |
|---|---|---|---|
| `run-analytics` | `skills/user/run-analytics/` | Merged via PR #19 (`440f36e`) — the only skill here built on a feature branch; `claude/run-analytics-meta-skill-b2mum2` still exists post-merge | Has its own INSTALL.md with a curl one-shot |
| `redpen` | `skills/redpen/` | On `main`, direct commit (no PR), last touched 2026-06-14 | Has its own INSTALL.md with a curl one-shot; `--tickets`/`--pr` require GitHub MCP connected |
| `git-push-handoff` | `skills/user/git-push-handoff/` | On `main`, direct commit (no PR), last touched 2026-03-29 | — |
| `review-document` | `skills/user/review-document/` | **Open — PR #31, not yet merged** | Must include `reference/` — SKILL.md links to it, symlinking the whole directory (not just SKILL.md) covers this |
| `multi-model-review` | `reading-with-ears/skills/user/multi-model-review/` | On `main`, direct commit (no PR), last touched 2026-04-05 | Requires Codex registered as an MCP server (`claude mcp add codex -- npx codex mcp-server`) |
| `personal-podcast` | `reading-with-ears/skills/user/personal-podcast/` | On `main`, direct commit (no PR), last touched 2026-04-08 | — |
| `reading-list-builder` | `reading-with-ears/skills/user/reading-list-builder/` | On `main`, direct commit (no PR), last touched 2026-05-20 | — |

Most of these were committed straight to `main` in ad-hoc sessions, not via a
feature branch — `run-analytics` is the exception, and `review-document` is
still mid-PR. "Last touched" is the most recent commit that changed the
skill's `SKILL.md`, not necessarily when it was first added.

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
