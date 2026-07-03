#!/usr/bin/env bash
# End-to-end connectivity checks for reading-with-ears headless runs (rwe-catchup,
# rwe-run, rwe-weekly-audio). Mirrors the exact claude -p flags those scripts use.
#
# Usage:
#   rwe-connectivity-check.sh              # standard: toolchain + auth + MCP registry
#   rwe-connectivity-check.sh --live       # + headless claude -p probes (OAuth, Gmail tools)
#   rwe-connectivity-check.sh --deep       # + full debug-log analysis + optional --doctor
#   rwe-connectivity-check.sh --quick      # skip claude -p probes
#   rwe-connectivity-check.sh --verbose    # extra detail
#   rwe-connectivity-check.sh --date 2026-06-23   # Gmail probe date (default: yesterday)
#
# Artifacts: ~/logs/reading-with-ears/connectivity-<timestamp>/
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${HERE}/rwe-common.sh"

LEVEL="standard"
VERBOSE=0
RUN_DOCTOR=0
PROBE_DATE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)    LEVEL="quick"; shift ;;
    --standard) LEVEL="standard"; shift ;;
    --live)     LEVEL="live"; shift ;;
    --deep)     LEVEL="deep"; shift ;;
    --verbose|-v) VERBOSE=1; shift ;;
    --doctor)   RUN_DOCTOR=1; shift ;;
    --date)     PROBE_DATE="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

[[ "${LEVEL}" == "deep" ]] && LEVEL="live" && RUN_DOCTOR=1

REPO_ROOT="$(rwe_repo_root "${HERE}")" || exit 1
RWE_ROOT="${REPO_ROOT}/reading-with-ears"
MCP_CONFIG="${RWE_ROOT}/automation/mcp-headless.json"
SKILL_FILE="${RWE_ROOT}/skills/user/reading-list-builder/SKILL.md"

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

if [[ -z "${PROBE_DATE}" ]]; then
  PROBE_DATE="$(date -v-1d +%F 2>/dev/null || date -d 'yesterday' +%F)"
fi

STAMP="$(date +%Y%m%dT%H%M%S)"
ARTIFACT_DIR="${HOME}/logs/reading-with-ears/connectivity-${STAMP}"
mkdir -p "${ARTIFACT_DIR}"

ISSUES=0
WARNS=0
STEP=0

log() { echo "$*"; echo "$*" >> "${ARTIFACT_DIR}/summary.log"; }
ok()  { log "  OK   $*"; }
warn(){ log "  WARN $*"; WARNS=$((WARNS + 1)); }
note(){ log "  NOTE $*"; }
bad() { log "  FAIL $*"; ISSUES=$((ISSUES + 1)); }
phase() {
  STEP=$((STEP + 1))
  log ""
  log "=== [${STEP}] $* ==="
}

verbose_file() {
  local label="$1" path="$2"
  [[ "${VERBOSE}" -eq 1 && -f "${path}" ]] && log "  (${label}: ${path})"
}

rwe_claude_headless_cmd() {
  # Same invocation as bin/rwe-catchup.sh — keep in sync via rwe_claude_headless().
  rwe_claude_headless "${RWE_ROOT}" "$@"
}

run_claude_probe() {
  local name="$1" prompt="$2" debug_file="$3" timeout_sec="${4:-180}"
  local out_file="${ARTIFACT_DIR}/${name}.stdout"
  local err_file="${ARTIFACT_DIR}/${name}.stderr"
  log "  Running headless probe: ${name} (timeout ${timeout_sec}s)…"
  log "  debug → ${debug_file}"

  # macOS lacks GNU timeout; use background waiter.
  (
    echo "${prompt}" | rwe_claude_headless_cmd \
      --debug \
      --debug-file "${debug_file}" \
      >"${out_file}" 2>"${err_file}"
  ) &
  local pid=$!
  local waited=0
  while kill -0 "${pid}" 2>/dev/null; do
    if [[ "${waited}" -ge "${timeout_sec}" ]]; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
      bad "${name}: timed out after ${timeout_sec}s"
      verbose_file "stdout" "${out_file}"
      verbose_file "stderr" "${err_file}"
      return 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
  wait "${pid}" || true

  verbose_file "stdout" "${out_file}"
  verbose_file "stderr" "${err_file}"

  local combined="${out_file}.combined"
  { echo "=== stdout ==="; cat "${out_file}" 2>/dev/null || true
    echo "=== stderr ==="; cat "${err_file}" 2>/dev/null || true
  } >"${combined}"

  if grep -qiE 'not logged in|please run /login|invalid api key' "${combined}"; then
    bad "${name}: Claude auth failure — see ${combined}"
    grep -iE 'not logged in|please run /login|invalid api key' "${combined}" | head -5 | while read -r line; do
      log "    ${line}"
    done
    return 1
  fi
  if grep -qiE 'gmail_search_messages|gmail_read_message|mcp__gmail__' "${combined}"; then
    ok "${name}: Gmail MCP tools referenced in output"
  fi
  if grep -qiE 'not available as callable tools|do not appear in the deferred tools|blocks step 1' "${combined}"; then
    bad "${name}: Gmail tools not loaded in headless session — see ${combined}"
    return 1
  fi
  return 0
}

