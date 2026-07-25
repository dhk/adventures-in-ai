You are doing prior-art / competitive research to de-risk a design doc
called "Workmap." Answer the questions below independently — you have not
seen and should not seek out any other source's answers to this same
brief. Web search is expected; don't rely on your own recall alone.

## Context

Workmap is a proposed personal tool: a self-monitoring activity map for
someone with many concurrent projects/repos/issues/PRs/AI-agent sessions
going at once. It's structured as a Theme → Project → Thread hierarchy
(where a Thread is a single GitHub issue, PR, git branch/worktree, or AI
coding-agent session). Every Thread carries three fields:

- `status` — what it's currently blocked on (e.g. waiting-on-review,
  waiting-on-user-input, in-progress, stale)
- `do-next` — the single next concrete action
- `go-here` — instructions to resume/continue the work

Data is meant to come from a hybrid of auto-discovery (crawling GitHub API
state, local git/worktree state, and AI-agent session transcripts) plus a
manual-override file for cases the crawler can't infer, with manual entries
always winning on conflict. It's meant to render as a zoomable D3
hierarchy (treemap or radial/icicle), color-coded by status, with a
click-to-drill-down detail panel — plus a flat filterable-table fallback
view for quick scanning.

## Your task

Answer each question below. For each, list concrete entries (named tools,
libraries, articles, projects — not vague categories), and for each entry
give: what it is, how it overlaps with the workmap concept described
above, and a verdict.

**Verdict must be exactly one of:** `adopt/reference` (directly usable or a
pattern worth copying), `differentiate` (relevant, but workmap should do
this differently — say why in your notes), or `ignore` (surfaced but not
actually relevant). Do not invent other verdict labels.

**If a question turns up nothing after a real search, say so explicitly**
(what you searched, why you believe it's genuinely absent) rather than
leaving it blank.

### 1. Is there existing prior art for the whole concept?

Are there existing tools, products, or well-known personal setups that
already solve "one map of all my active work across many
repos/projects/threads"? Include both dev-focused tools (multi-repo
PR/issue dashboards, GitHub project-board alternatives) and general
personal-PKM/second-brain tools adapted for this use, if genuinely
comparable.

### 2. Status inference from GitHub issue/PR state

Do existing tools or libraries already classify a GitHub issue/PR's
"waiting on me" vs. "waiting on them" vs. "stale" status from the GitHub
API? What signals do they use beyond review-requested /
changes-requested / last-commenter (e.g. CI state, assignee, label
conventions)? Cite anything with a public algorithm or open-source
implementation.

### 3. Local multi-repo / worktree state crawling

Are there existing CLI tools or scripts that scan across many local git
repos/worktrees and report branch staleness, uncommitted work, or
divergence from `main`? How do they define "stale," and do they handle
`git worktree` specifically (not just plain clones)?

### 4. Mining AI coding-agent session transcripts/logs for status

Is there prior art — from Anthropic/Claude Code, or adjacent AI coding-agent
tooling (Cursor, Aider, Windsurf, etc.) — for extracting structured "what
state did this session end in" data from agent session transcripts or
logs, for the purpose of resuming or tracking work?

### 5. D3 zoomable-hierarchy patterns for status dashboards

What are the established D3 (or D3-adjacent, e.g. Observable Plot)
patterns for a zoomable treemap/icicle/radial layout with per-node status
color and click-to-drill-down + detail panel? Are there off-the-shelf
examples or libraries close enough to fork rather than build from scratch?

### 6. Hybrid auto-discovery + manual-override conflict resolution

In other tools that combine an auto-generated data layer with manual
hand-edits that must survive regeneration (config-as-code with local
overrides, generated docs with manual annotations, dotfile managers, etc.),
what patterns exist for (a) the override file format, (b) merge/precedence
rules, and (c) flagging an override as stale (e.g. written before the
underlying auto-discovered state changed)?

## Non-goals

Don't design the implementation (schema, code structure, repo layout) —
just report what already exists. Don't try to answer "where should the
output live," "what repo scope," or "what triggers a regen" — those are
product decisions specific to the requester, not things prior art can
resolve.

## Output format

Return one section per question above, in order, each with a table:

`Entry | What it is | Workmap concept overlap | Verdict`

followed by a Notes paragraph, and a final "Open gaps" section for
anything you couldn't resolve. Plain markdown, no other format needed.
