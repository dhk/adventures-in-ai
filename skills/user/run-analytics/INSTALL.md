# Run Analytics — Install Guide

Analytics study meta-skill. Interviews you to define the problem, verifies
tool connections, and writes the allow-list to `settings.json` before a
single line of analysis runs. Also has a discovery mode that crawls your
session history and skill definitions to build a default allow-list without
needing an active study.

## One-shot install

```bash
mkdir -p ~/.claude/skills/run-analytics && \
  curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/user/run-analytics/SKILL.md \
    -o ~/.claude/skills/run-analytics/SKILL.md
```

Claude Code picks up skills from `~/.claude/skills/` automatically.

## Manual install

```bash
mkdir -p ~/.claude/skills/run-analytics
curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/user/run-analytics/SKILL.md \
  -o ~/.claude/skills/run-analytics/SKILL.md
ls -lh ~/.claude/skills/run-analytics/SKILL.md
```

## Usage

```
/run-analytics                    # standard mode — interview + setup + analysis
/run-analytics --discover         # discover tools from session history (last 30 days)
/run-analytics --discover 7d      # discovery with a 7-day window
/run-analytics --discover 90d     # 90-day window
/run-analytics --discover all     # all available history
```

## What it does

**Standard mode:**
1. Interviews you (one message, six questions) to define the problem statement
2. Identifies the tool stack — BigQuery, Python, MCPs, shell, web fetch, etc.
3. Verifies each tool is connected and working before analysis starts
4. Curates an allow-list (Tier 1 safe reads / Tier 2 consequential reads /
   Tier 3 mutations) and writes approved rules to `settings.json`
5. Hands off with a crisp study brief, then runs the analysis immediately

**Discovery mode:**
1. Checks for local session history (`~/.claude/projects/`) — skips transcript
   crawl gracefully in cloud/ephemeral environments
2. Crawls session transcripts to count tool calls by name and Bash binary
3. Reads all `SKILL.md` files in the repo to extract declared tool dependencies
4. Scans `CLAUDE.md` and `.claude/` for context-implied tool needs
5. Presents a merged, tiered candidate list (no invented scoring — raw signals)
6. Writes approved rules to global (`~/.claude/settings.json`) and/or project
   (`.claude/settings.json`) settings

## Updating

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/user/run-analytics/SKILL.md \
  -o ~/.claude/skills/run-analytics/SKILL.md
```
