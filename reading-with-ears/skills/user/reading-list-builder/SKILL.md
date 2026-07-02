---
name: reading-list-builder
version: "3.0"
description: >
  Fetches newsletter emails by label, routes them into a per-feed NotebookLM notebook
  that accumulates all of an ISO week's sources, and logs a full per-article record —
  URL extraction, full article fetch, Claude synthesis, infographic generation — to
  the reading-db YAML store. Runs unattended. One mode only (previously "deep" — the
  "light" fast-audio mode was removed when audio moved to a separate weekly step).
  Daily triggers: "process my newsletters", "triage my inbox", "build my reading
  list", "add newsletters to NotebookLM", "run my email triage", "run the pipeline",
  "/reading-list-builder", "reading list with analysis", "full pipeline".
  Weekly audio triggers (separate, explicit): "/reading-list-builder weekly-audio",
  "publish this week's audio", "weekly audio".
  Handles today or a multi-day range for the daily flow.
compatibility: "Gmail MCP, NotebookLM MCP, nlm CLI, ffmpeg, web_fetch, filesystem write to adventures-in-ai/dhkondata/reading-db/runs/"
---

# Reading List Builder

## Model

Use **Sonnet-class** (`claude-sonnet-4-6`) for both the daily flow and the weekly
audio flow. Steps 4-6 (article fetch, synthesis, infographic generation) require
genuine reasoning; the rest is deterministic but shares a run, so there's no
Haiku-tier sub-mode to switch to.

---

One mode for the daily flow (STEPS 0-8 below), plus a separate weekly audio flow
(STEPS W1-W4) triggered independently, on its own cadence.

Version is defined in this skill's frontmatter (version: "3.0"). At the start of every
daily run, read this value and write it as `skill_version` in the YAML run file header.

**What changed from v2.1:** audio generation, polling, titling, download, and publish
used to happen every day, per feed, right after that day's sources were loaded. As of
v3.0, the daily flow stops after writing the reading-db YAML and briefs — no audio
step runs as part of a daily invocation. A per-feed NotebookLM notebook now
accumulates a full ISO week of sources before any audio is generated; the weekly audio
flow (STEPS W1-W4) is a separate, explicitly-triggered run that finds each feed's
week-old notebook, generates audio, and publishes it. See
`docs/weekly-cadence-migration.md` for the full rationale. This does not affect the
separate "Week That Was" feature (`docs/week-that-was-design.md`) — that's a fifth,
new show with its own synthesis; this skill's notebooks are the four pre-existing
shows (news, think, professional, vital-signs).

State this at the start of a daily run: "Running v3.0 -- [date range]"
State this at the start of a weekly audio run: "Running weekly audio v3.0 -- [ISO week]"

---

# DAILY FLOW — STEPS 0-8

## STEP 0: Load Feeds Config

**Before any Gmail or NotebookLM step**, read `config/feeds.json` at
`reading-with-ears/config/feeds.json` relative to the repo root.
Prefer `~/.config/reading-with-ears/feeds.json` if readable — it takes precedence.

For each feed where `"enabled": true`, sorted by `notebook_order` ascending, record:
- `slug` — used in audio filename
- `gmail_labels` (array) — labels to search
- `notebook_category` — full title suffix with emoji
- `notebook_order` — determines nn suffix
- `audio_focus_prompt` — used by the weekly audio flow, not the daily flow
- `audio_dir` (top-level) — where the weekly audio flow saves downloaded audio

Assign `nn` (zero-padded two digits) by position in the sorted enabled list:
lowest `notebook_order` → `01`, next → `02`, etc.

If no feeds are enabled, report and stop.

---

## STEP 1: Determine Date Range & Fetch by Label

If no date is given, use today. For a range, use the earliest day as the start.

Search each enabled feed's labels individually (one call per label):

```
gmail_search_messages(q="label:<gmail_label> after:YYYY/MM/DD")
```

Single past date (catch-up): add a `before:` bound to scope exactly that day:

```
gmail_search_messages(q="label:<gmail_label> after:YYYY/MM/DD before:YYYY/MM/DD+1")
```

Fetch every label across every enabled feed before doing anything else.
If zero emails found across all labels, tell user and stop.

---

## STEP 2: Fetch Full Email Content

For each email returned, fetch the full message:

```
gmail_read_message(messageId=<id>)
```

