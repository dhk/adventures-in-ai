# Findings — submission convention

## Naming

One file per source: `<source-slug>-findings.md`. The source slug is short
and identifies who/what produced it, e.g. `claude-findings.md`,
`chatgpt-findings.md`, `gemini-findings.md`, `dave-findings.md`.

## Format

Copy [`TEMPLATE.md`](TEMPLATE.md) and fill it in — one section per brief
question, in the same order as `brief.md`, each with:

- A table: `Entry | What it is | Workmap concept overlap | Verdict`
- A `Notes` block below the table for rationale, caveats, and detail

Followed by a final `## Open gaps` section covering anything the brief
asked that you couldn't find a good answer to.

### Verdict — closed set, no exceptions

Every table row's `Verdict` column must be exactly one of:

- `adopt/reference` — directly usable, or a pattern worth copying
- `differentiate` — relevant, but workmap should do this differently, and
  why goes in Notes
- `ignore` — surfaced by the search but not actually relevant

Don't invent new labels. Don't put rationale in the Verdict cell — a
one-word verdict plus a Notes explanation, not `adopt/reference (because it
has X)`.

### No empty tables

If a question turns up nothing, the table still gets one row:
`none found | — | — | ignore`, with the reason (what you searched, why you
believe it's genuinely absent) in Notes. Silence in a table reads as "not
researched," not as "researched and found nothing" — those are different
and the reader needs to know which one happened.

## Submitting without repo write access

If you don't have write access to this repo, use
[`../handoff-prompt.md`](../handoff-prompt.md) as your starting prompt, then
paste your completed findings (matching `TEMPLATE.md`) back to the person
who gave you the prompt — they'll commit it as
`<your-source-slug>-findings.md`.
