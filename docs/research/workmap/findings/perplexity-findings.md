# Workmap research findings — `perplexity`

## 1. Prior art for the whole concept ("one map of all my active work")

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| GitHub native Issues/PR dashboards + saved views | Built-in cross-repo issue/PR lists with up to 25 saved search-based views[^1] | Covers auto-discovery of GitHub state but flat list only, no hierarchy, no status inference beyond raw fields, no manual overrides | differentiate |
| DashGit | Browser-only dashboard aggregating issues, PRs, review requests, branches, build status across GitHub/GitLab repos, with a "manager repo" for follow-up reminders[^2] | Same auto-discovery goal (GitHub API crawl, multi-repo), has a "follow-up reminder" concept close to do-next/manual annotation, but flat tabbed UI, no Theme→Project→Thread hierarchy, no local git/worktree or AI-agent layer | differentiate |
| octopeek | Keyboard-driven TUI unifying PR/issue inbox across repos by role (author/reviewer/assignee)[^3] | Overlaps on "what needs my attention across many repos" but terminal-only, no hierarchy/visualization, no local or agent-session data | differentiate |
| Repo Dashboard (rouralberto) | Local-first Node app showing a three-column (issues/PRs/branches) view per selected org/repos[^4] | Matches "local-first personal tool" instinct and includes branches, but no worktree/agent data, no manual override layer, flat table only | differentiate |
| gh-dashboard (debba) | Self-hosted dashboard pulling REST+GraphQL data: issues, PRs, commits, Actions runs, stars, mentions per repo, with server-side token handling[^5] | Broad auto-discovery breadth is comparable, but again flat/tabular, single-source (GitHub only, no worktree/agent), no explicit status taxonomy or override file | differentiate |
| git-pull-request-dashboard, github-pr-dashboard, PR Radar, camelAI GitHub dashboards | Various open-source/commercial multi-repo PR trackers (CI status, review state, age)[^6][^7][^8][^9] | All solve the "PR portion" of Workmap's Thread layer; none add issues+branches+agent sessions in one hierarchy or the manual-override mechanism | differentiate |
| GitKraken Workspaces | Commercial multi-repo grouping tool showing open PRs, insights (throughput, merge rate), filters across a defined repo set[^10][^11] | Closest commercial analogue to "Theme/Project" grouping of many repos with PR-level detail, but no branch-level worktree awareness, no AI-agent transcript ingestion, no D3 hierarchy visualization, closed-source | differentiate |
| ZenHub / CodeTree | Multi-repo issue/board tools layered on top of GitHub, letting teams manage issues across repos in one board[^12] | Solves cross-repo issue aggregation for teams, but oriented around kanban boards, not personal solo-maintainer status/resume workflows, and no local/agent state | ignore |
| Grafana GitHub Organization dashboard | Prebuilt Grafana dashboard visualizing issue/PR counts and active/inactive states across an org via a GitHub data source[^13] | Demonstrates color-coded "active vs needs attention" states similar to Workmap's status coloring, but it's aggregate metrics, not a per-thread drill-down map | ignore |

**Notes:** No tool found combines all four data sources Workmap targets (GitHub API, local git/worktree, AI-agent session transcripts, manual overrides) into a single hierarchical, drill-downable, status-colored view. The closest analogues are multi-repo PR/issue dashboards (DashGit, gh-dashboard, GitKraken Workspaces), all of which stop at "list of items with filters" rather than a Theme→Project→Thread zoomable hierarchy, and none ingest AI coding-agent session state. On the PKM/second-brain side, searches for "second brain" or "PKM" tools adapted to this exact use case (Obsidian/Notion-based dev work trackers) surfaced only generic task-plugin ecosystems (e.g., Obsidian Dataview) used for note-querying, not GitHub/git/agent-state aggregation — genuinely adjacent but not comparable enough to list as direct prior art beyond the pattern noted in Question 6. Workmap's specific combination (hierarchy + tri-field status/do-next/go-here schema + hybrid auto+manual data + dual visualization modes) appears to be a novel synthesis rather than a re-implementation of an existing product.[^14]

