# Context Snapshot: repo-template proposal & move
Generated: 2026-07-18T03:31:57Z
Closed: 2026-07-18
Branch: claude/repo-template-proposal-pfsid3 (superseded — see Resolution)
Status: **closed — done**
Description: Scaffolded repo-template in adventures-in-ai, then relocated it
to the dedicated `dhk/repo-template` repo. All blockers cleared, all next
actions resolved.

## Objective
Propose and build a personal repo-template (instructive, build-in-public,
workflow-visible) distilled from patterns across dhk's existing repos, then
relocate it into the dedicated `dhk/repo-template` repo the user just created
on GitHub.

**Outcome: achieved.** Both halves are done and merged to `main`.

## Resolution

This snapshot was written mid-task while `dhk/repo-template` was unreachable
(MCP `add_repo`/`list_repos` erroring). A later session picked it up with
`repo-template` already in its reachable repo scope and finished the job:

- **`dhk/repo-template`**: scaffold added on branch
  `claude/repo-template-completion-2k04db` (commit `6d13e7f`, "Add
  repo-template scaffold"), merged to `main` via PR #1 (`95fd43d`). Structure
  kept as originally proposed here — meta `README.md` at root, fillable files
  under `template/`.
- **`dhk/adventures-in-ai`**: `templates/repo-template/` removed and
  `CLAUDE.md`'s `## repo-template` section updated to point at the new repo
  instead of local files, on the same completion branch, merged via PR #35
  (`96fec64`) — also already on `main`.
- **CONTRIBUTING.md / ISSUE_TEMPLATE default**: explicitly confirmed by the
  user in this closing session — leave them out of the base template, add
  per-repo (skill-map is the model) when a project wants contributors. This
  was the only open decision left unconfirmed; it's now settled.
- **PR for `claude/repo-template-proposal-pfsid3`**: never opened, and now
  moot — its content was superseded by the completion branch above before a
  PR was ever requested. The branch itself is stale; no action needed on it.

Original branch (`claude/repo-template-proposal-pfsid3`) and its commit
`47fae04` are kept for history but are no longer the active line of work —
`main` in both repos reflects the finished state.

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

## Technical Decisions (as shipped)

### Scaffold location: `dhk/repo-template`, not `adventures-in-ai`
Final home is the dedicated repo, per the user's explicit ask. The
`adventures-in-ai` copy was a staging step, since removed.

### Two-tier structure (meta README + `template/` subfolder)
Kept as originally designed: root `README.md` explains rationale and the
pattern table; fillable files (`README.md`, `CLAUDE.md`, `HANDOFF.md`,
`LICENSE`, `.gitignore`, `docs/`, `.scratch/`) live under `template/`. The
flat-vs-nested question flagged as open in the original snapshot was
resolved in favor of keeping the nested structure.

### CONTRIBUTING.md / ISSUE_TEMPLATE left out by default
**Confirmed** (previously the recommendation had gone unanswered after
`AskUserQuestion` errored twice). Not included in the base template — most
surveyed repos are solo build-in-public; add per-repo (skill-map is the
model) when a project wants contributors.

## Artifacts (final state)
- `dhk/repo-template` `main`: `README.md`, `template/{README.md,CLAUDE.md,
  HANDOFF.md,LICENSE,.gitignore,.scratch/.gitkeep,docs/design/README.md,
  docs/snapshots/README.md}` — 9 files, PR #1 merged.
- `dhk/adventures-in-ai` `main`: `templates/repo-template/` removed;
  `CLAUDE.md` updated to link out to `dhk/repo-template` — PR #35 merged.

## Known Gaps & Limitations
None outstanding. The MCP repo-access issue that originally blocked this
(`add_repo`/`list_repos` erroring on `dhk/repo-template`) had cleared by the
time the completion session ran.

## Out of Scope (unchanged)
- Retrofitting this template pattern onto existing repos (work-ledger,
  familiar-places, etc.) — not requested.
- CI workflow files — deliberately left per-repo (copy from praxis/crucible/
  skill-map/tricorder as needed), not templated generically.

## Next Actions
None. All items from the original snapshot are resolved:
- [x] `dhk/repo-template` reachable and scaffold moved in (PR #1)
- [x] Flat-vs-nested structure decided (nested, as designed)
- [x] `templates/repo-template/` removed from `adventures-in-ai`, `CLAUDE.md`
      updated (PR #35)
- [x] CONTRIBUTING.md/ISSUE_TEMPLATE leave-out-by-default confirmed by user
- [x] PR for `claude/repo-template-proposal-pfsid3` — not needed, superseded

---
*This snapshot is closed. No resume action required.*
