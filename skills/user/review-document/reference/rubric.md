# Document Review Rubric

Six axes, each 0–100, weighted per document type. Same grading philosophy as
the rubric in `dhk/skill-map`: derived from what good documents in each genre
actually do, not a generic writing-class checklist.

## The six axes

1. **Purpose & audience fit** — states what it's for and who it's for;
   matches the reader's actual knowledge level.
2. **Structure & flow** — logical order, scannable headings/sections, no
   orphaned or redundant sections, right length for the job.
3. **Argument & evidence** — claims are supported; no unearned leaps;
   addresses the obvious counterargument where one exists.
4. **Clarity & concision** — plain language, no unexplained jargon, no
   padding, active voice by default.
5. **Actionability / completeness** — reader knows what to do next, or the
   doc delivers everything its own opening promised.
6. **Tone & consistency** — one voice throughout, appropriate formality,
   consistent terminology (doesn't call the same thing two names).

## Grades

| Grade | Score | Meaning |
|---|---|---|
| A | ≥85 | Ready to ship |
| B | 70–84 | Solid, minor gaps |
| C | 55–69 | Usable, needs a revision pass |
| D | 40–54 | Significant rework |
| F | <40 | Not ready |

## Weighting by document type

Default weight is even (1/6 each, ~16.7 points per axis). Adjust for these
common types:

| Type | Emphasize | De-emphasize |
|---|---|---|
| Business proposal / memo | Actionability (clear ask/decision), Structure | Tone |
| Technical spec / PRD | Completeness, Argument & evidence (constraints, edge cases) | — |
| Blog post / newsletter | Clarity, Tone (voice, hook) | Actionability |
| README / how-to doc | Structure (scannable), Actionability (can the reader do the thing) | Argument & evidence |
| Status update / handoff note | Actionability, Concision | Tone |

If the document doesn't fit a listed type, use even weighting and say so in
the report.

## What "good" looks like per axis (calibration anchors)

- **Purpose & audience fit, A-level** — the first paragraph tells you what
  this is and who should read it, without a throat-clearing preamble.
- **Structure, A-level** — you could skim just the headings and get the shape
  of the argument.
- **Argument & evidence, A-level** — every load-bearing claim has a number, a
  citation, or an explicit "unverified — flag before publishing."
- **Clarity, A-level** — a reader outside the immediate context could follow
  it on one read.
- **Actionability, A-level** — the reader's next step is stated, not implied.
- **Tone, A-level** — reads like one person wrote it, even if several people
  did.

## Common defects (check these first — cheap to fix, high leverage)

- Buried ask / no clear next step (actionability)
- Claims with no source and no hedge ("this will save $2M" with nothing
  behind it)
- Section order that doesn't match how a reader actually needs the
  information (context before ask, not the ask buried in paragraph 4)
- Terminology drift — same concept, three different names across one
  document
- Padding — sentences that restate the previous sentence with more words
