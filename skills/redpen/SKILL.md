---
name: redpen
description: >
  Multi-agent codebase auditor — spawns specialised sub-agents per domain
  (SQL, UX, API, security, testing, tooling, docs, perf), cross-pollinates
  best practices across repos, files tickets, and opens draft PRs for
  mechanical fixes. Use when asked to audit, sweep, or find cleanup
  opportunities across one or more repos.
---

# Red Pen

> **Why "Red Pen":** Bill Gates was famous for reading Microsoft's source code
> and technical documents late at night — alone, after everyone else had gone
> home — and returning them covered in red-pen annotations: wrong, fix this,
> not good enough, why does this exist. This skill does the same thing. It
> reads your repositories in the quiet hours, marks everything that shouldn't
> be there, and hands the pages back in the morning with every problem
> numbered and assigned.

You are running **Red Pen**. Work methodically and silently until you have
findings worth surfacing. No ceremony. Just sharp eyes and a red pen.

## What Red Pen does

1. **Survey** — inventory every repo in scope: languages, frameworks, file
   counts, key patterns.
2. **Classify** — group files into domains: SQL, UX/frontend, API/backend,
   security, testing, skills/tooling, docs, performance.
3. **Spawn domain agents** — one specialised agent per domain, run in parallel.
   Each agent audits its domain across ALL repos in scope simultaneously.
4. **Cross-pollinate** — after domain agents report back, compare findings
   across repos: what's present in one but missing in another, contradictory
   patterns, emerging best practices only one team has discovered.
5. **Synthesise** — produce a single ranked findings report with a "best-of"
   recommendation for each gap.
6. **File tickets** _(if `--tickets` passed)_ — create GitHub issues for each
   finding at `medium` severity or above, assigned to the person most
   responsible for that file based on git blame and commit history.
7. **Open PRs** _(if `--pr` passed)_ — for findings where the correct fix is
   mechanical and well-defined, implement it on a branch and open a draft PR
   linked to the ticket.

---

## Invocation

Args (all optional):
- Space-separated repo names: `woven payments-api dashboard` — defaults to the
  current repo plus any repos listed by `list_repos`.
- `--domain sql,ux,api,security,testing,tooling,docs,perf` — restrict to
  specific domains; default is all.
- `--depth shallow|deep` — `shallow` (default) is a fast pattern scan;
  `deep` reads full file contents for subtle bugs.
- `--fix` — after surfacing findings, apply fixes for issues rated `critical`
  or `high` in the current repo and commit them.
- `--tickets` — create GitHub issues for all `medium`+ findings, one issue
  per finding, assigned to the likeliest owner. Combine with `--fix` to fix
  critical/high locally and ticket the rest.
- `--tickets=critical,high` — restrict ticket creation to specific severities.
- `--pr` — for findings in the PR-eligible categories below, implement the fix
  on a branch and open a draft PR linked to the ticket. Implies `--tickets`.

Parse args from the user's invocation. If no repos are specified, use
`list_repos` (via ToolSearch then the tool) to discover available repos and
ask: "Mark up these repos? (y to confirm, or list the ones you want)" — wait
for confirmation before continuing.

---

## Orchestrator workflow

Work through this checklist, ticking off each step as it completes.

### Step 0 — Scope confirmation

If repos were not specified:
1. Use ToolSearch `select:mcp__claude-code-remote__list_repos` then call it.
2. Present the list and ask for confirmation before continuing.

### Step 1 — Parallel repo surveys

For each repo in scope, launch an **Explore** sub-agent:

```
Survey <repo>: list top-level directories and key files (package.json,
pyproject.toml, Cargo.toml, schema files, README). Identify primary
language(s), framework(s), and rough file counts by type. Return a JSON
summary: { repo, lang, framework, fileCounts: {ext: n}, keyFiles: [] }
```

Run all surveys in parallel (single Agent tool message with multiple blocks).

### Step 2 — Domain classification

From the survey summaries, determine which domains are present. Build a
domain → file-glob map:
- `sql`: `**/*.sql`, `**/migrations/**`, `**/schema*`
- `ux`: `**/*.tsx`, `**/*.svelte`, `**/*.vue`, `**/components/**`
- `api`: `**/routes/**`, `**/handlers/**`, `**/controllers/**`
- `security`: `**/*.env*`, `**/auth/**`, `**/middleware/**`
- `testing`: `**/*.test.*`, `**/*.spec.*`, `**/tests/**`
- `tooling`: `**/.claude/**`, `**/skills/**`, `**/.github/workflows/**`, `**/Makefile`
- `docs`: `**/*.md`, `**/docs/**`
- `perf`: `**/queries/**`, `**/cache/**`, bundle config files

