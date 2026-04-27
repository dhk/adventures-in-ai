#!/usr/bin/env bash
# Catch-up mode: find days with missing sentinels in a range and run the pipeline
# for each, one day at a time, preserving the day-by-day feed structure.
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

STATE_DIR="${HOME}/.local/state/reading-with-ears"
mkdir -p "${STATE_DIR}"

processed=0
skipped=0
failed=0

current="${FROM_DATE}"
while [[ "$current" <= "$TO_DATE" ]]; do
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

    CLAUDE_PROMPT="Read and follow skills/user/reading-list-builder/SKILL.md and run the full pipeline for ${current}. In all Gmail searches use 'after:${gmail_after} before:${gmail_before}' to scope results to exactly this day. Complete all four phases through Element.fm publish."

    cd "${RWE_ROOT}"

    # Use 'if' so a single day's failure doesn't abort the whole catch-up run.
    if claude -p \
      --permission-mode bypassPermissions \
      --strict-mcp-config \
      --mcp-config "${RWE_ROOT}/automation/mcp-headless.json" \
      --add-dir "${RWE_ROOT}" \
      "${CLAUDE_PROMPT}"; then
      touch "${SENTINEL}"
      echo "[${current}] Done."
      processed=$((processed + 1))
    else
      echo "[${current}] Pipeline failed — sentinel not written, will retry on next catch-up run."
      failed=$((failed + 1))
    fi
  fi

  current=$(date -j -v+1d -f "%Y-%m-%d" "${current}" +"%Y-%m-%d")
done

echo "=== Catch-up complete: ${processed} processed, ${skipped} already done, ${failed} failed ==="
