# Doc-Package Rubric

Scopes to everything a repo's documentation presents to someone who needs to
**encounter**, **understand**, **use**, or **extend/maintain/develop** the
project. Four journey scores + one hygiene score, each 0–100.

## The four journeys

1. **Encounter** — a stranger with no context lands on the repo. Does the
   README's first paragraph say what this is, why it matters, and who it's
   for — in under a minute, no digging required?
2. **Understand** — someone wants the shape of the system: architecture,
   design rationale, key decisions and why they were made (not just what the
   code does — a reader can already see that).
3. **Use** — someone wants to install, run, or consume it: install steps,
   a working example, API/CLI reference, troubleshooting for the obvious
   failure modes.
4. **Extend / maintain / develop** — someone wants to contribute or modify
   it: a CONTRIBUTING guide, local dev setup, test/lint commands, where
   things live, and — if decisions aren't obvious from the code — why they
   were made that way.

## Grades (per journey and overall)

| Grade | Score | Meaning |
|---|---|---|
| A | ≥85 | A newcomer succeeds at this journey without asking a human |
| B | 70–84 | Succeeds with minor friction |
| C | 55–69 | Succeeds only by piecing together multiple files |
| D | 40–54 | Likely gives up or asks a human |
| F | <40 | No entry point exists |

## Hygiene checks (apply across the whole doc surface, not per-journey)

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
- **Numbers that don't match the current state** — a headline stat quoted in
  prose that's drifted from the generated source of truth (if one exists).

## Common failure pattern

The **Extend/maintain** journey is the one most often scored F — READMEs get
written for the "encounter" and "use" journeys (they're what outside visitors
see first) and CONTRIBUTING/dev-setup docs get skipped because the author
already knows how to run their own project. Check this journey first; it's
usually the cheapest to fix (a CONTRIBUTING.md with dev setup + test/lint
commands) and the most commonly missing.
