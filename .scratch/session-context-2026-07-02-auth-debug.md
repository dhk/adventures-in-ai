## Context handoff — auth debugging (updated 2026-07-03)

**Status:** Root cause confirmed on laptop (2026-07-03).

### Confirmed root cause

Two **different** `ANTHROPIC_API_KEY` values:

| Source | Fingerprint | API test |
|--------|-------------|----------|
| Shell / keychain (`.zshrc`) | `sk-a…nQAA` | **valid** |
| `~/.claude/settings.json` env | `sk-a…HgAA` | **rejected** |

`rwe-catchup.sh` scrubs the shell key with `env -u`, but Claude Code still injects the
**dead** key from `~/.claude/settings.json`. That produces `Invalid API key · Fix external
API key`. Shell/.zshrc warnings are benign — keep keychain for `week_that_was.py`.

### Fix (run on laptop)

```bash
# 1. New audit (replaces the four manual cat commands)
bin/rwe-auth-check.sh --test-api --doctor

# 2. If blockers found in ~/.claude/settings.json:
jq 'del(.env.ANTHROPIC_API_KEY)' ~/.claude/settings.json > /tmp/s.json \
  && mv /tmp/s.json ~/.claude/settings.json

# 3. Re-check, then single-day catch-up
bin/rwe-auth-check.sh --test-api
bin/rwe-catchup.sh --from 2026-06-22 --to 2026-06-22

# 4. Confirm sentinel + run YAML written
ls -la ~/.local/state/reading-with-ears/done-2026-06-22
ls -la ~/dhkondata/reading-db/runs/2026-06-22.yaml   # or path from config
```

If auth check passes but catch-up still fails, inspect the full debug log (not just tail):

```bash
wc -l ~/logs/reading-with-ears/catchup-debug-2026-06-22.log
cat ~/logs/reading-with-ears/catchup-debug-2026-06-22.log | rg -i 'mcp|axios|401|invalid'
```

### MCP isolation test (only if auth check is clean)

```bash
cd reading-with-ears
claude --mcp-config automation/mcp-headless.json --strict-mcp-config
# "list my notebooklm notebooks"  — tests notebooklm
# "search gmail for label:newsletter/news after:2026/06/22"  — tests gmail
```

### After daily flow works

1. Remaining catch-up: `--from 2026-06-23 --to 2026-07-01` (watch STEP 3 reconciliation)
2. Weekly audio: `bin/rwe-weekly-audio` (unverified live)

### What changed in repo (this session)

- `bin/rwe-auth-check.sh` — audits all credential sources + optional API test + `claude doctor`
- `rwe-run.sh`, `rwe-catchup.sh`, `rwe-weekly-audio` — preflight auth check before `claude -p`
- `verify-reading-with-ears-setup.sh` — includes auth preflight when `claude` is on PATH
- `docs/install.md` — troubleshooting section for this error