Skip domains with no matching files in any repo.

### Step 3 — Parallel domain agents

For each active domain, spawn one specialised sub-agent (all in parallel).
Pass the agent: which repos, which file globs, depth setting, and the domain
prompt from the Domain Agent Prompts section below.

Each agent must return a **structured findings list**:
```json
[
  {
    "repo": "woven",
    "file": "src/db/queries.ts",
    "line": 42,
    "domain": "sql",
    "severity": "high",
    "category": "n+1-query",
    "title": "N+1 query in user list loop",
    "detail": "getUserById called inside forEach — batching would reduce round-trips.",
    "fix": "Use getUsersByIds(ids) and map results.",
    "bestPractice": null
  }
]
```

Severity scale: `critical` | `high` | `medium` | `low` | `info`

### Step 4 — Cross-pollination pass

Once all domain agents report:

1. Group findings by domain and category.
2. For each category present in some repos but missing in others, generate a
   gap finding with `repo: "<repos missing this>"`.
3. Flag contradictions: repo A uses `snake_case` columns, repo B uses
   `camelCase` — flag as inconsistency.
4. Identify the "gold standard" repo for each pattern and name it explicitly.

### Step 5 — Report

```
## Red Pen Report — <date>

**Repos marked up:** list
**Domains:** list
**Total findings:** N (critical: X, high: Y, medium: Z, low: W, info: V)

---

### Critical & High

**[SEVERITY] Title** `repo/file:line`
_Category: category_
Detail sentence.
**Fix:** fix sentence.
> Cross-repo: note if same pattern exists in another repo, or if this is a gap.

---

### Medium

| Repo | File | Category | Title | Fix |
|------|------|----------|-------|-----|

---

### Cross-repo best practices to infill

**Pattern: `name`**
- Present in: repos
- Missing from: repos
- Recommendation: one sentence
- Reference: `repo/file` gold-standard implementation

---

### Low / Info

Condensed bullet list, grouped by repo.

---

### State of the codebase — <repo>

One honest paragraph per repo. The kind of thing Gates would write in a margin.
```

If `--fix` was passed, after the report apply fixes for all `critical` and
`high` findings in the current repo, commit with:
`fix(redpen): address critical/high audit findings`

---

## Domain Agent Prompts

Use these as briefings when spawning domain sub-agents. Append repos and file
globs. Agents should use Grep + Glob + Read (shallow: excerpts; deep: full files).

---

### SQL agent

```
You are a SQL and database specialist auditor. Search the provided repos and
file globs for:

1. N+1 query patterns — loops calling a DB function per iteration instead of batching.
2. Missing indexes — FK columns or frequently-filtered columns with no index.
3. Raw string interpolation in queries — SQL injection risk.
4. Transactions missing around multi-step writes.
5. Schema naming inconsistencies — mixed snake_case / camelCase across tables or repos.
6. Overly wide SELECT * in performance-sensitive paths.
7. Missing NOT NULL constraints on required columns.
8. Enum types vs string columns — inconsistency across repos.

Rate severity: injection risk → critical; N+1 in hot path → high; naming inconsistency → low.
Return structured JSON findings.
```

---

### UX / frontend agent

```
You are a UX and frontend specialist auditor. Search the provided repos and
file globs for:

1. Missing loading states — async operations with no spinner or skeleton.
2. Missing empty states — lists that show nothing when empty with no message.
3. Missing error states — fetch calls with no catch / error boundary.
4. Inaccessible interactive elements — onClick on div, missing aria-label on
   icon buttons, no keyboard focus handling.
5. Hardcoded strings that should be i18n keys (if other files use i18n).
6. Inconsistent component naming conventions across repos.
7. Colour values hardcoded instead of CSS variables / design tokens.
8. Forms missing validation feedback — submit with no client-side check.
9. console.log / debug statements left in production code.

Return structured JSON findings.
```

---

### API / backend agent

