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

Optional: pin the repo root for `~/bin` wrappers (see section 4):

```zsh
export DHK_DAILY_BRIEF_REPO="$HOME/Documents/dev/adventures-in-ai"
```

---

## 2. Config file

Create `~/.config/dhk-daily-brief/config.json`. Copy [config/config.example.json](../config/config.example.json) and edit paths.

- `audio_dir` / `audio_format` — where Phase 2 writes and reads podcast files.
- `repo_root` — absolute or `~`-expanded path to your **adventures-in-ai** clone (parent of `dhk-daily-brief/`). Required if you install `run-reading-list.sh` and `daily-brief` into `~/bin` and do **not** set `DHK_DAILY_BRIEF_REPO`.

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

From your clone root (the directory that contains `dhk-daily-brief/` and `bin/`):

```bash
REPO="$HOME/Documents/dev/adventures-in-ai"   # adjust if needed

# One-time: deploy skill + Python to ~/.local/share (also done automatically each launchd run)
"$REPO/dhk-daily-brief/scripts/sync-to-local.sh"

mkdir -p "$HOME/bin"
"$REPO/dhk-daily-brief/scripts/sync-to-local.sh" --install-bin
```

`--install-bin` copies `bin/dhk-common.sh`, `bin/run-reading-list.sh`, and `bin/daily-brief` into `~/bin/` and marks the two entry scripts executable.

Ensure `~/bin` is on your PATH in `~/.zshrc`:

```zsh
export PATH="$HOME/bin:$PATH"
```

---

## 5. Git hooks (optional)

To refresh `~/.local/share/dhk-daily-brief/` after every `git pull` or branch checkout **without** waiting for the next launchd run:

```bash
cd /path/to/adventures-in-ai
git config core.hooksPath .githooks
```

Hooks run [`dhk-daily-brief/scripts/sync-to-local.sh`](../scripts/sync-to-local.sh) (no `--install-bin`).

---

## 6. Gmail label filters

Create three Gmail labels: `newsletter/news`, `newsletter/think`, `newsletter/pro`.

Add filters for each sender in [process-overview.md](../process-overview.md#newsletter-label-system) routing them to the appropriate label.

---

## 7. launchd (automated 6am local time)

The plist template uses `StartCalendarInterval` at **6:00** in the Mac’s **system timezone**. For 6am Pacific, set the machine timezone to `America/Los_Angeles` (or adjust the hour in the plist).

Install the launch agent (substitute your home directory into log paths):

```bash
REPO="$HOME/Documents/dev/adventures-in-ai"
sed "s|__HOME__|${HOME}|g" "$REPO/dhk-daily-brief/com.dhk.reading-list.plist" \
  > "$HOME/Library/LaunchAgents/com.dhk.reading-list.plist"
launchctl load "$HOME/Library/LaunchAgents/com.dhk.reading-list.plist"
```

The agent runs `$HOME/bin/run-reading-list.sh`. Per-run logs: `~/logs/reading-list/YYYY-MM-DD.log`. launchd stdout/stderr: `~/logs/reading-list/launchd.log`.

To run manually at any time:

```bash
run-reading-list.sh
```

---

## 8. Verify

```bash
# Check pipeline status for today
daily-brief --show-status

# Test Phase 2 without uploading
daily-brief --dry-run
```

---

## Updating

`run-reading-list.sh` runs [`dhk-daily-brief/scripts/sync-to-local.sh`](../scripts/sync-to-local.sh) at the start of every scheduled (and manual) run, so the live skill and Python under `~/.local/share/dhk-daily-brief/` stay aligned with your clone.

After `git pull`, either rely on that sync on the next run, use the git hooks (section 5), or run `dhk-daily-brief/scripts/sync-to-local.sh` once by hand.

If you change the bin scripts, re-run `sync-to-local.sh --install-bin` to refresh `~/bin/`.