Fetch ALL emails before doing anything else. Keep tool calls front-loaded.
Record the received date for each email (from message headers).

**HTML-only emails** (empty plain-text body): use subject + snippet to create a
minimal source entry. Title format: "<subject> -- <sender> [body unavailable]".
Note in the report.

---

## STEP 3: Route to NotebookLM (weekly-accumulating notebooks)

Labels are the routing. No triage table. No confirmation. Proceed immediately.

**One notebook per ISO week per non-empty feed** — not one per day. A notebook
created on the first day of the week that has mail for a feed keeps accumulating
sources from every subsequent day in that same week. Process days chronologically
(oldest first) when handling a multi-day range.

### Finding this week's notebook for a feed

Before creating a notebook, determine the current ISO week (Monday-Sunday) for the
date being processed, then check whether this feed already has a notebook this week:

1. Read `reading-db/runs/YYYY-MM-DD.yaml` for every date in this ISO week *prior to*
   the date being processed (Monday through yesterday, if any exist).
2. For this feed's slug, collect every `notebook_id` recorded under that day's
   top-level `notebooks:` list.
3. **Zero found:** no notebook yet this week for this feed — create one (see below).
4. **Exactly one found:** reuse it — `source_add` today's emails onto it, don't
   create a new one.
5. **More than one distinct `notebook_id` found:** this week was already partway
   through under the old per-day scheme (mid-week cutover to v3.0, or a bug). Run
   reconciliation before proceeding — see "Reconciliation" below. After
   reconciliation there is exactly one canonical notebook_id for this feed this
   week; use it.

### Notebook naming

```
reading-list-YYYY-Www-nn <notebook_category>
```

Examples (ISO week 26 of 2026):
- `reading-list-2026-W26-01 📰 News & Current Affairs`
- `reading-list-2026-W26-02 🧠 Things to Think About`
- `reading-list-2026-W26-03 💼 Professional Reading`
- `reading-list-2026-W26-05 🏥 Healthcare Reading`

If a notebook with that exact title already exists (per NotebookLM itself, not just
the YAML scan), use it — do not create a duplicate.

Create each new notebook:
```
notebook_create(title="reading-list-YYYY-Www-nn <notebook_category>")
```

Add each email as a text source (process all sources for one notebook before the
next):
```
source_add(
  notebook_id=<id>,
  source_type="text",
  title="<subject> -- <sender> (<date>)",
  text="From: <sender>\nDate: <date>\n\n<body truncated to 8000 chars>",
  wait=True
)
```

### Reconciliation (only when STEP 3 finds >1 notebook_id for a feed this week)

No notebook merge/delete tool exists in this MCP surface. Reconcile by replaying
sources into one canonical notebook, using data already on hand:

1. **Canonical notebook = the earliest day's notebook.** Leave it as-is.
2. For every *other* day this week that has its own separate notebook for this feed:
   re-fetch that day's emails via `gmail_read_message`, using the `email_id` values
   already recorded in that day's YAML (no new Gmail search needed). `source_add`
   each one onto the canonical notebook.
3. Update that day's YAML `notebooks:` entry for this feed to point at the canonical
   `notebook_id`, and add `reconciled_from: <original_notebook_id>` for traceability.
4. Leave the orphaned original notebook(s) alone — no delete call. They're harmless
   leftovers, not referenced again, not included in this week's audio.

This only triggers on a feed's first out-of-sync week (e.g. the v2.1→v3.0 cutover
week). Every week after converges on exactly one notebook per feed by construction,
so reconciliation should not recur.

---

## STEP 4: Extract & Fetch Articles

For each email processed in Step 3, extract article links from the email HTML body.

**Include links that:**
- Have meaningful anchor text (headline-like, >15 chars)
- Point to editorial content (news articles, essays, reports, blog posts)

**Exclude using the versioned block list:**
```
adventures-in-ai/dhkondata/reading-db/blocked-domains.yaml
```

Load this file at the start of Step 4 and apply:
- All domains under `blocked.esp`, `blocked.tracker`, `blocked.social`
- All anchor text patterns under `suspicious_anchor_patterns`
- Domains under `watch` are NOT blocked — fetch and record `fetch_status` for monitoring

Do not hardcode domain lists in this skill. The config file is the single source of truth.

