## Context handoff — reading-list-builder v3.0 catch-up (2026-07-10)

**Saved:** 2026-07-10 16:29 UTC via `/save-context`
**Session status:** Paused at headless Gmail blocker; laptop steps below unblock catch-up.

**Goal:** Backfill daily flow for week of 2026-06-22 via
`bin/rwe-catchup.sh --from 2026-06-22 --to 2026-07-01` on branch
`claude/reading-list-pipeline-ahpsE` (PR #25). First live test of weekly-notebook
accumulation + STEP 3 reconciliation (unverified live).

**User machine:** macOS, repo at `~/Documents/dev/adventures-in-ai`,
`claude --version` → **2.1.200** in interactive shell (but scripts were picking up
**2.1.87** from `/opt/homebrew/bin/claude` until PATH fix).

---

### Issues resolved (in order discovered)

| # | Symptom | Root cause | Fix |
|---|---------|------------|-----|
| 1 | `Invalid API key · Fix external API key` | Dead `ANTHROPIC_API_KEY` in `~/.claude/settings.json` (different from valid keychain key in `.zshrc`) | `jq 'del(.env.ANTHROPIC_API_KEY)' ~/.claude/settings.json` |
| 2 | `Not logged in · Please run /login` | OAuth session cleared during debugging; `env -u` scrubs shell API key | `claude /login` |
| 3 | `gmail.mcp.claude.com` Failed in `claude mcp list` | Deprecated endpoint (404) | Use `gmailmcp.googleapis.com`; remove legacy `claude mcp remove gmail` |
| 4 | `--strict-mcp-config` blocked claude.ai Gmail | Only loaded dead HTTP URL from config | Removed strict mode; `mcp-headless.json` = notebooklm + gmail HTTP |
| 5 | Connectivity check shows 2.1.87, shell shows 2.1.200 | Scripts prepended `/opt/homebrew/bin` before user's PATH | `rwe_ensure_path` + `rwe_claude_bin` picks newest version |
| 6 | Interactive Gmail works (`search_threads`), headless `-p` has no Gmail | claude.ai Connectors load Calendar/Drive/etc. but Gmail missing in `-p`; needs user-scoped HTTP MCP login | `claude mcp login gmail` after `claude mcp add ... gmailmcp.googleapis.com` |

**Interactive Gmail confirmed working** (2026-07-03): `search_threads "dolphin club"` → 201 threads.

**Still failing on 2026-06-24 catch-up** (last report): headless session lists Dropbox,
Calendar, Drive, Notion, Twilio, NotebookLM — **no Gmail**. Plus stale 2.1.87 warning.

---

### Repo tooling added (branches / PRs)

| PR | Branch | What |
|----|--------|------|
| #29 | `cursor/rwe-auth-diagnostics-001e` | `bin/rwe-auth-check.sh`, auth preflight in rwe scripts |
| #30 | `cursor/rwe-connectivity-check-001e` | `bin/rwe-connectivity-check.sh`, Gmail MCP model fix, PATH pinning, skill tool-name flexibility |

**Key scripts:**
- `bin/rwe-auth-check.sh` — settings/keychain audit (`--test-api --doctor`)
- `bin/rwe-connectivity-check.sh` — layered probes (`--live --verbose --date YYYY-MM-DD`)
- `rwe_claude_bin()` in `rwe-common.sh` — picks highest-version `claude` on PATH
- Override: `export RWE_CLAUDE_BIN=/path/to/claude`

**Gmail tool names (skill v3.0 updated):**
- claude.ai connector: `search_threads`, `get_thread` (`mcp__claude_ai_Gmail__*`)
- Legacy: `gmail_search_messages`, `gmail_read_message`

**mcp-headless.json (current):**
```json
{
  "mcpServers": {
    "gmail": { "type": "http", "url": "https://gmailmcp.googleapis.com/mcp/v1" },
    "notebooklm": { "type": "stdio", "command": "uvx", "args": ["--from", "notebooklm-mcp-cli", "notebooklm-mcp"] }
  }
}
```

`ENABLE_CLAUDEAI_MCP_SERVERS=true` set in `rwe_claude_headless()`.

---

### What to run on laptop next (in order)

```bash
cd ~/Documents/dev/adventures-in-ai
git fetch
git checkout cursor/rwe-connectivity-check-001e   # or merge PR #30
git pull

# 1. Confirm scripts use 2.1.200 (not brew 2.1.87)
which -a claude
claude --version
# Optional: brew uninstall claude-code

# 2. Register + authenticate Gmail for headless -p
claude mcp remove gmail 2>/dev/null || true
claude mcp add --transport http --scope user gmail https://gmailmcp.googleapis.com/mcp/v1
claude mcp login gmail

# 3. Verify
claude mcp list   # gmail + claude.ai Gmail both Connected
bin/rwe-connectivity-check.sh --live --verbose --date 2026-06-24
# Expect: step 9 finds Gmail tools; catchup log shows "Using claude: ... 2.1.200"

# 4. Force re-run one day
rm -f ~/.local/state/reading-with-ears/done-2026-06-24
bin/rwe-catchup.sh --from 2026-06-24 --to 2026-06-24

# 5. Confirm success
ls ~/.local/state/reading-with-ears/done-2026-06-24
wc -l ~/Documents/dev/adventures-in-ai/dhkondata/reading-db/runs/2026-06-24.yaml
```

Then remaining days: `--from 2026-06-25 --to 2026-07-01` (skip days with valid sentinels).

---

### How to verify catch-up succeeded

| Check | Path / signal |
|-------|----------------|
| Script output | `[YYYY-MM-DD] Done.` and `0 failed` |
| Sentinel | `~/.local/state/reading-with-ears/done-YYYY-MM-DD` exists |
| Run YAML | `dhkondata/reading-db/runs/YYYY-MM-DD.yaml` non-empty |
| Logs | `~/logs/reading-with-ears/catchup-$(date +%F).log` |
| Debug | `~/logs/reading-with-ears/catchup-debug-YYYY-MM-DD.log` |

**Force re-run:** `rm ~/.local/state/reading-with-ears/done-YYYY-MM-DD` then catch-up that day.

---

### Not yet verified live

- Full catch-up week with STEP 3 reconciliation (mid-week v3.0 cutover)
- `bin/rwe-weekly-audio` + `--notebook-week` in `publish_episodes.py`
- `2026-06-22` may have sentinel from partial run — verify YAML content, not just sentinel

---

### Unrelated but noted

- **codex MCP** on laptop triggers macOS malware block — `claude mcp remove codex` if not needed
- **gmail-send** is send-only, wrong for this pipeline
- **woven** has no Gmail
- Issue #28: `rwe-catchup.sh: command not found` when `~/bin` not on PATH
