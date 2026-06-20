---
name: run-analytics
description: >
  Analytics study meta-skill. Two modes: standard (interview → tool stack →
  connection verification → allow-list → analysis) and discovery (crawl past
  sessions, skill definitions, and context snapshots to build a default
  allow-list). Use when starting any analytics investigation or calibrating
  the project allow-list.
  Triggers: "run analytics", "let's do an analysis", "I want to study X",
  "/run-analytics", "/run-analytics --discover [timeframe]".
---

# Run Analytics

You are running **Run Analytics** — a meta-skill that resolves the setup friction
(permissions, tool connections, problem clarity) before a single line of real
analysis runs.

---

## MODE DETECTION

Check the invocation args before doing anything else.

**Discovery mode** — triggered by any of:
- `/run-analytics --discover`
- `/run-analytics discover`
- `/run-analytics --discover 7d` (or `14d`, `30d`, `90d`, `180d`, `all`)
- "discover my tools", "calibrate my allow-list", "what tools do I use"

→ Jump to **DISCOVERY MODE**. Do not run the intake interview.

**Standard mode** — all other invocations:
→ Work through Phases 1–5 below in order.

---

## DISCOVERY MODE

Goal: crawl the historical record to build a data-driven default allow-list
without requiring the user to describe a specific study upfront.

### Step 0 — Environment check

Before crawling transcripts, check whether local session history exists:

```bash
ls ~/.claude/projects/ 2>/dev/null | head -5
```

**If the directory is absent or empty**, the session is likely ephemeral
(cloud-hosted, CI, or a fresh machine). State this clearly:
> "No local session history found — this appears to be a cloud or fresh
>  environment. Skipping transcript crawl. Proceeding with skill definitions
>  and context files only."

Skip Steps 2–3 and go directly to Step 4.

**If history exists**, continue.

---

### Step 1 — Parse the timeframe

Default: `30d`. Accept: `7d`, `14d`, `30d`, `90d`, `180d`, `all`.

Convert to days for `find -mtime`: `30d → -mtime -30`, `all → no -mtime filter`.

Tell the user what you're scanning:
> "Scanning the last [N] days of session transcripts, skill definitions, and
>  project context files to infer your tool usage patterns.
>  No data leaves your machine — reads local files only."

---

### Step 2 — Session Transcript Crawl

**Find matching session files:**

```bash
# List the project dirs to orient
ls -lt ~/.claude/projects/ 2>/dev/null | head -10

# Find JSONL session files within the timeframe
# Use -mtime (integer days) rather than -newer to avoid process-substitution fragility
find ~/.claude/projects -name "*.jsonl" -mtime -<N> 2>/dev/null | head -200
```

For `all` timeframe omit `-mtime`. Cap file list at 200.

**Extract tool usage — pass filenames as arguments so session identity is tracked:**

```bash
find ~/.claude/projects -name "*.jsonl" -mtime -<N> 2>/dev/null \
  | head -200 \
  | xargs python3 -c "
import sys, json
from collections import defaultdict

tool_sessions = defaultdict(set)   # tool_name -> set of filenames
tool_calls    = defaultdict(int)   # tool_name -> total call count

def extract_tools(obj, fname):
    if isinstance(obj, dict):
        if obj.get('type') == 'tool_use' and 'name' in obj:
            name = obj['name']
            tool_calls[name] += 1
            tool_sessions[name].add(fname)
        for v in obj.values():
            extract_tools(v, fname)
    elif isinstance(obj, list):
        for item in obj:
            extract_tools(item, fname)

for fname in sys.argv[1:]:
    try:
        with open(fname) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        extract_tools(json.loads(line), fname)
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass

for tool, count in sorted(tool_calls.items(), key=lambda x: -x[1]):
    print(f'{count:5d} calls  {len(tool_sessions[tool]):3d} sessions  {tool}')
"
```

**Extract Bash command patterns (what binaries were actually run):**

