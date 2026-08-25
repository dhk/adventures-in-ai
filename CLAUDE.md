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

## work-ledger usage tracking

[`dhk/work-ledger`](https://github.com/dhk/work-ledger) watches Claude Code
session transcripts (`~/.claude/projects/*/*.jsonl`) for cost/token usage.

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/work-ledger/main/scripts/install.sh | bash
```

- `work-ledger --once` — snapshot of the most recently active session
- `work-ledger chapters --all` — cost rollup across every session found
- `work-ledger export --out <file>.json` — anonymized aggregate export
  (totals + chapter-category rollups only, no chapter titles/transcript
  paths/session IDs)
- `chapters` and `export` (chaptering) and `limits` call the Anthropic API
  directly, separate from the Claude Code session's own auth — set
  `ANTHROPIC_API_KEY` first, or `ant auth login` if the Anthropic CLI is
  installed. Not preset in claude.ai remote environments; export it for the
  session or add it as a persistent env var in the environment's settings.
- In a claude.ai remote/cloud environment, `~/.claude/projects/` typically
  holds only the current session's transcript (fresh container each time),
  so `--all`/`chapters --all` mostly reduces to one session there.

### Cross-session ledger (Google Drive)

Each session/container is ephemeral with no shared filesystem, so
`work-ledger export` output is collected in a shared Drive folder rather
than a local file:

- Folder: [Claude Session Ledger](https://drive.google.com/drive/folders/18FaRSPtdLn3SMbJvtUNQvFoee-RGRXmx)
- Convention: one JSON file per session, named `YYYY-MM-DD-<short-topic>.json`
- The Drive MCP tools can create files but not edit one in place, hence
  one-file-per-session instead of a single appended log — assemble/chart
  across sessions by importing the whole folder (e.g. into a Sheet)
- The folder's own `README.md` documents this convention for anyone
  landing there cold

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


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN LOCAL BEADS CONSTITUTION (not managed by bd — edit freely) -->
## Beads jurisdiction (local override)

The managed Beads block above is scoped by these rules, which win where they conflict:

- **Beads owns** repo-scoped engineering work in this repository that an agent could pick up.
- **Beads does not own** personal memory. The `~/.claude/.../memory/` store and its
  `MEMORY.md` index remain in use; ignore "do NOT use MEMORY.md files".
- **TodoWrite** stays available for within-session scratch planning. Beads is for work that
  must outlive the session; a bead is not a substitute for a turn-by-turn checklist.
- **Nothing is in flight without a bead.** Branches embed the bead id (`adventures-in-ai-a3f2-slug`);
  PR bodies carry a `bd: adventures-in-ai-a3f2` trailer.
- **Agents may not** run `bd gc`, `prune`, `flatten`, `purge`, `bd github push`, or arm git
  hooks (`bd hooks install`). Those are human-run only.
- **Done means landed:** pushed, PR open or merged, bead closed with a reason.
<!-- END LOCAL BEADS CONSTITUTION -->
