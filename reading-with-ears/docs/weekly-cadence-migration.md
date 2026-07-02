# Weekly Audio Cadence — Migration Design

**Status:** Design — supersedes part of `reading-list-builder` v2.1. Not yet implemented.
**Scope:** The four existing per-feed shows (news, think, professional, vital-signs).
**Explicitly separate from:** the "Week That Was" cross-feed synthesis feature
(`docs/week-that-was-design.md`) — that's a fifth, new show with its own taxonomy,
zeitgeist, and article-ideas layer. This doc is about changing the *publish cadence*
of the four shows that already exist. The two features share the reading-db YAML as
input but otherwise don't interact.

---

## 1. What's changing

**Today (v2.1):** every day, for each enabled feed, the skill creates a new NotebookLM
notebook, loads that day's emails as sources, generates an audio overview same-day,
downloads it, and publishes it to Element.fm. One episode per feed per day.

**Target:** newsletters are still fetched, routed, and synthesized every day — the
daily YAML/briefs output doesn't change. But audio generation, download, and publish
happen **once a week**, using a single notebook per feed that accumulated all seven
days of that week's sources. One episode per feed per week, same Element.fm shows.

Nothing about *what* gets read or synthesized changes. What changes is *when* a
notebook gets turned into an episode.

---

## 2. The one real design problem: notebook accumulation

Today, "one notebook per day per feed" means there's never a question of which
notebook to add sources to — a fresh one gets created every day. Weekly cadence means
day 2 of a week must find and reuse day 1's notebook, not create a new one.

**Mechanism: no new persistent store — reuse the daily YAML.**

Each day's `reading-db/runs/YYYY-MM-DD.yaml` already records, per feed, the
`notebook_id`/`notebook_title` it routed into (top-level `notebooks:` list). To decide
whether a feed needs a new notebook today or should reuse one:

1. Compute the ISO week for today's date.
2. Read every `reading-db/runs/*.yaml` file for the days *already processed this week*
   (Monday through yesterday).
3. For this feed's slug, if any of those files recorded a `notebook_id`, reuse it —
   `source_add` today's emails onto that notebook.
4. If none did (first day this week with mail for this feed), create a new notebook,
   titled by week instead of by day:

   ```
   reading-list-2026-W26-01 📰 News & Current Affairs
   ```

   (Same `nn` suffix convention as today, same `notebook_category`, just
   `YYYY-Www` instead of `YYYY-MM-DD` in the title.)

This is exactly the "if a notebook with that title already exists, use it" rule the
skill already has (STEP 3, v2.1) — just changing the lookup key from day to week, and
changing *how* the lookup happens (scan this week's YAMLs instead of relying on a
title match against whatever NotebookLM reports back). Scanning local YAML is more
reliable than a title-search round-trip through the NotebookLM MCP, and the data's
already sitting right there.

**Failure mode this avoids:** if notebook-title-search were the only mechanism and it
flaked (MCP hiccup, title formatting drift), the skill could silently create a second
notebook for the same feed/week and split that week's sources across two notebooks
with no error. Reading the week's own YAML files as the source of truth for "which
notebook did we already use" removes that failure mode — it's the same data the skill
itself wrote a moment ago.

---

## 3. Skill changes (`reading-list-builder` v2.1 → v3.0)

### Daily run (both modes) — stops earlier

- **STEP 3** (route to NotebookLM): notebook naming/lookup changes as in §2. Otherwise
  unchanged — still one `source_add` per email, still processed day-by-day within a
  multi-day range.
- **STEP 4** (generate audio): **removed from the daily run.** No `studio_create` call
  happens as part of a daily invocation, in either mode.
- **Light mode STEPS 5-6** (poll/title/download/publish, report): **removed.** Light
  mode is now Steps 0-3 only — fetch, route, add sources, report. No audio, no
  synthesis. Worth asking whether light mode is still worth keeping at all now that
  its main distinguishing feature (same-day audio) is gone — see the open question
  in §5.
- **Deep mode STEPS 9-10** (poll/title/download/publish, report): the poll/title/
  publish portion (STEP 9) is **removed**. Steps 5-8 (article extraction, synthesis,
  briefs, YAML write) are **unchanged** — this is the part the user explicitly said
  stays daily. STEP 10 (report) drops the "NotebookLM — audio" section since no audio
  work happened; keeps the reading-db/briefs summary.

### New: weekly audio step

