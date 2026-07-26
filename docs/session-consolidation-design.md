# Session Consolidation — Design Doc

**Status:** draft, not yet built.

## Problem

Claude Code session transcripts accumulate under `~/.claude/projects/<project>/*.jsonl`
across every repo you've worked in, with no built-in view of the sprawl: duplicate
sessions restarted on the same topic, sessions left mid-task with uncommitted work,
sessions whose work was superseded by a later one. There's no periodic hygiene pass,
so the pile just grows.

This is the same shape of problem `git branch` sprawl is: stale and merged branches
pile up until someone runs a prune pass, sees what's safe to drop, and confirms before
anything is deleted. Session Consolidation applies that same discipline to sessions
instead of branches — sweep, classify, propose, get explicit approval, only then act.

## Goals

- On-demand sweep (e.g. `/session-consolidation [--since 30d]`) over local session
  transcripts across all projects in `~/.claude/projects/`.
- A relatedness report: cluster sessions by project, topic, and time proximity.
- Classification per session: active, completed, stale, orphaned (touched files with
  no corresponding commit), or superseded by a later session in the same cluster.
- A concrete, itemized action list derived from the classification — not just prose.
- Nothing executes without explicit user approval, matching the "connection
  verification ≠ permission pre-approval" discipline already used in `run-analytics`:
  seeing the report is not the same as approving the actions.

## Non-goals (v1)

- Does not touch git branches, PRs, or any git state — that's a distinct problem
  from a distinct signal source (git branch metadata vs. local transcripts) and
  should be its own pass if wanted later.
- Does not merge or summarize conversation content across sessions into a new
  session — the CLI has no primitive for that, and it isn't clear it should.
- Does not delete anything by default. The only destructive-adjacent action is
  "archive" (move, not delete), and even that is opt-in per batch.
- Not a background/automatic job — invocation-only, like `run-analytics`.

## Approach

### Step 1 — Sweep

Reuse the `run-analytics` discovery-mode crawl pattern (`find ~/.claude/projects
-name "*.jsonl" -mtime -<N>`, parsed via `xargs python3` with filenames as argv so
session identity stays attached to each transcript — same reasoning captured in
this repo's `run-analytics` design notes).

Per session, extract:
- project directory (cwd)
- first user message (topic seed) and last assistant message (where it stopped)
- message count, start/end timestamp
- files touched (`Edit`/`Write` tool_use `file_path` inputs)
- git activity inside the session (branch names, `git commit` calls) — the signal
  for whether the session's work actually landed anywhere

### Step 2 — Cluster

Group sessions that are plausibly "the same effort split across sessions":
same project dir, keyword/file overlap in what was touched, and recency (e.g.
within ~14 days of each other). Keep this heuristic and dependency-free for v1 —
shared `file_path` touches and shared keywords in the topic seed, no embeddings.

### Step 3 — Classify

- **Active** — recent activity, plausibly still in progress
- **Completed** — session includes a `git commit`/`git push` that plausibly
  finished the work
- **Stale** — no activity in N days, no commit
- **Orphaned work** — touched files with no corresponding commit found
- **Superseded** — a later session in the same cluster covers the same ground

### Step 4 — Report + proposed actions

Present clusters and classifications, then a tiered action list (mirroring the
Tier 1/2/3 shape from `run-analytics`'s allow-list curation, since it's already
a pattern for "here's what's safe to batch-approve vs. what needs a per-item
decision"):

- **Safe to archive** — stale, no orphaned work, superseded by a completed
  session in the same cluster
- **Needs a decision** — orphaned uncommitted work, or ambiguous clustering
- **Keep as-is** — active or completed, canonical for its cluster

Ask for approval per tier or per item — never assume silence means approve.

### Step 5 — Execute (only on approval)

"Archive" means **move**, not delete: relocate the `.jsonl` to a mirrored path
under `~/.claude/projects-archive/`, so it's fully reversible and drops out of
the live project listing without destroying anything. Log each action (what
moved, why, when) to an append-only manifest for auditability.

Deletion is not offered in v1. If it's added later, it must be a separate,
explicitly-named confirmation step — never bundled into "archive."

## Architecture: shared core, three surfaces

Decision: build as an **MCP server from the start**, with a plain core module
underneath so the CLI never needs a running server for a simple sweep.

- **Core module** — Steps 1–5 above as plain functions with no MCP/CLI/web
  dependencies: `sweep()`, `cluster()`, `classify()`, `propose_actions()`,
  `archive()`. This is the one place the logic lives; everything else is a
  thin surface over it.
- **MCP server** — wraps the core functions as MCP tools (`sweep_sessions`,
  `cluster_sessions`, `classify_sessions`, `propose_actions`,
  `archive_sessions`), so any MCP host — Claude Desktop, another agent, or
  this Claude Code skill via MCP instead of shelling out — can call the same
  logic. This is what justifies "from the get-go": the capability is usable
  outside this one CLI/skill pair immediately, not bolted on after the fact.
- **CLI** — imports the core module directly, so a plain `sweep`/`report`
  call doesn't require the MCP server process to be running. Subcommands
  mirror the tool names (`sweep`, `report`, `archive --approve <ids>`).
  Writes the Step 4 report as JSON.
- **Web viewer** — static HTML that reads the CLI's JSON report and renders
  it as a collapsible tree (cluster → session → classification, tier-colored
  for safe-to-archive / needs-a-decision / keep-as-is). No server process —
  open the file locally or view as an artifact. Approve/archive actions stay
  in the CLI, not the browser, for v1 — the viewer is a renderer, not a
  client, so it can't become a second place the logic drifts.
- **Claude Code skill** — thin `SKILL.md` wrapping the CLI (same pattern as
  the `rwe-*` scripts in `bin/` wrapped by the reading-with-ears skills), or
  calling the MCP server directly once it's registered in the session —
  decide at build time based on which is less installation friction.

## Open questions for the build phase

- Heuristic clustering (file/keyword overlap) vs. a lightweight sub-agent read
  of each session's first few messages for topic classification — the latter
  is likely more accurate but costs more per sweep. Start with heuristics,
  revisit if clusters look wrong in practice.
- Whether v1 should even include Step 5, or ship report-only first and add
  execution once the classification quality is trusted.
- Cross-repo sweep (all of `~/.claude/projects/`) is the default, since sprawl
  is inherently a cross-repo problem — single-repo scoping can be a flag.

## Safety discipline

- Read-only through Step 4; Step 5 requires explicit confirmation, tier-by-tier
  or item-by-item.
- No deletion in v1 — archive is a reversible move.
- No git state, branch, or repo content is touched.
- Mirrors `git branch --merged` hygiene: nothing is pruned without the user
  seeing the equivalent listing first and confirming it's safe.