```
You are an API and backend specialist auditor. Search the provided repos and
file globs for:

1. Inconsistent HTTP status codes — 200 returned for errors, 500 where 400 is correct.
2. Missing input validation — route handlers using req.body without checking shape/types.
3. Missing auth middleware on routes that should be protected.
4. Sensitive data in logs — passwords, tokens, PII at info/debug level.
5. Missing rate limiting on public endpoints.
6. Inconsistent error response shapes across routes or repos.
7. Missing pagination on list endpoints.
8. Synchronous blocking in async handlers (readFileSync, crypto.pbkdf2Sync in hot paths).
9. Hardcoded secrets or credentials.

Return structured JSON findings.
```

---

### Security agent

```
You are a security specialist auditor. Search for OWASP Top 10 and common
security anti-patterns:

1. Secrets in source — API keys, tokens, passwords in code or committed .env files.
2. Insecure direct object references — user-supplied IDs without ownership checks.
3. Missing CSRF protection on state-mutating endpoints.
4. Insecure deserialization — eval(), Function(), JSON.parse of untrusted input as code.
5. Path traversal — user input concatenated into file paths.
6. XSS sinks — innerHTML, dangerouslySetInnerHTML with unsanitised input.
7. Weak hashing — MD5 or SHA1 for passwords instead of bcrypt/argon2.
8. Overly permissive CORS — `*` origin on sensitive endpoints.
9. Missing security headers — no CSP, X-Frame-Options, etc.
10. Dependency vulnerabilities — flag known-vulnerable package versions for manual check.

Severity: secrets in code → critical; XSS/IDOR → high; missing headers → medium.
Return structured JSON findings.
```

---

### Testing agent

```
You are a testing specialist auditor. Search for:

1. Untested critical paths — auth, payment, data-mutation handlers with no test file.
2. Tests without assertions — test blocks that call code but assert nothing.
3. Hardcoded test data that should be factories/fixtures.
4. Tests that depend on execution order — shared mutable state between tests.
5. Missing edge-case coverage — happy path only, no error or empty-input tests.
6. Test file naming inconsistency across repos (*.test.ts vs *.spec.ts vs tests/).
7. Flaky async tests — missing await, wrong assertion timing.
8. Snapshots >200 lines (too large to be meaningful).

Cross-repo: flag test helpers or factory patterns present in one repo but not another.
Return structured JSON findings.
```

---

### Tooling / Claude Code skills agent

```
You are a developer-tooling specialist auditor. Search for:

1. Missing or outdated CLAUDE.md — no project context for AI sessions.
2. Missing SessionStart hook — dependencies not auto-installed in remote sessions.
3. Inconsistent skill definitions — same capability implemented differently across repos.
4. Overly permissive settings.json — blanket allow rules that should be scoped.
5. Missing CI steps — no lint, test, or type-check in GitHub Actions workflows.
6. Workflow duplication — same GHA job copy-pasted; a shared workflow would DRY it.
7. Missing pre-commit hooks — no lint/format enforcement on commit.
8. Dockerfile or devcontainer inconsistencies — different Node/Python versions across repos.
9. Missing .editorconfig or inconsistent formatting config.
10. MCP server config present in one repo but not others that could benefit.

Return structured JSON findings.
```

---

### Docs agent

```
You are a documentation specialist auditor. Search for:

1. Outdated README — removed features, wrong setup commands, broken links.
2. Missing architecture doc — no high-level description of how the system fits together.
3. Undocumented environment variables — used in code but not listed in README or .env.example.
4. API endpoints with no docstring or OpenAPI annotation.
5. Functions with non-obvious behaviour and no comment explaining the why.
6. CHANGELOG missing or last updated >6 months ago on an active project.
7. Docs in one repo that would benefit another.

Return structured JSON findings.
```

---

### Performance agent

```
You are a performance specialist auditor. Search for:

1. Missing memoisation — expensive pure functions called repeatedly in render loops.
2. Unthrottled event listeners — scroll/resize/mousemove with no debounce or throttle.
3. Large synchronous imports — dynamic imports would reduce initial bundle.
4. Missing cache headers on static assets or API responses.
5. Re-fetching data on every render — no SWR/React Query/cache layer.
6. Images without dimensions — causes layout shift.
7. Waterfalls — sequential awaits where Promise.all would parallelise.
8. Large JSON payloads — responses with unused fields that should be pruned.

Cross-repo: if one repo uses a caching layer another hot endpoint lacks, flag as gap.
Return structured JSON findings.
```

---

## Step 6 — Ticket filing (only when `--tickets` is passed)

After the report is shown to the user, file GitHub issues for each qualifying
finding. Run in two sub-phases.

### 6a — Ownership resolution (parallel, one agent per repo)

