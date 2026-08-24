---
name: session-consolidation
description: >
  Sweeps local Claude Code session transcripts, clusters related ones,
  classifies each as active/completed/stale/orphaned/superseded, and
  proposes a tiered action list. Never archives without explicit approval;
  archiving is always a reversible move, never a delete. Modeled on git
  branch hygiene. Use when asked to sweep, clean up, consolidate, or tidy
  Claude Code sessions, or to find redundant/stale/abandoned sessions.
  Triggers: "/session-consolidation", "sweep my sessions", "clean up my
  claude sessions", "session hygiene", "consolidate my sessions",
  "what sessions am I duplicating".
---

# Session Consolidation

A thin wrapper around the `session-consolidation` CLI — this skill has no
logic of its own beyond locating the CLI, running it, and mediating approval.
See `session-consolidation/README.md` and
`docs/session-consolidation-design.md` in the repo for the full design.

## Step 1 — Locate the CLI

Try, in order:

1. `$SESSION_CONSOLIDATION_REPO/session-consolidation` if that env var is set.
2. `~/Documents/dev/adventures-in-ai/session-consolidation` (this repo's
   standard local checkout path, per its `CLAUDE.md`).
3. Ask the user where their `adventures-in-ai` checkout lives.

Verify with:

```bash
test -f <candidate>/session_consolidation/cli.py && echo found
```

If none resolve, tell the user the CLI isn't installed locally and stop —
do not attempt to install it yourself without asking.

## Step 2 — Parse the invocation

- `/session-consolidation` or no args → default: `--since 30d`
- `/session-consolidation [7d|14d|30d|90d|all]` → pass through as `--since`
- Note if the environment has no `~/.claude/projects/` at all (cloud/ephemeral
  session) — the CLI's `report` command already handles this gracefully
  (returns zero sessions, not an error), but say so plainly to the user
  rather than presenting an empty report as if nothing needed sweeping.

## Step 3 — Run the report

```bash
cd <cli_dir> && python3 -m session_consolidation.cli report --since <timeframe> --out /tmp/session-consolidation-report.json
```

The command prints a human-readable tiered summary to stderr — relay it to
the user directly rather than re-deriving your own summary from the JSON.
Mention the report JSON path so they can open it in `web/viewer.html` if
they want the visual tree instead of the text summary.

## Step 4 — Present and seek approval

State the three tiers plainly, matching the CLI's own language:

- **Safe to archive** — stale or superseded sessions, no orphaned work.
  Can be bulk-approved.
- **Needs a decision** — orphaned uncommitted work. Walk through these
  individually; never bulk-approve them.
- **Keep as-is** — active or completed; no action offered.

Ask explicitly:

> "Archive the N safe-to-archive sessions? (This moves their transcripts to
> `~/.claude/projects-archive/`, never deletes them.) For the sessions that
> need a decision, tell me per-session: archive, or leave alone."

Do not archive anything on your own initiative. Silence is not approval.

## Step 5 — Execute only what's approved

```bash
# bulk, for the safe tier
python3 -m session_consolidation.cli archive --report /tmp/session-consolidation-report.json --approve-tier safe_to_archive --yes

# per-session, for anything the user approved individually
python3 -m session_consolidation.cli archive --report /tmp/session-consolidation-report.json --approve <id> [<id> ...] --yes
```

Relay the per-session archive results (archived / missing) back to the user.
If any session is reported `missing`, say so — don't silently drop it.

## Notes

- This skill never touches git branches, PRs, or repo content — only local
  session transcripts under `~/.claude/projects/`.
- Fast/deep categorization modes and a "merge sessions into one brief"
  offering are Phase 2, not implemented here — see
  [issue #42](https://github.com/dhk/adventures-in-ai/issues/42) if the user
  asks for either.
