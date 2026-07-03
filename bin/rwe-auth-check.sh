#!/usr/bin/env bash
# Audit Claude Code auth sources that break headless OAuth runs (rwe-run.sh,
# rwe-catchup.sh, rwe-weekly-audio). The daily/weekly-audio flows use
# `claude -p` with a claude.ai subscription — any ANTHROPIC_API_KEY or
# apiKeyHelper injected from settings files overrides OAuth and causes
# "Invalid API key · Fix external API key" even when the shell has nothing
# exported (env -u does not clear settings.json env blocks).
#
# Usage:
#   rwe-auth-check.sh              # print audit, exit 1 if blockers found
#   rwe-auth-check.sh --test-api   # also curl-test any keys found
#   rwe-auth-check.sh --doctor     # also run `claude doctor` if available
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${HERE}/rwe-common.sh"

TEST_API=0
RUN_DOCTOR=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --test-api) TEST_API=1; shift ;;
    --doctor)   RUN_DOCTOR=1; shift ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(rwe_repo_root "${HERE}")" || exit 1

export RWE_AUTH_TEST_API="${TEST_API}"
export RWE_AUTH_REPO_ROOT="${REPO_ROOT}"

python3 - <<'PY'
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ["RWE_AUTH_REPO_ROOT"])
TEST_API = os.environ.get("RWE_AUTH_TEST_API") == "1"

AUTH_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")
BLOCKER_ENV_KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

issues = []
notes = []


