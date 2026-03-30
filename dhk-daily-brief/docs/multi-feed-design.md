# Multi-Feed Design & Migration Plan

**Status:** Draft — pending show names from DHK  
**Goal:** Split DHK Daily Brief into one podcast per category, driven by a single human-editable feed config file.

---

## Problem with the current design

All three episode types (news, think, professional) publish to one Element.fm show. This means:

- Subscribers get everything whether they want it or not
- The show can't have a focused identity or description
- Category-specific artwork, descriptions, and Apple Podcasts metadata are impossible
- Adding or removing a category requires code changes

---

## Target architecture

Each feed is an independent podcast with its own:
- Element.fm show ID
- Apple Podcasts listing
- Artwork and description
- Gmail label(s) that feed it
- NotebookLM notebook naming convention
- Audio focus prompt (optional per-feed override)

Everything about a feed lives in one config file. No feed-specific logic in code.

---

## Feed config schema

**Location:** `~/.config/dhk-daily-brief/feeds.json`

```json
{
  "workspace_id": "b08a0951-94a4-441d-a446-81cc7950749c",
  "audio_dir": "~/Library/Mobile Documents/com~apple~CloudDocs/Personal Podcast",
  "audio_format": "mp3",
  "feeds": [
    {
      "slug": "news",
      "enabled": true,
      "show_name": "TBD — e.g. The Morning Read",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/news"],
      "notebook_category": "📰 News & Current Affairs",
      "notebook_emoji": "📰",
      "notebook_order": 1,
      "audio_focus_prompt": null
    },
    {
      "slug": "think",
      "enabled": true,
      "show_name": "TBD — e.g. Signal",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/think"],
      "notebook_category": "🧠 Things to Think About",
      "notebook_emoji": "🧠",
      "notebook_order": 2,
      "audio_focus_prompt": null
    },
    {
      "slug": "professional",
      "enabled": true,
      "show_name": "TBD — e.g. The Stack",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/pro"],
      "notebook_category": "💼 Professional Reading",
      "notebook_emoji": "💼",
      "notebook_order": 3,
      "audio_focus_prompt": null
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `slug` | string | Identifier used in filenames (`YYYY-MM-DD-{slug}.mp3`) and manifest keys |
| `enabled` | bool | Set to `false` to skip without removing the entry |
| `show_name` | string | Human label — used in logs and summaries |
| `elementfm_show_id` | string | Element.fm show UUID — determines which podcast episodes publish to |
| `gmail_labels` | string[] | Gmail labels whose emails feed this notebook (supports multiple) |
| `notebook_category` | string | Canonical NotebookLM notebook title suffix (emoji + text) |
| `notebook_emoji` | string | Emoji used as primary slug-matching signal for variant titles |
| `notebook_order` | int | `nn` suffix in notebook name (`reading-list-YYYY-MM-DD-{nn}`) |
| `audio_focus_prompt` | string\|null | Per-feed focus prompt override; falls back to global default if null |

### Adding a new feed

Add an entry to `feeds.json`, create the Gmail label filter, and create the Element.fm show. No code changes required.

### Disabling a feed

Set `"enabled": false`. The skill skips the label, no notebook is created, no episode is published.

---

## Code changes required

### `podcast_config.py`
- Add `load_feeds()` → reads `~/.config/dhk-daily-brief/feeds.json`, returns list of feed dicts
- Remove hardcoded `CATEGORY_SLUGS` dict (or keep as fallback if config not found)
- `category_title_to_slug()`: use `notebook_emoji` from config as primary matching signal
- `category_title_to_slug()`: use `notebook_category` from config for exact matching

### `daily_brief.py`
- Replace `WORKSPACE_ID`, `SHOW_ID`, `SLUGS_ALL` with values loaded from config
- `ElementFmClient` instantiated once per feed (each has its own `show_id`)
- Upload loop: for each slug, look up `elementfm_show_id` from config → create client → upload
- Manifest: structure unchanged (`episodes.{slug}.{...}`) — slug is still the key

### `SKILL.md`
- Newsletter label table already in skill; pull `gmail_labels` per feed into the table
- `notebook_category` names come from config; skill currently hardcodes these
- Phase 1 impact is minimal — the skill creates notebooks named by category; the mapping is already emoji-driven

### `elementfm_client.py`
- No changes needed — client already takes `show_id` as a parameter

---

## What doesn't change

- File naming: `YYYY-MM-DD-{slug}.mp3` — unchanged
- Manifest format: `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json` — unchanged
- Notebook naming convention: `reading-list-YYYY-MM-DD-{nn} {emoji} {category}` — unchanged
- `nlm` download and conversion — unchanged
- launchd schedule and `run-reading-list.sh` — unchanged

---

## Migration plan

### Step 1 — Name the shows (you)
Decide on show names and descriptions for each of the three feeds. Create them in Element.fm (or reuse the existing show for one of them). Capture the `show_id` for each.

### Step 2 — Create `feeds.json`
Populate the config with real `show_id` values. Keep the existing single-show `show_id` for whichever feed inherits it (to preserve existing episodes and Apple Podcasts subscription).

### Step 3 — Submit new shows to Apple Podcasts
Each new Element.fm show generates an RSS feed URL. Submit via [podcasters.apple.com](https://podcasters.apple.com). Approval takes 24–48 hours — do this before flipping to multi-feed.

### Step 4 — Update code
Implement the `load_feeds()` config reader and update `daily_brief.py` to use it. Keep the current hardcoded values as fallback so `--show-status` still works during the transition.

### Step 5 — Test with `--dry-run`
```bash
daily-brief --dry-run --date 2026-03-27
```
Verify each slug resolves to the correct show name and show ID.

### Step 6 — First live multi-feed run
```bash
daily-brief --date today
```
Confirm all three episodes publish to their respective shows.

### Step 7 — Handle existing episodes (optional)
The existing "DHK Daily Brief" episodes (the unified show) can stay as-is — they're already published and indexed. No need to migrate or delete them. Subscribers to the original show will continue to see past episodes; new episodes will appear in the per-category shows.

---

## Open questions

1. **Show names** — what are the three shows called? (needed to create Element.fm shows and submit to Apple Podcasts)
2. **Shared show** — does one of the three feeds inherit the existing "DHK Daily Brief" show ID? If so, which one? (keeps existing subscribers)
3. **Artwork** — does each show get distinct artwork, or shared artwork with a category badge?
4. **`audio_focus_prompt`** — should any feed get a distinct focus prompt, or keep the shared 12-minute insight-first prompt for all three?
