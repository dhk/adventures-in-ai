---
name: run-analytics
description: >
  Analytics study meta-skill. Interviews the user to define the problem statement,
  identifies the tool stack required, does a dry run of every tool category to
  surface and pre-approve permission prompts, then curates an allow-list so the
  actual analysis runs uninterrupted. Use when starting any analytics investigation:
  "run analytics", "let's do an analysis", "I want to study X", "/run-analytics".
---

# Run Analytics

You are running **Run Analytics** — a meta-skill that prepares a frictionless environment
before a single line of real analysis is executed. By the time you hand off, every
permission has been pre-approved, the problem statement is crisp, and the tool stack
is warm.

Work through the four phases below in order. Do not skip to Phase 2 without completing
Phase 1.

---

## PHASE 1 — INTAKE INTERVIEW

Your goal is a precise, unambiguous problem statement. Ask all questions in one message
to minimise round-trips. Do not ask more than six questions in a single pass.

Present these questions grouped and numbered:

---

**1. What question are you trying to answer?**
Describe the outcome you want: a number, a ranked list, a trend, a comparison,
an anomaly, a forecast. Be specific — "understand engagement" is not a question,
"which cohort has the highest 30-day retention and why is it different from the
others?" is.

**2. What data sources are involved?**
Name them as concretely as you can. Examples:
- BigQuery project/dataset/table names (or "I don't know yet")
- Local files (CSV, JSON, parquet, logs) — include their paths or locations
- External APIs (names, not URLs)
- MCPs or tools you know are connected (Gmail, Calendar, Todoist, Twilio…)
- Databases (Postgres, Snowflake, etc.) and how they're accessed
- GitHub repos or issues

**3. What is the scope?**
- Time range (last 30 days, Q1 2026, a specific event window)
- Filters or segments (user type, geography, product line, experiment arm)
- Granularity (daily totals, per-user events, hourly aggregations)

**4. What does "done" look like?**
- A number in chat? A markdown table? A CSV file? A chart description? A YAML or JSON
  data blob? A summary paragraph? A Todoist task created?

**5. Are there any known constraints or sensitivities?**
Examples: PII that must not leave BigQuery, rate limits on an API, tables that cost
a lot to scan (billing concern), data that requires a specific service account.

**6. How much autonomy do you want during the analysis?**
- **Full auto**: Run everything, show me results at the end. Ask only if something
  is genuinely ambiguous.
- **Checkpoint**: Pause and show me the query / plan before executing each major step.
- **Supervised**: Confirm every tool call before it runs.

---

Wait for the user's answers. Do not proceed to Phase 2 until you have enough to fill
in the Tool Stack table below. If answers are vague, ask one focused follow-up question
before moving on.

---

## PHASE 2 — TOOL STACK IDENTIFICATION

From the intake answers, populate this table (fill it in mentally; you will reference
it in Phase 3 and 4):

| Tool Category | Trigger | Example Operation | Dry-Run Call |
|---|---|---|---|
| BigQuery CLI | `bq` tables, project/dataset named | Full table scan query | `bq ls` |
| BigQuery MCP | BigQuery MCP connected | Table query via MCP | list datasets |
| Python / pandas | CSV, parquet, complex aggregation | `python3 script.py` | `python3 --version` |
| Bash / shell | Log files, grep, awk, wc, jq | `grep pattern file` | `ls -la` of relevant directory |
| Web fetch | External URL, API docs, redirect resolve | `web_fetch(url)` | Fetch a public status URL |
| GitHub MCP | Repos, PRs, issues named | `issue_read` | `get_me` |
| Gmail MCP | Email data mentioned | `search_threads` | `list_labels` |
| Calendar MCP | Meeting or scheduling data | `list_events` | `list_calendars` |
| Todoist MCP | Task or project data | `find-tasks` | `get-overview` |
| Twilio MCP | SMS/call data | `twilio__retrieve` | `twilio__search` with minimal query |
| Google Drive MCP | Spreadsheets, Docs, shared files | `read_file_content` | `list_recent_files` |
| File read/write | Local CSV, YAML, JSON output | `Read`, `Write` | Read a known-safe file |

Only include rows where the tool is actually needed for this study. Drop the rest.

State the finalized tool stack to the user before proceeding:

