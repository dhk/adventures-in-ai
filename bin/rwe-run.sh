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

SKILL_VERSION_REQUIRED="1.1"
SKILL_FILE="${RWE_ROOT}/skills/user/reading-list-builder/SKILL.md"
SKILL_VERSION=$(grep -m1 '^version:' "${SKILL_FILE}" | sed 's/version:[[:space:]]*"\([^"]*\)"/\1/')
if [[ "${SKILL_VERSION}" != "${SKILL_VERSION_REQUIRED}" ]]; then
  echo "ERROR: rwe-run.sh expects skill version ${SKILL_VERSION_REQUIRED} but ${SKILL_FILE} reports '${SKILL_VERSION}'. Pull latest changes or update SKILL_VERSION_REQUIRED."
  exit 1
fi

LOG_DIR="${HOME}/logs/reading-with-ears"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/$(date +%F).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== $(date "+%Y-%m-%dT%H:%M:%S%z") rwe-run ==="

"${RWE_ROOT}/scripts/install-local.sh"

STATE_DIR="${HOME}/.local/state/reading-with-ears"
mkdir -p "${STATE_DIR}"
SENTINEL="${STATE_DIR}/done-$(date +%F)"

if [[ -f "${SENTINEL}" ]]; then
  echo "Pipeline already completed for today (${SENTINEL}) — skipping."
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

python3 "${HOME}/.local/share/reading-with-ears/scripts/publish_episodes.py"

touch "${SENTINEL}"
