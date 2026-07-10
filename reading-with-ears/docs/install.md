# Installation — Reading with Ears

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
export RWE_REPO="$HOME/Documents/dev/reading-with-ears"
```

---

## 2. Config file

Create `~/.config/reading-with-ears/config.json`. Copy [config/config.example.json](../config/config.example.json) and edit paths.

- `audio_dir` / `audio_format` — where Phase 2 writes and reads podcast files.
- `repo_root` — absolute or `~`-expanded path to your **reading-with-ears** clone (parent of `reading-with-ears/`). Required if you install `rwe-run.sh` and `rwe-publish` into `~/bin` and do **not** set `RWE_REPO`.
- `sync_mode` — **`"symlink"` (default in [config.example.json](../config/config.example.json))** or `"copy"`. **Symlink** points `~/.local/share/reading-with-ears/` and (with `--install-bin`) `~/bin` at the clone, so **`git pull` is usually enough** — no sync required after every merge unless links broke or you added new files and need new symlinks. **Copy** if the clone path moves often or you want isolated snapshots. Override: `RWE_SYNC_MODE=copy` or `install-local.sh --copy`. With no config file, `install-local.sh` still defaults to **symlink** (repo policy).

**Element.fm per-show IDs:** Optional `~/.config/reading-with-ears/feeds.json` — if missing, Phase 2 uses the bundled [config/feeds.json](../config/feeds.json) (`workspace_id` + each enabled feed’s `elementfm_show_id`). Each daily slug uploads to its own show.

**Architecture (repo as source of truth, MCP email notes, symlink policy):** [docs/current-design.md](current-design.md).


---

## Migrating from DHK Daily Brief (`dhk-daily-brief`)

If you used the old names and paths:

- Move `~/.config/dhk-daily-brief/` to `~/.config/reading-with-ears/` (copy `config.json` and `feeds.json`).
- Run [`install-local.sh`](../scripts/install-local.sh) with `--install-bin` so `~/.local/share/reading-with-ears/` and `~/bin` match this repo.
- Move `~/.local/state/dhk-daily-brief/` to `~/.local/state/reading-with-ears/` (keep existing `manifest-*.json` files).
- Remove obsolete `~/bin` entries: `run-reading-list.sh`, `daily-brief`, `dhk-common.sh`.
- `launchctl unload ~/Library/LaunchAgents/com.dhk.reading-list.plist` if loaded, then install [`com.dhk.reading-with-ears.plist`](../com.dhk.reading-with-ears.plist) as in section 7.
- Use `RWE_REPO`, `RWE_SYNC_MODE`, and `RWE_AUDIO_DIR` instead of `DHK_DAILY_BRIEF_*`.
- Logs: `~/logs/reading-with-ears/` (was `~/logs/reading-list/`).


---

## 3. MCP authentication

Register the Gmail MCP at user scope so it works in non-interactive (`-p`) mode:

```bash
claude mcp add --transport http --scope user gmail https://gmail.mcp.claude.com/mcp
```

Then open an interactive Claude Code session and authorize each connector via OAuth (browser flow, one-time per connector).

Authenticate the `nlm` CLI:

```bash
nlm login
```

### Claude Code auth for headless runs (`rwe-run`, `rwe-catchup`, `rwe-weekly-audio`)

These scripts invoke `claude -p` with your **claude.ai subscription (OAuth)**. They scrub
`ANTHROPIC_API_KEY` from the shell, but Claude Code also reads keys from settings files —
`~/.claude/settings.json` (global) and `~/.claude.json` (config) are **different files**.

If catch-up fails immediately with `Invalid API key · Fix external API key`, run:

```bash
bin/rwe-auth-check.sh --test-api --doctor
```

Remove any `ANTHROPIC_API_KEY` from settings `env` blocks and any `apiKeyHelper` entries.
That error is Claude Code auth, not Gmail or NotebookLM MCP (MCP failures appear as `[MCP]`
lines in `~/logs/reading-with-ears/catchup-debug-*.log`).

Headless runs also require an active **claude.ai OAuth session** (`claude /login`). The
scripts scrub your shell API key with `env -u`; without OAuth you will see
`Not logged in · Please run /login`.

---

## 4. Install shell wrappers

From your clone root (the directory that contains `reading-with-ears/` and `bin/`):

```bash
REPO="$HOME/Documents/dev/reading-with-ears"   # adjust if needed

