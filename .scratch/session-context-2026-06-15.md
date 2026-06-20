# Session Context — 2026-06-15

## What we're working on

Building `run-analytics`, a meta-skill for Claude Code that eliminates setup
friction before analytics studies. The core idea: interview the user, identify
the tool stack, verify connections, write the allow-list to `settings.json`,
then hand off to the actual analysis — all in one upfront pass instead of
scattered permission interrupts mid-study.

Also added a `--discover` mode that crawls past session transcripts, skill
definitions, and CLAUDE.md to infer a default allow-list without needing a
live study to define it.

## Current status

**Shipped.** Merged to main via PR #19 (squash commit `440f36e`).

Files on main:
- `skills/user/run-analytics/SKILL.md` — the skill
- `skills/user/run-analytics/INSTALL.md` — curl install (pointing to main)
- `CLAUDE.md` — repo context doc (new this session, commit `71e768`)

Installed in this session at `~/.claude/skills/run-analytics/` — invocable
as `/run-analytics` right now.

Key things that got fixed after an independent review pass:
- Removed fake scoring formula from discovery mode (Phase D)
- Fixed transcript parsing bugs (`id(obj)` → filename tracking, `-newer` → `-mtime`)
- Replaced hardcoded MCP UUIDs with ToolSearch pattern (UUIDs are session-specific)
- Reframed dry runs as connection verification — clarified that `settings.json`
  write is the actual pre-approval mechanism, not prompt approvals
- Added cloud/ephemeral environment detection in discovery (skips transcript
  crawl gracefully when `~/.claude/projects/` is absent)
- Made allow-list curation dynamic (built from context, not hardcoded BQ rows)
- Added global vs. project settings distinction for the write phase
- Phase 5 "run it" now starts analysis immediately in the same session

## Next actions

1. **Install `save-context` and `ivy-archive` skills** — user references these
   but they don't exist in this container. Likely on local machine only.
   Ask user to share or push to repo so they survive cloud sessions.

2. **Test `run-analytics` end-to-end** — hasn't been run against a real study
   yet. First live run will shake out any edge cases in the connection
   verification and settings write phases.

3. **Wire up a SessionStart hook** that installs skills from this repo
   automatically — so `save-context`, `ivy-archive`, `run-analytics` etc.
   are available in every new cloud session without manual curl.

4. **Create `.claude/settings.json`** — doesn't exist yet in this repo.
   The `run-analytics` skill will create it on first allow-list write, but
   seeding it now with Tier 1 safe defaults (from a `--discover` run) would
   be useful.

## Repo state

Branch `claude/run-analytics-meta-skill-b2mum2` still exists (merged,
not deleted). Local working tree is on that branch and behind main by
several commits (pushed via GitHub API to avoid merge conflicts).

## Skills available in this session

- `/run-analytics` — installed at `~/.claude/skills/run-analytics/`
- Built-in: `session-start-hook`, `deep-research`, `update-config`,
  `code-review`, `simplify`, `fewer-permission-prompts`, `run`, `init`,
  `review`, `security-review`, `verify`, `loop`, `claude-api`,
  `keybindings-help`
