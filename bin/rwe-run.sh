#!/usr/bin/env bash
# Daily flow via reading-list-builder skill (fetch → notebooks → synthesize → YAML/briefs).
# As of skill v3.0, audio/publish no longer happens daily — see bin/rwe-weekly-audio
# and docs/weekly-cadence-migration.md. Intended for launchd and manual runs. Syncs
# repo → ~/.local/share before each run.
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

if [[ "${1:-}" == "--catch-up" ]]; then
  shift
  exec "${HERE}/rwe-catchup.sh" "$@"
fi

if [[ "${1:-}" == "--weekly-audio" ]]; then
  shift
  exec "${HERE}/rwe-weekly-audio" "$@"
fi

SKILL_VERSION_REQUIRED="3.0"
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

if ! rwe_audit_claude_auth "${REPO_ROOT}"; then
  echo "Aborting — fix Claude auth blockers above, then re-run."
  echo "Run: bin/rwe-auth-check.sh --test-api --doctor"
  exit 1
fi

if ! rwe_check_claude_oauth; then
  exit 1
fi

STATE_DIR="${HOME}/.local/state/reading-with-ears"
mkdir -p "${STATE_DIR}"
SENTINEL="${STATE_DIR}/done-$(date +%F)"

if [[ -f "${SENTINEL}" ]]; then
  echo "Pipeline already completed for today (${SENTINEL}) — skipping."
  exit 0
fi

cd "${RWE_ROOT}"

CLAUDE_PROMPT=$'Read and follow skills/user/reading-list-builder/SKILL.md and run the DAILY FLOW (Steps 0-8) for today\'s date (use America/Los_Angeles for "today"). Do not run the weekly audio flow.'

# Full claude debug capture (unfiltered — a category filter like "mcp" broke
# stdin prompt piping in testing), so a failure (Gmail vs. NotebookLM vs. something
# else in the MCP handshake) doesn't require manually reproducing it interactively —
# the detail is already on disk when the failure happens.
DEBUG_FILE="${LOG_DIR}/run-debug-$(date +%F).log"

# Print what the shell actually sees before we scrub it — this is diagnostic
# only: claude may still pick up a key from its own settings (~/.claude.json
# env block) even when nothing is exported here, so an empty line below does
# NOT prove claude is unauthenticated, only that this shell isn't the source.
echo "ANTHROPIC_API_KEY in shell (first 20 chars): ${ANTHROPIC_API_KEY:0:20}${ANTHROPIC_API_KEY:+ (...truncated)}"

# claude -p uses the claude.ai/Pro session, not ANTHROPIC_API_KEY. If the caller's
# shell has that var set (e.g. for a prior rwe-weekly/week_that_was.py run in the
# same terminal), claude refuses to start with an auth-conflict error — scrub it
# for this invocation regardless of what the parent shell has exported.
if ! echo "${CLAUDE_PROMPT}" | env -u ANTHROPIC_API_KEY claude -p \
  --permission-mode bypassPermissions \
  --strict-mcp-config \
  --mcp-config "${RWE_ROOT}/automation/mcp-headless.json" \
  --add-dir "${RWE_ROOT}" \
  --debug \
  --debug-file "${DEBUG_FILE}"; then
  echo "ERROR: daily flow failed. MCP debug log: ${DEBUG_FILE}"
  rwe_tail_debug_log "${DEBUG_FILE}" "MCP debug log"
  exit 1
fi

touch "${SENTINEL}"