phase "Repo layout"
if [[ -f "${SKILL_FILE}" ]]; then
  ok "Skill present: ${SKILL_FILE}"
else
  bad "Missing skill: ${SKILL_FILE}"
fi
if [[ -f "${MCP_CONFIG}" ]]; then
  ok "MCP config: ${MCP_CONFIG}"
  cp "${MCP_CONFIG}" "${ARTIFACT_DIR}/mcp-headless.json"
else
  bad "Missing MCP config: ${MCP_CONFIG}"
fi

phase "Toolchain"
for cmd in claude python3 uvx curl jq; do
  if command -v "${cmd}" >/dev/null 2>&1; then
    ok "${cmd}: $(command -v "${cmd}")"
  else
    bad "${cmd}: not on PATH"
  fi
done
if command -v claude >/dev/null 2>&1; then
  claude --version 2>&1 | head -1 | tee "${ARTIFACT_DIR}/claude-version.txt" | while read -r line; do
    ok "claude version: ${line}"
  done
fi
if command -v nlm >/dev/null 2>&1; then
  ok "nlm: $(command -v nlm)"
else
  warn "nlm CLI not found (notebooklm-mcp-cli) — audio/notebook CLI steps may fail"
fi

phase "Claude auth (settings + OAuth)"
if [[ -x "${_RWE_BIN_DIR}/rwe-auth-check.sh" ]]; then
  if RWE_REPO="${REPO_ROOT}" "${_RWE_BIN_DIR}/rwe-auth-check.sh" --test-api \
      >"${ARTIFACT_DIR}/auth-check.txt" 2>&1; then
    ok "rwe-auth-check.sh: no settings-file blockers"
    grep -E '^  [0-9]+\.|MISMATCH|blocker|WARN' "${ARTIFACT_DIR}/auth-check.txt" | head -20 >> "${ARTIFACT_DIR}/summary.log" || true
  else
    bad "rwe-auth-check.sh: blockers found — see ${ARTIFACT_DIR}/auth-check.txt"
    tail -20 "${ARTIFACT_DIR}/auth-check.txt" | while read -r line; do log "    ${line}"; done
  fi
else
  warn "rwe-auth-check.sh not found"
fi

phase "Claude OAuth credential files"
found_cred=0
for f in "${HOME}/.claude/.credentials.json" "${HOME}/.claude/credentials.json"; do
  if [[ -f "${f}" ]]; then
    ok "Found ${f}"
    found_cred=1
  fi
done
[[ "${found_cred}" -eq 0 ]] && warn "No ~/.claude/.credentials.json — run: claude /login"

status_out="$(env -u ANTHROPIC_API_KEY claude /status 2>&1 || true)"
printf '%s\n' "${status_out}" > "${ARTIFACT_DIR}/claude-status.txt"
if echo "${status_out}" | grep -qiE 'not logged in|please run /login'; then
  bad "claude /status: not logged in — run: claude /login"
elif echo "${status_out}" | grep -qiE 'auth token|logged in|claude\.ai|subscription|max'; then
  ok "claude /status: OAuth session appears active"
else
  warn "claude /status inconclusive — see ${ARTIFACT_DIR}/claude-status.txt"
  [[ "${VERBOSE}" -eq 1 ]] && head -15 "${ARTIFACT_DIR}/claude-status.txt" | while read -r line; do log "    ${line}"; done
fi

