#!/usr/bin/env bash
# Verify (and optionally fix) machine setup for reading-list-builder + Phase 2.
# Usage:
#   ./verify-reading-with-ears-setup.sh              # all feature groups (default)
#   ./verify-reading-with-ears-setup.sh --apply      # install missing tools, chmod, install-local --install-bin
#   ./verify-reading-with-ears-setup.sh --features=toolchain,repo,mcp
# Env: RWE_VERIFY_FEATURES=comma-separated list (same names); overridden by --features=
#
# Feature groups (allowlist): all | toolchain, notebooklm, claude, repo, user_config,
#   elementfm, permissions, sync, mcp, cursor
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIEF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BRIEF_ROOT}/.." && pwd)"
CFG_DIR="${HOME}/.config/reading-with-ears"
EXAMPLE_CFG="${BRIEF_ROOT}/config/config.example.json"
FEEDS_BUNDLED="${BRIEF_ROOT}/config/feeds.json"

APPLY=0
FEATURES_RAW="${RWE_VERIFY_FEATURES:-all}"
for arg in "$@"; do
  case "${arg}" in
    --apply) APPLY=1 ;;
    --features=all) FEATURES_RAW="all" ;;
    --features=*) FEATURES_RAW="${arg#--features=}" ;;
    -h|--help)
      head -n 15 "$0"
      exit 0
      ;;
  esac
done

feature_enabled() {
  local n="${1:?}"
  local raw="${FEATURES_RAW//[[:space:]]/}"
  [[ -z "${raw}" ]] && raw="all"
  [[ "${raw}" == "all" ]] && return 0
  local IFS=,
  local x
  for x in ${raw}; do
    [[ "${x}" == "${n}" ]] && return 0
  done
  return 1
}

have() { command -v "$1" >/dev/null 2>&1; }

py_ok() {
  python3 -c 'import sys; v=sys.version_info; raise SystemExit(0 if v[:2]>=(3,10) else 1)' 2>/dev/null
}

issues=0
warn() { echo "⚠️  $*" >&2; }
note() { echo "    $*"; }
ok() { echo "✓  $*"; }
bad() { echo "✗  $*" >&2; issues=$((issues + 1)); }

# Reject unknown --features tokens (avoids a silent no-op "pass").
_validate_feature_list() {
  [[ "${FEATURES_RAW}" == "all" ]] && return 0
  local raw="${FEATURES_RAW//[[:space:]]/}"
  [[ -z "${raw}" ]] && return 0
  local known=" toolchain notebooklm claude repo user_config elementfm permissions sync mcp cursor "
  local IFS=,
  local x unk=0
  for x in ${raw}; do
    [[ -z "${x}" ]] && continue
    if [[ "${known}" != *" ${x} "* ]]; then
      warn "Unknown feature \"${x}\" (typo?). Known: toolchain notebooklm claude repo user_config elementfm permissions sync mcp cursor"
      unk=$((unk + 1))
    fi
  done
  [[ "${unk}" -gt 0 ]] && issues=$((issues + unk))
}

_validate_feature_list

echo "Reading with Ears — configuration verification"
echo "Repo root: ${REPO_ROOT}"
echo "Mode: $([[ "${APPLY}" -eq 1 ]] && echo apply || echo check-only)"
echo "Features: ${FEATURES_RAW}"
echo ""

if [[ "$(uname -s)" != "Darwin" ]]; then
  warn "Docs target macOS; some install paths assume Homebrew."
fi

# --- Toolchain ---
if feature_enabled toolchain; then
if py_ok; then
  ok "Python $(python3 -c 'import sys; print("%d.%d.%d"%sys.version_info[:3])') (>= 3.10)"
else
  bad "Python 3.10+ required (install via python.org, Homebrew, or uv)."
fi

if have ffmpeg; then
  ok "ffmpeg ($(command -v ffmpeg))"
else
  bad "ffmpeg not found"
  if [[ "${APPLY}" -eq 1 ]] && have brew; then
    echo "    Installing ffmpeg via Homebrew…"
    HOMEBREW_NO_AUTO_UPDATE=1 brew install ffmpeg || warn "brew install ffmpeg failed — fix brew/network and retry."
  elif [[ "${APPLY}" -eq 1 ]]; then
    warn "Install Homebrew or ffmpeg manually: https://ffmpeg.org"
  fi
