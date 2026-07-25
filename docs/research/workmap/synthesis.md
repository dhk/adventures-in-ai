# Synthesis: Workmap research

Sources: [`claude-findings.md`](findings/claude-findings.md) (web search, this
session) and [`perplexity-findings.md`](findings/perplexity-findings.md)
(Perplexity, pasted in independently). Two sources, gathered without either
seeing the other's answers first.

**A methodology note before the substance:** the two sources apply the
`adopt/reference` vs. `differentiate` verdict noticeably differently.
Claude's pass tends to mark any close analogue `adopt/reference` even when
it only covers part of the problem; Perplexity reserves `adopt/reference`
for things that solve a specific sub-problem precisely, and uses
`differentiate` more often for "close but not reusable as-is." Read the
*Notes* prose in each findings file as the primary signal — the verdict
labels alone aren't directly comparable across the two docs.

## 1. Prior art for the whole concept

**Agreement:** Both sources independently converge on the strongest
conclusion of the whole research pass: **no existing tool combines GitHub
API state, local git/worktree state, and AI-agent session state into one
hierarchical, drill-downable view.** Both also independently name DashGit,
Repo Dashboard (rouralberto), and gh-dashboard (debba) as the closest
GitHub-side analogues — three-way agreement on the same three tools from
two fully independent searches is a strong signal these are the right
GitHub-dashboard prior art to look at.

**Conflict — and the most important one in this pass:** Claude found
**Canopy** (two unrelated projects sharing the name, `juliensimon/canopy`
and `isacssw/canopy`) — tools specifically for managing many parallel
Claude Code sessions across git worktrees, with commands like `status`,
`state`, `resume`. Perplexity's search never surfaced Canopy at all. This
matters because Canopy overlaps directly with workmap's Thread=session
concept — the "no tool combines all three data sources" conclusion both
sources reached should be read as "no tool combines all three, but Canopy
gets two of three (worktree + session) and DashGit-style tools get GitHub."
The design doc should explicitly address why workmap isn't "Canopy plus a
GitHub crawler bolted on."

**What only one source caught:**
- Claude only: Canopy (both projects), `gh-dash` (dlvhdr — a well-known
  tool Perplexity's search missed entirely), Obsidian Canvas as a
  zoomable-but-manual PKM comparison.
- Perplexity only: octopeek, several more PR-only trackers (git-pull-request-dashboard,
  github-pr-dashboard, PR Radar, camelAI), GitKraken *Workspaces* (distinct
  from the Launchpad product Claude found), ZenHub/CodeTree, a Grafana
  GitHub-org dashboard.

**Mapped to issue #39:** Both sources support treating workmap's
three-source combination as genuinely novel, not a re-implementation —
this directly answers the implicit "are we reinventing something"
question behind the whole research commission. It does not resolve Open
Question #1 (where the output lives) or #3 (repo scope) — those remain
user-specific product decisions, as the brief said they would.

## 2. Status inference from GitHub issue/PR state

**Agreement:** Both sources converge on the same underlying answer: there
is no bespoke classification algorithm to build — every tool found
composes GitHub's own native signals (search qualifiers / `reviewDecision`
/ CI check-run state). Neither source found a public "stale" auto-classifier
based on GitHub API state alone.

**Perplexity's pass is substantially stronger here.** Claude's findings
stopped at "the qualifiers exist and gh-dash composes them." Perplexity
found actual documented algorithms with more precision:
- **Pull Reminders** (`pullreminders/backlog`) has published SQL/pseudocode
  for waiting-on-author vs. waiting-on-reviewer, using non-dismissed
  reviews vs. current requested-reviewer list.
- **Rust Forge's triage procedure** gives a battle-tested label taxonomy
  (`S-waiting-on-review`, `S-waiting-on-author`, etc.) with explicit
  transition rules per activity type.
- **`gh-wait`** (k1LoW) has a directly useful refinement neither source's
  other entries mention: **filtering out the user's own comments/approvals**
  when deciding "waiting on me" — a subtle but important signal-cleaning
  step workmap's crawler would need and might otherwise miss.