## 2. Status inference from GitHub issue/PR state

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| Pull Reminders (pullreminders/backlog) | SaaS + open-sourced issue tracker with a documented "waiting on author" vs "waiting on reviewer" algorithm, including SQL and pseudocode for stale-review detection[^15] | Directly matches the status field's core problem: distinguishing "waiting-on-review" from "waiting-on-user-input"/stale using non-dismissed reviews vs. current requested-reviewer list and review-request timestamps | adopt/reference |
| Rust Forge triage procedure (S-waiting-on-* labels) | Documented human triage workflow using explicit status labels (waiting-on-review, waiting-on-author, waiting-on-t-lang, waiting-on-bors, etc.) plus rules for flipping labels based on activity type (CI failure, new review, new commit)[^16] | Provides a battle-tested taxonomy and transition rules very close to Workmap's "status: waiting-on-review / waiting-on-user-input / in-progress / stale" set, including "no activity in N days → escalate" logic | adopt/reference |
| Suricata GitHub PR workflow doc | Documents draft-vs-ready, changes-requested-vs-approved states and gives concrete `gh pr list` / search-qualifier filters (`review:changes-requested`, `review:approved`, `review:none`) for deriving state via GitHub CLI[^17] | Gives directly reusable GitHub CLI/API filter queries for the crawler component (review decision, draft state) | adopt/reference |
| gh-wait (k1LoW) | GitHub CLI extension that polls PR/issue/discussion/workflow-run state and fires an action when a specific condition (approved, CI completed, commented) is met[^18] | Encodes discrete, checkable state-transition signals (approved, CI-completed, commented) that map onto Workmap's status enum, and its self-comment filtering (ignoring the user's own comments/approvals when deciding "waiting on me") is a directly relevant signal-refinement pattern | adopt/reference |
| GitHub's own review-decision field (`reviewDecision`) and REST/GraphQL review/CI status endpoints | Native API fields (`REVIEW_REQUIRED`, `APPROVED`, `CHANGES_REQUESTED`, check-run conclusions, `mergeable_state`) | These are the raw signals every tool above is built on; Workmap's crawler would consume the same fields directly | adopt/reference |
| Trigger.tools GitHub PR Review Router | A commercial low-code "automation" that surfaces "what each PR is waiting on" for reviewers/authors[^19] | Same problem framing but no public algorithm or code shown, closed/no-code platform | ignore |

**Notes:** The clearest, publicly documented algorithms combine (a) GitHub's native `reviewDecision` and check-run/CI status, (b) whether a reviewer still has an open review request versus having already submitted a non-dismissed review, and (c) last-actor/last-comment attribution with self-action filtering. None of these tools produce a "stale" classification purely from GitHub state without an explicit human-triage cadence (Rust's is manual, 15-day threshold); Workmap would need to combine last-updated timestamp thresholds itself, as no crawler-side "stale" auto-classifier with a public spec was found beyond simple "sort by updated-asc" filters.[^15][^18][^16][^17]

## 3. Local multi-repo / worktree state crawling

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| Grove (gw) | Python CLI managing git worktree-based workspaces spanning multiple repos; `gw status <workspace>` reports git status across all repos in a named workspace[^20] | Directly addresses "local multi-repo worktree state crawling," explicitly worktree-native (not just clones) | adopt/reference |
| Mars | Multi-repo workspace manager (`mars.yaml`) with `mars status` showing dirty files, branch info, and sync state across tagged repo groups, plus shared Claude/agent config per workspace[^21] | Overlaps closely with Workmap's Project grouping and even shares "agent config" per repo group, but is clone-based, not worktree-first, and no explicit staleness metric | differentiate |
| RepoFleet | CLI for creating/switching/removing branches across multiple repos simultaneously with a unified terminal status dashboard of uncommitted changes and current branch per repo[^22] | Matches "branch divergence/uncommitted work across many repos" reporting goal | differentiate |
| deadbranch | Rust CLI defining "stale" as branches with no commits in the last 30 days (configurable), used for safe cleanup rather than status reporting[^23] | Gives one concrete, adoptable numeric default for "stale" branch age threshold | adopt/reference |
| Ad hoc branch-aging bash scripts (e.g., CodePulse guide) | Shell scripts computing branch age via `git for-each-ref` + last-commit timestamp, bucketed into fresh/aging/stale/fossilized (7/30/90-day thresholds)[^24] | Gives a directly reusable, simple staleness algorithm and threshold scheme that a crawler can replicate without new tooling | adopt/reference |
| GitHub native "stale branch" label | GitHub itself flags branches with no recent activity in the branch listing UI[^24] | Confirms staleness-by-inactivity is an established convention, but it's UI-only, not a queryable local signal | ignore |