Also exclude:
- Image sources (src= attributes)
- Anchor-only links (#section)
- Anchor text shorter than 15 chars

For digest newsletters (1440, Morning Dispatch, The 7, TLDR): extract one record per article link.
For single-article newsletters: extract one record.

For each extracted link:

1. Assign `article_id`: `<messageId>-<sequence>` (e.g. `19d77ecea1ccb554-01`)
2. Store `url_raw` (as found in email HTML)
3. Resolve redirect → `url_canonical` via `web_fetch` (follow redirects, store final URL)
4. Extract `domain` from `url_canonical`
5. Store `anchor_text` and `excerpt` (surrounding sentence(s) from email body)
6. Set `resolve_status`: `resolved | failed | redirect_loop | timeout`
7. Set `parse_confidence`: 0.0–1.0
   - 0.9–1.0: clean canonical URL, clear headline anchor text
   - 0.7–0.89: resolved but anchor text vague or URL looks like a section page
   - 0.5–0.69: resolved but uncertain if this is the primary article
   - <0.5: could not resolve or anchor text is unclear

Fetch full article body for each article where `resolve_status = "resolved"`:
```
web_fetch(url=url_canonical)
```

Extract main article body (strip nav, ads, footers, sidebars — main content only).
Truncate to 12,000 chars if needed.

Set `fetch_status`: `success | paywalled | not_found | bot_blocked | timeout | error`
Set `full_body_available`: `true | false`
Set `full_body_chars`: character count of what was retrieved

---

## STEP 5: Synthesize Articles

For each article, generate synthesis bullets using only the fetched content.

Input priority:
1. Full article body (`fetch_status = success`) → use this
2. Email excerpt (fetch failed or paywalled) → use as fallback, flag it
3. Anchor text only → skip synthesis entirely, set `status: skipped`

Synthesis prompt (use exactly):
```
Extract 3-5 key claims from this article.
Only include claims that are directly and explicitly stated in the text.
Do not infer, extrapolate, summarize themes, or editorialize.
Do not combine claims from different parts of the article into a single bullet.
Each bullet should be independently verifiable against the source text.
If you are uncertain whether a claim is directly stated, omit it.
If fewer than 3 clear claims are present, return only those that are certain.
```

Set `synthesis.source`: `article | email_body | skipped`
Set `synthesis.status`: `complete | skipped`
Set `synthesis.confidence_note`: null, or a brief note if fallback was used

---

## STEP 6: Generate Article Brief Infographics

For each article where `synthesis.status = "complete"`, generate an HTML infographic
using the template at:
```
adventures-in-ai/dhkondata/reading-db/templates/article-brief-template.html
```

The template uses mustache-style placeholders. Replace each with article data:

| Placeholder        | Value                                                                  |
|--------------------|------------------------------------------------------------------------|
| {{ARTICLE_TITLE}}  | article.source.anchor_text (headline)                                  |
| {{SENDER_NAME}}    | email.sender_name                                                      |
| {{RECEIVED_DATE}}  | email.received_at (formatted: MMM D, YYYY)                             |
| {{CATEGORY_LABEL}} | routing.category mapped to full label (e.g. "💼 Professional Reading") |
| {{CANONICAL_URL}}  | article.source.url_canonical                                           |
| {{RUN_DATE}}       | run_date                                                               |
| {{SKILL_VERSION}}  | skill_version from frontmatter                                         |

For the summary/takeaway split:
- LEFT panel (Summary Points): bullets 1–3 (or up to 5 if available)
- RIGHT panel (Takeaways): final 2–3 bullets
- If only 3 bullets total: show all 3 left, repeat strongest 1–2 on right reframed as takeaways
- If `synthesis.source = "email_body"`: add footnote marker (*) to title and footer note

Output each infographic to:
```
adventures-in-ai/dhkondata/reading-db/briefs/YYYY-MM-DD/<article_id>.html
```

Create the directory if it does not exist.
Skip if `synthesis.status != "complete"`. Record path as `infographic.path`.

---

## STEP 7: Write YAML to reading-db

Write one YAML file per run date to:
```
adventures-in-ai/dhkondata/reading-db/runs/YYYY-MM-DD.yaml
```

If processing a multi-day range, write one file per day.
If a file for that date already exists, append new emails — do not overwrite.
If the directory does not exist, create it before writing.

Read the version from this skill's frontmatter and write it as `skill_version`.

File structure:

```yaml
run_date: YYYY-MM-DD
skill_version: "3.0"
pipeline_mode: standard
notebooks:
  - label: "newsletter/pro"
    notebook_id: "ghi789-..."
    notebook_title: "reading-list-2026-W26-03 💼 Professional Reading"
    reconciled_from: null   # set only if STEP 3 reconciliation ran for this entry

emails:
  - email_id: "19d77ecea1ccb554"
    thread_id: "19d77ecea1ccb554"
    received_at: "2026-05-09T07:14:00Z"
    label: "newsletter/pro"
    sender: "dan@tldrnewsletter.com"
    sender_name: "TLDR"
    subject: "TLDR: OpenAI's new model, DuckDB 2.0"
    article_count: 3
    parse_notes: null

    articles:
      - article_id: "19d77ecea1ccb554-01"
        position: 1

        source:
          url_raw: "https://links.tldrnewsletter.com/abc123"
          url_canonical: "https://openai.com/blog/gpt-5"
          domain: "openai.com"
          anchor_text: "OpenAI announces GPT-5"
          resolve_status: "resolved"
          parse_confidence: 0.95

        content:
          full_body_available: true
          full_body_chars: 4821
          fetch_status: "success"
          fetch_notes: null

        routing:
          category: "pro"
          notebook_id: "ghi789-..."
          notebook_title: "reading-list-2026-W26-03 💼 Professional Reading"

        synthesis:
          status: "complete"
          source: "article"
          bullets:
            - "GPT-5 scores 87% on MMLU benchmark, up from 72% on GPT-4"
            - "API access launches May 15 at $15 per million tokens"
            - "Context window extended to 256k tokens"
          generated_at: "2026-05-09T09:32:00Z"
          confidence_note: null

        infographic:
          status: "generated"
          path: "reading-db/briefs/2026-05-09/19d77ecea1ccb554-01.html"
          generated_at: "2026-05-09T09:45:00Z"

        tags: []
        status: "synthesized"
```

After writing, confirm file path and record count.

---

## STEP 8: Report

```
Done -- [date range] -- v3.0

NotebookLM -- [N] feeds routed this run:

  📰 News & Current Affairs -> "reading-list-2026-W26-01 📰 News & Current Affairs"
    +3 sources today (week total: 11)
  💼 Professional Reading -> "reading-list-2026-W26-03 💼 Professional Reading"
    +2 sources today (week total: 7)

No audio generated -- audio runs separately via the weekly audio flow (see below).

Reading DB -- adventures-in-ai/dhkondata/reading-db/runs/YYYY-MM-DD.yaml
  skill_version: 3.0
  [N] emails processed
  [N] articles extracted
  [N] fully fetched (synthesis from article)
  [N] fallback (synthesis from email excerpt)
  [N] skipped (paywalled / no body)

Briefs -- adventures-in-ai/dhkondata/reading-db/briefs/YYYY-MM-DD/
  [N] infographics generated
  [N] skipped (synthesis incomplete)

Fetch issues (if any):
  - paywalled: [N] -- [sender names]
  - failed/timeout: [N] -- [sender names]

Reconciliation (if any ran this week): [feed] -- merged [N] notebook(s) into
  <canonical_notebook_id>

HTML-only emails (if any): [list]
Nothing was deleted or archived in Gmail.
```

---

# WEEKLY AUDIO FLOW — STEPS W1-W4

Separate, explicitly-triggered run. Not part of the daily flow, and not the same
feature as "Week That Was" (`docs/week-that-was-design.md`) — this generates one
audio episode per week for each of the four existing feeds, from the notebook that
accumulated over the week via STEP 3 above.

If no ISO week is given, use the current one.

## STEP W1: Find This Week's Notebooks

For the target ISO week, read every `reading-db/runs/YYYY-MM-DD.yaml` whose date
falls in that week. For each enabled feed, collect the distinct `notebook_id` under
that day's `notebooks:` list.

- **Exactly one distinct `notebook_id`:** this is the feed's week notebook. Proceed.
- **Zero:** no mail for this feed all week — skip it, not an error.
- **More than one:** STEP 3's reconciliation should have already prevented this by
  the time weekly audio runs. If it still happens, stop and report it rather than
  guessing which notebook is authoritative — this indicates STEP 3 reconciliation
  didn't run or didn't complete for that feed/week.

## STEP W2: Generate Audio

For each feed's week notebook found in STEP W1:
```
studio_create(
  notebook_id=<id>,
  artifact_type="audio",
  audio_format="deep_dive",
  audio_length="long",
  focus_prompt="<audio_focus_prompt from feeds.json for this feed>",
  confirm=True
)
```

Fire all audio generations before polling any of them.

## STEP W3: Poll, Title & Publish Audio

Poll each notebook with `studio_status` every 30 seconds until `status == "complete"`.
Timeout: 10 minutes. Log any that time out and continue with the rest.

### Episode titling

```
notebook_describe(notebook_id=<id>)

studio_status(
  notebook_id=<id>,
  action="rename",
  artifact_id=<artifact_id>,
  new_title="<NotebookLM-generated title>\n\n• <key idea 1>\n• <key idea 2>\n• <key idea 3>\n\nSources: <Newsletter (topic)> · <Newsletter (topic)> · ..."
)
```

Titling rules:
- Keep NotebookLM's auto-generated title — do not replace it
- Bullets state what something *means*, not what it *covers* — insight-first,
  drawing on the whole week's sources, not just one day
- 3 bullets minimum, 5 maximum
- Sources line: `Newsletter Name (topic shorthand) · ...`

### Download & Publish

Once all artifacts are titled, hand off to `rwe-publish` for download, m4a→mp3
conversion, and Element.fm upload — the audio file is dated/named with **today's
date** (the day this weekly run executes), but notebook lookup must use the ISO
week (`--notebook-week`), since notebook titles are week-scoped
(`reading-list-YYYY-Www-nn ...`), not date-scoped:

```bash
rwe-publish --date YYYY-MM-DD --notebook-week YYYY-Www --no-wait-for-studio-status --audio-format mp3
```

The downloaded-audio filename/title convention (`YYYY-MM-DD-<slug>.mp3`,
`<show_name> - YYYY-MM-DD`) is unchanged — it's scoped by "the day this episode was
published," which is now once a week instead of once a day, but that mechanism
doesn't need to know that. **Notebook discovery is a separate mechanism** and does
need to know: `--notebook-week` tells `rwe-publish` to look up notebooks by ISO week
label instead of by date (see `find_notebooks_for_week` in `publish_episodes.py`).
Omitting `--notebook-week` here would make `rwe-publish` search for a
`YYYY-MM-DD`-titled notebook that no longer exists under v3.0's weekly naming — it
would find zero notebooks and exit non-zero. `rwe-publish` is idempotent:
already-downloaded files are skipped automatically.

To skip the Element.fm upload, add `--download-only`. Do not manually invoke
`nlm download` or `ffmpeg` — `rwe-publish` handles both.

## STEP W4: Report

```
Done -- weekly audio -- [ISO week] -- v3.0

  📰 News & Current Affairs -> 2026-07-03-news.mp3 (published)
  💼 Professional Reading -> 2026-07-03-professional.mp3 (published)
  🧠 Things to Think About -> skipped (no mail this week)

Timeouts (if any): [feed] -- studio_status did not complete within 10 min
```

---

## Edge Cases

Daily flow:
- No emails in range: tell user, offer to widen date range
- HTML-only email body: use subject + snippet, note body unavailable in report
- Gmail MCP unavailable: tell user to check Settings → Connectors
- Notebook already exists (same title): reuse it, do not create a duplicate
- Tool call limit hit mid-run: report what is done, what is pending; continue next turn with "proceed"
- No emails on a given day in range: skip that day silently, no empty notebooks
- URL resolve fails: store `url_raw` only, set `resolve_status: failed`, continue
- Article fetch paywalled: fall back to email excerpt for synthesis, flag in report
- Article fetch any other failure: set `synthesis.status: skipped`, flag in report
- YAML write path missing: create directory structure before writing
- Multi-day range: one YAML file per day, process and write sequentially
- Infographic synthesis incomplete: set `infographic.status: skipped`, continue
- Infographic template missing: log warning, skip generation, continue
- `blocked-domains.yaml` missing: log warning, fall back to hardcoded minimal list,
  flag prominently in report so user knows config was not loaded
- More than one `notebook_id` found for a feed this week (STEP 3): run reconciliation
  before adding today's sources

Weekly audio flow:
- `studio_status` timeout (10 min): log it, continue with other notebooks
- Audio file already exists at download path: `rwe-publish` skips automatically
- More than one `notebook_id` found for a feed this week (STEP W1): stop and report
  rather than guessing — this means STEP 3 reconciliation didn't complete
- No notebook at all for a feed this week: skip it in the report, not an error
