# Doc-Package Rubric

Scopes to everything a repo's documentation presents to someone who needs to
**encounter**, **understand**, **use**, or **extend/maintain/develop** the
project.

**Levels, triggers, scale, and concerns come from the Doc Watson standard
0.2.0** ([`docs/standard.md`](https://github.com/dhk/doc-watson/blob/main/docs/standard.md)
in `dhk/doc-watson`). That standard wins on any conflict. This file copies
the parts a review needs because the skill cannot fetch it, and adds the
journey grouping, which is this skill's own lens. When the standard's version
changes, re-copy the level table, trigger rules, and concern list.

## 1. Pick the level first

A repo is only scored on what its level and triggers require. Choose the
smallest level the evidence supports and say why in one line.

Typical repositories: Level 0 an experiment, personal script, or archive;
Level 1 an active early tool or library; Level 2 a mature system or service;
Level 3 credible public OSS with outside consumers. What each level requires:

| Concern | Level 0 — experiment | Level 1 — active early | Level 2 — mature system | Level 3 — public OSS |
|---|---|---|---|---|
| README | Minimal | Standard | Standard | Public-facing |
| Licence posture | Explicit | Explicit | Explicit | Licence file required |
| Install | One truthful path | Reliable common path | Complete supported paths | Published, direct/source, careful paths where available |
| Usage | One example | First successful outcome | Core workflows | User guides and examples |
| Status and limits | Required | Required | Required | Required, including support posture |
| Repository map | If non-obvious | If multi-part | Required | Required |
| “So what” | One sentence | Required | Required | Required |
| Architecture | If helpful | One useful context/flow | Context and containers | As needed; avoid code mirrors |
| Security/privacy | Risks named | Data, credentials, permissions, side effects | Policy and operating boundaries | Public reporting and support posture |
| Ownership/contribution | Not normally | When others participate | Ownership required | Contribution path required |
| Operations | Not normally | For real operational needs | Deployment/recovery; triggered runbooks | For hosted surfaces |
| Decisions | Not normally | For a real tradeoff | Major ADRs | Major ADRs |
| Machine contract | If parsed | If parsed | If API/schema exists | If applicable |
| Agent memory | If agents return | If agents return | If agents return | If agents return |

Levels are baselines, not cumulative. A triggered need overrides the typical
row.

### Trigger rules

Apply these independently of the level:

- Add an install guide when there is more than one supported path or setup no
  longer fits a reliable README section.
- Add user guides when first success or common tasks require more than a compact example.
- Add architecture when the mental model is not clear from one repository read.
- Add ADRs only for decisions with real alternatives and consequences.
- Add agent memory when an agent returns across sessions; keep it current.
- Add machine contracts only when a program parses the repository or interface.
- Add CODEOWNERS when ownership or review routing is shared.
- Add CONTRIBUTING when people outside maintainers are invited to make changes.
- Add governance when multiple maintainers have authority questions.
- Add a Now/Next/Later roadmap when a public audience needs direction.
- Add runbooks only when alerts page someone; include owner, trigger,
  last-verified date, fallback, escalation, and rollback.
- Add handover docs when another party must operate the asset independently.

A missing document with no trigger is **not a finding** — don't recommend
adding it.

## 2. Score each concern, grouped by journey

Score each concern **0** absent, **1** partial or stale, **2** fit for purpose,
or **n/a** when the level does not require it and no trigger applies. Record
n/a separately from 0. Never award points for unnecessary files.

| Journey | Question it answers | Concerns |
|---|---|---|
| **Encounter** | Can a stranger tell what this is, why it matters, and who it's for, in under a minute? | Purpose and audience · Status and limits · Value (“so what”) · Licence |
| **Understand** | Can someone get the shape of the system and why it was built this way? | Architecture · Decisions |
| **Use** | Can someone install, run, or consume it, and know what it touches? | First success · Install paths · Usage · Data, privacy, and security |
| **Extend / maintain** | Can someone modify, operate, or pick it back up? | Ownership and contribution · Operations · Agent memory · Machine contracts · Maintenance and verification |
| **Whole surface** | Do the docs work together? | Navigation · Truthfulness · Hygiene and duplication |

Those are the standard's 18 concerns, each in exactly one journey.

**Journey result** = points earned / points available across its applicable
concerns (e.g. `Use 5/8`). A journey whose concerns are all n/a is reported as
n/a, not as a pass or a fail. Don't convert to a letter grade: Mode A's grades
measure writing quality, and these measure coverage against a level.

## 3. Hygiene checks (whole surface)

These aren't about any one file being badly written — they're about the
*set* of docs working together. Checked in order of how often they show up:

- **Duplicate/conflicting canonical docs** — two files claiming to define the
  same spec/rubric/process, with no indication which one is current.
- **Stale artifacts still committed** — closed-out PR review notes, one-off
  session snapshots, superseded drafts. If it documented a decision that's
  now resolved, it belongs in git history, not the working tree.
- **Broken internal links** — a doc links to a file that doesn't exist
  (renamed, deleted, or never actually created).
- **No index when there are many docs** — a `docs/` directory with 10+ files
  and no file telling a reader which is which, or which are auto-generated
  vs. hand-written vs. planning material.
- **Contradictory claims** — install steps, versions, privacy, or status stated
  differently in two places, or a headline number that has drifted from its
  generated source of truth.
- **Leaks and machine-specific detail** — private example data, or paths that
  only work on the author's machine.
- **Doc debt recorded but never closed** — a known-issues list or earlier
  audit whose items are still open.

## Common failure pattern

**Extend / maintain** is the journey most often scored low. READMEs get
written for encounter and use, which is what visitors see first. The
maintenance docs get skipped because the author already knows how to run
their own project. Check it first, but score it against the level:

- **Maintenance and verification** (how to run tests, lint, and the build
  locally) applies at every level, including a solo repo. It is usually the
  cheapest fix and the most often missing.
- **CONTRIBUTING** only counts when outside contributors are invited. On a
  solo repo, Ownership and contribution is normally n/a, and its absence is
  not a gap.
