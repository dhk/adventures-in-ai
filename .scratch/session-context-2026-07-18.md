# Context Snapshot: repo-template proposal & move
Generated: 2026-07-18T03:31:57Z
Branch: claude/repo-template-proposal-pfsid3
Status: blocked
Description: Scaffolded repo-template in adventures-in-ai; blocked moving it to dedicated dhk/repo-template

## Objective
Propose and build a personal repo-template (instructive, build-in-public,
workflow-visible) distilled from patterns across dhk's existing repos, then
relocate it into the dedicated `dhk/repo-template` repo the user just created
on GitHub.

## Authoritative Inputs
- **Business ask**: "Look at these repos and then propose a repo template...
  instructive, adherent to my principles of building in public, display how
  I use my workflow management (eg save context)." Later: "I created
  repo-template. Move it to there."
- **Key metrics**: [not established — no quantitative target]
- **Source tables**: N/A — surveyed repo structures instead: CLAUDE.md files,
  READMEs, CONTRIBUTING.md, context-snapshot/handoff docs across
  `work-ledger`, `familiar-places`, `fossil`, `crucible`, `skill-map`,
  `praxis`, `ivy-archive`, `reading-with-ears`, `DHK-website`, `woven`.
- **Business rules**: This session's task instructions require developing on
  branch `claude/repo-template-proposal-pfsid3` per repo, never pushing
  directly to main without explicit permission, and never opening a PR
  unless asked.

## Technical Decisions

### Where the template scaffold lives
**Decision**: Built first inside `dhk/adventures-in-ai` at
`templates/repo-template/`, since that's the user's existing home for
cross-cutting tooling and skills.
**Why**: adventures-in-ai was reachable immediately; `dhk/repo-template` did
not exist yet when scaffolding started.
**Alternatives rejected**: Waiting to scaffold until repo-template existed —
rejected to make progress in parallel with the user creating the repo.
**State**: tentative — this is explicitly *not* the final location. The user
has since created `dhk/repo-template` and asked for the content to be moved
there.

### Two-tier structure (meta README + template/ subfolder)
**Decision**: Root `templates/repo-template/README.md` explains the
rationale and pattern table; the actual fillable files
(`README.md`, `CLAUDE.md`, `HANDOFF.md`, `LICENSE`, `.gitignore`, `docs/`,
`.scratch/`) live one level down in `template/`.
**Why**: Keeps "why this template looks this way" separate from "what you
copy into a new project."
**Alternatives rejected**: Flat structure (fillable files directly at repo
root) — more idiomatic for GitHub's "Use this template" button, but not
chosen yet.
**State**: tentative — worth revisiting once actually inside the dedicated
`dhk/repo-template` repo, since a standalone template repo may want the
fillable files at root instead of nested under `template/`. Flagged as an
open decision, not yet made.

### CONTRIBUTING.md / ISSUE_TEMPLATE left out by default
**Decision**: Not included in the base template.
**Why**: Most of the surveyed repos are solo build-in-public, not soliciting
outside PRs; skill-map (which does want contributors) is the model to copy
per-repo when needed.
**Alternatives rejected**: Including them by default so every repo starts
contributor-ready.
**State**: implemented — this was presented as the recommended default via
`AskUserQuestion`, but that tool call errored out (stream closed) twice
before an answer came back. Proceeded with the recommended option and said
so explicitly; **the user has not explicitly confirmed this choice.**

## Artifacts

### `templates/repo-template/README.md` (in adventures-in-ai)
**File**: `templates/repo-template/README.md`
**Purpose**: Explains the template's rationale, a pattern-to-source table,
and the HANDOFF.md-vs-docs/snapshots/ split.
**Status**: completed, committed, pushed — pending relocation.

### `templates/repo-template/template/*` (in adventures-in-ai)
**Files**: `README.md`, `CLAUDE.md`, `HANDOFF.md`, `LICENSE` (MIT),
`.gitignore`, `.scratch/.gitkeep`, `docs/design/README.md`,
`docs/snapshots/README.md`
**Purpose**: The actual copyable scaffold — fillable stub files with
`<placeholders>`, each documented inline.
**Status**: completed, committed, pushed — pending relocation.

