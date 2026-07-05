---
name: review-document
description: >
  Reviews a written document — report, proposal, memo, blog post, README,
  spec — scores it against a quality rubric, and offers specific edits to
  apply on confirmation. Use when asked to review, critique, grade, or
  improve the writing quality of a document. Not for reviewing source code
  (use redpen) or a Claude Agent Skill's SKILL.md (use skill-doctor, in the
  skill-map repo).
---

# Review Document

Full lifecycle, one document at a time: **review → score → offer changes**.
Never apply an edit without confirmation.

## Step 0 — Intake

- Identify what's being reviewed: a file path, or pasted text.
- Identify document type + audience if not obvious from content/context
  (report, proposal, README, blog post, memo, spec, email, handoff note...).
  If genuinely ambiguous, ask ONE question covering both — don't guess quietly,
  but don't ask if it's inferable (a PRD reads as a PRD).
- Read `reference/rubric.md` — six axes, weighted per document type.

## Step 1 — Review

Read the whole document once before writing anything. Note, with line or
section references:

- Structural issues (missing sections, wrong order, buried lede)
- Unsupported claims / logic gaps
- Unclear or padded passages
- Tone or terminology inconsistencies
- Anything a reader would stumble on

Cite specifics. "The intro is weak" is not a finding; "paragraph 2 promises a
recommendation the doc never delivers" is.

## Step 2 — Score

Apply `reference/rubric.md`. Score each of the 6 axes (0–100), take the
weighted overall for the document's type, assign a grade. Present as a
compact table — axis, score, one-line reason — not paragraphs of hedging.

Grades: A ≥85 ship it · B 70–84 solid, minor gaps · C 55–69 usable, needs a
pass · D 40–54 significant rework · F <40 not ready.

## Step 3 — Offer changes

Group findings by severity — **critical** (breaks the doc's purpose) /
**major** (weakens it materially) / **minor** (polish). Same three tiers on
every finding. No padding, no "great work" filler.

For each finding, give the actual suggested rewrite, not "make this clearer":

> **[major] Section 3** — claims a 40% improvement with no source.
> Fix: cite the benchmark, or soften to "in early testing" if unverified.

## Step 4 — Confirm and apply

Ask which to apply: all / critical+major only / none — never apply silently.

- Reviewing a real file → apply via Edit, then re-state the score for what
  changed.
- Reviewing pasted text → return the revised document inline.

## Behavior rules

- Don't pad findings with praise — same policy as this repo's `redpen` skill,
  for the same reason: this is a red pen, not a compliment sandwich.
- Don't rewrite the whole document when a scoped edit will do.
- If the document is a type the rubric doesn't cover well (poetry, legal
  contracts, code comments), say so before scoring rather than force-fitting
  a bad grade.