```bash
find ~/.claude/projects -name "*.jsonl" -mtime -<N> 2>/dev/null \
  | head -200 \
  | xargs python3 -c "
import sys, json
from collections import defaultdict

cmd_sessions = defaultdict(set)
cmd_calls    = defaultdict(int)

def find_bash(obj, fname):
    if isinstance(obj, dict):
        if obj.get('type') == 'tool_use' and obj.get('name') == 'Bash':
            cmd = obj.get('input', {}).get('command', '')
            tokens = cmd.strip().split()
            for tok in tokens:
                if not tok.startswith(('-', 'export ', 'set ', 'unset ', 'VAR=')):
                    binary = tok.split('/')[-1]
                    cmd_calls[binary] += 1
                    cmd_sessions[binary].add(fname)
                    break
        for v in obj.values():
            find_bash(v, fname)
    elif isinstance(obj, list):
        for item in obj:
            find_bash(item, fname)

for fname in sys.argv[1:]:
    try:
        with open(fname) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        find_bash(json.loads(line), fname)
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass

for cmd, count in sorted(cmd_calls.items(), key=lambda x: -x[1])[:30]:
    print(f'{count:5d} calls  {len(cmd_sessions[cmd]):3d} sessions  {cmd}')
"
```

If either script returns no output, note it and continue.

---

### Step 3 — Skill Definition Crawl

Find all `SKILL.md` files in the repository:

```bash
find . -name "SKILL.md" 2>/dev/null
```

For each file found, extract tool references:

```bash
find . -name "SKILL.md" -exec grep -Hn \
  -E "(compatibility:|Bash\(|mcp__|bq |python3|pip3|jq |ffmpeg|nlm |rwe-publish|gh |curl |WebFetch|WebSearch)" \
  {} \;
```

Build a map: `skill_name → [tool references]`. Read the `compatibility:` frontmatter
line for declared MCP dependencies.

Check the existing project allow-list so candidates already there are excluded:

```bash
cat .claude/settings.json 2>/dev/null || echo "none"
```

---

### Step 4 — Context Snapshot Crawl

```bash
# CLAUDE.md tool references
find . -name "CLAUDE.md" -exec grep -Hn \
  -E "(bq|python3|BigQuery|pandas|MCP|mcp__|tool|allow|permission|ffmpeg|nlm)" \
  {} \;

# .claude directory structure
ls -la .claude/ 2>/dev/null

# SessionStart hooks imply install commands
find .claude -name "*.sh" -o -name "*.json" 2>/dev/null | xargs grep -l "install\|pip\|npm\|apt" 2>/dev/null
```

Note anything that implies a tool dependency.

---

### Step 5 — Merge, Deduplicate, and Present

Combine the signals from Steps 2–4. For each unique allow-rule candidate:

1. **Normalize** raw tool/binary names to allow-rule syntax using the mapping table
   in the Allow-List Curation section below.
2. **Deduplicate**: if the same rule appears in multiple sources, merge into one row
   and list all sources.
3. **Assign tier** (see Allow-List Curation for tier definitions).
4. **Sort**: Tier 1 first, then Tier 2, then Tier 3. Within each tier, sort by
   transcript call count descending (tools with no transcript signal sort last).
5. **Exclude** anything already in the existing allow-list.

Present the results:

```
Discovery results — last [N] days
  Sessions crawled:  [N] files across [N] project dirs
  Skill files found: [N]
  Context files:     [N]
  (Note: transcript crawl skipped — no local session history found)

Candidate allow-list rules:

Tier 1 — Safe reads
  Rule                      Calls  Sessions  Sources
  ─────────────────────────────────────────────────────────────
  Bash(ls*)                  203      47     transcripts
  Bash(python3*)              84      19     transcripts + reading-list-builder
  Bash(jq*)                   55      22     transcripts
  Bash(git*)                  48      31     transcripts
  Bash(bq ls*,bq show*)       67      23     transcripts + redpen

Tier 2 — Consequential reads
  Rule                            Calls  Sessions  Sources
  ─────────────────────────────────────────────────────────────
  Bash(bq query*)                  60      23     transcripts
  mcp__github__*_read              61      31     transcripts
  WebFetch(*)                      44      12     transcripts + reading-list-builder
  mcp__gmail__search_threads       29       8     transcripts + reading-list-builder

Tier 3 — Writes / mutations (shown for awareness; not auto-recommended)
  Rule                        Calls  Sessions  Sources
  ─────────────────────────────────────────────────────────────
  mcp__github__*_write          12       7     transcripts
  mcp__gmail__label*             8       3     transcripts
  mcp__todoist__add-tasks        5       2     transcripts

Already in allow-list (excluded):
  — none
```

