# Tab Tamer — Requirements & Design

> A Chrome extension for managing large numbers of open tabs.
> Target: Chrome Web Store (Manifest V3)

---

## Problem

Users with many open tabs have no built-in way to sort, organize, or bulk-close them. The default Chrome tab bar is first-in-first-out with no structure.

---

## Scope & Constraints

| Decision | Choice | Reason |
|---|---|---|
| UI surface | Popup (toolbar icon click) | Simple, always accessible, no new tab takeover |
| Tab scope | Current window only | Focused; avoids cross-window complexity |
| Tech stack | Vanilla JS + HTML + CSS | No build step; minimal footprint; easiest to ship |
| Manifest version | V3 | Current Chrome standard; required for new store submissions |

---

## Features

### 1. Tab List

- Popup opens and immediately displays all tabs in the current window
- Each tab row shows:
  - Favicon
  - Title (truncated with ellipsis if too long)
  - Domain (e.g. `github.com`)
  - Checkbox (left side) for selection
- Clicking a tab row (not the checkbox) **switches to that tab** and closes the popup
- Active/current tab is visually highlighted

---

### 2. Search / Filter

- Text input at the top of the popup
- Filters the tab list in real time by **title or URL** (case-insensitive)
- Clears with an × button or by deleting the text
- Grouping and sort order are preserved within filtered results

---

### 3. Sorting

Toolbar with two sort controls:

| Sort | Options |
|---|---|
| By Title | A→Z / Z→A |
| By Last Visited | Newest first / Oldest first |

- Selecting a sort **physically reorders the tabs in Chrome's tab bar** (not just the popup display)
- One active sort at a time; selecting a new axis clears the previous
- Toggle same button to reverse direction

---

### 4. Group / Ungroup by Website

#### Grouping
- "Group by Site" button in the toolbar
- Groups all tabs by domain (e.g. all `github.com` tabs together)
- Creates **Chrome native tab groups** (color-coded, visible in the tab bar)
- Also reflects the grouping **visually inside the popup** (collapsible sections per domain)
- Group label = domain name

#### Ungrouping
- "Ungroup All" button (visible when groups exist)
- **Disbands Chrome native tab groups** — tabs return to ungrouped in the tab bar
- In the popup, groups **collapse** (are hidden) without being re-expanded; flat list is restored

---

### 5. Select & Close

- Each tab has a **checkbox** on the left
- **"Select All" / "Deselect All"** toggle at the top of the list (or in toolbar)
- When one or more tabs are checked, a **"Close Selected (N)"** button appears
- Clicking it closes all checked tabs; button disappears if none remain selected
- Closing a tab removes it from the popup list immediately

---

## UI Layout

```
┌─────────────────────────────────────┐
│  🗂 Tab Tamer              [×close] │
├─────────────────────────────────────┤
│  🔍 Search tabs...          [×]     │
├─────────────────────────────────────┤
│  Sort: [Title ↑↓]  [Last Visited ↑↓] │
│  [Group by Site]  [Ungroup All]     │
├─────────────────────────────────────┤
│  ☐ Select All          [Close (N)] │
├─────────────────────────────────────┤
│  ▼ github.com (3)                   │
│    ☐ 🌐 Pull Request #42 — my-repo  │
│    ☐ 🌐 Issues · dhk/proj           │
│    ☐ 🌐 Actions · CI run            │
│  ▼ notion.so (2)                    │
│    ☐ 📄 Q2 Planning                 │
│    ☐ 📄 Team Docs                   │
│  ─ (ungrouped)                      │
│    ☐ 🌐 Google                      │
└─────────────────────────────────────┘
```

Popup width: ~400px. Max height: ~600px with scroll.

---

## Chrome APIs Required

| API | Use |
|---|---|
| `chrome.tabs` | Query, move, remove, update tabs |
| `chrome.tabGroups` | Create, update, ungroup native tab groups |
| `chrome.windows` | Get current window ID |

---

## Permissions (manifest.json)

```json
"permissions": ["tabs", "tabGroups"]
```

No host permissions needed (we don't read page content).

---

## File Structure

```
tab-tamer/
  manifest.json       — extension config
  popup.html          — popup shell
  popup.css           — styles
  popup.js            — all logic
  icons/
    icon16.png
    icon48.png
    icon128.png
```

---

## Out of Scope (v1)

- Multi-window tab management
- Keyboard shortcuts
- "Show all like this" filter shortcut
- Bookmarking selected tabs
- Moving tabs to a new window
- Muting tabs
- Syncing state across devices
- Any backend / server component

---

## Publishing Checklist (Chrome Web Store)

- [ ] Manifest V3 compliant
- [ ] Icons at 16×16, 48×48, 128×128
- [ ] Privacy policy (required for store submission)
- [ ] Store listing: screenshots, description, category
- [ ] One-time $5 developer registration fee
- [ ] Review turnaround: typically 1–3 business days

---

## Open Questions

None — all resolved in requirements interview (2026-04-29).
