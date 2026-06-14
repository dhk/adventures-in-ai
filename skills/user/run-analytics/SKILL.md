---
name: run-analytics
description: >
  Analytics study meta-skill. Two modes: standard (interview → tool stack → dry runs
  → allow-list → handoff) and discovery (crawl past sessions, skill definitions, and
  context snapshots to infer a default allow-list without a live study). Use when
  starting any analytics investigation or calibrating the project allow-list.
  Triggers: "run analytics", "let's do an analysis", "I want to study X",
  "/run-analytics", "/run-analytics --discover [timeframe]".
---

# Run Analytics

You are running **Run Analytics** — a meta-skill that prepares a frictionless environment
before a single line of real analysis is executed. By the time you hand off, every
permission has been pre-approved, the problem statement is crisp, and the tool stack
is warm.

---

## MODE DETECTION

Check the invocation args before doing anything else.

**Discovery mode** — triggered by any of:
- `/run-analytics --discover`
- `/run-analytics discover`
- `/run-analytics --discover 7d` (or `30d`, `90d`, `all`)
- "discover my tools", "calibrate my allow-list", "what tools do I use"

→ Skip to **DISCOVERY MODE** below. Do not run the intake interview.

**Standard mode** — all other invocations:
→ Work through Phases 1–5 in order. Do not skip to Phase 2 without completing Phase 1.

---

## DISCOVERY MODE

> Goal: crawl the historical record — session transcripts, skill definitions, and
> context snapshots — to build a data-driven default allow-list without requiring
> the user to describe a specific study upfront.

### Parse the timeframe

Default: `30d` (last 30 days). Accept: `7d`, `14d`, `30d`, `90d`, `180d`, `all`.

Convert to a cutoff date:
```
30d  → today minus 30 days
all  → epoch (no filter)
```

Tell the user what you're about to do:
> "Scanning the last [N] days of session transcripts, [N] skill definitions,
>  and project context files to infer your tool usage patterns.
>  No data leaves your machine — this reads local files only."

---

### DISCOVERY PHASE A — Session Transcript Crawl

Claude Code stores session transcripts as JSONL files under `~/.claude/projects/`.
Each project directory is named after a hash of the project path.
Each file is one session; each line is a conversation turn.

**Step A1 — Find the project directory**

The current repo path is the working directory. Encode it to find the matching
`~/.claude/projects/` subdirectory:

```bash
# List all project dirs and their sizes to help identify the active one
ls -lt ~/.claude/projects/ 2>/dev/null | head -20
```

If multiple directories exist, the correct one is the most-recently-modified directory
whose name, when decoded, matches the current working directory path. If you cannot
determine which is correct, list all project directories and ask the user to confirm
which one to crawl, or crawl all of them.

**Step A2 — Filter by timeframe**

```bash
# Find JSONL files modified within the timeframe
find ~/.claude/projects -name "*.jsonl" -newer <(date -d "-<N> days" +%Y-%m-%d) 2>/dev/null \
  | sort -t/ -k6 -r \
  | head -200
```

For `all` timeframe, omit the `-newer` filter. Cap at 200 files to avoid runaway
reads.

**Step A3 — Extract tool usage**

Parse tool_use entries from the filtered session files. Tool calls appear as JSON
objects with `"type":"tool_use"` and a `"name"` field, either at the top level or
nested inside an assistant message's `content` array.

```bash
# Count tool calls across sessions, grouped by tool name
find ~/.claude/projects -name "*.jsonl" -newer <(date -d "-<N> days" +%Y-%m-%d) \
  2>/dev/null -exec cat {} \; \
  | python3 - <<'EOF'
import sys, json
from collections import defaultdict

tool_sessions = defaultdict(set)   # tool -> set of session filenames
tool_calls    = defaultdict(int)   # tool -> total call count
current_file  = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        continue

    def extract_tools(o, session):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and "name" in o:
                name = o["name"]
                tool_calls[name] += 1
                tool_sessions[name].add(session)
            for v in o.values():
                extract_tools(v, session)
        elif isinstance(o, list):
            for item in o:
                extract_tools(item, session)

    extract_tools(obj, id(obj))   # session approximated by line group

for tool, count in sorted(tool_calls.items(), key=lambda x: -x[1]):
    sessions = len(tool_sessions[tool])
    print(f"{count:5d} calls  {sessions:3d} sessions  {tool}")
EOF
```