phase "MCP registry (claude mcp list)"
if command -v claude >/dev/null 2>&1; then
  claude mcp list 2>&1 | tee "${ARTIFACT_DIR}/mcp-list.txt" || true
  if grep -qiE 'claude\.ai Gmail|gmailmcp\.googleapis' "${ARTIFACT_DIR}/mcp-list.txt" \
      && grep -i 'Gmail' "${ARTIFACT_DIR}/mcp-list.txt" | grep -qi 'Connected'; then
    ok "claude.ai Gmail connector connected (gmailmcp.googleapis.com)"
  else
    bad "claude.ai Gmail connector not connected — enable in Claude Settings → Connectors → Gmail"
  fi
  if grep -E '^gmail:.*gmail\.mcp\.claude\.com' "${ARTIFACT_DIR}/mcp-list.txt" | grep -qi 'Failed'; then
    warn "Legacy gmail.mcp.claude.com registration failed (expected — endpoint deprecated/404). Remove with: claude mcp remove gmail"
  fi
  if grep -qi 'notebooklm\|nlm' "${ARTIFACT_DIR}/mcp-list.txt"; then
    ok "NotebookLM-related MCP listed"
  else
    warn "NotebookLM not in claude mcp list (headless adds it via mcp-headless.json — OK if uvx probe passed)"
  fi
  if grep -qi 'codex' "${ARTIFACT_DIR}/mcp-list.txt"; then
    warn "codex MCP registered — unrelated to RWE; may trigger macOS malware block. Remove: claude mcp remove codex"
  fi
else
  bad "claude CLI missing — cannot list MCP servers"
fi

phase "Deprecated endpoint check (gmail.mcp.claude.com)"
legacy_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  'https://gmail.mcp.claude.com/mcp' 2>/dev/null || echo '000')"
echo "${legacy_code}" > "${ARTIFACT_DIR}/gmail-legacy-mcp-http.txt"
if [[ "${legacy_code}" == "404" || "${legacy_code}" == "000" ]]; then
  ok "gmail.mcp.claude.com unavailable (${legacy_code}) — RWE uses claude.ai Gmail connector instead"
else
  warn "gmail.mcp.claude.com returned HTTP ${legacy_code} (unexpected)"
fi

phase "NotebookLM subprocess (uvx)"
if command -v uvx >/dev/null 2>&1; then
  if uvx --from notebooklm-mcp-cli notebooklm-mcp --help \
      >"${ARTIFACT_DIR}/notebooklm-mcp-help.txt" 2>&1; then
    ok "uvx notebooklm-mcp starts"
  else
    bad "uvx notebooklm-mcp failed — see ${ARTIFACT_DIR}/notebooklm-mcp-help.txt"
  fi
fi
if command -v nlm >/dev/null 2>&1; then
  if nlm login --check >"${ARTIFACT_DIR}/nlm-login-check.txt" 2>&1; then
    ok "nlm login --check passed"
  else
    warn "nlm login --check failed — run: nlm login (see ${ARTIFACT_DIR}/nlm-login-check.txt)"
  fi
fi

if [[ "${LEVEL}" != "quick" ]]; then
  phase "Headless OAuth probe (claude -p, same flags as rwe-catchup)"
  OAUTH_DEBUG="${ARTIFACT_DIR}/probe-oauth.debug.log"
  OAUTH_PROMPT='Reply with exactly the single word PONG and nothing else. Do not use any tools.'
  if run_claude_probe "probe-oauth" "${OAUTH_PROMPT}" "${OAUTH_DEBUG}" 120; then
    if grep -qi '^PONG$' "${ARTIFACT_DIR}/probe-oauth.stdout" 2>/dev/null; then
      ok "OAuth probe: model responded PONG"
    else
      warn "OAuth probe: no PONG in stdout — auth may still work; see ${ARTIFACT_DIR}/probe-oauth.stdout"
    fi
  fi
fi

if [[ "${LEVEL}" == "live" ]]; then
    phase "Headless Gmail tool probe (claude -p + ToolSearch)"
    GMAIL_DEBUG="${ARTIFACT_DIR}/probe-gmail-tools.debug.log"
    GMAIL_PROMPT='This is a connectivity test only. Use ToolSearch to find tools whose names contain "gmail" (case insensitive). List every matching tool name exactly as registered, one per line, no other text. If ToolSearch finds none, say exactly: NO_GMAIL_TOOLS.'
    run_claude_probe "probe-gmail-tools" "${GMAIL_PROMPT}" "${GMAIL_DEBUG}" 180 || true

    python3 - "${GMAIL_DEBUG}" "${ARTIFACT_DIR}/probe-gmail-tools.stdout" <<'PY'
