# "The Week That Was" — Design Doc

**Status:** Design — not yet built. No code in this doc has been written.
**Owner:** Dave Holmes-Kinsella
**Depends on:** `reading-list-builder` skill v2.1 deep mode (already shipped, running daily)

---

## 1. Purpose

Once a week, synthesize everything the deep pipeline collected into three outputs:

1. **Article ideas for me** — 2-4 specific writing angles, each grounded in actual
   sources (links included), filtered against what I actually write about.
2. **A NotebookLM weekly podcast** — a synthesis doc + audio overview, published to
   its own Element.fm show, for weekend listening.
3. **A zeitgeist surfer** — which themes are growing, which are dipping, across the
   weeks. Not a list of this week's news — a trend line.

Manual trigger. Run it Friday or over the weekend. No cron for v1 — see §10.

---

## 2. Current state (what already exists vs. what doesn't)

| Piece | State |
|---|---|
| Daily deep pipeline (`reading-list-builder` v2.1) | ✅ Running, writes `dhkondata/reading-db/runs/YYYY-MM-DD.yaml` |
| Per-article synthesis bullets + tags | ✅ In every run YAML (see schema below) |
| HTML article briefs | ✅ `dhkondata/reading-db/briefs/YYYY-MM-DD/<article_id>.html` — but **not generated for every article** (skipped when `infographic.status: skipped`, e.g. paywalled) |
| `rwe-publish` / Element.fm wiring | ✅ Existing, per-feed `elementfm_show_id` in `feeds.json` |
| Sentinel/idempotency pattern (`done-YYYY-MM-DD`) | ✅ Established convention, reused below |
| **Writer profile** (themes I write about, used to filter the ideation layer) | ❌ **Not built.** Interview started, paused after one question ("thoughtful use of AI to augment everyone's work" — contrast not yet defined). This blocks output #1 only. |
| Weekly Element.fm show | ❌ No show ID yet — needs to be created in Element.fm and added to config |
| Zeitgeist theme history store | ❌ Doesn't exist — new artifact, see §6.3 |
| Weekly synthesis script/skill | ❌ Doesn't exist — this doc specs it |

**Practical implication:** outputs #2 and #3 (NotebookLM synthesis, zeitgeist) don't
need the writer profile and can ship first. Output #1 (article ideas) is gated on
finishing that interview. Build order follows this in §9.

---

## 3. What the daily run actually gives us

Real excerpt from `dhkondata/reading-db/runs/2026-05-18.yaml`, trimmed:

```yaml
run_date: 2026-05-18
skill_version: "2.1"
pipeline_mode: deep
emails:
  - email_id: msg-19e3b470e4c5491b
    thread_id: 19e3b470e4c5491b
    label: news
    sender_name: Axios AI+
    articles:
      - article_id: 19e3b470e4c5491b-01
        source:
          url_canonical: "https://www.axios.com/2026/05/18/trump-ai-steve-bannon..."
        content:
          full_body_available: true
        synthesis:
          bullets: ["Over 60 Trump loyalists...", "..."]
          confidence_note: full article retrieved
        infographic:
          status: complete
          path: ".../briefs/2026-05-18/19e3b470e4c5491b-01.html"
        tags: [AI-policy, regulation, Trump, MAGA, frontier-AI]
        status: synthesized
```

Three things this schema already gives us for free, that the weekly design should
lean on instead of re-deriving:

- **`tags`** — free-form per-article tags. Noisy (not a controlled vocabulary) but
  free, already computed, and good enough for deterministic frequency counting
  (§6.3).
- **`thread_id`** — enough to build a direct Gmail deep link:
  `https://mail.google.com/mail/u/0/#all/<thread_id>` — no extra Gmail MCP call
  needed at weekly-synthesis time.
- **`confidence_note`** — flags `email excerpt only` vs `full article retrieved`.
  Worth surfacing in article-idea sourcing so I know how much to trust a claim
  before I write about it.

Coverage gap to design around: not every article has a brief (paywalled / bot-blocked
sources get `infographic.status: skipped`). Bullets are the only thing guaranteed to
exist for every article — briefs are a bonus when present.