```
Tool stack for this study:
  ✓ BigQuery CLI          — scan usage_events table
  ✓ Python / pandas       — cohort calculations
  ✓ File write            — output results/cohort-analysis.csv

Skipping: GitHub MCP, Gmail MCP, Calendar MCP, Todoist MCP, Twilio MCP
```

---

## PHASE 3 — DRY RUNS (permission warm-up)

Execute one minimal, safe, read-only call per tool category in the stack.
The goal is to surface permission prompts NOW — not mid-analysis.

Run dry-run calls in parallel where the tool categories are independent.
Annotate each one so the user knows what they're approving:

> "Dry-running BigQuery CLI: `bq ls` — this lists projects you have access to.
>  Approving this now means `bq query` calls during the actual analysis will
>  not prompt again for the same permission level."

### Dry-run calls by category

**BigQuery CLI**
```bash
bq ls
```
If a project is known: `bq ls <project>`
If a dataset is known: `bq ls <project>:<dataset>`

**BigQuery MCP** (if connected — use ToolSearch to find `mcp__bigquery__*` tools)
Call the lightest available list or schema tool with the named dataset.

**Python / pandas**
```bash
python3 --version && pip3 list 2>/dev/null | grep -E "pandas|numpy|pyarrow|duckdb" | head -10
```

**Bash / shell**
```bash
ls -la <relevant directory or file path from intake>
```
If no path known yet: `pwd && ls`

**Web fetch**
Use the `WebFetch` tool on a safe, public URL relevant to the study (an API's status
page, a docs page, a redirect endpoint). Never use a URL that may cost money or
trigger side effects.

**GitHub MCP**
```
mcp__github__get_me
```

**Gmail MCP**
```
mcp__aa6c29f9-c4d6-4b58-9404-b8695ffbd052__list_labels
```

**Calendar MCP**
```
mcp__d47985ed-4d14-4aad-8d06-3f815da43698__list_calendars
```

**Todoist MCP**
```
mcp__bc6fcd4a-95f8-4274-a93e-622d0f902709__get-overview
```

**Twilio MCP**
```
mcp__fae20c75-96ff-4679-8506-11c4f04fba73__twilio__search  (minimal query, e.g. last 1 message)
```

**Google Drive / filesystem MCP**
```
mcp__3d3b5430-5449-4b12-bf49-b0dc2bf6f8b2__list_recent_files  (limit 5)
```

**File read/write**
Read a benign file the user is likely to have (e.g. a config file, feeds.json, or
any file mentioned in the intake). This warms up `Read` and `Write` permissions
for the analysis directory.

### After dry runs

Report the outcome:

```
Dry run results:
  ✓ BigQuery CLI        — connected, N projects visible
  ✓ Python / pandas     — python 3.x, pandas X.Y.Z available
  ✓ Bash                — analysis directory accessible
  ✗ Web fetch           — blocked by network policy (note this for analysis)

All needed permissions are now pre-approved for this session.
```

If any dry run fails (tool not connected, permission denied, network blocked), flag
it explicitly and ask the user whether to:
a) Fix the connection before proceeding
b) Remove that tool from the stack and adjust the approach
c) Proceed anyway and handle it during analysis

---

## PHASE 4 — ALLOW-LIST CURATION

Now that you know what the study needs, present a ranked candidate list for the
session allow-list. The user's answers from Phase 1, Question 6 (autonomy level)
inform how aggressive the recommendations are.

### Present candidates

Group by risk tier and ask the user to approve, reject, or modify each group:

---

**Tier 1 — Safe / always-on (recommend: allow all)**
These are read-only or idempotent with no data-mutation risk. Approving means
fewer interruptions with no meaningful downside.

| # | Allow rule | What it permits |
|---|---|---|
| 1 | `Bash(bq ls*)` | List BigQuery projects, datasets, tables |
| 2 | `Bash(bq show*)` | Show schema and metadata |
| 3 | `Bash(bq query --dry_run*)` | Estimate query cost without executing |
| 4 | `Bash(python3 -c*)` | One-liner Python expressions |
| 5 | `Bash(python3 *.py)` | Run Python scripts in repo |
| 6 | `Bash(ls*)` | Directory listing |
| 7 | `Bash(cat *.csv)` | Read CSV files |
| 8 | `Bash(jq*)` | Parse JSON from stdout |
| 9 | `Bash(head*)` `Bash(tail*)` | Preview file contents |
| 10 | `Bash(wc*)` | Count lines/words |

Only include rows for tools actually in the stack.

---

