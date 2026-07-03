#!/usr/bin/env bash
# Catch-up mode: find days with missing sentinels in a range and run the daily flow
# (fetch/synthesize/YAML — no audio, see docs/weekly-cadence-migration.md) for each,
# one day at a time.
#
# Usage: rwe-catchup [--from YYYY-MM-DD] [--to YYYY-MM-DD]
# Defaults: 14 days ago through yesterday. Does not process today (use rwe-run.sh).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${HERE}/rwe-common.sh"

REPO_ROOT="$(rwe_repo_root "${HERE}")"
RWE_ROOT="${REPO_ROOT}/reading-with-ears"

# Do not source ~/.zshrc — see note in rwe-run.sh.
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

SKILL_VERSION_REQUIRED="3.0"
SKILL_FILE="${RWE_ROOT}/skills/user/reading-list-builder/SKILL.md"
SKILL_VERSION=$(grep -m1 '^version:' "${SKILL_FILE}" | sed 's/version:[[:space:]]*"\([^"]*\)"/\1/')
if [[ "${SKILL_VERSION}" != "${SKILL_VERSION_REQUIRED}" ]]; then
  echo "ERROR: rwe-catchup.sh expects skill version ${SKILL_VERSION_REQUIRED} but ${SKILL_FILE} reports '${SKILL_VERSION}'. Pull latest changes or update SKILL_VERSION_REQUIRED."
  exit 1
fi

# --- Argument parsing ---
FROM_DATE=$(date -v-14d +%F)
TO_DATE=$(date -v-1d +%F)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) FROM_DATE="$2"; shift 2 ;;
    --to)   TO_DATE="$2";   shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

LOG_DIR="${HOME}/logs/reading-with-ears"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/catchup-$(date +%F).log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== $(date "+%Y-%m-%dT%H:%M:%S%z") rwe-catchup from=${FROM_DATE} to=${TO_DATE} ==="

"${RWE_ROOT}/scripts/install-local.sh"

if ! rwe_audit_claude_auth "${REPO_ROOT}"; then
  echo "Aborting — fix Claude auth blockers above, then re-run."
  echo "Run: bin/rwe-auth-check.sh --test-api --doctor"
  exit 1
fi

if ! rwe_check_claude_oauth; then
  exit 1
fi
rwe_claude_version_warn 2>&1 | while read -r line; do [[ -n "${line}" ]] && echo "${line}"; done

STATE_DIR="${HOME}/.local/state/reading-with-ears"
mkdir -p "${STATE_DIR}"

processed=0
skipped=0
failed=0

current="${FROM_DATE}"
while [[ "$current" < "$TO_DATE" || "$current" == "$TO_DATE" ]]; do
  SENTINEL="${STATE_DIR}/done-${current}"

  if [[ -f "${SENTINEL}" ]]; then
    echo "[${current}] Already complete — skipping."
    skipped=$((skipped + 1))
  else
    echo "[${current}] Running pipeline..."

    # Upper bound for Gmail search: the day after, so results are scoped to exactly this day.
    next=$(date -j -v+1d -f "%Y-%m-%d" "${current}" +"%Y-%m-%d")
    gmail_after=$(echo "${current}" | tr '-' '/')
    gmail_before=$(echo "${next}" | tr '-' '/')

    CLAUDE_PROMPT="Read and follow skills/user/reading-list-builder/SKILL.md and run the DAILY FLOW (Steps 0-8) for ${current}. In all Gmail searches use 'after:${gmail_after} before:${gmail_before}' to scope results to exactly this day. Do not run the weekly audio flow."

    cd "${RWE_ROOT}"

    # Full claude debug capture (unfiltered — a category filter like "mcp" broke
    # stdin prompt piping in testing) per day, so a failure (Gmail vs. NotebookLM
    # vs. something else in the MCP handshake) doesn't require manually reproducing
    # it interactively — the detail is already on disk when the failure happens.
    DEBUG_FILE="${LOG_DIR}/catchup-debug-${current}.log"

    # Print what the shell actually sees before we scrub it — this is diagnostic
    # only: claude may still pick up a key from its own settings (~/.claude.json
    # env block) even when nothing is exported here, so an empty line below does
    # NOT prove claude is unauthenticated, only that this shell isn't the source.
    echo "[${current}] ANTHROPIC_API_KEY in shell (first 20 chars): ${ANTHROPIC_API_KEY:0:20}${ANTHROPIC_API_KEY:+ (...truncated)}"

    # claude -p uses the claude.ai/Pro session, not ANTHROPIC_API_KEY — scrub it in
    # case the caller's shell has it set (e.g. a prior rwe-weekly run this session),
    # which otherwise makes claude refuse to start with an auth-conflict error.
    # Use 'if' so a single day's failure doesn't abort the whole catch-up run.
    if echo "${CLAUDE_PROMPT}" | rwe_claude_headless "${RWE_ROOT}" \
        --debug \
        --debug-file "${DEBUG_FILE}"; then
      touch "${SENTINEL}"
      echo "[${current}] Done."
      processed=$((processed + 1))
    else
      echo "[${current}] Pipeline failed — sentinel not written, will retry on next catch-up run."
      echo "[${current}] Diagnose: bin/rwe-connectivity-check.sh --live --verbose --date ${current}"
      echo "[${current}] MCP debug log: ${DEBUG_FILE}"
      rwe_tail_debug_log "${DEBUG_FILE}" "[${current}] MCP debug log"
      failed=$((failed + 1))
    fi
  fi

  current=$(date -j -v+1d -f "%Y-%m-%d" "${current}" +"%Y-%m-%d")
done

echo "=== Catch-up complete: ${processed} processed, ${skipped} already done, ${failed} failed ==="
