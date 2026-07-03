# Shared helpers for Reading with Ears bin scripts.
# shellcheck shell=bash

# Absolute path to bin/ — set at source time so helpers work after callers cd elsewhere.
_RWE_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Append tool dirs as fallbacks for launchd/cron (minimal PATH). Never prepend
# /opt/homebrew/bin — an old Homebrew `claude` there shadows a newer install
# in ~/.local/bin that the user's interactive shell uses.
rwe_ensure_path() {
  local dir
  # Prefer ~/.local/bin (native claude install) over entries already on PATH.
  if [[ -d "${HOME}/.local/bin" ]]; then
    case ":${PATH}:" in
      *:"${HOME}/.local/bin":*) ;;
      *) PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}" ;;
    esac
  fi
  for dir in /opt/homebrew/bin /usr/local/bin; do
    [[ -d "${dir}" ]] || continue
    case ":${PATH}:" in
      *:"${dir}":*) ;;
      *) PATH="${PATH:+${PATH}:}${dir}" ;;
    esac
  done
  export PATH
}

rwe_ensure_path

# Resolve the newest claude on PATH (avoids stale Homebrew shadowing native install).
# Override: export RWE_CLAUDE_BIN=/path/to/claude
rwe_claude_bin() {
  if [[ -n "${RWE_CLAUDE_BIN:-}" && -x "${RWE_CLAUDE_BIN}" ]]; then
    echo "${RWE_CLAUDE_BIN}"
    return 0
  fi
  rwe_ensure_path
  python3 - <<'PY'
import os, re, subprocess, sys

def ver_tuple(s):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

path = os.environ.get("PATH", "")
seen = set()
best = None
best_v = (0, 0, 0)
for d in path.split(":"):
    p = os.path.join(d, "claude")
    if not os.path.isfile(p) or os.access(p, os.X_OK):
        continue
    rp = os.path.realpath(p)
    if rp in seen:
        continue
    seen.add(rp)
    try:
        out = subprocess.run([rp, "--version"], capture_output=True, text=True, timeout=10)
        vt = ver_tuple((out.stdout or "") + (out.stderr or ""))
    except Exception:
        vt = (0, 0, 0)
    if vt > best_v:
        best_v = vt
        best = rp
print(best or "claude")
PY
}

rwe_log_claude_bin() {
  local bin
  bin="$(rwe_claude_bin)"
  echo "Using claude: ${bin} ($("${bin}" --version 2>/dev/null | head -1 || echo unknown))"
}
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
  if echo "${status_out}" | grep -qiE 'unknown skill'; then
    # /status is not a valid command on all Claude Code versions (e.g. 2.1.87).
    return 0
  fi
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

# Headless claude -p invocation shared by rwe-run / rwe-catchup / rwe-weekly-audio.
# Gmail: claude.ai connectors (mcp__claude_ai_Gmail__*) may load in -p on recent
# Claude Code versions; also try user-scoped HTTP gmail in mcp-headless.json.
# Set RWE_STRICT_MCP=1 to exclude claude.ai connectors (legacy/debug only).
rwe_claude_headless() {
  local rwe_root="${1:?reading-with-ears root}"
  shift
  local strict=()
  [[ "${RWE_STRICT_MCP:-0}" == "1" ]] && strict=(--strict-mcp-config)
  export ENABLE_CLAUDEAI_MCP_SERVERS="${ENABLE_CLAUDEAI_MCP_SERVERS:-true}"
  local claude_bin
  claude_bin="$(rwe_claude_bin)"
  env -u ANTHROPIC_API_KEY "${claude_bin}" -p \
    --permission-mode bypassPermissions \
    ${strict[@]+"${strict[@]}"} \
    --mcp-config "${rwe_root}/automation/mcp-headless.json" \
    --add-dir "${rwe_root}" \
    "$@"
}

# Warn when Claude Code is below the version where claude.ai MCP in -p was restored.
rwe_claude_version_warn() {
  local bin
  bin="$(rwe_claude_bin)"
  if [[ ! -x "${bin}" ]] && ! command -v "${bin}" >/dev/null 2>&1; then
    return 0
  fi
  local ver
  ver="$("${bin}" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
  [[ -z "${ver}" ]] && return 0
  python3 - "${ver}" <<'PY'
import sys
parts = [int(x) for x in sys.argv[1].split(".")[:3]]
while len(parts) < 3:
    parts.append(0)
if tuple(parts) < (2, 1, 180):
    print(
        f"WARN: Claude Code {sys.argv[1]} — Gmail in claude -p needs 2.1.180+ "
        f"(you have {parts[0]}.{parts[1]}.{parts[2]}). Run: claude install",
        file=sys.stderr,
    )
PY
}
