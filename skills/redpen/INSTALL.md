# Red Pen — Install Guide

Red Pen is a multi-agent codebase auditor. It reads your repos like Bill Gates
used to read Microsoft source code — every file, every pattern, everything that
shouldn't be there gets marked up and handed back with a fix attached.

## One-shot install (recommended)

```bash
mkdir -p ~/.claude/skills/redpen && \
  curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/redpen/SKILL.md \
    -o ~/.claude/skills/redpen/SKILL.md
```

That's it. Claude Code picks up skills from `~/.claude/skills/` automatically.

## Manual install

1. Create the directory:
   ```bash
   mkdir -p ~/.claude/skills/redpen
   ```

2. Download the skill file:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/redpen/SKILL.md \
     -o ~/.claude/skills/redpen/SKILL.md
   ```

3. Verify it landed:
   ```bash
   ls -lh ~/.claude/skills/redpen/SKILL.md
   ```

## Usage

Once installed, trigger it in any Claude Code session:

```
/redpen                          # audit current repo, all domains
/redpen payments-api dashboard   # audit specific repos
/redpen --domain sql,security    # restrict to specific domains
/redpen --depth deep             # full file reads instead of pattern scan
/redpen --tickets                # file GitHub issues for medium+ findings
/redpen --pr                     # open draft PRs for mechanical fixes
/redpen --fix                    # apply critical/high fixes in current repo
```

## What it does

1. **Surveys** every repo in scope — languages, frameworks, file counts
2. **Classifies** files into domains: SQL, UX, API, security, testing, tooling, docs, perf
3. **Spawns parallel domain agents** — one specialist per domain, running simultaneously
4. **Cross-pollinates** — flags patterns present in one repo and missing from another
5. **Synthesises** a ranked findings report with severity and one-sentence fixes
6. **Files tickets** (with `--tickets`) — GitHub issues assigned by git blame
7. **Opens draft PRs** (with `--pr`) — for mechanical fixes only, never security findings

## Requirements

- Claude Code with agent/sub-agent support
- GitHub MCP (`mcp__github__*`) connected — required for `--tickets` and `--pr`
- Read access to the repos you want to audit

## Updating

To get the latest version:

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/adventures-in-ai/main/skills/redpen/SKILL.md \
  -o ~/.claude/skills/redpen/SKILL.md
```
