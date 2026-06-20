# Session Context

**Saved:** 2026-06-20 21:32 UTC
**Branch:** claude/unified-persistence-arch-6ivww6
**Surface:** web (Claude Code on the web)

## Goal
Design and implement a unified persistence architecture for Claude Code that works
across all surfaces: web, desktop, CLI, VS Code, and JetBrains extensions.

## Current State
All work on this branch is complete and pushed. The branch contains:
- A deep-research report on Claude Code persistence (in this conversation)
- The `/save-context` skill and SessionStart hook, committed and pushed

## Work in Progress
Nothing uncommitted. Branch is clean and pushed to
`origin/claude/unified-persistence-arch-6ivww6`.

## Recent Decisions
- **gitignore strategy**: Changed from ignoring all of `.claude/` to only ignoring
  local/personal files (`settings.local.json`, `projects/`, `sessions/`) — this is
  what lets the skill, hook, and context travel to web sessions via git clone.
- **context storage in `.claude/context/`**: Chose a committed subdirectory rather
  than `docs/context/` to keep Claude tooling self-contained under `.claude/`.
- **restore is automatic, not a slash command**: `SessionStart` hook injects
  `current.md` on every surface; no `/restore-context` needed.
- **SessionStart hook uses `additionalContext`**: The hook outputs JSON with
  `hookSpecificOutput.additionalContext` which Claude Code injects before the first
  prompt on every session.

## Next Steps
1. **Merge this branch into main** so the hook and skill are active on the default
   branch (web sessions clone from the default branch unless you specify otherwise).
2. **Test on web**: Start a new web session at claude.ai/code — it should open with
   the restored context banner automatically.
3. **Run `/save-context` before switching surfaces** going forward — that's the whole
   ritual now.
4. Optionally: add a `CLAUDE.md` to give Claude project-wide context that also
   travels to all surfaces (complements the session context).

## Gotchas
- **Web sessions clone from the default branch** unless you specify a branch. If you
  want context from a feature branch to travel to web, either merge to main or
  explicitly select the branch when starting the web session.
- **The context file must be committed to travel to web**. An `uncommitted`
  `current.md` only exists locally. The `/save-context` skill always commits — but
  if you edit `current.md` manually, remember to commit it.
- **Auto memory (`~/.claude/projects/.../memory/`) is machine-local** and does NOT
  travel to web sessions. Only what's committed in the repo does.
- **User-level `~/.claude/CLAUDE.md`** is also machine-local. If you have personal
  preferences there that you want in web sessions, copy them to the project `CLAUDE.md`.
- **`jq` must be available** for the `session-start.sh` hook to output valid JSON.
  It's pre-installed in web cloud sessions and on most dev machines; verify on
  non-standard environments.

## Open Questions
- Should this branch be merged to main via PR or direct merge?
- Should a `CLAUDE.md` be added to the repo root for broader project context?