Capture the output as the **transcript signal**.

**Step A4 — Extract Bash command patterns**

For `Bash` tool calls, the raw count is not enough — we need what commands were run.
Extract the leading token of each Bash `command` input:

```bash
find ~/.claude/projects -name "*.jsonl" -newer <(date -d "-<N> days" +%Y-%m-%d) \
  2>/dev/null -exec cat {} \; \
  | python3 - <<'EOF'
import sys, json, re
from collections import Counter

cmd_counter = Counter()

for line in sys.stdin:
    try:
        obj = json.loads(line.strip())
    except:
        continue

    def find_bash(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and o.get("name") == "Bash":
                cmd = o.get("input", {}).get("command", "")
                # Extract the leading binary (first word, ignoring env vars)
                tokens = cmd.strip().split()
                for tok in tokens:
                    if not tok.startswith(("-", "export", "set", "unset")):
                        binary = tok.split("/")[-1]
                        cmd_counter[binary] += 1
                        break
            for v in o.values():
                find_bash(v)
        elif isinstance(o, list):
            for item in o:
                find_bash(item)

    find_bash(obj)

for cmd, count in cmd_counter.most_common(30):
    print(f"{count:5d}  {cmd}")
EOF
```

Capture as the **bash command signal**.

---

### DISCOVERY PHASE B — Skill Definition Crawl

Read all `SKILL.md` files in the repository to extract declared tool dependencies.

**Step B1 — Find skill files**

```bash
find . -name "SKILL.md" 2>/dev/null
```

**Step B2 — Extract tool references from each skill**

For each SKILL.md found, scan for:
- `compatibility:` frontmatter line — lists MCP dependencies
- `Bash(` patterns — explicit allow-rule syntax
- `mcp__` prefixes — MCP tool references
- Known binary names: `bq`, `python3`, `pip3`, `jq`, `ffmpeg`, `rwe-publish`, `nlm`, `gh`, `git`, `curl`
- `WebFetch`, `WebSearch`, `Read`, `Write`, `Edit`, `Glob`, `Grep` — built-in Claude Code tools

```bash
# Extract tool signals from all skill files
find . -name "SKILL.md" -exec grep -Hn \
  -E "(compatibility:|Bash\(|mcp__|bq |python3|jq |ffmpeg|WebFetch|WebSearch|rwe-publish|nlm )" \
  {} \;
```

Build a skill → tools map from the output.

**Step B3 — Check existing allow-list**

```bash
cat .claude/settings.json 2>/dev/null || echo "none"
```

Record any rules already in `permissions.allow` — these are excluded from the
new candidates (no duplicates).

---

### DISCOVERY PHASE C — Context Snapshot Crawl

**Step C1 — CLAUDE.md files**

```bash
find . -name "CLAUDE.md" -exec grep -Hn \
  -E "(bq|python3|BigQuery|pandas|MCP|mcp__|tool|allow|permission)" \
  {} \;
```

Note any tool references or permission guidance.

**Step C2 — .claude directory**

```bash
ls -la .claude/ 2>/dev/null
```

Check for hooks, custom commands, or additional settings files. Note anything that
implies a tool dependency (e.g. a SessionStart hook that installs packages implies
`pip3 install`).

---

### DISCOVERY PHASE D — Analysis and Ranking

Merge the three signals into a single ranked candidate list.

**Scoring formula (per tool/command):**

| Signal | Weight |
|---|---|
| Session transcript calls | 3 pts per 10 calls (capped at 30 pts) |
| Session breadth (distinct sessions) | 2 pts per session (capped at 20 pts) |
| Referenced in a skill definition | 10 pts flat |
| Referenced in CLAUDE.md or context | 5 pts flat |
| Already in allow-list | subtract 100 (exclude from candidates) |

**Recency decay**: multiply the transcript signal by:
- Last 7 days: 1.0
- Last 8–30 days: 0.8
- Last 31–90 days: 0.6
- Older: 0.4

**Map raw tool/command names to allow-rule syntax:**