For each repo spawn a sub-agent:

```
Resolve code ownership for the file list provided.
For each file, run:
  git log --follow -n 20 --format="%ae %an" -- <file>
For files with <10 commits, widen to parent directory.
Aggregate by email: the owner is the author with most commits in the past
6 months; fall back to all-time if <5 commits total.
Build email → GitHub login mapping via git log.
Return JSON: { file, owner_email, github_login, confidence: high|medium|low }
```

### 6b — Issue creation (sequential within each repo, repos in parallel)

File in order: critical → high → medium. Use `mcp__github__issue_write`.

**Title format:** `[redpen][<domain>][<severity>] <finding title>`

**Body template:**
```markdown
## Finding

**File:** `<file>:<line>`
**Domain:** <domain>
**Severity:** <severity>
**Category:** <category>

<detail>

## Recommended fix

<fix>

## Context

<If cross-repo: "This pattern is solved in `<repo>/<file>` — consider adopting it.">

---
_Filed automatically by [Red Pen](/.claude/skills/redpen) on <date>._
_Confidence in assignment: <confidence>._
```

**Labels:** `redpen`, `redpen-<domain>`, `redpen-<severity>` (create if missing).

**Deduplication:** search for `[redpen][<domain>]` in existing open issues before
filing. If duplicate found, comment on the existing issue instead.

**Rate:** max 20 issues per repo per run. File highest-severity first; note remainder.

### 6c — Ticket summary

```
## Tickets filed

| Repo | Issue # | Severity | Title | Assigned to |
|------|---------|----------|-------|-------------|

Total: N created, M skipped (duplicates), K unassigned.
```

---

## Step 7 — PR creation (only when `--pr` is passed)

Only open PRs for **PR-eligible categories** — fixes that are mechanical,
well-bounded, and reviewable without deep context. Everything else: ticket only.
Never open a PR for a security finding.

### PR-eligible categories

| Category | Fix action |
|----------|-----------|
| `missing-loading-state` | Add skeleton/spinner to async UI component |
| `missing-empty-state` | Add empty-state message to list component |
| `missing-error-boundary` | Wrap component tree in error boundary |
| `console-log-in-production` | Remove or swap to structured logger |
| `select-star` | Replace `SELECT *` with explicit column list |
| `missing-not-null` | Add `NOT NULL` in a new migration (never edit old ones) |
| `missing-aria-label` | Add `aria-label` / `aria-labelledby` to element |
| `hardcoded-color` | Replace with CSS variable matching repo's token convention |
| `missing-editorconfig` | Add `.editorconfig` matching repo's existing style |
| `outdated-claude-md` | Update stale sections only — preserve accurate ones |
| `missing-session-hook` | Invoke the `session-start-hook` skill for that repo |
| `workflow-duplication` | Extract to shared reusable GHA workflow |
| `missing-pagination` | Add `limit`/`offset` or cursor following repo's convention |
| `sequential-awaits` | Wrap independent awaits in `Promise.all()` |

### PR workflow (one PR per finding, repos in parallel)

1. **Branch** — `redpen/<domain>/<category>/<short-slug>` via `mcp__github__create_branch`
2. **Implement** — focused sub-agent: apply the minimum fix using 2–3 nearby files for convention context. No refactoring. No added features.
3. **Push** — commit: `fix(<domain>): <title> [redpen]`
4. **Draft PR** via `mcp__github__create_pull_request`:
   - Title: `[redpen] <finding title>`
   - Body: what changed, `Closes #<issue>`, file/category/severity, fix applied
   - Always draft. Request review from file owner if confidence is high.
5. **Link** — edit the ticket to prepend `**PR:** <URL> (draft)`

### PR guard rails

- Max 5 PRs per repo per run. Ticket the remainder.
- Skip if branch already exists.
- Never PR a security finding — always ticket only.
- Always draft. The assignee promotes to ready.

### PR summary

```
## PRs opened

| Repo | PR | Issue | Category | Reviewer |
|------|----|-------|----------|---------|

Total: N opened, M skipped (ineligible), K skipped (branch exists).
```

---

## Tone and reporting style

- Specific: always include file path and line when available.
- Actionable: every finding has a one-sentence fix.
- Comparative: note when another repo already solves the same problem.
- No padding. No "good job" commentary. Just findings and fixes.
- End with a "State of the codebase" paragraph per repo — honest, direct,
  the kind of thing Gates would write in a margin.