fi

if have uv && have uvx; then
  ok "uv / uvx ($(uv --version 2>/dev/null | head -1))"
else
  bad "uv / uvx not on PATH"
  if [[ "${APPLY}" -eq 1 ]]; then
    if have brew; then
      echo "    Installing uv via Homebrew…"
      HOMEBREW_NO_AUTO_UPDATE=1 brew install uv || warn "brew install uv failed — fix brew/network and retry."
    else
      echo "    Installing uv via official installer…"
      ( curl -LsSf https://astral.sh/uv/install.sh | sh ) || warn "uv installer failed — install uv manually (https://docs.astral.sh/uv/)."
      note 'Add ~/.local/bin to PATH (or restart the shell), then re-run with --apply.'
    fi
  fi
fi
fi

if feature_enabled notebooklm; then
if have nlm; then
  ok "nlm at $(command -v nlm) ($(nlm --version 2>&1 | tr '\n' ' ' | cut -c1-120))"
else
  bad "nlm CLI not found (comes with notebooklm-mcp-cli)"
  if [[ "${APPLY}" -eq 1 ]] && have uv; then
    echo "    uv tool install notebooklm-mcp-cli…"
    uv tool install notebooklm-mcp-cli || warn "uv tool install notebooklm-mcp-cli failed."
  fi
fi

if have uvx; then
  if uvx --from notebooklm-mcp-cli notebooklm-mcp --help >/dev/null 2>&1; then
    ok "NotebookLM MCP (uvx notebooklm-mcp) starts"
  else
    bad "NotebookLM MCP (uvx) failed — check uv cache and network"
    if [[ "${APPLY}" -eq 1 ]] && have uv; then
      uv tool install notebooklm-mcp-cli || true
    fi
  fi
fi
fi

if feature_enabled claude; then
if have claude; then
  ok "claude CLI ($(claude --version 2>/dev/null | head -1 || echo present))"
  auth_check="${REPO_ROOT}/bin/rwe-auth-check.sh"
  if [[ -x "${auth_check}" ]]; then
    if bash "${auth_check}" >/dev/null 2>&1; then
      ok "Claude OAuth preflight (rwe-auth-check.sh) — no blockers"
    else
      bad "Claude auth blockers detected — run: bin/rwe-auth-check.sh --test-api --doctor"
      note "Headless rwe-run / rwe-catchup need claude.ai OAuth, not ANTHROPIC_API_KEY in settings files."
    fi
  fi
else
  bad "claude CLI not found (required for rwe-run.sh)"
  if [[ "${APPLY}" -eq 1 ]] && have npm; then
    echo "    npm install -g @anthropic-ai/claude-code…"
    npm install -g @anthropic-ai/claude-code || warn "npm install @anthropic-ai/claude-code failed."
  elif [[ "${APPLY}" -eq 1 ]]; then
    warn "Install Node/npm, then: npm install -g @anthropic-ai/claude-code"
  fi
fi
fi

# --- Repo layout ---
if feature_enabled repo; then
if [[ -f "${BRIEF_ROOT}/skills/user/reading-list-builder/SKILL.md" ]]; then
  ok "Skill reading-list-builder present"
else
  bad "Missing ${BRIEF_ROOT}/skills/user/reading-list-builder/SKILL.md"
fi

if [[ -f "${FEEDS_BUNDLED}" ]]; then
  ok "Bundled config/feeds.json present"
else
  bad "Missing ${FEEDS_BUNDLED}"
fi
fi

# --- User config ---
if feature_enabled user_config; then
if [[ -f "${CFG_DIR}/config.json" ]]; then
  ok "User config ${CFG_DIR}/config.json"
  if ! python3 -c "import json, pathlib, os
p = pathlib.Path(os.path.expanduser('${CFG_DIR}')) / 'config.json'
d = json.loads(p.read_text(encoding='utf-8'))
r = (d.get('repo_root') or '').strip()
r = os.path.expanduser(r)
ok = bool(r and (pathlib.Path(r) / 'reading-with-ears/scripts/install-local.sh').is_file())
raise SystemExit(0 if ok else 1)" 2>/dev/null; then
    warn "config.json repo_root may not point at parent of reading-with-ears/ (see docs/install.md)."
  fi
else
  bad "Missing ${CFG_DIR}/config.json"
  if [[ "${APPLY}" -eq 1 ]]; then
    mkdir -p "${CFG_DIR}"
    if [[ -f "${EXAMPLE_CFG}" ]]; then
      cp "${EXAMPLE_CFG}" "${CFG_DIR}/config.json"
      note "Created ${CFG_DIR}/config.json from example — edit repo_root and audio_dir."
    fi
  fi
fi

if [[ -f "${CFG_DIR}/feeds.json" ]]; then
  ok "Optional override ${CFG_DIR}/feeds.json"
else
  note "No ~/.config/reading-with-ears/feeds.json (using bundled feeds.json is fine)."
fi
fi

if feature_enabled elementfm; then
if [[ -n "${CLAUDE_ELEMENT_FM_KEY:-}" ]]; then
  ok "CLAUDE_ELEMENT_FM_KEY is set (Element.fm upload)"
else
  warn "CLAUDE_ELEMENT_FM_KEY unset — rwe-publish upload will fail until set (docs/install.md §1)."
fi
fi

# --- Permissions & sync ---
if feature_enabled permissions; then
bin_dir="${REPO_ROOT}/bin"
if [[ -d "${bin_dir}" ]]; then
  for x in rwe-common.sh rwe-run.sh rwe-publish rwe-catchup.sh rwe-auth-check.sh; do
    [[ -f "${bin_dir}/${x}" ]] || continue
    if [[ ! -x "${bin_dir}/${x}" ]]; then
      warn "${bin_dir}/${x} is not executable — fixing chmod +x"
      chmod +x "${bin_dir}/${x}"
      ok "chmod +x ${bin_dir}/${x}"
    fi
  done
fi
fi

if [[ "${APPLY}" -eq 1 ]] && feature_enabled sync; then
  chmod +x "${SCRIPT_DIR}/install-local.sh" "${SCRIPT_DIR}/verify-reading-with-ears-setup.sh" 2>/dev/null || true
  echo ""
  echo "Running install-local.sh --install-bin (skill + scripts + ~/bin links)…"
  bash "${SCRIPT_DIR}/install-local.sh" --install-bin || warn "install-local.sh --install-bin failed (see messages above)."
  echo "Re-run without --apply to confirm all checks pass."
fi

# --- MCP registration (Claude Code user scope) ---
if feature_enabled mcp; then
if ! have claude; then
  warn "Claude CLI not on PATH — cannot check or register Gmail MCP (enable claude feature or install)."
else
  if claude mcp list 2>/dev/null | grep -qi 'gmail'; then
    ok "Gmail MCP registered (claude mcp list)"
  else
    warn "Gmail MCP not listed — run: claude mcp add --transport http --scope user gmail https://gmail.mcp.claude.com/mcp"
    if [[ "${APPLY}" -eq 1 ]]; then
      if claude mcp add --transport http --scope user gmail https://gmail.mcp.claude.com/mcp 2>/dev/null; then
        ok "Registered Gmail MCP (complete OAuth in an interactive claude session if prompted)."
      else
        note "claude mcp add failed or already configured under another name — run manually (install.md §3)."
      fi
    fi
  fi
fi
fi

if feature_enabled cursor; then
if [[ -f "${REPO_ROOT}/.cursor/mcp.json" ]]; then
  ok "Cursor project MCP config present (.cursor/mcp.json)"
else
  note "No .cursor/mcp.json in repo root (optional — add for Gmail + NotebookLM in Cursor)."
fi
fi

echo ""
echo "Manual steps (cannot be scripted safely):"
if feature_enabled mcp; then
  note "Interactive OAuth for Gmail / Google: open Claude Code once and approve connectors."
fi
if feature_enabled notebooklm; then
  note "NotebookLM: nlm login"
fi
if feature_enabled cursor; then
  note "Cursor: connect Gmail + NotebookLM MCP in Settings if you use .cursor/mcp.json."
fi
echo ""

if [[ "${issues}" -gt 0 ]]; then
  bad "${issues} required item(s) missing — fix above or re-run with --apply."
  exit 1
fi

echo "All required checks passed."
exit 0