**Notes:** None of the surfaced worktree-aware tools (Grove, Mars) publish an explicit "staleness" definition — they report current state (dirty/clean, ahead/behind) rather than classifying age-based staleness; the age-threshold pattern instead comes from branch-cleanup tools (deadbranch, ad hoc scripts) that were not built with worktree support and assume plain clones. Workmap would need to combine a worktree-aware status crawl (Grove/Mars style, using `git worktree list --porcelain` semantics) with a separately-sourced age-threshold rule (deadbranch/CodePulse style) since no single existing tool does both.[^23][^24]

## 4. Mining AI coding-agent session transcripts/logs for status

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| continue-claude-work skill | A published Claude Skill with a bundled script (`extract_resume_context.py`) that parses `~/.claude/projects/*.jsonl`, finds the last compaction boundary, classifies session end reason (completed / interrupted / error_cascade / abandoned), extracts pending work, files touched, and git state, producing a structured "briefing" for resuming[^25] | This is the single closest piece of prior art to Workmap's "mine agent session transcripts for status/do-next/go-here": it already implements JSONL parsing, end-state classification, and pending-work extraction from Claude Code sessions specifically | adopt/reference |
| Claude Code native `--resume` / `/resume` and session JSONL storage | Claude Code persists every session continuously as local JSONL transcripts under `~/.claude/projects/`, and provides `--resume`/`--continue` to replay them[^26][^27][^28] | Confirms the raw data source Workmap would crawl exists and is documented, but native resume replays the whole transcript rather than emitting structured status/next-action fields | differentiate |
| Claude Code session-handoff skill (gist, edwilde) | A SKILL.md prompt template instructing Claude to write a structured Markdown "session summary" (goal, completed, in-progress, blocking issues, next steps, restoration procedure) at end of session[^29] | Directly matches Workmap's status/do-next/go-here schema conceptually — it's a manual/LLM-generated version of exactly those three fields, written by the agent itself rather than mined after the fact | adopt/reference |
| KeepGoing (keepgoing.dev) | A third-party tool that connects to Claude Code, gathers session context from git activity plus session notes, and gives a "recap" on return to a project[^28] | Same goal as Workmap's agent-session ingestion layer (turn scattered agent activity into a resumable status), but it's an external hosted product rather than a documented open algorithm | differentiate |
| Cursor / Aider / Windsurf session logs | Search for public, structured "session end-state" extraction specs from these tools' logs turned up no equivalent open-source implementation; Aider keeps a `.aider.chat.history.md` and `.aider.input.history` but no known structured state-extraction tool was found for it | Partial data-source overlap (Aider does persist chat history to a file that could be crawled) but no existing "extract resumable status" tooling | ignore |

**Notes:** Prior art here is genuinely present but narrow: only the Claude Code ecosystem has both (a) a stable, documented JSONL transcript format and (b) at least one open community tool (continue-claude-work) that parses it into structured resumable state, plus a prompt-engineering pattern (handoff skill) for having the agent self-report state in the exact status/do-next/go-here shape. For Cursor, Aider, and Windsurf specifically, repeated searches ("Cursor session transcript structured extraction," "Aider session log resume state," "Windsurf agent log parse status") returned no comparable public algorithm or tool — this is a genuine gap, not an oversight, likely because those tools either don't persist transcripts in as durable/documented a format or the ecosystem around them hasn't produced a public parser yet.[^29][^25]