import re, sys
from pathlib import Path

debug = Path(sys.argv[1])
stdout = Path(sys.argv[2])
text = ""
if debug.is_file():
    text += debug.read_text(encoding="utf-8", errors="replace")
if stdout.is_file():
    text += "\n" + stdout.read_text(encoding="utf-8", errors="replace")

tools = sorted(set(re.findall(r"mcp__gmail__\w+", text, re.I)))
deferred = [ln for ln in text.splitlines() if "deferred" in ln.lower() and "gmail" in ln.lower()]
errors = [ln for ln in text.splitlines() if re.search(r"gmail.*(not available|failed|401|error)", ln, re.I)]

print("Gmail tool scan:")
if tools:
    print(f"  OK   Found tool IDs in logs/output: {', '.join(tools[:12])}")
else:
    print("  FAIL No mcp__gmail__* tools in probe output/debug log")
if "NO_GMAIL_TOOLS" in text:
    print("  FAIL Model reported NO_GMAIL_TOOLS")
if deferred:
    print("  INFO deferred-tool lines (sample):")
    for ln in deferred[:5]:
        print(f"    {ln[:140]}")
if errors:
    print("  FAIL Gmail error lines:")
    for ln in errors[:5]:
        print(f"    {ln[:140]}")
raise SystemExit(0 if tools and "NO_GMAIL_TOOLS" not in text else 1)
PY
    gmail_scan=$?
    [[ "${gmail_scan}" -eq 0 ]] && ok "Gmail tools visible in headless probe" \
      || bad "Gmail tools NOT visible in headless probe — this matches catch-up failures"

    phase "Headless Gmail search probe (optional live query)"
    SEARCH_DEBUG="${ARTIFACT_DIR}/probe-gmail-search.debug.log"
    gmail_after="$(echo "${PROBE_DATE}" | tr '-' '/')"
    gmail_next="$(date -j -v+1d -f "%Y-%m-%d" "${PROBE_DATE}" +%F 2>/dev/null || date -d "${PROBE_DATE} +1 day" +%F)"
    gmail_before="$(echo "${gmail_next}" | tr '-' '/')"
    SEARCH_PROMPT="Connectivity test only. Call gmail_search_messages with q='label:newsletter/news after:${gmail_after} before:${gmail_before}' and reply with only the integer count of messages returned, nothing else."
    if run_claude_probe "probe-gmail-search" "${SEARCH_PROMPT}" "${SEARCH_DEBUG}" 240; then
      ok "Gmail search probe completed for ${PROBE_DATE}"
      head -5 "${ARTIFACT_DIR}/probe-gmail-search.stdout" 2>/dev/null | while read -r line; do
        log "    stdout: ${line}"
      done
    else
      bad "Gmail search probe failed for ${PROBE_DATE}"
    fi
fi

if [[ "${LEVEL}" == "quick" ]]; then
  log ""
  log "=== Skipped headless claude -p probes (--quick) ==="
  log "Re-run with --live to test OAuth + Gmail tools exactly as rwe-catchup does."
fi

if [[ "${RUN_DOCTOR}" -eq 1 ]] && command -v claude >/dev/null 2>&1; then
  phase "claude doctor"
  claude doctor 2>&1 | tee "${ARTIFACT_DIR}/claude-doctor.txt" || true
fi

log ""
log "=== Summary ==="
log "Artifacts: ${ARTIFACT_DIR}"
log "Failures: ${ISSUES}  Warnings: ${WARNS}"
if [[ "${ISSUES}" -gt 0 ]]; then
  log ""
  log "Common fixes:"
  log "  claude /login"
  log "  Claude Settings → Connectors → enable Gmail (claude.ai Gmail / gmailmcp.googleapis.com)"
  log "  claude mcp remove gmail   # remove broken legacy gmail.mcp.claude.com registration"
  log "  nlm login"
  log "  Re-run: bin/rwe-connectivity-check.sh --live --verbose"
  exit 1
fi
log "All required connectivity checks passed."
exit 0
