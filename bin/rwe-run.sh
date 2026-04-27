#!/usr/bin/env bash
# Full pipeline via reading-list-builder skill (fetch → notebooks → audio → Element.fm).
# Intended for launchd and manual runs. Syncs repo → ~/.local/share before each run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${HERE}/rwe-common.sh"

REPO_ROOT="$(rwe_repo_root "${HERE}")"
RWE_ROOT="${REPO_ROOT}/reading-with-ears"

# Do not source ~/.zshrc: this script is bash with `set -u`. Zsh startup (oh-my-zsh,
# $ZSH_VERSION, zsh-only syntax) is not valid here. For `claude` / `python3` / `nlm` on
# PATH in launchd or cron, use ~/.profile, ~/.bash_profile, launchd EnvironmentVariables,
# or conda `conda init bash` — not only ~/.zshrc.
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

LOG_DIR="${HOME}/logs/reading-with-ears"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/$(date +%F).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== $(date "+%Y-%m-%dT%H:%M:%S%z") rwe-run ==="

"${RWE_ROOT}/scripts/install-local.sh"

# Skip entire run if today's manifest shows all *enabled* feed slugs published (from feeds.json).
if PYTHONPATH="${HOME}/.local/share/reading-with-ears/scripts" python3 -c "
import json, sys
from datetime import date
from pathlib import Path

from podcast_config import enabled_slugs_ordered

state = Path.home() / '.local/state/reading-with-ears'
d = date.today().strftime('%Y-%m-%d')
p = state / f'manifest-{d}.json'
slugs = enabled_slugs_ordered()
if not slugs:
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
  echo "All enabled feeds already published for today — skipping Phase 1 and Phase 2."
  exit 0
fi

cd "${RWE_ROOT}"

CLAUDE_PROMPT=$'Read and follow skills/user/reading-list-builder/SKILL.md and run the full pipeline for today\'s date (use America/Los_Angeles for "today"). Complete all four phases through Element.fm publish.'

claude -p \
  --permission-mode bypassPermissions \
  --strict-mcp-config \
  --mcp-config "${RWE_ROOT}/automation/mcp-headless.json" \
  --add-dir "${RWE_ROOT}" \
  "${CLAUDE_PROMPT}"