## 5. D3 zoomable-hierarchy patterns for status dashboards

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| Observable "Zoomable treemap" (d3/zoomable-treemap) | Canonical D3 example: click-to-zoom treemap using `d3.hierarchy` + custom tiling, breadcrumb-style zoom-out via top bar[^30] | This is the direct off-the-shelf pattern for Workmap's treemap rendering mode, including the zoom/breadcrumb interaction Workmap wants for drill-down | adopt/reference |
| Observable "Zoomable icicle" | Canonical D3 example using `d3.partition()` for an icicle layout with click-to-zoom-in and click-top-to-zoom-out[^31][^32] | Direct match for the "icicle" layout option Workmap lists as an alternative to treemap; same interaction model, well documented and forkable (gists exist for multiple D3 versions)[^32][^33] | adopt/reference |
| Observable "Zoomable sunburst" (D3 gallery) | Radial equivalent of the icicle, same partition-layout approach rendered as arcs[^34] | Direct match for the "radial" layout option Workmap lists | adopt/reference |
| D3 Gallery Vanilla JS (takanori-fujiwara) | A full port of every Observable D3 example (including zoomable treemap/icicle/sunburst, collapsible tree, zoomable circle packing) into plain JS usable outside Observable's runtime, with source on GitHub[^34] | Solves the practical friction of adapting Observable-notebook code to a standalone app — directly forkable base for Workmap's implementation | adopt/reference |
| Pangea Proxima Treemap component | A reusable, parameterized D3 Treemap component (data/value/label/tile/group props) built for reuse across dashboards rather than a single notebook demo[^35] | Closer to a "library" than a demo — a good structural reference for building a reusable status-colored treemap component with a `group`/color accessor | adopt/reference |
| Click-to-drill-down + separate detail panel (as opposed to in-place zoom-only) | No single canonical example combines a zoomable hierarchy with a *separate* side detail panel on click, in the sources found; existing examples handle "zoom" and "tooltip on hover" but the side-panel-on-click pattern is assembled by combining a zoom example with a standard "click node → update side div" handler, not something with dedicated prior art | Directly what Workmap needs (drill zoom + persistent detail panel), but must be composed from the zoom examples plus ordinary DOM event handling rather than found as one packaged example | differentiate |

**Notes:** All three layout variants Workmap considers (treemap, icicle, radial/sunburst) have mature, well-documented, directly-forkable Observable/D3 reference implementations using the same `d3.hierarchy`/`d3.partition` primitives, so this is the strongest "adopt, don't rebuild" area of the whole prior-art review. Per-node status coloring is a trivial extension of these examples (swap the existing depth/size color scale for a categorical scale keyed on a `status` field) and was not found as a distinct blocking problem in any source. The detail-panel-on-click UX is the one piece that needs original composition rather than forking, since it's a straightforward but not pre-packaged combination of the zoom examples with a standard click-to-update-panel handler.[^34][^30][^32]

## 6. Hybrid auto-discovery + manual-override conflict resolution

