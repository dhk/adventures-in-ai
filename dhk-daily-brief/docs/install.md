# Installation — DHK Daily Brief

---

## Prerequisites

- macOS (launchd required for scheduled runs)
- Python 3.10+
- [ffmpeg](https://ffmpeg.org): `brew install ffmpeg`
- [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli): `uv tool install notebooklm-mcp-cli`
- [Claude Code CLI](https://github.com/anthropics/claude-code): `npm install -g @anthropic-ai/claude-code`
- An [Element.fm](https://element.fm) account with a show created

---

## 1. Environment variables

Add to `~/.zshrc`:

```zsh
export CLAUDE_ELEMENT_FM_KEY='your-element-fm-api-key'
```

Reload: `source ~/.zshrc`

---

## 2. Config file

Create `~/.config/dhk-daily-brief/config.json`:

```json
{
  "audio_dir": "~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast",
  "audio_format": "mp3"
}
```

---

## 3. MCP authentication

Register Gmail and Todoist MCPs at user scope so they work in non-interactive (`-p`) mode:

```bash
claude mcp add --transport http --scope user gmail https://gmail.mcp.claude.com/mcp
claude mcp add --transport http --scope user todoist https://ai.todoist.net/mcp
```

Then open an interactive Claude Code session and authorize each connector via OAuth (browser flow, one-time per connector).

Authenticate the `nlm` CLI:

```bash
nlm login
```

---

## 4. Install shell wrappers

```bash
cp ~/Documents/dev/adventures-in-ai/dhk-daily-brief/scripts/*.py ~/.local/share/dhk-daily-brief/scripts/
mkdir -p ~/bin

# run-reading-list.sh — launchd entry point
cp ~/Documents/dev/adventures-in-ai/bin/run-reading-list.sh ~/bin/
chmod +x ~/bin/run-reading-list.sh

# daily-brief — ad-hoc Phase 2 wrapper
cp ~/Documents/dev/adventures-in-ai/bin/daily-brief ~/bin/
chmod +x ~/bin/daily-brief
```

Ensure `~/bin` is on your PATH in `~/.zshrc`:

```zsh
export PATH="$HOME/bin:$PATH"
```

---

## 5. Gmail label filters

Create three Gmail labels: `newsletter/news`, `newsletter/think`, `newsletter/pro`.

Add filters for each sender in [process-overview.md](../process-overview.md#newsletter-label-system) routing them to the appropriate label.

---

## 6. launchd (automated 6am run)

Install the launch agent:

```bash
cp ~/Documents/dev/adventures-in-ai/dhk-daily-brief/com.dhk.reading-list.plist \
   ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dhk.reading-list.plist
```

The agent runs `run-reading-list.sh` at 6:00am PT daily. Logs go to `~/logs/reading-list/YYYY-MM-DD.log`.

To run manually at any time:

```bash
run-reading-list.sh
```

---

## 7. Verify

```bash
# Check pipeline status for today
daily-brief --show-status

# Test Phase 2 without uploading
daily-brief --dry-run
```

---

## Updating

The launchd script syncs the skill and Python scripts from the repo at each run — no manual copy step needed after initial setup.

To update: pull the repo, then the next run picks up changes automatically.