# One-time: deploy skill + Python to ~/.local/share (symlinks into clone by default)
"$REPO/reading-with-ears/scripts/install-local.sh"

mkdir -p "$HOME/bin"
"$REPO/reading-with-ears/scripts/install-local.sh" --install-bin
```

`--install-bin` installs `bin/rwe-common.sh`, `bin/rwe-run.sh`, and `bin/rwe-publish` into `~/bin/` as **symlinks into the clone** unless `sync_mode` / env / `--copy` requests copy mode. Marks the two entry scripts executable.

For **copy** mode instead, set `"sync_mode": "copy"` in `config.json` or run:

```bash
"$REPO/reading-with-ears/scripts/install-local.sh" --install-bin --copy
```

Ensure `~/bin` is on your PATH in `~/.zshrc`:

```zsh
export PATH="$HOME/bin:$PATH"
```

---

## 5. Git hooks (optional)

To refresh `~/.local/share/reading-with-ears/` after every `git pull` or branch checkout **without** waiting for the next launchd run:

```bash
cd /path/to/reading-with-ears
git config core.hooksPath .githooks
```

Hooks run [`reading-with-ears/scripts/install-local.sh`](../scripts/install-local.sh) (no `--install-bin`). Optional with **symlink** mode: rewires links after new scripts or renames. Mode follows `sync_mode` in `config.json`.

---

## 6. Gmail label filters

Create three Gmail labels: `newsletter/news`, `newsletter/think`, `newsletter/pro`.

Add filters for each sender in [process-overview.md](../process-overview.md#newsletter-label-system) routing them to the appropriate label.

---

## 7. launchd (automated 6am local time)

The plist template uses `StartCalendarInterval` at **6:00** in the Mac’s **system timezone**. For 6am Pacific, set the machine timezone to `America/Los_Angeles` (or adjust the hour in the plist).

Install the launch agent (substitute your home directory into log paths):

```bash
REPO="$HOME/Documents/dev/reading-with-ears"
sed "s|__HOME__|${HOME}|g" "$REPO/reading-with-ears/com.dhk.reading-with-ears.plist" \
  > "$HOME/Library/LaunchAgents/com.dhk.reading-with-ears.plist"
launchctl load "$HOME/Library/LaunchAgents/com.dhk.reading-with-ears.plist"
```

The agent runs `$HOME/bin/rwe-run.sh`. Per-run logs: `~/logs/reading-with-ears/YYYY-MM-DD.log`. launchd stdout/stderr: `~/logs/reading-with-ears/launchd.log`.

To run manually at any time:

```bash
rwe-run.sh
```

---

## 8. Verify

**Configuration (Python, ffmpeg, uv, nlm, Claude CLI, `~/.config`, MCP, optional `.cursor/mcp.json`):** from the directory that contains `reading-with-ears/` (repo root), run:

```bash
REPO_ROOT="$HOME/Documents/dev/adventures-in-ai"   # your clone
"$REPO_ROOT/reading-with-ears/scripts/verify-reading-with-ears-setup.sh"
```

- **`--apply`** — install missing tools where possible, `chmod` `bin/rwe-*.sh`, and run `install-local.sh --install-bin`.
- **`--features=a,b,c`** or env **`RWE_VERIFY_FEATURES`** — run only selected groups: `toolchain`, `notebooklm`, `claude`, `repo`, `user_config`, `elementfm`, `permissions`, `sync`, `mcp`, `cursor`, or `all` (default).

**Pipeline (today’s audio / upload):**

```bash
# Check pipeline status for today
rwe-publish --show-status

# Test Phase 2 without uploading
rwe-publish --dry-run
```

---

## Updating

**Symlink mode (default):** After **`git pull`**, the code under `~/.local/share/reading-with-ears/` already **is** the repo (via symlinks). You **do not** need to run `install-local.sh` every time. Run it (or the git hook) if you **add a new `scripts/*.py`** file, rename paths, or a symlink broke.

`rwe-run.sh` still runs `install-local.sh` at the start of each run — harmless for symlink mode (refreshes links); it **does** matter for **copy** mode so scheduled runs pick up new bytes.

**Copy mode:** Run `install-local.sh` after each `git pull`, or rely on that first step inside `rwe-run.sh`.

If you switch bin layout or mode, re-run `install-local.sh --install-bin`.