Then proceed to **ALLOW-LIST CURATION** below. Note to user that these rules
are intended as permanent project defaults, not session-specific approvals.

Skip Phase 5 (handoff brief) — discovery mode does not produce a study brief.

---

## STANDARD MODE

### Phase 1 — Intake Interview

Goal: a precise, unambiguous problem statement. Ask all questions in one message.

---

**1. What question are you trying to answer?**
Specific outcome: a number, a trend, a comparison, an anomaly, a forecast.
"Understand engagement" is not a question. "Which cohort has the highest 30-day
retention and why is it different from the others?" is.

**2. What data sources are involved?**
- BigQuery project/dataset/table names (or "I don't know yet")
- Local files (CSV, JSON, parquet, logs) — paths or locations
- External APIs — names
- MCPs connected to this session (Gmail, Calendar, Todoist, Twilio, Drive…)
- Databases (Postgres, Snowflake…) and how they're accessed
- GitHub repos or issues

**3. What is the scope?**
- Time range, filters or segments, granularity

**4. What does "done" look like?**
A number in chat? A markdown table? A CSV? A YAML blob? A Todoist task created?

**5. Known constraints or sensitivities?**
PII that must not leave BigQuery, billing-sensitive tables, required service
accounts, rate-limited APIs.

**6. How much autonomy during the analysis?**
- **Full auto** — run everything, show results at the end
- **Checkpoint** — show query/plan before each major step
- **Supervised** — confirm every tool call

---

Wait for answers. If vague, ask one focused follow-up before proceeding.

---

### Phase 2 — Tool Stack Identification

Map intake answers to the needed tool categories. Only include rows where the tool
is actually needed. Drop the rest.

| Tool Category | Trigger | Verification call |
|---|---|---|
| BigQuery CLI | `bq` tables / project named | `bq ls` |
| BigQuery MCP | BigQuery MCP connected | lightest list tool |
| Python / pandas | CSV, parquet, complex aggregation | `python3 --version` |
| Bash / shell | Logs, grep, awk, wc, jq | `ls` of relevant dir |
| Web fetch | External URL, API, redirect | `WebFetch` on a safe URL |
| GitHub MCP | Repos, PRs, issues | lightest read tool |
| Gmail MCP | Email data | `list_labels` equivalent |
| Calendar MCP | Scheduling data | `list_calendars` equivalent |
| Todoist MCP | Task / project data | `get-overview` equivalent |
| Twilio MCP | SMS / call data | lightest search |
| Drive / filesystem MCP | Spreadsheets, Docs | `list_recent_files` (limit 5) |
| File read/write | Local CSV, YAML, JSON output | Read a known config file |

State the stack to the user before proceeding:

```
Tool stack for this study:
  ✓ BigQuery CLI          — scan usage_events table
  ✓ Python / pandas       — cohort calculations
  ✓ File write            — output results/cohort-analysis.csv

Not needed: GitHub MCP, Gmail MCP, Calendar MCP, Todoist MCP, Twilio MCP
```

---

### Phase 3 — Connection Verification

Run one lightweight call per tool in the stack. The purpose is **not** to
pre-approve permissions for later — Claude Code's permission system grants
approval per command pattern, not per tool family. The actual pre-approval
mechanism is writing to `settings.json` in the next phase.

What connection verification accomplishes:
- Confirms the tool/MCP is installed, authenticated, and responding
- Surfaces configuration problems before they interrupt analysis
- Gives you visibility into what Claude will do before the analysis starts