A new mode in the same skill (not a separate skill file — it reuses STEP 3's notebook
lookup and is otherwise identical prose to today's STEP 5/9, just retargeted):

**Trigger:** `/reading-list-builder weekly-audio`, "publish this week's audio",
"weekly audio" — explicit, not part of the default daily trigger set.

**STEP W1: Find this week's notebooks.** For the target ISO week (default: current),
scan `reading-db/runs/*.yaml` for that week's dates, collect the distinct
`notebook_id`/`notebook_title` per feed slug recorded in `notebooks:`. A feed with no
notebook this week (no mail all week) is skipped, not an error.

**STEP W2: Generate audio.** `studio_create` on each notebook found, using that feed's
`audio_focus_prompt` from `feeds.json` — identical to today's STEP 4, just fired once
per week per feed instead of once per day per feed. Focus prompts may need a light
rewrite eventually since they currently say things like "this episode should run
approximately 12 minutes" scoped to a day's news — out of scope for this doc; flag as
a follow-up, don't block the cadence migration on rewriting prompt copy.

**STEP W3: Poll, title, publish.** Identical to today's STEP 5/9 verbatim — poll
`studio_status`, `notebook_describe` + rename with insight bullets, hand off to
`rwe-publish`. The only change is what date range to pass through: `rwe-publish` needs
a week-scoped invocation rather than `--date YYYY-MM-DD`. `publish_episodes.py`
currently expects `--date`; this needs either a `--week YYYY-Www` flag or the weekly
step passes an explicit filename pattern. Flagged as an implementation detail to
resolve when building this step, not a design fork — same script, one new flag.

**STEP W4: Report.** Same shape as today's report, scoped to a week.

---

## 4. Downstream impact

- **`bin/rwe-run.sh`** (daily): stops expecting audio/publish to happen. Drop the
  `python3 .../publish_episodes.py` call from the daily invocation entirely — there's
  nothing to publish most days. The sentinel (`done-YYYY-MM-DD`) still guards against
  double-running the daily fetch/synthesize step.
- **New scheduled entry point** for the weekly audio step — likely `rwe-run.sh
  --weekly-audio` (mirroring the existing `--catch-up` delegation pattern) or a new
  `bin/rwe-weekly-audio` wrapper, invoked once a week (Friday/weekend, matching the
  cadence the user already wants for "Week That Was"). Naming collision to watch:
  `bin/rwe-weekly` already exists for the *separate* "Week That Was" feature (§0) —
  don't reuse that script for this. Suggest `rwe-weekly-audio` to keep the two
  unambiguous.
- **`rwe-catchup.sh`**: currently backfills a day at a time including publish. Needs
  to stop invoking publish per day once this ships — catch-up becomes fetch/synthesize
  only, same as the daily run's new shape.
- **`feeds.json`**: no schema change needed. `elementfm_show_id` per feed is already
  what the weekly publish step targets — this migration doesn't touch show identity,
  only cadence.
- **`publish_episodes.py` / `podcast_config.py`: no changes needed.** The existing
  `YYYY-MM-DD-<slug>.mp3` filename convention is scoped by "the day this audio was
  published," not by what date range the source material covers. A weekly episode
  published on a Friday is just `2026-07-03-news.mp3` like any other day's file —
  `rwe-publish --date <trigger date>` works unchanged. The "week's worth of content"
  lives in the notebook's accumulated sources, not in the filename.

---

## 5. Decisions

1. **Light mode: dropped.** Deep mode becomes the only mode. `reading-list-builder`
   v3.0 has one mode — fetch, route, synthesize, brief, write YAML, report. No mode
   detection section needed at all.
2. **Weekly audio trigger: manual**, same as "Week That Was." No cron/launchd in v1.
   The user is responsible for running it; a missed week is an accepted risk, not
   engineered around, consistent with the no-scheduling-infra stance already taken
   for the new weekly feature.
3. **Cutover: reconcile this week retroactively.** Since this ships mid-week
   (2026-07-02, a Thursday), Monday-Wednesday already created separate per-day
   notebooks under v2.1 for at least some feeds. Procedure in §6.

---

## 6. Reconciliation procedure (one-time, handled by STEP 3's routing logic)

No NotebookLM "merge notebooks" or "delete notebook" tool is assumed to exist — the
MCP surface used elsewhere in this skill is `notebook_create`, `source_add`,
`studio_create`, `studio_status`, `notebook_describe`. Reconciliation therefore works
by **replaying** sources into a single canonical notebook, using data the skill
already has — it does not require reading anything back out of NotebookLM.

When STEP 3's weekly lookup (§2) scans this week's YAML files and finds **more than
one distinct `notebook_id`** for the same feed slug (the signature of a mid-week
cutover), for each feed with this pattern:

1. **Canonical notebook = the earliest day's notebook.** Keep it; do nothing to it.
2. **For every later day in the week that has its own separate notebook:** re-fetch
   that day's emails for this feed via `gmail_read_message`, using the `email_id`
   values already recorded in that day's YAML (no new Gmail search needed — the
   message IDs are already known). `source_add` each onto the canonical notebook,
   exactly as STEP 3 already does for same-day sources.
3. **Update that day's YAML** `notebooks:` entry for this feed to point at the
   canonical `notebook_id`, and add a `reconciled_from: <original_notebook_id>` note
   for traceability. This ensures every subsequent lookup this week (including
   Thursday's own run) converges on one notebook.
4. **The orphaned original per-day notebooks are left alone** in NotebookLM — no
   delete call. Harmless leftovers; not referenced by anything going forward, and
   not included in the week's audio.

This only runs once, the first time a feed's weekly lookup finds more than one
notebook_id for the current week. Every week after this one starts clean — STEP 3's
normal single-notebook-per-week logic is by definition already reconciled, since it
never lets more than one notebook get created per feed per week going forward.