def mask_key(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return value[:2] + "…"
    return value[:4] + "…" + value[-4:]


def load_json(path: Path):
    if not path.is_file():
        return None, "not found"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"


def test_api_key(key: str, label: str) -> None:
    if not TEST_API or not key.strip():
        return
    try:
        proc = subprocess.run(
            [
                "curl", "-sS",
                "https://api.anthropic.com/v1/models",
                "-H", f"x-api-key: {key.strip()}",
                "-H", "anthropic-version: 2023-06-01",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        body = (proc.stdout or proc.stderr or "").strip()
        if "authentication_error" in body or "invalid x-api-key" in body:
            issues.append(f"{label}: Anthropic API rejects this key (authentication_error)")
        elif proc.returncode == 0 and '"data"' in body:
            notes.append(f"{label}: Anthropic API accepts this key")
        else:
            notes.append(f"{label}: API test inconclusive ({body[:120]})")
    except Exception as exc:  # noqa: BLE001
        notes.append(f"{label}: API test failed ({exc})")


def audit_env_block(data: dict, label: str) -> None:
    env = data.get("env")
    if not isinstance(env, dict) or not env:
        return
    keys = sorted(env.keys())
    print(f"  env keys: {', '.join(keys)}")
    for key in BLOCKER_ENV_KEYS:
        if key in env and str(env.get(key) or "").strip():
            val = str(env[key])
            issues.append(
                f"{label}: {key} is set in settings env block ({mask_key(val)}) — "
                "overrides OAuth in claude -p and causes auth failures when invalid"
            )
            test_api_key(val, f"{label} env.{key}")


def audit_file(path: Path, label: str) -> None:
    print(f"\n{label}")
    print(f"  path: {path}")
    data, err = load_json(path)
    if err:
        print(f"  status: {err}")
        if err != "not found":
            issues.append(f"{label}: {err}")
        return
    print("  status: present")
    audit_env_block(data, label)
    helper = data.get("apiKeyHelper")
    if helper:
        issues.append(
            f"{label}: apiKeyHelper is set ({helper!r}) — conflicts with OAuth; "
            "remove unless you intend API-key auth"
        )
        print(f"  apiKeyHelper: {helper}")


def audit_shell_env() -> None:
    print("\nShell environment (this process)")
    for key in AUTH_ENV_KEYS:
        val = os.environ.get(key, "")
        if val:
            print(f"  {key}: {mask_key(val)}")
            if key in BLOCKER_ENV_KEYS:
                issues.append(
                    f"Shell exports {key} ({mask_key(val)}) — scrub with env -u before claude -p"
                )
                test_api_key(val, f"shell {key}")
        else:
            print(f"  {key}: (unset)")


def audit_shell_profiles() -> None:
    print("\nShell startup files (grep ANTHROPIC_API_KEY)")
    pattern = re.compile(r"ANTHROPIC_API_KEY")
    found = False
    for rel in (".zshrc", ".zprofile", ".bash_profile", ".bashrc", ".profile"):
        path = HOME / rel
        if not path.is_file():
            continue
        hits = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if pattern.search(line) and not line.strip().startswith("#")
        ]
        if hits:
            found = True
            print(f"  {path}: {len(hits)} non-comment line(s)")
            for hit in hits[:3]:
                print(f"    {hit[:100]}")
            issues.append(
                f"{path} exports ANTHROPIC_API_KEY — remove or comment out for OAuth headless runs"
            )
    if not found:
        print("  (no ANTHROPIC_API_KEY exports found in common profile files)")


def audit_claude_json() -> None:
    path = HOME / ".claude.json"
    print("\n~/.claude.json (global config — distinct from ~/.claude/settings.json)")
    print(f"  path: {path}")
    data, err = load_json(path)
    if err:
        print(f"  status: {err}")
        return
    print("  status: present")
    env = data.get("env")
    if isinstance(env, dict) and env:
        print(f"  env keys: {', '.join(sorted(env.keys()))}")
        for key in BLOCKER_ENV_KEYS:
            if key in env and str(env.get(key) or "").strip():
                val = str(env[key])
                issues.append(
                    f"~/.claude.json env.{key} is set ({mask_key(val)}) — "
                    "Claude Code injects this into every session (settingsEnv/globalEnv)"
                )
                test_api_key(val, f"~/.claude.json env.{key}")
    helper = data.get("apiKeyHelper")
    if helper:
        issues.append(f"~/.claude.json apiKeyHelper is set ({helper!r})")
        print(f"  apiKeyHelper: {helper}")


# --- main audit ---
print("=== Claude Code auth audit for Reading with Ears headless runs ===")
print("Daily/weekly-audio flows expect claude.ai OAuth — not ANTHROPIC_API_KEY.")
print("The error 'Invalid API key · Fix external API key' is Claude Code auth,")
print("not Gmail or NotebookLM MCP (those show [MCP] errors in debug logs).")

audit_shell_env()
audit_claude_json()
audit_file(HOME / ".claude" / "settings.json", "Global settings (~/.claude/settings.json)")
audit_file(HOME / ".claude" / "settings.local.json", "Global local settings (~/.claude/settings.local.json)")
audit_file(REPO / ".claude" / "settings.json", "Project settings (.claude/settings.json)")
audit_file(REPO / ".claude" / "settings.local.json", "Project local settings (.claude/settings.local.json)")

managed = Path("/Library/Application Support/ClaudeCode/managed-settings.json")
audit_file(managed, "Managed settings (MDM)")

audit_shell_profiles()

print("\n=== Summary ===")
if notes:
    for n in notes:
        print(f"NOTE: {n}")

if issues:
    print(f"\n{len(issues)} blocker(s) found:\n")
    for i, item in enumerate(issues, 1):
        print(f"  {i}. {item}")
    print(
        "\nFix (OAuth headless — rwe-run / rwe-catchup / rwe-weekly-audio):\n"
        "  1. Remove ANTHROPIC_API_KEY from every settings env block above.\n"
        "  2. Remove or fix apiKeyHelper entries.\n"
        "  3. Run: claude doctor\n"
        "  4. Re-run: rwe-auth-check.sh --test-api --doctor\n"
        "  5. Retry: bin/rwe-catchup.sh --from YYYY-MM-DD --to YYYY-MM-DD\n"
        "\nTo remove a key from ~/.claude/settings.json:\n"
        "  jq 'del(.env.ANTHROPIC_API_KEY)' ~/.claude/settings.json > /tmp/s.json && mv /tmp/s.json ~/.claude/settings.json"
    )
    sys.exit(1)

print("\nNo OAuth blockers detected in audited sources.")
print("If claude -p still fails, run with --doctor and inspect the debug log for [MCP] lines.")
sys.exit(0)
PY

status=$?

if [[ "${RUN_DOCTOR}" -eq 1 ]] && command -v claude >/dev/null 2>&1; then
  echo ""
  echo "=== claude doctor ==="
  claude doctor || true
elif [[ "${RUN_DOCTOR}" -eq 1 ]]; then
  echo "NOTE: claude CLI not on PATH — skipping claude doctor"
fi

exit "${status}"
