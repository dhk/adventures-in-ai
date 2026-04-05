#!/usr/bin/env bash
# Deploy Reading with Ears skill + Python from the repo clone to ~/.local/share/reading-with-ears/
# Optional: --install-bin → ~/bin/ (copy or symlink, same mode)
#
# Mode (first match wins):
#   1. CLI: --symlink | --copy
#   2. Env:  RWE_SYNC_MODE=symlink|copy
#   3. Config: ~/.config/reading-with-ears/config.json → "sync_mode": "symlink" | "copy"
#   4. Default: symlink (repo policy — override with sync_mode or --copy)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIEF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BRIEF_ROOT}/.." && pwd)"

DEST_SKILL_ROOT="${HOME}/.local/share/reading-with-ears/skills/user/reading-with-ears"
DEST_SCRIPTS="${HOME}/.local/share/reading-with-ears/scripts"
SKILL_SRC="${BRIEF_ROOT}/skills/user/reading-with-ears/SKILL.md"

INSTALL_BIN=0
CLI_MODE=""

for arg in "$@"; do
  case "${arg}" in
    --install-bin) INSTALL_BIN=1 ;;
    --symlink)     CLI_MODE="symlink" ;;
    --copy)        CLI_MODE="copy" ;;
  esac
done

export _RWE_SYNC_CLI="${CLI_MODE}"
SYNC_MODE="$(
  python3 << 'PY'
import json, os
from pathlib import Path

cli = (os.environ.get("_RWE_SYNC_CLI") or "").strip().lower()
if cli in ("copy", "symlink"):
    print(cli)
    raise SystemExit(0)
env = (os.environ.get("RWE_SYNC_MODE") or "").strip().lower()
if env in ("copy", "symlink"):
    print(env)
    raise SystemExit(0)
p = Path.home() / ".config" / "reading-with-ears" / "config.json"
if p.is_file():
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        m = (d.get("sync_mode") or d.get("install_mode") or "").strip().lower()
        if m in ("copy", "symlink"):
            print(m)
            raise SystemExit(0)
    except Exception:
        pass
print("symlink")
PY
)"
unset _RWE_SYNC_CLI

mkdir -p "${DEST_SKILL_ROOT}" "${DEST_SCRIPTS}"

skill_abs="$(cd "$(dirname "${SKILL_SRC}")" && pwd)/$(basename "${SKILL_SRC}")"
if [[ "${SYNC_MODE}" == "symlink" ]]; then
  ln -sf "${skill_abs}" "${DEST_SKILL_ROOT}/SKILL.md"
else
  cp -f "${SKILL_SRC}" "${DEST_SKILL_ROOT}/SKILL.md"
fi

shopt -s nullglob
for py in "${BRIEF_ROOT}/scripts"/*.py; do
  base="$(basename "${py}")"
  dest="${DEST_SCRIPTS}/${base}"
  py_abs="$(cd "$(dirname "${py}")" && pwd)/$(basename "${py}")"
  if [[ "${SYNC_MODE}" == "symlink" ]]; then
    ln -sf "${py_abs}" "${dest}"
  else
    cp -f "${py}" "${dest}"
  fi
done
shopt -u nullglob

if [[ "${INSTALL_BIN}" -eq 1 ]]; then
  mkdir -p "${HOME}/bin"
  bin_abs="$(cd "${REPO_ROOT}/bin" && pwd)"
  for f in rwe-common.sh rwe-run.sh rwe-publish; do
    if [[ "${SYNC_MODE}" == "symlink" ]]; then
      ln -sf "${bin_abs}/${f}" "${HOME}/bin/${f}"
    else
      cp -f "${REPO_ROOT}/bin/${f}" "${HOME}/bin/${f}"
    fi
  done
  chmod +x "${HOME}/bin/rwe-run.sh" "${HOME}/bin/rwe-publish"
fi

echo "reading-with-ears: synced (${SYNC_MODE}) → ${DEST_SCRIPTS} (+ skill)"