Run all calls in parallel where independent. Before each call, state what it does:

> "Verifying BigQuery CLI: `bq ls` — confirms bq is installed and authenticated.
>  This does not pre-approve later bq query calls; that happens when we write
>  to settings.json."

**For CLI tools** — use the specific command from the Tool Stack table above.

**For MCP tools** — do not hardcode tool IDs (they vary by session). Instead,
use ToolSearch to find the lightest available tool for each MCP:
- Gmail: `ToolSearch("gmail list labels")`
- Calendar: `ToolSearch("calendar list calendars")`
- Todoist: `ToolSearch("todoist overview")`
- GitHub: `ToolSearch("github get me")`
- Twilio: `ToolSearch("twilio search")`
- Drive: `ToolSearch("drive list recent files")`

Call whichever tool the search returns. If ToolSearch returns nothing for an MCP,
that MCP is not connected — flag it.

**Report the outcome:**

```
Connection verification:
  ✓ BigQuery CLI   — authenticated, 3 projects visible
  ✓ Python 3.11    — pandas 2.1.0, numpy 1.26.0 available
  ✓ Gmail MCP      — connected, 24 labels found
  ✗ Twilio MCP     — not connected (ToolSearch returned no match)

Proceed with: BigQuery, Python, Gmail
Blocked: Twilio
```

For any blocked tool, ask:
- a) Fix the connection before proceeding
- b) Remove it from the stack and adjust the approach
- c) Proceed anyway; handle it during analysis if it comes up

---

## ALLOW-LIST CURATION

_Used by both standard mode (after Phase 3) and discovery mode (after Step 5)._

Build the candidate table from the **current context**: the tool stack from Phase 2
(standard) or the merged discovery results (discovery). Do not show tools that
aren't in scope.

**Tier definitions:**

- **Tier 1 — Safe reads**: read-only or idempotent, no billing, no live system mutation.
  Recommend allowing all.
- **Tier 2 — Consequential reads**: read from live systems or incur cost (BigQuery
  billing, external API calls). Recommend allowing, but note the scope.
- **Tier 3 — Writes / mutations**: create or modify data. Recommend prompt-per-call,
  not blanket allow. Show them here so the user can decide.

**Allow-rule normalization** (map raw tool/binary names to settings.json syntax):

| Observed | Allow rule(s) | Tier |
|---|---|---|
| `bq ls`, `bq show` | `Bash(bq ls*)`, `Bash(bq show*)` | 1 |
| `bq query --dry_run` | `Bash(bq query --dry_run*)` | 1 |
| `bq query` (real) | `Bash(bq query*)` | 2 |
| `python3` | `Bash(python3*)` | 1 |
| `pip3` | `Bash(pip3*)` | 1 |
| `ls`, `cat`, `head`, `tail`, `wc` | `Bash(ls*)` etc. | 1 |
| `jq` | `Bash(jq*)` | 1 |
| `git` | `Bash(git*)` | 1 |
| `gh` | `Bash(gh*)` | 2 |
| `curl` | `Bash(curl*)` | 2 |
| `ffmpeg`, `rwe-publish`, `nlm` | `Bash(<name>*)` | 1 |
| `WebFetch` | `WebFetch(*)` | 2 |
| GitHub read tools | `mcp__github__*_read` | 2 |
| GitHub write tools | `mcp__github__*_write` | 3 |
| Gmail search/read | tool name pattern `*search*`, `*get_thread*` | 2 |
| Gmail label/draft writes | tool name pattern `*label*`, `*draft*` | 3 |
| Calendar list | tool name pattern `*list_events*` | 1 |
| Todoist reads | tool name pattern `*find*`, `*get*` | 1 |
| Todoist writes | tool name pattern `*add*`, `*update*`, `*complete*` | 3 |

Built-in tools (`Read`, `Glob`, `Grep`, `Edit`, `Write`) do not require allow-list
entries — skip them.

**Present candidates grouped by tier and ask for approval:**

