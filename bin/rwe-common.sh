# Shared helpers for Reading with Ears bin scripts.
# shellcheck shell=bash

# Absolute path to bin/ — set at source time so helpers work after callers cd elsewhere.
_RWE_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve repo root (directory that contains reading-with-ears/).
# Precedence: RWE_REPO → ~/.config/reading-with-ears/config.json repo_root
# → caller lives in-repo at bin/ (parent is repo root).
rwe_repo_root() {
  local caller_bin_dir="${1:?caller bin dir}"

  if [[ -n "${RWE_REPO:-}" ]]; then
    (cd "${RWE_REPO}" && pwd)
    return 0
  fi

  local from_cfg
  from_cfg="$(
    python3 -c "
import json, os
from pathlib import Path
p = Path.home() / '.config' / 'reading-with-ears' / 'config.json'
if not p.is_file():
    print('', end='')
    raise SystemExit(0)
d = json.loads(p.read_text(encoding='utf-8'))
r = d.get('repo_root') or ''
print(os.path.expanduser(str(r).strip()), end='')
"
  )" || true
  if [[ -n "${from_cfg}" && -f "${from_cfg}/reading-with-ears/scripts/install-local.sh" ]]; then
    (cd "${from_cfg}" && pwd)
    return 0
  fi

  caller_bin_dir="$(cd "${caller_bin_dir}" && pwd)"
  if [[ -f "${caller_bin_dir}/../reading-with-ears/scripts/install-local.sh" ]]; then
    (cd "${caller_bin_dir}/.." && pwd)
    return 0
  fi

  echo "reading-with-ears: set RWE_REPO or repo_root in ~/.config/reading-with-ears/config.json (see docs/install.md)." >&2
  return 1
}

# Preflight for headless OAuth runs. Fails fast when settings files still inject
# ANTHROPIC_API_KEY (env -u in the caller does not clear settings.json env blocks).
rwe_audit_claude_auth() {
  local repo_root="${1:?repo root}"
  if [[ -x "${_RWE_BIN_DIR}/rwe-auth-check.sh" ]]; then
    RWE_REPO="${repo_root}" "${_RWE_BIN_DIR}/rwe-auth-check.sh"
    return $?
  fi
  echo "WARN: rwe-auth-check.sh not found at ${_RWE_BIN_DIR} — skipping Claude auth preflight" >&2
  return 0
}

# Headless flows scrub ANTHROPIC_API_KEY — they need an active claude.ai OAuth session.
rwe_check_claude_oauth() {
  if ! command -v claude >/dev/null 2>&1; then
    echo "WARN: claude CLI not on PATH — cannot verify OAuth login" >&2
    return 0
  fi
  local status_out
  status_out="$(env -u ANTHROPIC_API_KEY claude /status 2>&1 || true)"
  if echo "${status_out}" | grep -qiE 'not logged in|please run /login'; then
    echo "ERROR: Claude Code is not logged in."
    echo "  rwe-catchup / rwe-run scrub ANTHROPIC_API_KEY and use your claude.ai subscription."
    echo "  Fix: run interactively once, then retry catch-up:"
    echo "    claude /login"
    return 1
  fi
  if echo "${status_out}" | grep -qiE 'auth token|logged in|claude\.ai|subscription'; then
    return 0
  fi
  echo "WARN: Could not confirm Claude OAuth login from 'claude /status'."
  echo "  If catch-up fails with 'Not logged in · Please run /login', run: claude /login"
  return 0
}

rwe_tail_debug_log() {
  local debug_file="${1:?debug log path}"
  local label="${2:-debug log}"
  if [[ -f "${debug_file}" ]]; then
    local lines
    lines="$(wc -l < "${debug_file}" | tr -d ' ')"
    echo "--- ${label} (${lines} lines, last 40) ---"
    tail -40 "${debug_file}"
    echo "--- end ${label} ---"
  else
    echo "WARN: ${label} not found at ${debug_file}"
  fi
}
