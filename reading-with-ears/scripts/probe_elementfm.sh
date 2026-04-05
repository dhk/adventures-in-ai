#!/bin/zsh
# element.fm API probe — for debugging/exploring the API
# Usage: ./probe_elementfm.sh

WORKSPACE_ID="b08a0951-94a4-441d-a446-81cc7950749c"
# Default probe show (news). Others: think=626ef543-… professional=01a6981c-… ai-everybody=4bd34c62-…
SHOW_ID="d5be8d71-5fe3-4d2c-b641-0cd7343e4e36"
KEY="${CLAUDE_ELEMENT_FM_KEY}"

if [[ -z "$KEY" ]]; then
  echo "❌ CLAUDE_ELEMENT_FM_KEY not set. Run: source ~/.zshrc"
  exit 1
fi

probe() {
  local label="$1" url="$2"; shift 2
  local http_code body
  body=$(curl -s -o /tmp/efm.txt -w "%{http_code}" "$@" "$url")
  http_code="$body"
  body=$(cat /tmp/efm.txt | python3 -m json.tool 2>/dev/null | head -5 || head -c 120 /tmp/efm.txt | tr -d '\n')
  printf "%-50s → %s  %.100s\n" "$label" "$http_code" "$body"
}

echo ""
echo "=== element.fm API Probe ==="
echo ""
probe "List shows"     "https://app.element.fm/api/workspaces/$WORKSPACE_ID/shows"                              -H "Authorization: Token $KEY"
probe "Show detail"    "https://app.element.fm/api/workspaces/$WORKSPACE_ID/shows/$SHOW_ID"                     -H "Authorization: Token $KEY"
probe "List episodes"  "https://app.element.fm/api/workspaces/$WORKSPACE_ID/shows/$SHOW_ID/episodes"            -H "Authorization: Token $KEY"
echo ""
