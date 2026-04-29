# Tab Tamer

A Chrome extension for managing large numbers of open tabs. Sort, group, search, and bulk-close tabs from a clean popup — all within the current window.

---

## Features

- **Sort** tabs by title (A→Z / Z→A) or last visited — reorders tabs in Chrome's actual tab bar
- **Group by site** — creates native Chrome tab groups (color-coded in the tab bar) and reflects them visually in the popup
- **Ungroup** — disbands Chrome native groups; collapses view in the popup
- **Search** — real-time filter by title or URL
- **Multi-select & close** — checkbox selection with a "Close (N)" button; Select All / Deselect All

---

## Install (Developer Mode)

Chrome extensions can be loaded directly from a local folder without publishing to the store.

### 1. Download the extension

**Option A — Clone the repo:**
```bash
git clone https://github.com/dhk/adventures-in-ai.git
cd adventures-in-ai
git checkout tab-tamer
```

**Option B — Download the zip:**

Download [`tab-tamer.zip`](./tab-tamer.zip), then unzip it. You'll have a `tab-tamer/` folder.

### 2. Load in Chrome

1. Open Chrome and go to **`chrome://extensions`**
2. Toggle **Developer mode** on (top-right corner)
3. Click **Load unpacked**
4. Select the `tab-tamer/` folder
5. The Tab Tamer icon appears in your toolbar — click it to open the popup

> If you don't see the icon, click the puzzle-piece icon in the Chrome toolbar and pin Tab Tamer.

### 3. Updating

After pulling new changes:
1. Go to **`chrome://extensions`**
2. Find Tab Tamer and click the **↺ refresh** icon

---

## File Structure

```
tab-tamer/
  manifest.json     — extension config (Manifest V3)
  popup.html        — popup shell
  popup.css         — styles (DHK design system)
  popup.js          — all logic
  icons/
    icon16.png
    icon48.png
    icon128.png
  REQUIREMENTS.md   — feature spec and design decisions
  README.md         — this file
```

---

## Permissions Used

| Permission | Why |
|---|---|
| `tabs` | Read tab titles, URLs, last-accessed time; move and close tabs |
| `tabGroups` | Create, update, and disband Chrome native tab groups |

No host permissions — Tab Tamer never reads page content.

---

## Publishing (Chrome Web Store)

> Not yet published. This section tracks what's needed.

- [ ] Final icon assets (professional versions of 16, 48, 128px)
- [ ] Privacy policy page (required by Google)
- [ ] Store listing: name, description (132 chars), detailed description, category, screenshots (1280×800 or 640×400)
- [ ] One-time $5 developer registration at [chrome.google.com/webstore/devconsole](https://chrome.google.com/webstore/devconsole)
- [ ] Submit for review (typically 1–3 business days)

---

## Development Notes

Built with vanilla JS, HTML, and CSS — no build step, no dependencies. Load the folder directly in Chrome developer mode and changes take effect on popup re-open (no page reload needed for JS/CSS changes; hit ↺ in `chrome://extensions` for manifest changes).