> "Here are the candidate allow rules for this context.
>  For each tier: approve all, approve with modifications, or skip.
>  For Tier 3: tell me if any should become blanket-allowed."

Show only tiers that have candidates. Example:

```
Tier 1 — Safe reads (recommend: allow all)
  Bash(bq ls*)          list BigQuery projects, datasets, tables
  Bash(bq show*)        show schema and metadata
  Bash(bq query --dry_run*)  estimate query cost without executing
  Bash(python3*)        run Python
  Bash(jq*)             parse JSON

Tier 2 — Consequential reads (billed / live data)
  Bash(bq query*)       execute BigQuery SQL — billed against your project
  WebFetch(*)           fetch external URLs

Tier 3 — Writes (shown for awareness; recommend prompt-per-call)
  mcp__github__*_write  create issues, PRs, comments
```

---

### Write to Settings

Once approved, determine where to write the rules.

**Global vs. project settings:**
- Tools you use across all your projects (`python3`, `ls`, `git`, `jq`, `pip3`) →
  recommend `~/.claude/settings.json` (global, applies to every repo)
- Tools specific to this project or org (project-scoped `bq`, specific MCPs) →
  recommend `.claude/settings.json` (project-only)

Ask if any approved Tier 1 rules look like they belong globally.

**Check what exists:**

```bash
cat ~/.claude/settings.json 2>/dev/null || echo "global: none"
cat .claude/settings.json 2>/dev/null || echo "project: none"
```

Read the existing file(s) before writing. Merge new rules into the `permissions.allow`
array — do not overwrite existing rules. Deduplicate by rule string.

If a file does not exist, create it with:
```json
{
  "permissions": {
    "allow": []
  }
}
```

Show the diff before writing:

```
Writing to ~/.claude/settings.json (global):
  + "Bash(python3*)"
  + "Bash(ls*)"
  + "Bash(jq*)"

Writing to .claude/settings.json (project):
  + "Bash(bq ls*)"
  + "Bash(bq show*)"
  + "Bash(bq query --dry_run*)"
  + "Bash(bq query*)"
```

After writing, read the files back and confirm the final state.

> "Rules written. To remove a rule later, edit the file directly or
>  run `/update-config`."

---

## Phase 5 — Handoff (standard mode only)

Produce the study brief:

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

**Constraints:** <PII rules, billing limits — or "none noted">

**Connections verified:** <list of tools confirmed working>
**Allow-list written:** <global and/or project settings>
```

Ask: "Does this brief look right? Correct anything, or say 'run it' to start."

If the user confirms, **begin the analysis immediately in this session** — do not
wait for a new message. Use the brief as the specification and proceed according
to the autonomy level they chose.

---

## Tone and operating principles

- **One round-trip rule**: Batch all questions into as few messages as possible.
  Never ask one question at a time.

- **Connection verification ≠ permission pre-approval**: Approving a specific
  `bq ls` prompt does not carry to `bq query`. The settings.json write is what
  actually pre-approves command patterns. State this clearly; do not imply otherwise.

- **Billing discipline**: For BigQuery, always run `bq query --dry_run` before
  the real query and report the estimated bytes. If the estimate exceeds 10 GB,
  stop and ask the user before executing.

- **PII discipline**: If the user names tables or fields that look like PII
  (email, name, phone, IP, SSN, user_id linked to identity), call it out during
  intake and confirm handling instructions before querying.

- **No analysis during setup**: Phases 1–4 and discovery Steps 0–5 are prep only.
  Do not start answering the research question until Phase 5 hands off.

- **Fail loudly on blocked connections**: If a connection verification fails, say
  so explicitly. Do not silently adjust the plan. Give the user a clear choice.

- **Mid-analysis new tool**: If analysis reaches a tool not in the verified stack,
  pause. Run connection verification for that tool only, offer to add it to the
  allow-list, then continue.

- **Cloud / ephemeral environments**: Discovery mode's transcript crawl will
  return nothing in cloud-hosted or CI sessions. This is expected — the skill
  gracefully falls back to skill-definition and context crawls only. Do not
  treat empty transcript results as an error.