---

## 4. Architecture

Same split that already works for the daily pipeline: **deterministic mechanics in
Python, judgment calls via Claude.** The daily pipeline put mechanics in
`rwe-publish`/`publish_episodes.py` and reasoning in the skill. The weekly pipeline
follows the same line, but because it needs *three different model tiers* in one
run, the orchestration itself moves to Python (direct Anthropic API), with `claude -p`
called only for the one step that genuinely needs MCP tools (NotebookLM).

> **Review comment (credentials):** This is the first place in the repo that
> would call the Anthropic API directly rather than going through `claude -p` /
> the existing Claude Pro session. Worth spelling out where `ANTHROPIC_API_KEY`
> lives (env var read by `rwe-weekly`? a new entry alongside
> `automation/mcp-headless.json`? macOS keychain like other secrets here?) and
> what happens if it's unset or invalid — since steps 3-5 are the only paid
> stages, a missing/bad key should fail at pre-flight, not partway through a run.

```
rwe-weekly (new bin script)
  │
  ├─ 1. Pre-flight (Python, no model)
  │     - find ISO week's run YAMLs in dhkondata/reading-db/runs/
  │     - flag missing days (don't abort — annotate and proceed)
  │
  ├─ 2. Zeitgeist counts (Python, no model)
  │     - aggregate `tags` across the week + trailing 4 weeks
  │     - update dhkondata/reading-db/zeitgeist/themes.yaml
  │     - compute movers: emerging / growing / dipping / steady
  │
  ├─ 3. Section synthesis (Sonnet x 6, direct API)
  │     - one call per taxonomy section, reading briefs (fallback: bullets)
  │     - input: that section's articles only
  │
  ├─ 4. Zeitgeist narrative (Sonnet x 1, direct API)
  │     - input: the deterministic mover list from step 2 + relevant article bullets
  │     - output: "what's rising and why" prose
  │
  ├─ 5. Article ideas / ideation layer (Opus x 1, direct API)
  │     — gated on writer profile existing —
  │     - input: full weekly synthesis doc (steps 3+4 output) + writer profile
  │     - output: 2-4 angles, each with source links
  │
  ├─ 6. Assemble weekly Markdown doc (Python, no model)
  │     - combine 3+4+5 into one doc, write to
  │       dhkondata/reading-db/weekly/YYYY-Www/synthesis.md
  │
  ├─ 7. NotebookLM + audio (claude -p, MCP — same pattern as daily skill)
  │     - new notebook, single source = synthesis.md
  │     - studio_create, poll, title, download (delegates to rwe-publish)
  │
  └─ 8. Element.fm publish (rwe-publish, existing script, weekly show ID)
```

Steps 1, 2, 6 are pure Python and free. Steps 3-5 are the only token cost (see §7).
Step 7 is the only step that needs `claude -p` / MCP, mirroring why the daily skill
exists at all.

---

## 5. New artifacts

```
reading-with-ears/
  scripts/
    week_that_was.py            # orchestrator: steps 1-6 above
  config/
    weekly.json                 # NEW — taxonomy, weekly show config (see §5.1)
  skills/user/week-that-was/
    SKILL.md                    # NEW — thin: just step 7 (NotebookLM + handoff to rwe-publish)

bin/
  rwe-weekly                    # NEW — wrapper, same shape as rwe-publish/rwe-run.sh

dhkondata/reading-db/
  zeitgeist/
    themes.yaml                 # NEW — rolling per-week tag counts, see §6.3
  weekly/
    2026-W26/
      synthesis.md              # the doc fed to NotebookLM
      manifest.yaml             # per-stage status, cost, timestamps — see §8
  writer-profile.yaml           # NEW — output of the (unfinished) interview, see §9
```

### 5.1 Why a new `config/weekly.json` instead of overloading `feeds.json`

