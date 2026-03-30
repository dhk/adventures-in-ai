# Multi-Feed Design & Migration Plan

**Status:** Show names confirmed — pending Element.fm show IDs  
**Goal:** Split DHK Daily Brief into one podcast per category, driven by a single human-editable feed config file.

---

## The three shows

| Show | Slug | Identity |
|---|---|---|
| **DHK: News Signal** | `news` | Cutting through noise to find what actually matters, from everywhere |
| **DHK: Thinking with Threads** | `think` | Pulling patterns from disparate ideas into something coherent |
| **DHK: Professional Stack** | `professional` | What's moving in your professional world, curated and current |

---

## Problem with the current design

All three episode types publish to one Element.fm show. This means:

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
- Audio focus prompt tuned to its editorial identity

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
      "show_name": "DHK: News Signal",
      "show_description": "Cutting through noise to find what actually matters, from everywhere.",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/news"],
      "notebook_category": "📰 News & Current Affairs",
      "notebook_emoji": "📰",
      "notebook_order": 1,
      "audio_focus_prompt": "This episode should run approximately 12 minutes. Your job is to find the signal — the things that actually matter — and lead with them. Open with the 2-3 most consequential developments across all sources: why do they matter, and what do they change? Then go deeper on each story in turn. Close by stepping back: what does today's news tell us about where things are heading? Cut noise aggressively. If it's process, not outcome — skip it."
    },
    {
      "slug": "think",
      "enabled": true,
      "show_name": "DHK: Thinking with Threads",
      "show_description": "Pulling patterns from disparate ideas into something coherent.",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/think"],
      "notebook_category": "🧠 Things to Think About",
      "notebook_emoji": "🧠",
      "notebook_order": 2,
      "audio_focus_prompt": "This episode should run approximately 12 minutes. Your job is to find the thread — the underlying pattern or tension that connects these ideas. Open by naming what the sources have in common, even if they seem unrelated on the surface. Then unpack each piece: what's the argument, what's the evidence, what's the implication? Close by pulling it together: what does this body of thinking, taken as a whole, suggest? Prioritize synthesis over summary. The listener already knows how to read — give them something they couldn't have gotten on their own."
    },
    {
      "slug": "professional",
      "enabled": true,
      "show_name": "DHK: Professional Stack",
      "show_description": "What's moving in your professional world, curated and current.",
      "elementfm_show_id": "TBD",
      "gmail_labels": ["newsletter/pro"],
      "notebook_category": "💼 Professional Reading",
      "notebook_emoji": "💼",
      "notebook_order": 3,
      "audio_focus_prompt": "This episode should run approximately 12 minutes. Your job is to surface what's moving — the shifts, launches, and decisions that matter for someone building and leading in tech. Open with the 2-3 most significant developments and why they change something. Then cover each piece: what happened, who it affects, what to watch for. Close with a practical frame: given everything in this episode, what should a thoughtful operator or builder be paying attention to this week? Be direct. Skip the context people already have."
    }
  ]
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `slug` | string | Identifier used in filenames (`YYYY-MM-DD-{slug}.mp3`) and manifest keys |
| `enabled` | bool | Set to `false` to skip without removing the entry |
| `show_name` | string | Full show name — used in logs, summaries, and Element.fm |
| `show_description` | string | One-line show description for Element.fm and Apple Podcasts |
| `elementfm_show_id` | string | Element.fm show UUID — determines which podcast episodes publish to |
| `gmail_labels` | string[] | Gmail labels whose emails feed this notebook (supports multiple) |
| `notebook_category` | string | Canonical NotebookLM notebook title suffix (emoji + text) |
| `notebook_emoji` | string | Emoji used as primary slug-matching signal for variant titles |
| `notebook_order` | int | `nn` suffix in notebook name (`reading-list-YYYY-MM-DD-{nn}`) |
| `audio_focus_prompt` | string | Per-show focus prompt sent to NotebookLM audio generation |

### Adding a new feed

Add an entry to `feeds.json`, create the Gmail label filter, and create the Element.fm show. No code changes required.

### Disabling a feed

Set `"enabled": false`. The skill skips the label, no notebook is created, no episode is published.

---

## Code changes required

### `podcast_config.py`
- Add `FeedConfig` dataclass (slug, show_name, elementfm_show_id, gmail_labels, notebook_emoji, audio_focus_prompt, etc.)
- Add `load_feeds()` → reads `~/.config/dhk-daily-brief/feeds.json`, returns `list[FeedConfig]`
- `category_title_to_slug()`: use `notebook_emoji` from loaded config as primary matching signal
- Remove hardcoded `CATEGORY_SLUGS` (or keep as fallback if config not found)

### `daily_brief.py`
- Replace hardcoded `WORKSPACE_ID`, `SHOW_ID`, `SLUGS_ALL` with values from `load_feeds()`
- `ElementFmClient` instantiated per feed using each feed's `elementfm_show_id`
- Upload loop: for each slug, look up feed → create client with feed's show ID → upload
- Manifest: structure unchanged (`episodes.{slug}.{...}`)

### `SKILL.md`
- Replace the single hardcoded `focus_prompt` in `studio_create` with a per-category lookup table
- Embed all three prompts in the skill, keyed by emoji (`📰`, `🧠`, `💼`)
- When creating a notebook for a category, use that category's prompt

### `elementfm_client.py`
- No changes needed — client already takes `show_id` as a parameter

---

## What doesn't change

- File naming: `YYYY-MM-DD-{slug}.mp3`
- Manifest format: `~/.local/state/dhk-daily-brief/manifest-YYYY-MM-DD.json`
- Notebook naming: `reading-list-YYYY-MM-DD-{nn} {emoji} {category}`
- `nlm` download and conversion
- launchd schedule and `run-reading-list.sh`

---

## Migration plan

### Step 1 — Create shows in Element.fm *(you)*
Create two new shows in the Element.fm UI:
- **DHK: Thinking with Threads**
- **DHK: Professional Stack**

Rename the existing "DHK Daily Brief" show to **DHK: News Signal** — this preserves existing episodes and Apple Podcasts subscribers for the news feed.

Capture the `elementfm_show_id` for all three shows (visible in the show URL or settings).

### Step 2 — Populate `feeds.json`
Replace the three `"TBD"` values with real show IDs and save to `~/.config/dhk-daily-brief/feeds.json`.

### Step 3 — Submit new shows to Apple Podcasts
Each Element.fm show has an RSS feed URL (Show Settings → Distribution).
Submit the two new shows at [podcasters.apple.com](https://podcasters.apple.com). Approval takes 24–48 hours — do this before the first live multi-feed run.

### Step 4 — Update code
Implement `FeedConfig` and `load_feeds()` in `podcast_config.py`. Update `daily_brief.py` to use per-feed show IDs. Update `SKILL.md` with per-category focus prompts.

### Step 5 — Test
```bash
daily-brief --dry-run
```
Verify each slug resolves to the correct show name and show ID.

### Step 6 — First live multi-feed run
```bash
daily-brief
```
Confirm all three episodes publish to their respective shows.

### Step 7 — Existing episodes
Old "DHK Daily Brief" episodes remain on News Signal's feed (reused show ID). No migration needed.

---

## Open questions

1. **Show IDs** — create shows in Element.fm and share the IDs to complete `feeds.json`
2. **Artwork** — shared template with a per-show accent color, or distinct art for each?
3. **Apple Podcasts descriptions** — use `show_description` from config, or write longer bios per show?
