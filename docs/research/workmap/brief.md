# Research brief: Workmap

**Design doc:** [dhk/adventures-in-ai#39 — Design: Workmap](https://github.com/dhk/adventures-in-ai/issues/39)
**Topic slug:** `workmap`

Workmap is a proposed self-monitoring activity map: a Theme → Project →
Thread hierarchy (GitHub issues/PRs, branches/worktrees, Claude sessions),
where each Thread carries `status` / `do-next` / `go-here`, rendered as a
zoomable D3 hierarchy and kept fresh by auto-discovery plus manual override.

Every question below traces back to a specific section of issue #39. Answer
each one on its own — don't skip ahead to "how would I build this," this
brief is prior-art and landscape research, not implementation design.

## 1. Is there existing prior art for the whole concept?

> Design doc, "Problem" section: "a single place to see... what's actually
> going on right now" across repos/issues/PRs/sessions.

Are there existing tools, products, or well-known personal setups that
already solve "one map of all my active work across many
repos/projects/threads"? Include both dev-focused tools (multi-repo PR/issue
dashboards, GitHub project-board alternatives) and general personal-PKM /
second-brain tools adapted for this use, if genuinely comparable.

## 2. Status inference from GitHub issue/PR state

> Design doc, "Data sources" section, auto-discovered/GitHub: "review
> state, last-comment author (a good proxy for 'waiting on me' vs 'waiting
> on them')." Also Open Question #2: "the concrete algorithm for inferring
> `status` from GitHub API state... needs real examples, not guesses."

Do existing tools or libraries already classify a GitHub issue/PR's "waiting
on me" vs. "waiting on them" vs. "stale" status from the API? What signals
do they use beyond review-requested/changes-requested/last-commenter (e.g.
CI state, assignee, label conventions)? Cite anything with a public
algorithm or open-source implementation.

## 3. Local multi-repo / worktree state crawling

> Design doc, "Data sources" section, auto-discovered/local git state:
> "branches, worktrees... and how stale each is... across
> `~/Documents/dev/*`."

Are there existing CLI tools or scripts that scan across many local git
repos/worktrees and report branch staleness, uncommitted work, or
divergence from `main`? How do they define "stale," and do they handle
`git worktree` specifically (not just plain clones)?

## 4. Mining Claude Code session transcripts for status

> Design doc, "Data sources" section, auto-discovered/Claude sessions, and
> "Prior art in this codebase" section: `work-ledger` and `ivy-archive`
> already parse `~/.claude/projects/**/*.jsonl`.

Beyond `work-ledger` and `ivy-archive` (already known, don't re-research
those two), is there other prior art — from Anthropic, the Claude Code
community, or adjacent agent-session tooling (Cursor, Aider, etc.) — for
extracting structured "what state did this session end in" data from
session transcripts or logs?

## 5. D3 zoomable-hierarchy patterns for status dashboards

> Design doc, "Visualization" section: "A D3 zoomable hierarchy (zoomable
> treemap or radial/icicle layout)... Each thread node shows status
> (color-coded), with do-next/go-here as a hover tooltip or side panel."
> Also Open Question #5, re: reuse vs. bespoke.

What are the established D3 (or D3-adjacent, e.g. Observable Plot)
patterns for a zoomable treemap/icicle/radial layout with per-node status
color and click-to-drill-down + detail panel? Are there off-the-shelf
examples or libraries close enough to fork rather than build from scratch?

## 6. Hybrid auto-discovery + manual-override conflict resolution

> Design doc, "Data sources" section, manual overrides: "Auto-discovery
> fills gaps; manual entries always win on conflict." Also Open Question
> #6: "file format, and how staleness of a manual override itself is
> surfaced."

In other tools that combine an auto-generated data layer with manual
hand-edits that must survive regeneration (config-as-code with local
overrides, generated docs with manual annotations, dotfile managers, etc.),
what patterns exist for (a) the override file format, (b) merge/precedence
rules, and (c) flagging an override as stale (e.g. written before the
underlying auto-discovered state changed)?

## Non-goals for this research pass

- Don't design the workmap's implementation (schema, code structure, repo
  layout) — that's for the design doc / a future RFC, not this brief.
- Don't answer issue #39's Open Questions #1, #3, #4 (where the output
  lives, repo scope, and regen triggers) — those are this-user-specific
  product decisions, not things prior art can resolve.
