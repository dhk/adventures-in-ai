#!/bin/bash
# Auto-restore saved session context into every new session.
# Works on all surfaces: web, desktop, CLI, VS Code, JetBrains.

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CONTEXT_FILE="$REPO_ROOT/.claude/context/current.md"

if [ ! -f "$CONTEXT_FILE" ]; then
  exit 0
fi

CONTEXT=$(cat "$CONTEXT_FILE")
LAST_SAVE=$(grep -m1 "^\*\*Saved:" "$CONTEXT_FILE" | sed 's/\*\*Saved:\*\* //' || echo "unknown")

jq -n \
  --arg context "$CONTEXT" \
  --arg last_save "$LAST_SAVE" \
  '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: ("**Restored session context** (saved: " + $last_save + ")\n\nRun `/save-context` at any time to update it.\n\n---\n\n" + $context)
    }
  }'
