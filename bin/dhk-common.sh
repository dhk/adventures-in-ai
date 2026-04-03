# Shared helpers for DHK Daily Brief bin scripts.
# shellcheck shell=bash

# Resolve adventures-in-ai repo root (directory that contains dhk-daily-brief/).
# Precedence: DHK_DAILY_BRIEF_REPO → ~/.config/dhk-daily-brief/config.json repo_root
# → caller lives in-repo at bin/ (parent is repo root).
dhk_daily_brief_repo_root() {
  local caller_bin_dir="${1:?caller bin dir}"

  if [[ -n "${DHK_DAILY_BRIEF_REPO:-}" ]]; then
    (cd "${DHK_DAILY_BRIEF_REPO}" && pwd)
    return 0
  fi

  local from_cfg
  from_cfg="$(
    python3 -c "
import json, os
from pathlib import Path
p = Path.home() / '.config' / 'dhk-daily-brief' / 'config.json'
if not p.is_file():
    print('', end='')
    raise SystemExit(0)
d = json.loads(p.read_text(encoding='utf-8'))
r = d.get('repo_root') or ''
print(os.path.expanduser(str(r).strip()), end='')
"
  )" || true
  if [[ -n "${from_cfg}" && -f "${from_cfg}/dhk-daily-brief/scripts/sync-to-local.sh" ]]; then
    (cd "${from_cfg}" && pwd)
    return 0
  fi

  caller_bin_dir="$(cd "${caller_bin_dir}" && pwd)"
  if [[ -f "${caller_bin_dir}/../dhk-daily-brief/scripts/sync-to-local.sh" ]]; then
    (cd "${caller_bin_dir}/.." && pwd)
    return 0
  fi

  echo "dhk-daily-brief: set DHK_DAILY_BRIEF_REPO or repo_root in ~/.config/dhk-daily-brief/config.json (see docs/install.md)." >&2
  return 1
}
