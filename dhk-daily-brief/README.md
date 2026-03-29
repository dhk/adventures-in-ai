# DHK Daily Brief

A personal AI pipeline that converts my morning newsletter reading list into published podcast episodes — automatically, every day.

**Newsletters in. Podcast out. No manual steps.**

---

## What it does

Each morning at 6am, the pipeline:

1. Fetches labeled newsletters from Gmail
2. Triages them into categories (news, ideas, professional)
3. Creates NotebookLM notebooks per category, loads the content, generates a ~12-minute audio overview
4. Converts and uploads each episode to Element.fm
5. Episodes appear in Apple Podcasts

The result: three episodes a day, insight-first, ready to listen during a commute — built entirely from what I was already reading anyway.

---

## Docs

| Document | Description |
|---|---|
| [Process Overview](process-overview.md) | End-to-end design: inputs, phases, parameters, file locations |
| [Key Ideas](docs/key-ideas.md) | Architectural principles and design decisions |
| [Context](docs/context.md) | Where this project stands and how it got here |
| [Installation](docs/install.md) | Prerequisites, environment setup, launchd configuration |

---

## Quick start

```bash
# Run the full pipeline for today
daily-brief

# Check what's been published
daily-brief --show-status

# Upload already-downloaded audio to Element.fm
daily-brief --upload-only

# Dry run — preview without doing anything
daily-brief --dry-run
```

---

## Part of Adventures in AI

This project lives in [adventures-in-ai](https://github.com/dhk/adventures-in-ai) — a collection of personal AI workflow experiments by DHK.
