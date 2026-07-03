# Shared helpers for Reading with Ears bin scripts.
# shellcheck shell=bash

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
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  if [[ -x "${here}/rwe-auth-check.sh" ]]; then
    RWE_REPO="${repo_root}" "${here}/rwe-auth-check.sh"
    return $?
  fi
  echo "WARN: rwe-auth-check.sh not found — skipping Claude auth preflight" >&2
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
