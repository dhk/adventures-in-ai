#!/usr/bin/env bash
# Sync DHK Daily Brief skill + Python scripts from this repo to ~/.local/share/dhk-daily-brief/
# Optional: --install-bin copies bin/* wrappers to ~/bin/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIEF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BRIEF_ROOT}/.." && pwd)"

DEST_SKILL_ROOT="${HOME}/.local/share/dhk-daily-brief/skills/user/reading-list-builder"
DEST_SCRIPTS="${HOME}/.local/share/dhk-daily-brief/scripts"

mkdir -p "${DEST_SKILL_ROOT}" "${DEST_SCRIPTS}"

cp -f "${BRIEF_ROOT}/skills/user/reading-list-builder/SKILL.md" "${DEST_SKILL_ROOT}/SKILL.md"
cp -f "${BRIEF_ROOT}/scripts/"*.py "${DEST_SCRIPTS}/"

if [[ "${1:-}" == "--install-bin" ]]; then
  mkdir -p "${HOME}/bin"
  for f in dhk-common.sh run-reading-list.sh daily-brief; do
    cp -f "${REPO_ROOT}/bin/${f}" "${HOME}/bin/${f}"
  done
  chmod +x "${HOME}/bin/run-reading-list.sh" "${HOME}/bin/daily-brief"
fi