| Observed | Allow rule | Tier |
|---|---|---|
| `bq` (ls/show commands) | `Bash(bq ls*)`, `Bash(bq show*)` | 1 |
| `bq` (query commands) | `Bash(bq query*)` | 2 |
| `python3` | `Bash(python3*)` | 1 |
| `pip3` | `Bash(pip3*)` | 1 |
| `jq` | `Bash(jq*)` | 1 |
| `ls` | `Bash(ls*)` | 1 |
| `cat` | `Bash(cat*)` | 1 |
| `grep` | `Bash(grep*)` | 1 |
| `head`/`tail` | `Bash(head*)`, `Bash(tail*)` | 1 |
| `wc` | `Bash(wc*)` | 1 |
| `git` | `Bash(git*)` | 1 |
| `gh` | `Bash(gh*)` | 2 |
| `curl` | `Bash(curl*)` | 2 |
| `ffmpeg` | `Bash(ffmpeg*)` | 1 |
| `rwe-publish` | `Bash(rwe-publish*)` | 1 |
| `nlm` | `Bash(nlm*)` | 1 |
| `WebFetch` | `WebFetch(*)` | 2 |
| `WebSearch` | `WebSearch(*)` | 2 |
| `mcp__github__*_read` | `mcp__github__*_read` | 2 |
| `mcp__github__*_write` | `mcp__github__*_write` | 3 |
| `mcp__*gmail*__search*` | `mcp__*gmail*__search_threads` | 2 |
| `mcp__*gmail*__get*` | `mcp__*gmail*__get_thread` | 2 |
| `mcp__*gmail*__label*` | (Tier 3, skip unless high score) | 3 |
| `mcp__*calendar*__list*` | `mcp__*calendar*__list_events` | 2 |
| `mcp__*todoist*__find*` | `mcp__*todoist*__find-tasks` | 1 |
| `mcp__*todoist*__add*` | (Tier 3) | 3 |

Built-in tools (`Read`, `Glob`, `Grep`, `Edit`, `Write`) are always available and
do not require allow-list entries. Skip them.

**Present the discovery results:**

```
Discovery results — last [N] days
  Sessions crawled:  47
  Skill files found:  5
  Context files found:  1

Top tool signals (ranked by score):

  Score  Rule                           Sources
  ─────────────────────────────────────────────────────────────
  82     Bash(ls*)                      transcripts (203 calls, 47 sessions)
  74     Bash(python3*)                 transcripts (84 calls, 19 sessions) + 2 skills
  71     Bash(bq ls*), Bash(bq show*)   transcripts (67 calls, 23 sessions) + 1 skill
  68     Bash(bq query*)                transcripts (60 calls, 23 sessions)
  55     mcp__github__*_read            transcripts (61 calls, 31 sessions)
  42     WebFetch(*)                    transcripts (44 calls, 12 sessions) + 1 skill
  38     mcp__*gmail*__search_threads   transcripts (29 calls, 8 sessions) + 2 skills
  31     Bash(jq*)                      transcripts (55 calls, 22 sessions)
  18     mcp__*todoist*__find-tasks     1 skill + CLAUDE.md
   8     Bash(ffmpeg*)                  1 skill
   4     mcp__*calendar*__list_events   1 skill

Already in allow-list (skipped):
  — none

Tier 3 (write/mutation — excluded from auto-recommend):
  mcp__github__*_write    — 12 calls, 7 sessions
  mcp__*gmail*__label*    — 8 calls, 3 sessions
  mcp__*todoist*__add*    — 5 calls, 2 sessions
```

---

### DISCOVERY PHASE E — Curation and Write

Proceed to **Phase 4 — Allow-List Curation** below, using the discovery results
as the pre-populated candidate list instead of the study-derived stack.

Key differences in discovery mode:
- Tier 1 and 2 candidates come from the ranked table above (score > 20 → include).
- Tier 3 items are shown with their call counts so the user can decide whether
  any of them should be promoted.
- The written rules are intended as **permanent project defaults**, not just for
  one session. State this clearly before writing.
- After writing, also offer to add a note to `CLAUDE.md` documenting what was
  added and why, so future sessions have context.

Skip Phase 5 (handoff brief) — discovery mode does not produce a study brief.

---

## STANDARD MODE

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
