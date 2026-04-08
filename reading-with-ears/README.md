# Reading with Ears

A personal AI pipeline that converts my morning newsletter reading list into published podcast episodes — automatically, every day.

**Newsletters in. Podcast out. No manual steps.**
<img width="1456" height="971" alt="image" src="https://github.com/user-attachments/assets/c9f0e309-1097-4f8f-8569-9a7536bf5188" />


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
| [Current Design](docs/current-design.md) | **Authoritative** architecture as of 5 Apr 2026 — repo ↔ machine, symlink deploy, OSS parameterization |
| [Process Overview](process-overview.md) | End-to-end operations: inputs, phases, parameters, file locations |
| [Key Ideas](docs/key-ideas.md) | Redirect to Current Design; archived principles in [`docs/archive/`](docs/archive/) |
| [Context](docs/context.md) | Where this project stands and how it got here |
| [Installation](docs/install.md) | Prerequisites, environment setup, launchd configuration |

---

## Quick start

```bash
# Run the full pipeline for today
rwe-publish

# Check what's been published
rwe-publish --show-status

# Upload already-downloaded audio to Element.fm
rwe-publish --upload-only

# Dry run — preview without doing anything
rwe-publish --dry-run
```

---

## Source repository

This pipeline is developed in [reading-with-ears](https://github.com/dhk/reading-with-ears) — the **reading-with-ears** monorepo (AI workflow experiments by DHK).
