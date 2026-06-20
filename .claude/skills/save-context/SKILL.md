---
name: save-context
description: >
  Save the current session's context to a committed file so it is automatically
  restored in every future session on any surface — web, desktop, CLI, or IDE.
  Use when the user says anything like "save context", "save my place",
  "checkpoint", "save session", "/save-context", "I want to pick this up later",
  "save before I switch surfaces", or "preserve context for the next session".
  NOT for committing code or generating handoff notes — use git-push-handoff for that.
---

# Save Context

You are the context preservation operator. Capture the essential state of this
session and write it to `.claude/context/current.md` — a committed file that
a `SessionStart` hook automatically injects into every new session on every
surface (web, desktop, CLI, VS Code, JetBrains).

---

## Step 1: Gather facts

Run these commands first so the context file contains objective state, not
just what you remember from conversation:

```bash
git branch --show-current
git status --short
git log --oneline -5
date +"%Y-%m-%d %H:%M %Z"
```

---

## Step 2: Answer these questions

Introspect the conversation and the command output above to fill in:

1. **Goal** — what is this session trying to accomplish? (1-2 sentences)
2. **Current state** — where are we right now? What's done, what's partial?
3. **Work in progress** — which files are actively being changed? Uncommitted work?
4. **Decisions made** — key choices and one-line rationale (skip anything obvious from the code)
5. **Next steps** — ordered, specific, actionable list
6. **Gotchas** — non-obvious constraints, broken dependencies, workarounds, or anything that will bite the next session if not written down
7. **Open questions** — unresolved blockers or pending decisions

---

## Step 3: Write `.claude/context/current.md`

Use exactly this format:

```markdown
# Session Context

**Saved:** <timestamp from date command>
**Branch:** <current branch>
**Surface:** <web | desktop | CLI | IDE — whichever this session is on>

## Goal
<1-2 sentences>

## Current State
<Where we are. Specific. "3 tests failing in src/auth.ts" not "tests need work".>

## Work in Progress
<Files being changed. Uncommitted work. Partial implementations.>

## Recent Decisions
- <decision>: <one-line rationale>
- <decision>: <one-line rationale>

## Next Steps
1. <Most important action>
2. <Second action>
3. <...>

## Gotchas
<Non-obvious constraints, workarounds, env quirks, or anything that will bite
the next session if they don't know about it. Skip if nothing qualifies.>

## Open Questions
<Unresolved decisions or blocked items. Skip if none.>
```

Keep the file under 150 lines. If detail is growing large, move it into a
linked file in `.claude/context/` and reference it here.

---

## Step 4: Save a timestamped snapshot

```bash
mkdir -p .claude/context/snapshots
SNAPSHOT=".claude/context/snapshots/$(date +%Y-%m-%d-%H%M%S).md"
cp .claude/context/current.md "$SNAPSHOT"
echo "Snapshot saved: $SNAPSHOT"
```

---

## Step 5: Commit and push

```bash
git add .claude/context/
git commit -m "context: checkpoint [$(date +%Y-%m-%d %H:%M %Z)]"
git push -u origin "$(git branch --show-current)"
```

If there are other uncommitted changes, ask:
> "You have uncommitted changes beyond the context file. Want to stage and
> commit those too before pushing?"

---

## Step 6: Confirm

Tell the user exactly:
- The context was saved to `.claude/context/current.md` and committed
- Every new session on **any surface** (web, desktop, CLI, VS Code, JetBrains)
  will automatically load this context via the `SessionStart` hook — no action needed
- Historical snapshots are in `.claude/context/snapshots/`
- To update: just run `/save-context` again at any time

---

## Rules

- Be specific and factual — vague context is worthless
- The goal: a new session with no conversation history should be productive
  in under 60 seconds of reading this file
- Don't pad — if a section is empty, omit it
- Commit every time — an uncommitted context file doesn't travel to web sessions
