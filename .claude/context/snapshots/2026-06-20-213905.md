# Session Context

**Saved:** 2026-06-20 21:38 UTC
**Branch:** claude/unified-persistence-arch-6ivww6
**Surface:** web (Claude Code on the web)

## Goal
Build and validate a unified persistence architecture for Claude Code across all
surfaces (web, desktop, CLI, VS Code, JetBrains), with `/save-context` as the
primary cross-surface checkpoint mechanism.

## Current State
Branch is complete and pushed. PR #21 is open against main. All commits are
clean. The `/save-context` skill and `SessionStart` hook are working and verified.

## Work in Progress
Nothing uncommitted. Branch is clean.

## Recent Decisions
- **Hook renamed to `restore-context.sh`**: avoids collision with the user-level
  `session-start-hook` skill which hardcodes `session-start.sh` as its output path;
  both hooks can now coexist in `settings.json`'s SessionStart array.
- **Removed "create a handoff" trigger from save-context**: that phrase belongs to
  `git-push-handoff`; added explicit exclusion note to description to prevent misrouting.
- **gitignore changed from `.claude/` to selective excludes**: only
  `settings.local.json`, `projects/`, `sessions/` are ignored; everything else in
  `.claude/` is committed and travels to web sessions via git clone.
- **Context stored in `.claude/context/`**: keeps Claude tooling self-contained;
  committed so it works on all surfaces.

## Next Steps
1. **Merge PR #21 into main** so the hook and skill are active on the default branch
   (web sessions clone from main by default).
2. **Test on web after merge**: start a new web session — restored context banner
   should appear automatically before the first prompt.
3. Optionally add a `CLAUDE.md` to repo root for broader project context.
4. Optionally move `git-push-handoff` and `redpen` into `.claude/skills/` if you
   want them to auto-load (currently they need manual install from `skills/`).

## Gotchas
- **Web sessions clone from the default branch** unless you specify a branch.
  Merge to main before expecting the hook to fire on web.
- **`jq` required** for `restore-context.sh` to output valid JSON. Pre-installed
  in web cloud sessions and most dev machines; verify on non-standard environments.
- **`session-start-hook` skill** (`~/.claude/skills/session-start-hook/`) creates
  `.claude/hooks/session-start.sh` — different filename, no conflict. Running it
  on this repo will add a deps-install hook alongside ours in `settings.json`.
- **Auto memory (`~/.claude/projects/.../memory/`) is machine-local** — does not
  travel to web sessions. Only committed files do.
