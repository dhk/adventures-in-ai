# Handoff — Install Guide

Handoff generates a self-contained context snapshot so you can continue
work in a new Claude Code session when you hit a repo scope wall. Instead
of losing thread mid-task, you get a paste-ready prompt that a fresh
session can receive and act on immediately — no clarifying questions.

## One-shot install

```bash
mkdir -p ~/.claude/skills/handoff && \
  curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/handoff/SKILL.md \
    -o ~/.claude/skills/handoff/SKILL.md
```

Claude Code picks up skills from `~/.claude/skills/` automatically.

## Manual install

1. Create the directory:
   ```bash
   mkdir -p ~/.claude/skills/handoff
   ```

2. Download the skill:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/handoff/SKILL.md \
     -o ~/.claude/skills/handoff/SKILL.md
   ```

3. Verify:
   ```bash
   ls -lh ~/.claude/skills/handoff/SKILL.md
   ```

## Usage

Trigger it in any Claude Code session when you need to hand off to a
different repo:

```
/handoff
/continue-in-new-session   # alias — same skill
```

The skill will:

1. Review the current conversation and git state
2. Produce a "Open this session" one-liner (which repo to open next)
3. Produce a fenced handoff prompt to paste as the first message in the
   new session — includes what's done, what's pending, exact next steps,
   and guard rails

## When to use it

- You're mid-task and realise you need to push to a repo that isn't in
  scope for the current session
- Context is getting long and you want a clean resume point
- You're handing work to another person or a scheduled agent

## Updating

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/handoff/SKILL.md \
  -o ~/.claude/skills/handoff/SKILL.md
```