| Entry | What it is | Workmap concept overlap | Verdict |
|---|---|---|---|
| Terraform override files (`*_override.tf` / `override.tf`) | Native mechanism where files with a special suffix/name are loaded last and merged attribute-by-attribute into blocks with the same header from the main config, with later-loaded overrides taking precedence and nested blocks replaced wholesale rather than deep-merged[^36] | This is a directly analogous, well-specified precedence model: "override always wins," matching Workmap's "manual entries always win on conflict" rule, and shows the tradeoff of block-replace vs. attribute-merge granularity that Workmap will need to choose between | adopt/reference |
| chezmoi templates + `chezmoi diff`/`status`/merge workflow | Dotfile manager where generated ("applied") files are produced from source templates; local drift is detected via `chezmoi status`/`diff`, and a documented conflict-resolution workflow captures local edits before pulling remote template changes, forcing explicit reconciliation rather than silent overwrite[^37][^38] | Directly relevant to "flagging an override as stale": chezmoi's model treats any manual edit to a generated file as *drift* to be captured and either kept or discarded, which is the closest documented pattern for detecting when a manual override predates a template/regeneration | adopt/reference |
| Kustomize overlays/patches (`patchesStrategicMerge`, `patches`) | Base config + ordered overlay patches, where overlay patches apply after and on top of base-generated resources, with well-defined ordering/merge semantics for lists vs. scalars[^39] | Provides an alternative precedence model (ordered patch layers rather than single override file) worth considering if Workmap ever needs partial-field overrides rather than whole-Thread overrides | differentiate |
| "DO NOT EDIT" banner convention (protobuf generated code, Debian lintian `generated-file` tag, dotfiles "do not edit below this line") | Ubiquitous convention of a comment banner marking generated vs. hand-edited regions in the same file[^40][^41][^42] | Establishes the informal, widely-recognized alternative to a separate override *file*: marking regions in a single file. Relevant as a rejected-alternative pattern since Workmap's brief already specifies a separate manual-override file rather than inline markers | differentiate |
| JSON Merge Patch / JSON Patch (RFC 7386 / RFC 6902) style semantics (as used by kustomize's `patchesJson6902`) | Standardized formats for expressing "apply this diff on top of a base document," with explicit rules for null-deletes-key vs. replace-value | Gives a standardized, off-the-shelf schema option for the override file's merge semantics rather than inventing a bespoke format | adopt/reference |
| Staleness flagging via file mtime/checksum comparison (general pattern seen in build tools, e.g., Terraform's own state/plan diffing, Make-style mtime checks) | No tool in this search implements exactly "flag manual override as stale if written before the underlying auto-discovered state changed," but the closest documented instance is chezmoi's status/diff detecting when the *applied* file has drifted from what the *source* would generate, which is the inverse of Workmap's stale-override problem[^37] | Confirms this specific direction (override-vs-current-truth staleness, rather than generated-vs-source drift) is not solved off the shelf; a bespoke timestamp/hash comparison between the override entry and the crawler's last-seen state for that Thread would need to be built | ignore |

**Notes:** Precedence rules ("manual always wins") and merge-file formats are well precedented (Terraform overrides, kustomize patches, JSON Merge Patch), and the closest real analogue to detecting *drift* between generated and hand-edited state is chezmoi's diff/status workflow — though chezmoi flags drift in the opposite direction (local file diverging from the managed template) rather than Workmap's need (a manual override becoming stale relative to newly observed auto-discovered ground truth, e.g., a "waiting-on-review" override left in place after the PR was actually merged). No tool found implements that specific override-staleness detection directly; it appears to be a genuine gap requiring bespoke logic (e.g., storing a "last-verified-against" timestamp or hash per override entry and diffing against the crawler's fresh read).[^36][^39][^37][^38]

## Open gaps

- No public, open-source tool combines GitHub API state, local git/worktree state, and AI-agent transcript state into one hierarchical personal dashboard — Workmap's overall concept appears to be a genuine synthesis rather than a re-implementation, confirmed via multiple searches on "personal work map," "multi-repo PR issue dashboard," and PKM-adjacent terms.
- No public algorithm was found for classifying a GitHub PR/issue as "stale" purely from API signals (as opposed to a fixed manual review cadence, as in Rust's 15-day triage rule); this remains a threshold Workmap will have to define itself.
- No structured session-state extraction tooling was found for Cursor, Aider, or Windsurf specifically (searched directly); only the Claude Code ecosystem has a documented transcript format and community parser (continue-claude-work).
- No off-the-shelf example combines a D3 zoomable hierarchy with a persistent side detail panel on click (only zoom-only or tooltip-only patterns exist); this will require composing existing zoom examples with standard DOM event handling.
- No existing tool implements "flag a manual override as stale because the underlying auto-discovered state has since changed" (as distinct from detecting drift in a generated file itself, which chezmoi does solve) — this appears to be a genuine, unaddressed gap in the prior art surveyed.

---

## References

1. [Viewing all issues and pull requests - GitHub Docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/viewing-all-of-your-issues-and-pull-requests) - The Issues and Pull Request dashboards list the open issues and pull requests you've created, as wel...

2. [GitHub - javiertuya/dashgit: DashGit - A Dashboard for GitHub and GitLab repositories. Consolidates in a single view all your open issues, PRs, review requests, branches and statuses. Combine and merge dependency updates from dependabot PRs.](https://github.com/javiertuya/dashgit) - DashGit - A Dashboard for GitHub and GitLab repositories. Consolidates in a single view all your ope...

3. [octopeek 0.3.0](https://docs.rs/crate/octopeek/latest)

4. [Repo Dashboard - A Local GitHub Visibility Tool](https://albertoroura.com/repo-dashboard-local-github-visibility-tool/) - When you're working across multiple repositories in an organization, keeping track of what's happeni...

5. [I built a local GitHub dashboard because managing many public/private repos was getting messy.](https://www.reddit.com/r/webdev/comments/1t1lfia/i_built_a_local_github_dashboard_because_managing/) - I built a local GitHub dashboard because managing many public/private repos was getting messy.

6. [GitHub - AKharytonchyk/git-pull-request-dashboard](https://github.com/AKharytonchyk/git-pull-request-dashboard) - The GitHub PR Dashboard offers a comprehensive view of PRs, making it an essential resource for effi...

7. [GitHub - rschuft/github-pr-dashboard: See pull requests at a glance, across multiple repos](http://github.com/rschuft/github-pr-dashboard) - See pull requests at a glance, across multiple repos - rschuft/github-pr-dashboard

8. [PR Radar – GitHub, GitLab & Bitbucket PRs](https://chromewebstore.google.com/detail/pr-radar-%E2%80%93-github-gitlab/hkombgibegjffiadmekpiabdakkoidmh) - Track PRs, CI status, code reviews & deployments across GitHub, GitLab and Bitbucket. No backend, fr...

9. [GitHub Dashboard Builder — AI Analytics](https://camelai.com/github) - Build DORA dashboards, PR trackers, and release notes from your GitHub repos with AI.

10. [How to track issues and PRs in many GitHub repositories](https://stackoverflow.com/questions/66985197/how-to-track-issues-and-prs-in-many-github-repositories) - I work on many GitHub repositories ( > 10 ) with fairly small user bases. I sometimes lose track of ...

11. [Git Workspaces: Multi-Repo Management Made Easy](https://www.gitkraken.com/features/workspaces) - Manage multiple Git repositories simultaneously with Workspaces. Group related repos, perform bulk o...

12. [Managing issues across multiple github repositories](https://stackoverflow.com/questions/69709469/managing-issues-across-multiple-github-repositories) - I am managing issues and projects in multiple GitHub repositories within a GitHub organization. Each...

13. [GitHub Organization | Grafana Labs](https://grafana.com/grafana/dashboards/14461-github-organization/)

14. [Issues 619](https://github.com/blacksmithgu/obsidian-dataview/issues) - A data index and query language over Markdown files, for https://obsidian.md/. - blacksmithgu/obsidi...

15. [As a user, I would like PRs to be "waiting on author" after a certain number of ...](https://github.com/pullreminders/backlog/issues/103) - Pull Reminders handles ・ when someone leaves a review, the review request ・ the pull request goes to...

16. [Triage Procedure - Rust Forge](https://forge.rust-lang.org/release/triage-procedure.html) - Supplemental documentation for contributing to The Rust Programming Language

17. [29.2.3. GitHub Pull Request Workflow](https://docs.suricata.io/en/latest/devguide/contributing/github-pr-workflow.html)

18. [待つツールを作って活用している ( gh-wait / gh-copilot-review )](https://k1low.hatenablog.com/entry/2026/04/17/083000) - 最近はCoding Agentを使って開発をしています。複数のCoding Agentを立ち上げて、それらと複数のタスクを並行して進めるようになりました。 一方で、感覚として「待つ」ことが多くなった気...

19. [GitHub PR Review Router - AI Agent Automations](https://www.trigger.tools/automations/github-pr-review-router/) - Shows what each open PR is waiting on, so reviewers and authors know where attention should go next.

20. [Grove — a CLI that manages git worktree workspaces across multiple repos](https://www.reddit.com/r/Python/comments/1s3id30/grove_a_cli_that_manages_git_worktree_workspaces/) - Grove — a CLI that manages git worktree workspaces across multiple repos

21. [Mars | Multi-Repo Workspace Manager](https://dean0x.github.io/x/mars/) - Multi-repo workspace manager for teams. Tag repos, run parallel operations, and share Claude config,...

22. [I built a CLI tool (RepoFleet) to manage Git branches across multiple ...](https://www.reddit.com/r/git/comments/1uq4pxh/i_built_a_cli_tool_repofleet_to_manage_git/) - I built a CLI tool (RepoFleet) to manage Git branches across multiple repositories simultaneously. M...

23. [I built deadbranch — a Rust CLI tool to safely clean up those 50+ stale git branches cluttering your repo](https://www.reddit.com/r/git/comments/1qtcae0/i_built_deadbranch_a_rust_cli_tool_to_safely/) - I built deadbranch — a Rust CLI tool to safely clean up those 50+ stale git branches cluttering your...

24. [Git Branch Aging Report: Finding and Cleaning Stale Branches](https://codepulsehq.com/guides/git-branch-aging-report) - Stale branches are hidden technical debt. Track branch aging, identify fossilized code, and automate...

25. [continue-claude-work](https://skills-anthropic.vercel.app/skill/continue-claude-work) - claude --resume replays the full session transcript into the context window. For long sessions this ...

26. [Manage sessions - Claude Code Docs](https://code.claude.com/docs/en/sessions) - Resume a session Sessions are saved continuously to local transcript files as you work, so you can r...

27. [Resume old sessions · Issue #371 · anthropics/claude-code](https://github.com/anthropics/claude-code/issues/371) - Right now closing a terminal window with a long chat is a pretty serious commitment. If I want to wo...

28. [Does Claude Code have any way to access previous ...](https://www.reddit.com/r/ClaudeCode/comments/1rvagol/does_claude_code_have_any_way_to_access_previous/) - I am working on a long term project and I want Claude Code to be able to read what happened in past ...

29. [Claude Code handoff skill - session state & handoff ... - Github-Gist](https://gist.github.com/edwilde/cb2bf5f8851ea1d79ddc19995eec8b5b) - Claude Code handoff skill - session state & handoff document generator - SKILL.md

30. [Zoomable treemap / D3](https://observablehq.com/@d3/zoomable-treemap) - This treemap supports zooming: click any cell to zoom in, or the top to zoom out. This custom tiling...

31. [Zoomable Icicle Javascript Example - The Observable Forum](https://talk.observablehq.com/t/zoomable-icicle-javascript-example/6974) - Why don't this show anything on the screen and there is no error? <!DOCTYPE html> <html> <head> <tit...

32. [Zoomable Icicle (d3 v4)](https://gist.github.com/a35c0f4f32400755a6a9b976be834ab3) - Zoomable Icicle (d3 v4). Download ZIP Zoomable Icicle (d3 v4) , "TreeMapLayout": 9191 }, Click anywh...

33. [D3 Responsive Zoomable Treemap (D3 v4+)](https://gist.github.com/Tak113/aab0f2944a44de4e5aeda8c0578d0bce) - D3 Responsive Zoomable Treemap (D3 v4+). GitHub Gist: instantly share code, notes, and snippets.

34. [D3 Gallery Vanilla JS](https://takanori-fujiwara.github.io/d3-gallery-javascript/)

35. [Treemap | Pangea Proxima](https://observablehq.observablehq.cloud/pangea/d3/treemap)

36. [Override Files - Configuration Language | Terraform](https://developer.hashicorp.com/terraform/language/files/override) - Override files merge additional settings into existing configuration objects. Learn how to use overr...

37. [working-with-chezmoi - Claude Skills](https://claude-plugins.dev/skills/@jlindley/jlindley-skills/working-with-chezmoi) - Use when working with any configuration file outside of project directories in ~/Code (unless alread...

38. [Chezmoi Guide: Manage Dotfiles Across Multiple Machines](https://www.deployhq.com/guides/chezmoi) - Learn how to use chezmoi to manage dotfiles across multiple machines. Covers installation, templates...

39. [Does the order in which the patches are defined matter? · Issue #727 · kubernetes-sigs/kustomize](https://github.com/kubernetes-sigs/kustomize/issues/727) - I'm trying to create an overrides patch to be applied last. It works a majority of the time but some...

40. [Change "DO NOT EDIT BELOW THIS LINE" to "DO NOT EDIT ABOVE THIS LINE" · Issue #151 · thoughtbot/dotfiles](https://github.com/thoughtbot/dotfiles/issues/151) - I believe it was @jessieay who noticed she wanted to override a setting somewhere (.gitconfig?) but ...

41. [Lintian Tag: generated-file - Debian](https://lintian.debian.org/tags/generated-file.html) - Explanation for the lintian tag generated-file

42. [Proto Best Practices](https://protobuf.dev/best-practices/dos-donts/) - Ensure that options in .proto file do not result in generation of code which violate the style guide...