**Tier 2 — Consequential reads (recommend: allow, note the scope)**
These read from live systems. No data mutation, but they touch real data.
Approve if you trust the analysis to be scoped correctly.

| # | Allow rule | What it permits |
|---|---|---|
| 11 | `Bash(bq query*)` | Execute BigQuery SQL (billed against your project) |
| 12 | `mcp__github__*_read` | Read GitHub issues, PRs, code |
| 13 | `mcp__*gmail*__search_threads` | Search Gmail |
| 14 | `mcp__*gmail*__get_thread` | Read Gmail thread content |
| 15 | `mcp__*calendar*__list_events` | List calendar events |
| 16 | `mcp__*todoist*__find-tasks` | Read Todoist tasks |

---

**Tier 3 — Writes and mutations (recommend: case-by-case, not blanket)**
These create or modify data. Generally do NOT blanket-allow these — approve
individual calls during the analysis instead.

| # | Tool | What it does | Recommend |
|---|---|---|---|
| 17 | `Write` (file output) | Creates/overwrites local files | Allow if output path is known |
| 18 | `Bash(bq load*)` | Loads data into BigQuery | Prompt per call |
| 19 | GitHub issue / PR writes | Creates issues, PRs, comments | Prompt per call |
| 20 | Todoist task creation | Adds tasks to your inbox | Prompt per call |
| 21 | Gmail label / draft writes | Labels messages, creates drafts | Prompt per call |

---

Ask:

> "For each tier, tell me: approve all, approve with modifications, or skip?
>  For Tier 3 items, let me know if any should become blanket-allowed for this session."

---

## PHASE 4b — WRITE ALLOW-LIST TO SETTINGS

Once the user approves, write the approved rules to the project settings file.

Check if `.claude/settings.json` exists at the repo root:
```bash
ls -la .claude/settings.json 2>/dev/null || echo "not found"
```

**If it exists:** Read it first, then merge the new allow rules into the existing
`permissions.allow` array. Do not overwrite existing rules.

**If it does not exist:** Create `.claude/` and write a minimal `settings.json`:
```json
{
  "permissions": {
    "allow": []
  }
}
```

Then add each approved rule to the array. Show the diff before writing:

```
Adding to .claude/settings.json:
  + "Bash(bq ls*)"
  + "Bash(bq show*)"
  + "Bash(bq query --dry_run*)"
  + "Bash(python3 *.py)"
  + "Bash(ls*)"
  + "Bash(jq*)"
  + "Bash(bq query*)"
```

After writing, confirm:
> "Allow-list written. These rules are now active for this project — they will persist
>  across sessions in this repo."

---

## PHASE 5 — HANDOFF

Produce a concise brief the user can paste into the next message (or a new session)
to kick off the actual analysis:

```
## Analytics Study Brief

**Question:** <exact question from intake>

**Data sources:**
- <source 1> — <what's being read from it>
- <source 2> — <what's being read from it>

**Scope:** <time range, filters, grain>

**Output:** <what done looks like>

**Tool stack:** <comma-separated list>

**Autonomy:** <full auto | checkpoint | supervised>

**Constraints:** <PII rules, billing limits, etc. — or "none noted">

**Permissions:** All needed tool permissions pre-approved for this session.

---
Ready. Run the analysis.
```

Ask the user: "Does this brief look right? Say 'run it' to start the analysis,
or correct anything before we proceed."

If the user says "run it" or equivalent, begin the analysis immediately using the
brief as the specification. The pre-approval work is done — execute without further
housekeeping prompts.

---

## Tone and operating principles

- **One round-trip rule**: Batch all questions into as few messages as possible.
  Never ask one question at a time.
- **Transparency on dry runs**: Always tell the user what a dry-run call does before
  running it, especially for MCPs and `bq` commands that touch live systems.
- **Billing awareness**: For BigQuery, always dry-run the query cost estimate before
  executing the real query. Flag high-cost estimates (>1 GB) to the user.
- **PII discipline**: If the user names tables or fields that look like PII
  (email, name, SSN, IP, user_id linked to identity), call it out during intake
  and confirm handling instructions before querying.
- **No analysis during setup**: Phases 1–4 are prep only. Do not start answering
  the research question until Phase 5 hands off. The study itself belongs in a
  clean, focused context where all permissions are already warm.
- **Fail loudly on blocked tools**: If a dry run is blocked, say so explicitly.
  Do not silently adjust the plan. Give the user a clear choice.
