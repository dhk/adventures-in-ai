---
name: review-document
description: >
  Reviews written documentation — a single document (report, proposal, memo,
  README, spec) or a repo's whole doc package (everything someone needs to
  encounter, understand, use, and extend/maintain/develop against a project)
  — scores it against a rubric, and offers specific edits to apply on
  confirmation. Use when asked to review, critique, grade, or improve a
  document, or to audit a repo's documentation coverage. Not for reviewing
  source code (use redpen) or a Claude Agent Skill's SKILL.md (use
  skill-doctor, in the skill-map repo).
license: MIT
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Review Document

Two modes, same lifecycle: **review → score → offer changes → confirm &
apply**. Never apply an edit — or create a file — without confirmation.

- **Mode A — Single document**: one report, proposal, memo, README, or spec.
- **Mode B — Doc package**: every doc a repo presents to someone who needs to
  encounter, understand, use, or extend/maintain/develop against it.

## Data handling

Either mode may operate on documents containing PII, financial figures, or
other sensitive content the user pastes in or points at. Never echo sensitive
values (names, SSNs, account numbers, credentials) verbatim in the findings
report — reference them by location ("paragraph 3, second sentence") instead
of quoting them. If a document appears to contain regulated data (PHI/PII/
financial), say so before scoring rather than silently processing it.

## Mode A — Single document

### Step 0 — Intake

- Identify what's being reviewed: a file path, or pasted text.
- Identify document type + audience if not obvious from content/context
  (report, proposal, README, blog post, memo, spec, email, handoff note...).
  If genuinely ambiguous, ask ONE question covering both — don't guess quietly,
  but don't ask if it's inferable (a PRD reads as a PRD).
- Read `reference/rubric.md` — six axes, weighted per document type.

### Step 1 — Review

Read the whole document once before writing anything. Note, with line or
section references:

- Structural issues (missing sections, wrong order, buried lede)
- Unsupported claims / logic gaps
- Unclear or padded passages
- Tone or terminology inconsistencies
- Anything a reader would stumble on

Cite specifics. "The intro is weak" is not a finding; "paragraph 2 promises a
recommendation the doc never delivers" is.

### Step 2 — Score

Apply `reference/rubric.md`. Score each of the 6 axes (0–100), take the
weighted overall for the document's type, assign a grade. Present as a
compact table — axis, score, one-line reason — not paragraphs of hedging.

Grades: A ≥85 ship it · B 70–84 solid, minor gaps · C 55–69 usable, needs a
pass · D 40–54 significant rework · F <40 not ready.

### Step 3 — Offer changes

Group findings by severity — **critical** (breaks the doc's purpose) /
**major** (weakens it materially) / **minor** (polish). Same three tiers on
every finding. No padding, no "great work" filler.

For each finding, give the actual suggested rewrite, not "make this clearer":

> **[major] Section 3** — claims a 40% improvement with no source.
> Fix: cite the benchmark, or soften to "in early testing" if unverified.

### Step 4 — Confirm and apply

Ask which to apply: all / critical+major only / none — never apply silently.

- Reviewing a real file → apply via Edit, then re-state the score for what
  changed.
- Reviewing pasted text → return the revised document inline.

## Mode B — Doc package

Reviews everything a repo presents across four audience journeys:
**encounter** (what is this, why does it matter — in under a minute),
**understand** (how/why it works), **use** (install, run, consume it),
**extend/maintain/develop** (contribute, modify, run it as a developer).

### Step 0 — Intake

- Identify the target: a GitHub `owner/repo` or a local path.
- Collect the doc surface: README, CONTRIBUTING, INSTALL/SETUP, CHANGELOG,
  LICENSE, the `docs/` tree (recursively), CLAUDE.md/AGENTS.md, issue/PR
  templates, ADRs, any index file already inside `docs/`.
- Read `reference/doc-package-rubric.md` — the four-journey checklist and the
  hygiene checks.

### Step 1 — Map

For each file, note: which journey(s) it serves, and its hygiene status —
current, stale (superseded but still committed), duplicate (two files
claiming the same canonical content), or orphaned (nothing links to it, it
links to nothing).

### Step 2 — Score

Per `reference/doc-package-rubric.md`: a completeness score per journey (does
it have an adequate, current, non-duplicated entry point?) plus an overall
hygiene score (dedup, staleness, broken links, navigability). Present as a
table: journey, score, entry point(s), gap.

### Step 3 — Offer changes

Same severity tiers as Mode A. Typical findings: a journey with no entry
point at all (critical), two files claiming to be the same canonical doc
(major), a stale artifact still committed — a closed PR's review notes, an
old session snapshot (major), a missing index when there are 10+ docs in one
directory (minor-to-major depending on size), broken internal links (minor).

### Step 4 — Confirm and apply

Ask which to apply. Some doc-package fixes create a new file (an index)
rather than edit an existing one — say so explicitly before doing it.

## Output

End with: the per-mode score table, findings grouped by severity with the
proposed fix for each, which fixes were applied, and — Mode B only — a
one-line per-journey verdict ("Use: solid. Extend: no entry point at all.").

## Behavior rules

- Don't pad findings with praise — same policy as this repo's `redpen` skill,
  for the same reason: this is a red pen, not a compliment sandwich.
- Don't rewrite the whole document (or repo) when a scoped edit will do.
- If the document is a type the rubric doesn't cover well (poetry, legal
  contracts, code comments), say so before scoring rather than force-fitting
  a bad grade.