`feeds.json` feeds all assume Gmail-label routing (`gmail_labels` is required by
`podcast_config.py`'s slug logic). The weekly show has no Gmail label — its source
is synthesized Markdown, not routed mail. Bolting it into `feeds.json` would mean
either a fake empty `gmail_labels: []` (and hoping nothing in `publish_episodes.py`
breaks on that) or special-casing the slug everywhere that iterates feeds. Cleaner:
a separate small config the weekly script reads directly, and a **single new field**
added to the existing feed schema only where actually needed —
`elementfm_show_id` for the weekly show lives in `weekly.json`, not `feeds.json`,
since `rwe-publish` for the weekly episode is invoked directly with that ID rather
than discovered via slug lookup.

```jsonc
// reading-with-ears/config/weekly.json
{
  "show_name": "The Week That Was",
  "elementfm_show_id": "<TBD — create show in Element.fm first>",
  "taxonomy": [
    { "key": "ai_tech",   "label": "🤖 AI & Technology",   "feeds": ["professional", "think", "news"] },
    { "key": "economy",   "label": "💰 Economy & Markets",  "feeds": ["news", "professional"] },
    { "key": "politics",  "label": "🏛️ Politics & Power",   "feeds": ["news", "think"] },
    { "key": "health",    "label": "🧬 Health & Science",   "feeds": ["vital-signs", "news"] },
    { "key": "ideas",     "label": "💡 Ideas & Culture",    "feeds": ["think", "news"] },
    { "key": "business",  "label": "🏢 Business & Strategy","feeds": ["professional", "think"] }
  ]
}
```

A section's article set = articles whose `label` (from the daily YAML) is in that
section's `feeds` list. This is deterministic — no classification call needed,
unlike the original "Haiku classifies each article" idea from earlier discussion.
Trade-off: sections are feed-shaped, not topic-shaped, so an AI-policy story under
`news` lands in "Politics & Power" alongside general news rather than "AI & Tech."
Acceptable for v1 — revisit only if it's actually annoying in practice.

---

## 6. Stage detail

### 6.1 Pre-flight (step 1)

Read `dhkondata/reading-db/runs/*.yaml` for the 7 days of the target ISO week.
Missing days are **not** a hard stop — annotate `manifest.yaml` with which days
are missing and proceed with what exists. A week with 5/7 days is still worth
synthesizing; a week with 0/7 days should abort with a clear message (nothing to
do, not a failure).

### 6.2 Section synthesis (step 3)

For each of the 6 taxonomy sections: gather that section's articles for the week,
prefer the HTML brief when `infographic.status: complete`, otherwise fall back to
`synthesis.bullets`. One Sonnet call per section — narrative "what happened this
week in X" prose, not bullet restatement. Sections with zero articles are skipped
(not every section fires every week — that's fine, it's not a checklist).

### 6.3 Zeitgeist counting (step 2) — deterministic, no model

This is the one place where doing it in code beats doing it with a model: tag
frequency is exact, free, and doesn't hallucinate. `themes.yaml` accumulates:

```yaml
# dhkondata/reading-db/zeitgeist/themes.yaml
themes:
  AI-policy:
    weekly_counts:
      "2026-W22": 3
      "2026-W23": 5
      "2026-W24": 4
      "2026-W25": 7
      "2026-W26": 11
  GLP-1:
    weekly_counts:
      "2026-W24": 2
      "2026-W25": 2
      "2026-W26": 1
```

Trend classification (pure arithmetic, no model):
- **emerging** — first appearance in the last 2 weeks, ≥2 mentions
- **growing** — this week's count > 1.5x trailing-4-week average
- **dipping** — this week's count < 0.5x trailing-4-week average, and was ≥2 last period
- **steady** — everything else

> **Review comment (noise floor):** The ratio thresholds have no minimum-volume
> gate. A tag going from 1 mention to 2 is a 100% increase and would be flagged
> **growing** right alongside a tag going from 10 to 20 — same label, very
> different signal strength. Consider requiring a minimum trailing-4-week
> average (e.g. ≥3) before applying the ratio math at all; below that, bucket
> as `steady` (or a distinct `low-volume`) regardless of the ratio.

Known limitation: tags are free-form (`AI-policy` vs `AI policy` vs `ai-regulation`
all plausible from different daily runs), so naive string-matching will undercount.
v1 accepts this — it's directionally useful, not a rigorous metric. If it turns out
to matter, the fix is a small synonym-merge table in `weekly.json`, not an LLM
classification pass (keep the free thing free).

The **narrative** wrapped around these numbers (step 4) is the one Sonnet call that
explains *why* something's rising, using the underlying article bullets for the
top 3-4 movers as context. The counting is mechanical; only the explanation costs
tokens.

### 6.4 Ideation layer (step 5) — gated

Reads `writer-profile.yaml` (doesn't exist yet) plus the assembled synthesis doc
from steps 3-4. Produces 2-4 angles, each with:
- the angle itself and why it's worth writing about
- direct links to the source articles (`url_canonical`) and the originating email
  (`https://mail.google.com/mail/u/0/#all/<thread_id>`)

If `writer-profile.yaml` doesn't exist, **this step is skipped, not faked.** The
weekly doc ships without an ideas section and a note: "writer profile not yet
configured — see `docs/week-that-was-design.md` §9." No placeholder content, no
guessing at my interests.

---

## 7. Cost

| Stage | Model | Est. tokens | Est. cost |
|---|---|---|---|
| Pre-flight, zeitgeist counts, assembly | — (Python) | 0 | $0 |
| Section synthesis (×6, briefs as input) | Sonnet | ~15-20k in/out total | ~$0.50 |
| Zeitgeist narrative | Sonnet | ~3k in/out | ~$0.10 |
| Ideation layer | Opus | ~8-10k in/out | ~$1.50-2.00 |
| **Total** | | | **~$2.10-2.60/week** |

Matches the earlier $3/week budget discussion: Opus only on the one call where
judgment quality actually matters (the ideation layer), Sonnet for narrative
synthesis, free code for everything mechanical.

Calls go through the **direct Anthropic API**, not Claude Pro `claude -p` quota —
this keeps the weekly run from competing with interactive usage, and makes the
multi-model mixing (Haiku/Sonnet/Opus in one run) straightforward, which a single
`claude -p` invocation can't do (one CLI invocation = one model). The one exception
is step 7 (NotebookLM), which genuinely needs MCP and stays on `claude -p`,
identical to how the daily skill works today.

**Guardrail:** `week_that_was.py` logs estimated token usage per stage to
`manifest.yaml` (§8) as it goes. If at any point projected total cost exceeds a
configurable ceiling (default $5), the script logs a warning and continues —
it does not silently abort a weekend run over a cost estimate. This is a budget
*signal*, not a budget *enforcement* mechanism. We're not saving lives here.

---

## 8. Instrumentation & auto-recovery

Every run writes `dhkondata/reading-db/weekly/YYYY-Www/manifest.yaml`, updated
**after each stage completes**, not just at the end:

```yaml
week: "2026-W26"
started_at: "2026-06-27T09:00:00Z"
days_found: ["2026-06-22", "2026-06-23", "2026-06-24", "2026-06-26", "2026-06-27"]
days_missing: ["2026-06-25", "2026-06-28"]
stages:
  preflight:        { status: complete, at: "2026-06-27T09:00:01Z" }
  zeitgeist_counts:  { status: complete, at: "2026-06-27T09:00:02Z" }
  section_synthesis: { status: complete, at: "2026-06-27T09:01:40Z", tokens: 18200, cost_usd: 0.48 }
  zeitgeist_narrative: { status: complete, at: "2026-06-27T09:02:05Z", tokens: 2900, cost_usd: 0.09 }
  ideation:          { status: skipped, reason: "writer-profile.yaml not found" }
  assemble_doc:      { status: complete, at: "2026-06-27T09:02:06Z" }
  notebooklm_audio:  { status: pending }
  elementfm_publish: { status: pending }
total_cost_usd: 0.57
```

> **Review comment (resume granularity):** `section_synthesis` is one manifest
> entry but it's actually 6 independent Sonnet calls, one per taxonomy section
> (§6.2). If section 4 of 6 fails, does resume re-pay for the 5 that already
> succeeded, or is there per-section sub-state? As written, the schema can only
> represent the whole stage as `complete`/`failed`/`pending`, which undercuts
> the "don't re-pay for what's already done" rationale this section argues for.
> Consider a `sections: {ai_tech: complete, economy: failed, ...}` map so a
> single section retry doesn't re-run all six.

**Why per-stage, not whole-run:** the existing sentinel pattern (`done-YYYY-MM-DD`)
is whole-run pass/fail, which is fine for the daily pipeline because it's cheap to
just retry. The weekly run has a $0.50-2.50 cost and a NotebookLM step that can take
minutes to poll — if step 7 (NotebookLM) fails or times out, re-running the whole
thing re-pays for steps 3-5. Instead: `rwe-weekly` reads `manifest.yaml` on start,
and **skips any stage already marked `complete`**, re-running only what's
`pending`/`failed`/absent. Mirrors the resume-on-failure shape already used
elsewhere in this codebase (Workflow's `resumeFromRunId` does the same thing for
a different reason — cache what's done, redo only what isn't).

This also makes "missing days" non-fatal in a useful way: if Tuesday's daily run
never completed (sentinel missing, sick day, whatever), the weekly run proceeds
with 5/7 days and records it plainly in `days_missing` — no retroactive backfill
attempt baked into this script. (`rwe-catchup.sh` already exists for backfilling
daily runs — if a day's missing, that's the tool to reach for before running
`rwe-weekly`, not something `rwe-weekly` should try to fix itself.)

**Retries:** each Anthropic API call gets a simple bounded retry (3 attempts,
exponential backoff) for transient errors (rate limit, 5xx). No retry-with-fallback-
model complexity — if a stage fails 3 times, it's marked `failed` in the manifest
and the run stops there, resumable on next invocation. Logs go to
`~/logs/reading-with-ears/weekly-YYYY-Www.log`, same convention as
`~/logs/reading-with-ears/YYYY-MM-DD.log` today.

> **Review comment (concurrency):** The daily pipeline's `done-YYYY-MM-DD`
> sentinel doubles as a lock against accidental double-runs. `rwe-weekly`'s
> manifest-based resume covers crash recovery but doesn't obviously prevent two
> concurrent invocations for the same week (e.g. a manual re-run fired while
> the first is still mid-flight) from racing on `manifest.yaml` and
> `themes.yaml` writes. Worth a simple in-progress marker (e.g. a `.lock` file,
> or an `in_progress` stage status checked at startup) alongside the manifest.

---

## 9. Build order

1. **Finish the writer profile interview** — blocks output #1 only, doesn't block
   anything else. Output: `dhkondata/reading-db/writer-profile.yaml`.
2. **Create the weekly Element.fm show**, get its ID into `config/weekly.json`.
3. **Build `week_that_was.py`** stages 1, 2, 3, 6 (pre-flight, zeitgeist counts,
   section synthesis, assembly) — none of this needs the writer profile. Ship the
   doc without an ideas section first; validate the mechanical pipeline works
   end-to-end before adding the judgment-heavy stage.
4. **Add stage 4** (zeitgeist narrative) once 1-3 are validated against a real week.
5. **Add stage 5** (ideation layer) once the writer profile exists.
6. **Wire steps 7-8** (NotebookLM `skills/user/week-that-was/SKILL.md` + `rwe-publish`
   for the weekly show) last — this is the part that mirrors existing, working code
   (daily skill's poll/title/download/publish sequence), lowest risk, do it once the
   upstream doc generation is stable so you're not debugging two things at once.

---

## 10. Non-goals (for now)

- **No cron/launchd trigger.** Manual invocation (`rwe-weekly` or
  `rwe-weekly --week 2026-W26`) only. Automate later if the manual cadence proves
  annoying — don't build scheduling infra for a once-a-week task before it's even
  been run once successfully.
- **No cross-week theme taxonomy governance UI.** If tag-merging becomes a real
  problem (§6.3), fix it with a static synonym table, not a system.
- **No multi-week or quarterly rollups.** "The Week That Was" is exactly that;
  `themes.yaml` accumulates history for trend math, but nothing in v1 reads further
  back than "trailing 4 weeks."
