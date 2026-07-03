## Context handoff from previous session

**What we were working on:**
Testing the `reading-list-builder` skill's v3.0 migration (weekly notebook
accumulation + separate weekly audio flow, replacing the old daily-audio
scheme — see `docs/weekly-cadence-migration.md`) by running a catch-up
backfill for the week of 2026-06-22 on the user's laptop:
`bin/rwe-catchup.sh --from 2026-06-22 --to 2026-06-22`. This is the first
live exercise of the new weekly-notebook/reconciliation logic in
`reading-list-builder` v3.0 — nothing in that logic has been verified
against real Gmail/NotebookLM MCP yet.

**Branch:** `claude/reading-list-pipeline-ahpsE` on `dhk/adventures-in-ai`
(this is the branch for PR #25, not yet merged). Latest relevant commits:
- `616527a` — scrub `ANTHROPIC_API_KEY` via `env -u` before every `claude -p`
  invocation in `bin/rwe-run.sh`, `bin/rwe-catchup.sh`, `bin/rwe-weekly-audio`
- `29adca1` — capture `claude`'s full `--debug`/`--debug-file` output on
  failure in all three scripts, tail the last 40 lines to console on failure
- `53730dd` — print the first 20 chars of `$ANTHROPIC_API_KEY` (shell-level)
  right before scrubbing it, as a diagnostic

**What's already done — ruled in/out, in order discovered:**

1. Every catch-up attempt fails identically with the exact same one-line
   banner: `Invalid API key · Fix external API key`, then
   `[2026-06-22] Pipeline failed — sentinel not written`.
2. Confirmed the daily flow's actual work never happens: no
   `dhkondata/reading-db/runs/2026-06-22.yaml` gets written. This is a real
   failure, not a spurious/benign exit code on top of successful work.
3. First hypothesis (WRONG on its own, but real and now fixed): a claude.ai
   token + `ANTHROPIC_API_KEY` auth conflict. User ran `claude /logout` —
   identical error persisted even before re-login, ruling this out as the
   *sole* cause.
4. Manually confirmed via `echo "ANTHROPIC_API_KEY is: ${ANTHROPIC_API_KEY:-<unset>}"`
   that the *shell* genuinely has nothing exported — yet Claude Code's
   startup banner still showed "API Usage Billing" mode and the auth-conflict
   warning. This proved the key wasn't coming from the shell environment at
   all.
5. Full `--debug`/`--debug-file` capture (added this session, commit
   `29adca1`) revealed the real signal:
   ```
   CA certs: Config fallback - globalEnv keys: , settingsEnv keys: VERCEL_TOKEN,ANTHROPIC_API_KEY
   ```
   — confirming `ANTHROPIC_API_KEY` was being force-injected from a
   **settings file**, not the process environment, which is why `/logout`
   and shell `unset` never touched it.
6. Found the source: `~/.claude.json`'s top-level `"env"` block had
   `ANTHROPIC_API_KEY` and `VERCEL_TOKEN` both set globally (applies to
   *every* Claude Code session on the machine, not just this repo).
   `/Library/Application Support/ClaudeCode/managed-settings.json` does
   **not exist** on this machine (ruled out — it's not an MDM/managed
   setting).
7. Directly tested the exact key value against Anthropic's API:
   ```bash
   curl -s https://api.anthropic.com/v1/models \
     -H "x-api-key: $(jq -r '.env.ANTHROPIC_API_KEY' ~/.claude.json)" \
     -H "anthropic-version: 2023-06-01"
   ```
   → `{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}`.
   **Confirmed fact:** this specific key is dead/rejected by Anthropic's API.
   (Earlier claim that the key was "malformed" was walked back — we don't
   actually know *why* it's invalid, just that it is. A separate JSON-parse
   error seen nearby in the debug log — `Unexpected token '/', "/Users/dhk"...
   is not valid JSON` at `Object.assign.cache` — was never confirmed to be
   related; may be a red herring from an unrelated cache file.)
8. User removed it: backed up (`~/.claude.json.bak`), then
   ```bash
   jq 'del(.env.ANTHROPIC_API_KEY)' ~/.claude.json > /tmp/claude.json.new && mv /tmp/claude.json.new ~/.claude.json
   ```
   Unexpectedly, `jq '.env' ~/.claude.json` now returns `null` entirely —
   `VERCEL_TOKEN` is gone too, not just the one key (still recoverable from
   the `.bak` file if needed for something unrelated).

**The specific blocker that caused this handoff:**
**Despite removing `ANTHROPIC_API_KEY` from `~/.claude.json` and confirming
the shell itself has nothing exported (the new diagnostic print showed a
blank value), the exact same `Invalid API key · Fix external API key`
failure still occurs on re-run.** This means the dead key we found and
removed was NOT the sole or even necessarily the correct source — there
must be another place Claude Code is picking up a bad credential from, or
this error was never actually about `ANTHROPIC_API_KEY` at all (it could be
a completely different "external API key" — e.g. the `notebooklm` MCP
server's own separate credential, unrelated to Anthropic auth).

On the most recent run, the debug log tail (`tail -40`) printed **nothing**
— either the debug file is empty, wasn't created, or the failure now
happens even earlier than before. This is unconfirmed — the following
commands were requested but their output was never received before this
handoff:

```bash
wc -l ~/logs/reading-with-ears/catchup-debug-2026-06-22.log
cat ~/logs/reading-with-ears/catchup-debug-2026-06-22.log
cat ~/.claude/settings.json 2>/dev/null       # NOTE: different file from ~/.claude.json, never actually checked
cat .claude/settings.json 2>/dev/null
cat .claude/settings.local.json 2>/dev/null
```

**What to do next — in order:**

1. Get the output of the four commands above. In particular, `~/.claude/settings.json`
   (global Claude Code settings — distinct from `~/.claude.json`, the config file
   already fixed) was flagged as a candidate early on and never actually inspected.
2. If the debug log is genuinely empty, re-run with the instrumented script
   (`bin/rwe-catchup.sh --from 2026-06-22 --to 2026-06-22` on branch
   `claude/reading-list-pipeline-ahpsE`, already pulled) and get the fresh debug
   file content — look specifically for `[MCP]`-tagged lines and any `AxiosError`/
   `401`/`invalid x-api-key` occurrences, and note what immediately precedes them
   (which server, Gmail vs. `notebooklm`, was active at that point).
3. Consider directly testing the `notebooklm` MCP server in isolation, since it's
   never been ruled in or out as the actual source of "invalid API key" (all
   investigation so far has focused on Anthropic account auth, not the
   third-party `notebooklm-mcp-cli` tool's own credential):
   ```bash
   cd reading-with-ears
   claude --mcp-config automation/mcp-headless.json --strict-mcp-config
   # ask: "list my notebooklm notebooks" and separately "search gmail for label:newsletter/news after:2026/06/22"
   ```
   Whichever one fails in isolation is the real answer.
4. Once the actual root cause is found and fixed, re-run the single-day test
   (`--from 2026-06-22 --to 2026-06-22`), confirm
   `dhkondata/reading-db/runs/2026-06-22.yaml` gets written with real content,
   *then* proceed to the remaining 9 days of catch-up
   (`--from 2026-06-23 --to 2026-07-01`), watching closely for the STEP 3
   reconciliation logic (untested live) if any pre-migration daily notebooks
   exist for this week.
5. Only after the daily flow is confirmed working: test the weekly audio flow
   (`bin/rwe-weekly-audio`), which depends on the `--notebook-week` flag added
   to `publish_episodes.py` this session (also unverified live).

**Other context, likely not relevant to this specific blocker but useful if asked:**
- Two other PRs opened this session, unrelated to this auth issue: PR #26
  (`handoff` skill, rebuilt cleanly on `main`) and PR #27 (three design-doc
  clarifications for `week-that-was-design.md`, recovered from an uncommitted
  local review). Both already merged-ready, no action needed.
- Filed issue #28 for a separate, minor install friction (`rwe-catchup.sh:
  command not found` when `~/bin` isn't on `PATH`) — unrelated to this auth
  investigation.