### `adventures-in-ai/CLAUDE.md` edit
**File**: `CLAUDE.md` (repo root)
**Purpose**: Added a `## repo-template` section pointing at
`templates/repo-template/` so it's discoverable the same way the skills
table is.
**Status**: completed, committed, pushed — **will need updating or removal**
once the content actually moves to `dhk/repo-template` (should point at the
GitHub repo instead of describing local files that will no longer exist).

### Commit
`47fae04` — "Add repo-template scaffold distilled from patterns across
existing repos" — pushed to `origin/claude/repo-template-proposal-pfsid3` on
`dhk/adventures-in-ai`.

## Validation
No automated validation applies (docs/scaffold work). Confirmed via
`git push` output ("new branch ... -> claude/repo-template-proposal-pfsid3")
and `find templates/repo-template -type f` showing the expected 9 files.

## Warnings
- ⚠️ **MCP repo access is currently broken, not just unapproved.** Both
  `add_repo` and `list_repos` (via the `bf7c680d-...` claude-code-remote MCP
  server) fail identically with `Streamable HTTP error: Error POSTing to
  endpoint: MCP tool call requires approval` — and the user confirmed no
  approval prompt is visible on their end. This points to the connector
  itself being stuck, not a per-call permission dialog waiting on a click.
- ⚠️ The scaffold still physically lives in `dhk/adventures-in-ai` — nothing
  has been deleted there yet. Until the MCP access issue clears, "move it to
  repo-template" is unexecuted; treat adventures-in-ai's copy as the source
  of truth for now, not as an already-superseded duplicate.
- ⚠️ No designated feature-branch name exists for `dhk/repo-template` (it
  wasn't in this session's original repo scope, so it has no assigned
  branch like the other 15 repos do). Confirm with the user whether to work
  directly on `main` there (plausible for a brand-new template-only repo) or
  cut a feature branch, before pushing anything.

## Known Gaps & Limitations
- ❌ **`dhk/repo-template` unreachable**: `add_repo`/`list_repos` both error
  out — *Impact*: cannot clone, read, or push to the new repo from this
  session. *Workaround*: user is checking for a sources/repositories panel
  in session settings, or may start a fresh session with `repo-template`
  attached as a source from the start.
- ⚠️ **Structure not finalized for the dedicated repo**: two-tier
  (meta-README + `template/`) vs. flat (fillable files at root, more
  standard for a GitHub "template repository") — *Decision*: deferred until
  we're actually working inside `dhk/repo-template`.

## Out of Scope
- Retrofitting this template pattern onto existing repos (work-ledger,
  familiar-places, etc.) — not requested this session.
- CI workflow files — deliberately left per-repo (copy from praxis/crucible/
  skill-map/tricorder as needed), not templated generically.

## Next Actions
- [ ] BLOCKED: Get `dhk/repo-template` into this session's reachable repo
      scope — retry `add_repo`, or wait for user to refresh/reconnect the
      session, or pick this back up in a fresh session that includes
      `repo-template` as a source from creation.
- [ ] Once reachable: decide flat-vs-nested structure for the dedicated repo
      (see Technical Decisions above), then copy the scaffold over from
      `dhk/adventures-in-ai` at `templates/repo-template/`
      (branch `claude/repo-template-proposal-pfsid3`, commit `47fae04`).
- [ ] Confirm with user: work directly on `main` in the new repo, or cut a
      feature branch first?
- [ ] After the move is confirmed in `dhk/repo-template`: remove
      `templates/repo-template/` from `dhk/adventures-in-ai` and update its
      `CLAUDE.md` `## repo-template` section to link out to the new repo
      instead of describing local files.
- [ ] Confirm with user whether the CONTRIBUTING.md/ISSUE_TEMPLATE
      leave-out-by-default decision stands (never got an explicit answer —
      `AskUserQuestion` errored twice).
- [ ] Not yet requested: opening a PR for
      `claude/repo-template-proposal-pfsid3` on adventures-in-ai.

---
*Resume:* load this file in your next session.
