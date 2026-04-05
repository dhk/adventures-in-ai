#!/usr/bin/env bash
# Phase 1 (Claude + reading-list-builder) then Phase 2 (daily_brief.py → Element.fm).
# Intended for launchd and manual runs. Syncs repo → ~/.local/share before each run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${HERE}/dhk-common.sh"

REPO_ROOT="$(dhk_daily_brief_repo_root "${HERE}")"
BRIEF_ROOT="${REPO_ROOT}/dhk-daily-brief"

if [[ -f "${HOME}/.zshrc" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/.zshrc" || true
fi

LOG_DIR="${HOME}/logs/reading-list"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/$(date +%F).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== $(date "+%Y-%m-%dT%H:%M:%S%z") run-reading-list ==="

"${BRIEF_ROOT}/scripts/sync-to-local.sh"

PY_SCRIPT="${HOME}/.local/share/dhk-daily-brief/scripts/daily_brief.py"

# Skip entire run if today's manifest shows all three slugs published.
if python3 -c "
import json, sys
from datetime import date
from pathlib import Path

state = Path.home() / '.local/state/dhk-daily-brief'
d = date.today().strftime('%Y-%m-%d')
p = state / f'manifest-{d}.json'
slugs = ['news', 'think', 'professional']
if not p.is_file():
    sys.exit(1)
try:
    m = json.loads(p.read_text(encoding='utf-8'))
except Exception:
    sys.exit(1)
eps = m.get('episodes') or {}
if all((eps.get(s) or {}).get('published') for s in slugs):
    sys.exit(0)
sys.exit(1)
"; then
  echo "All three episodes already published for today — skipping Phase 1 and Phase 2."
  exit 0
fi

cd "${BRIEF_ROOT}"

CLAUDE_PROMPT=$'Read and follow skills/user/reading-list-builder/SKILL.md and run the full workflow for today\'s date (use America/Los_Angeles for "today").\n\nAUTOMATED_MODE: This is a scheduled non-interactive run. After you have classified emails and built the triage table internally, proceed immediately without waiting for user confirmation. Complete through Step 8, including audio downloads to the configured Personal Podcast folder.'

claude -p \
  --permission-mode bypassPermissions \
  --strict-mcp-config \
  --mcp-config "${BRIEF_ROOT}/automation/mcp-headless.json" \
  --add-dir "${BRIEF_ROOT}" \
  "${CLAUDE_PROMPT}"

python3 "${PY_SCRIPT}" "$@"