**What's genuinely unanswered:** Neither source found a public
"stale-from-inactivity" classifier for issues/PRs specifically (as opposed
to Rust's fixed manual 15-day triage cadence). This directly answers issue
#39's Open Question #2 in part (the qualifier-composition approach is the
algorithm) but leaves the specific staleness threshold as something workmap
has to define itself — both sources agree on this gap independently.

## 3. Local multi-repo / worktree state crawling

**Zero tool overlap between the two sources** — worth noting on its own:
Claude found Canopy's worktree dashboard, `git-worktree-cli`, and a blog
post on bulk-cleaning stale worktrees; Perplexity found Grove, Mars,
RepoFleet, `deadbranch`, and a CodePulse branch-aging guide. Neither
source named a single tool the other one found. That non-overlap suggests
this space is large and fragmented enough that a third pass would likely
turn up still more tools — treat both lists as partial, not exhaustive.

**A conflict worth resolving, not just noting:** the two sources define
"stale" differently, and both definitions are probably needed as separate
status values rather than one bucket:
- Claude's sources (`git-worktree-cli`, the brtkwr.com post) define stale
  as **branch merged and/or its remote-tracking ref gone** — i.e., the work
  is *done*, the worktree is just administrative debt.
- Perplexity's sources (`deadbranch`, CodePulse) define stale as
  **no commits within a configurable age threshold** (deadbranch defaults
  to 30 days; CodePulse buckets at 7/30/90 days) — i.e., the work is
  *abandoned or paused*, not necessarily finished.

These are opposite implications for workmap's `status` field (one means
"safe to archive," the other means "needs a nudge or a decision") — the
design doc should treat them as two distinct signals, not collapse them
into a single `stale` value.

**What only one source caught:** Perplexity's **Mars** find is worth
elevating specifically — it's a multi-repo workspace manager that already
shares "Claude/agent config" per tagged repo group, which is closer to
workmap's Project-level grouping + agent-session awareness than anything
in Claude's Q3 list. Worth a closer read before designing workmap's own
grouping mechanism.

## 4. Mining AI coding-agent session transcripts for status

**Strong agreement, independently corroborated:** both sources
independently landed on **`continue-claude-work`** as the single closest
piece of prior art — high-confidence signal this is the right thing to
read before writing new extraction logic. Perplexity's version is more
detailed and more useful (names the actual script, `extract_resume_context.py`,
and its session-end classification: `completed` / `interrupted` /
`error_cascade` / `abandoned`) — treat Perplexity's description as the
higher-fidelity one to act on.

**A direct factual conflict that needs verification, not just noting:**
Perplexity's pass explicitly searched for Cursor/Aider/Windsurf equivalents
and reported finding nothing — a deliberate, stated negative result, not
silence. But Claude's pass separately found **`cli-continues`**
(`yigitkonur/cli-continues`), which claims to parse **16 different AI
coding tools' native session formats** (JSONL/JSON/SQLite/YAML) — including,
implicitly, tools beyond Claude Code — specifically to extract resumable
state for handoff between tools. These two findings directly contradict
each other on whether structured session-state extraction exists outside
the Claude Code ecosystem. **This should be checked by hand** (read
`cli-continues`'s actual source, not just its README description) before
either claim is trusted — it's possible `cli-continues`'s "16 tools" claim
is aspirational/thin for non-Claude formats, which would resolve the
conflict in Perplexity's favor, but that needs confirming.

**What only one source caught:** Perplexity's **session-handoff skill**
gist (edwilde) — a prompt template that has the agent *write* a structured
status/next-steps/restoration-procedure summary at the end of a session,
rather than mining it after the fact. This is a much closer match to
workmap's own Phase 2 plan ("sessions update their own thread's status as
a side effect of work happening") than any mining-based tool, and deserves
more weight in the design doc than either source's verdict label alone
suggests.

## 5. D3 zoomable-hierarchy patterns

**Strong agreement:** both sources name the same two canonical Observable
examples (zoomable treemap, zoomable icicle) as directly forkable, and —
independently, in different words — both conclude that **no existing
example combines the zoom interaction with a persistent side detail
panel**; every example found does either zoom-only or hover-tooltip-only.
Two independent searches reaching the same specific negative conclusion is
good evidence this is a real gap to design around, not a search miss.

**Perplexity's pass is more thorough here** and adds three things Claude's
didn't find, all genuinely useful:
- The **zoomable sunburst** (radial layout) — fills in the "radial" option
  the design doc explicitly lists alongside treemap/icicle, which Claude's
  search missed.
- **D3 Gallery Vanilla JS** (takanori-fujiwara) — solves a practical
  problem neither source flagged as a risk until Perplexity found the
  fix: Observable notebook code doesn't run standalone as-is, and this is
  a full port of the same examples into plain JS.
- **Pangea Proxima's Treemap component** — an actual reusable,
  parameterized component (data/value/label/tile/group props) rather than
  a single-purpose demo, a better structural starting point than forking
  a notebook directly.

**Mapped to issue #39:** this strongly resolves Open Question #5 in favor
of forking existing D3 examples rather than building bespoke — across two
independent passes, nothing suggested the visualization needs novel D3
work beyond composing the zoom examples with a standard click-to-panel
handler and adding a status color scale.

## 6. Hybrid auto-discovery + manual-override conflict resolution

**Agreement on the core precedence pattern:** both sources independently
found Terraform's override-file mechanism (separate file, always wins,
loaded last) as the closest analogue to workmap's "manual entries always
win" rule.

