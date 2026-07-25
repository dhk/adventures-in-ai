# Workmap research findings — `claude`

## 1. Is there existing prior art for the whole concept?

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [Canopy (juliensimon/canopy)](https://github.com/juliensimon/canopy) | Native macOS app for running parallel Claude Code sessions across git worktrees: auto-resume, merge & finish, token dashboard | Manages the exact "many concurrent AI-agent sessions across worktrees" slice of workmap's scope directly | adopt/reference |
| [canopy (isacssw/canopy)](https://github.com/isacssw/canopy) | Typed multi-repo MCP server + terminal UI for AI coding agents: `canopy status`, `state`, `triage`, `resume`, `preflight` | `canopy state`/`resume` is close to workmap's `status`/`go-here` fields, scoped to sessions+worktrees only (no GitHub issues, no theme hierarchy, no D3) | adopt/reference |
| [gh-dash (dlvhdr/gh-dash)](https://github.com/dlvhdr/gh-dash) | Terminal UI showing user-defined, per-repo sections of PRs/issues across many repos | Cross-repo aggregation + custom status sections, no worktree/session layer | adopt/reference |
| [DashGit (javiertuya/dashgit)](https://github.com/javiertuya/dashgit) | Dashboard consolidating open issues, PRs, review requests, branches, and statuses across GitHub + GitLab in one view | Closest single "one view of all my open threads" match; no theme grouping, no session data, no zoomable viz | adopt/reference |
| [Repo Dashboard (Alberto Roura)](https://albertoroura.com/repo-dashboard-local-github-visibility-tool/) | Local-first tool, no setup beyond a GitHub token, aggregates issues/PRs/branches | Matches workmap's "local, low-friction, auto-discovered" design goal | adopt/reference |
| [gh-dashboard (debba)](https://github.com/debba/gh-dashboard) | Kanban board + repo "insights" (Strong/Watch/Risky status per repo) + daily digest with an executive summary | The per-repo derived status label and daily digest are close analogues to workmap's Project-level rollup status and a "what changed" digest | adopt/reference |
| [GitKraken Launchpad](https://www.gitkraken.com/features/launchpad) | Commercial unified dashboard for PRs/issues/tasks across GitHub, GitLab, Bitbucket, Jira | Multi-provider aggregation at team/commercial scale; no worktree/session tracking, no do-next/go-here concept | differentiate |
| [Graphite Insights / PR dashboard](https://graphite.com/guides/github-pr-dashboard) | Org-wide "universal inbox" of PRs needing your attention | PR-only, no issues/branches/sessions, no theme/project hierarchy | differentiate |
| [Obsidian Canvas](https://www.obsibrain.com/blog/obsidian-canvas-complete-guide) used as a project dashboard (with Dataview/Kanban embeds) | Manually built, pannable/zoomable board of project notes and embedded queries | Matches the "zoom into clusters" UX goal, but is manually curated, not auto-discovered from GitHub/git/sessions | differentiate |

**Notes:** The single biggest finding here is `Canopy` (two unrelated projects share the name — `juliensimon/canopy` and `isacssw/canopy` — both aimed at exactly "many parallel Claude Code sessions across worktrees, one view, resume support"). This overlaps enough with workmap's Thread=session concept that the design doc should explicitly say why workmap isn't just "point Canopy at your repos" — e.g. Canopy doesn't ingest GitHub issues/PRs or do theme-level rollups or a D3 zoomable view, but the session-state/resume piece may be directly reusable or worth evaluating as a dependency rather than reimplementing. DashGit and Repo Dashboard are the closest matches for the GitHub-aggregation half; none of the entries found combine GitHub + local git + AI-session state in one hierarchy the way workmap proposes — that three-way combination looks like the genuinely novel part.

## 2. Status inference from GitHub issue/PR state

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [GitHub search qualifiers](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests) (`review-requested:@me`, `involves:@me -author:@me`, `author:@me`, `is:open`) | GitHub's own first-party search syntax for issue/PR state | This *is* the concrete classification algorithm workmap needs — status buckets are qualifier combinations, not a bespoke heuristic | adopt/reference |
| [gh-dash section config using the same qualifiers](https://www.gh-dash.dev/configuration/examples/) | gh-dash's own config examples build "Needs My Review" (`is:open review-requested:@me`) and "Waiting for Author" (`is:open involves:@me -author:@me`) sections from those qualifiers | Directly shows the qualifier-combination pattern applied to build the exact "waiting on me / waiting on them" buckets workmap wants | adopt/reference |
| [`gh search prs --review-requested=@me`](https://cli.github.com/manual/gh_search_prs) | GitHub CLI's native flag wrapping the same qualifier | Same algorithm, CLI-native form, easy to shell out to instead of hitting the REST/GraphQL API directly | adopt/reference |
| [Octobox](https://github.com/github/octobox) | GitHub-official (now archived) notification-triage app; tags notifications with PR/issue state, CI status, labels | Looked like a strong candidate but its actual "waiting on me" classification logic wasn't surfaced in what I could find — may need a source-read, not just docs, to confirm it has one | ignore |

**Notes:** No source found a bespoke inference algorithm beyond composing GitHub's own search qualifiers — that's good news for workmap: the "concrete algorithm" issue #39 asks for (Open Question #2) is largely "which qualifier combination maps to which status label," not a novel classifier. CI state and label conventions (also asked about in the brief) weren't clearly covered by any single source — that's a gap, see below.

## 3. Local multi-repo / worktree state crawling

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [Canopy worktree dashboard](https://medium.com/@ashmitbbiswas/git-worktrees-are-great-managing-them-across-3-repos-is-not-12262be5ddb0) | Single command showing every feature/repo, dirty file counts, ahead/behind status, which branches are checked out where | Near-exact match for workmap's "local git state" auto-discovery source | adopt/reference |
| [git-worktree-cli (jeffersongoncalves)](https://github.com/jeffersongoncalves/git-worktree-cli) | Audits worktrees, checks whether their branches are merged into main, prunes stale worktree records | Gives a concrete, citable definition of "stale": branch merged and/or remote-tracking ref gone | adopt/reference |
| [Bulk cleaning stale git worktrees post (brtkwr.com)](https://brtkwr.com/posts/2026-03-06-bulk-cleaning-stale-git-worktrees/) | Blog post/script defining a worktree as stale when its remote tracking branch no longer exists | Same staleness definition from a second independent source — corroborates rather than duplicates the entry above | adopt/reference |
| [worktree-cli (fnebenfuehr)](https://github.com/fnebenfuehr/worktree-cli), [wtree](https://github.com/ozeron/wtree), [git-worktree-manager (nanasess)](https://github.com/nanasess/git-worktree-manager) | Simpler worktree create/switch/remove CLIs | CRUD-focused, not dashboard/status-reporting tools — useful only as "what verbs exist," not as a status-crawling pattern | ignore |

**Notes:** "Stale" converges on one clean, citable definition across two independent sources: the worktree's branch has no live remote-tracking ref (deleted after merge) or is already merged into `main`. That's directly usable as the `stale` status value in workmap's Thread status enum, separate from `git worktree list --porcelain`'s own staleness (administrative files pointing at a removed directory), which is a different, narrower kind of "stale."

## 4. Mining Claude Code session transcripts for status

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [`continue-claude-work` skill](https://skills-anthropic.vercel.app/skill/continue-claude-work) | A Claude skill that reconstructs actionable context from a session: latest compact summary, pending work, known errors, current workspace state | Near-exact match for what workmap needs to derive `do-next`/`go-here` from a session transcript | adopt/reference |
| [cli-continues (yigitkonur/cli-continues)](https://github.com/yigitkonur/cli-continues) | Parses 16 different AI coding tools' native session formats (JSONL/JSON/SQLite/YAML, including Claude Code) and extracts recent messages, file changes, tool activity, and reasoning to resume in another tool | Directly relevant multi-format parsing prior art if workmap ever needs to track sessions from tools beyond Claude Code | adopt/reference |
| ["clerk" tool](https://dev.to/vulcan_shen_acdbffa0285d2/clerk-auto-summarize-your-claude-code-sessions-4m87) | Auto-summarizes Claude Code sessions; returns past summaries and transcript paths | Same problem as workmap's session-thread summarization, narrower scope (summarize only, not classify status) | adopt/reference |
| [claude-code-history-viewer (jhlee0409)](https://github.com/jhlee0409/claude-code-history-viewer) | Desktop app to browse and analyze Claude Code conversation history | Useful as a UI-pattern reference for a session detail view, not for status extraction itself | differentiate |
| [Simon Willison — extracting detailed transcripts from Claude Code](https://simonw.substack.com/p/a-new-way-to-extract-detailed-transcripts) | Background piece on the JSONL transcript format and extraction technique | Useful format documentation, not a status-classification tool | reference material — closest verdict: differentiate |

**Notes:** This is the area with the most direct, close prior art relative to workmap's own stated intent to reuse `work-ledger`/`ivy-archive` rather than reinvent — `continue-claude-work` in particular looks close enough to workmap's `do-next`/`go-here` derivation that it's worth reading its actual implementation (not just the description) before writing new extraction logic.

## 5. D3 zoomable-hierarchy patterns for status dashboards

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [Observable: Zoomable treemap (@d3/zoomable-treemap)](https://observablehq.com/@d3/zoomable-treemap) | Canonical D3 example: click any cell to zoom in, click the top bar to zoom out, via rescaling the x/y domains | Directly matches the "zoomable treemap" option in the design doc's Visualization section | adopt/reference |
| [Observable: Zoomable icicle (@d3/zoomable-icicle)](https://observablehq.com/@d3/zoomable-icicle) | Shows three layers of a hierarchy at a time; click a node to zoom in, click the left column to zoom out | Even closer match than the treemap to a Theme→Project→Thread three-level structure shown a level at a time | adopt/reference |
| [Zoomable Icicle gist (mbostock)](https://gist.github.com/mbostock/1005873) | D3 creator's original reference implementation of the zoomable icicle | Canonical source implementation to fork from | adopt/reference |
| Various forks/templates (andyburnett, john-guerra, ganeshv gist, codepen "Zoomable Treemap v4") | Community forks of the same Observable examples | Redundant with the canonical Observable notebooks above, no incremental pattern | ignore |

**Notes:** Both canonical layouts (zoomable treemap, zoomable icicle) are maintained, documented, forkable Observable notebooks — the design doc's "treemap or radial/icicle" framing maps directly onto these two, and the icicle in particular already implements "show N layers, click to drill down" which is exactly the interaction workmap describes. This strongly supports Open Question #5 leaning toward forking rather than building bespoke.

## 6. Hybrid auto-discovery + manual-override conflict resolution

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| [Terraform/OpenTofu override files](https://developer.hashicorp.com/terraform/language/files/override) | A separate `*_override.tf` file whose values always take precedence over the base config, merged at load time with documented merge semantics | Directly matches workmap's "separate manual-override file, manual always wins" design | adopt/reference |
| [Docker Compose override files](https://docker.recipes/docs/compose-overrides) | `docker-compose.override.yml` layered on top of a base `docker-compose.yml` | Same base+override layering pattern from a second, very widely-used tool | adopt/reference |
| [doctoc's generated-section markers](https://github.com/thlorenz/doctoc) (`<!-- START doctoc generated TOC -->` … `<!-- END doctoc generated TOC -->`) | Regeneration only touches content between two HTML-comment markers in the same file; everything outside the markers (i.e. manual content) is left untouched | A genuinely different pattern from the separate-override-file approach: instead of two files merged, one file with an auto-owned region and a manually-owned region | adopt/reference |
| [chezmoi machine-specific templating](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/) | Templates rendered per-machine from local config data; later directives override earlier ones | Solves a same-repo-different-machine problem, not an auto-generated-vs-manually-edited problem — precedence mechanics are adjacent but the use case doesn't match | differentiate |

**Notes:** Two structurally different, both well-established patterns are available: (a) separate override file merged over generated output (Terraform/Compose), or (b) marker-delimited manual region inside the same generated file (doctoc). Workmap's design doc already leans toward (a) ("a small YAML/JSON file... manual entries always win"), which is the more common and better-documented of the two for structured (non-prose) data — (b) is more natural for the free-text `go-here`/`do-next` fields specifically, so a hybrid (structured overrides in a sidecar file, but `go-here` text editable in a marked region) may be worth considering.

## Open gaps

- No source directly addressed **staleness-flagging of a manual override itself** (issue #39's Open Question #6b: surfacing that a hand-written `do-next` is 3 weeks old relative to newer auto-discovered state). Searched for generated/manual-merge tools that timestamp or expire manual annotations specifically and found only general "last verified" / annotation-merge tooling unrelated to this exact problem — this looks like it may be a genuinely under-addressed gap rather than something I failed to find, but a second source should confirm before treating it as novel.
- **CI status and label-convention signals** for status inference (part of Question 2's "beyond review-requested/changes-requested/last-commenter") weren't clearly covered by any single source — every tool found composes GitHub's built-in search qualifiers, and none of the sources documented incorporating CI/label state into a status label in a generalizable way.
- Didn't evaluate any tool by actually installing/running it — this pass is docs/README-level only, per the brief's non-goals. A follow-up pass (or the synthesis step) should flag if hands-on testing of Canopy, DashGit, or `continue-claude-work` specifically is worth doing before workmap's design doc is finalized, given how close those three are to the proposed scope.