**A productive disagreement about chezmoi:** Claude marked chezmoi
`differentiate`, reasoning it solves a different problem (same-repo,
different-machine templating, not generated-vs-manually-edited data).
Perplexity marked chezmoi `adopt/reference`, but for a narrower and more
precise reason: its `diff`/`status` workflow treats any manual edit to a
generated file as *drift* to be explicitly reconciled — which is the
closest documented mechanic to workmap's *staleness-detection* sub-problem,
even though chezmoi's drift direction is the inverse of what workmap needs
(local file diverging from a managed template, vs. workmap's manual
override becoming stale relative to newly observed ground truth). Claude's
verdict wasn't wrong about chezmoi's overall precedence model, but
Perplexity's read is more useful for this specific sub-problem — worth
re-reading chezmoi's diff mechanism specifically for the comparison
technique (timestamp vs. content hash), not for its overall approach.

**What only one source caught:** Perplexity found **Kustomize
overlays/patches** and **JSON Merge Patch / JSON Patch (RFC 7386 / RFC
6902)** — both give a standardized, off-the-shelf schema option for the
override file's merge semantics that neither Terraform's nor Claude's
doctoc-marker finding addresses (those establish *that* overrides should
win, not a portable *format* for expressing partial-field overrides).

**Strongly corroborated open gap:** both sources, independently and
explicitly, concluded that **no existing tool flags a manual override as
stale because the underlying auto-discovered truth has since changed**
(e.g., a hand-written "waiting-on-review" override left in place after the
PR actually merged). This is issue #39's Open Question #6 in its exact
form. Two independent research passes reaching the same specific gap is
strong evidence this is genuinely unsolved elsewhere, not a search
failure — workmap's design doc / a future RFC needs to invent this
mechanism rather than borrow one (a per-override "last-verified-against"
timestamp or hash, diffed against the crawler's fresh read each run, is
the shape both sources independently sketch as the likely answer).

## What's genuinely unanswered, across both passes

1. **Override staleness detection** (Q6) — confirmed as an open problem by
   both sources; no prior art to borrow, needs original design.
2. **CI status / label-convention signals** for status inference beyond
   review-requested/changes-requested — Claude flagged this as
   unaddressed; Perplexity's Pull Reminders and Rust Forge entries partly
   fill this in (activity-type-based label transitions) but neither source
   found a general, tool-agnostic pattern for folding CI/label state into
   a status value.
3. **Whether structured session-state extraction genuinely doesn't exist
   for Cursor/Aider/Windsurf**, or whether `cli-continues` already does it
   and Perplexity's search simply missed that tool — needs a manual check
   of `cli-continues`'s source before treating either claim as settled.
4. **A numeric staleness threshold for GitHub issues/PRs specifically**
   (as opposed to local branches, where Perplexity's sources gave concrete
   30-day / 7-30-90-day defaults) — neither source found a public default
   for this.

None of the above were answerable from documentation alone; a third
source, or hands-on testing of Canopy, `continue-claude-work`, and
`cli-continues` specifically, would be the next step if more confidence is
wanted before the design doc is finalized.
