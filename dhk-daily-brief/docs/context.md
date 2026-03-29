# Context — DHK Daily Brief

Where this project stands, and how it got here.

---

## The problem it started with

I read a lot of newsletters. Good ones — Noahpinion, The Dispatch, The Pragmatic Engineer, Axios, The Atlantic. But reading them at a desk competes with everything else that happens at a desk. Listening to them on a commute or a run doesn't compete with anything.

The question was: can the reading list become the podcast feed, automatically?

---

## How it evolved

**Phase 0 — Manual proof of concept**
Created NotebookLM notebooks by hand, added newsletter content, generated audio, downloaded, uploaded to Element.fm. Worked well. Too much friction to do daily.

**Phase 1 — Interactive Claude skill**
Built a Claude skill (`reading-list-builder`) that triages starred Gmail, routes emails to NotebookLM notebooks, generates audio, and downloads files. Run interactively via Claude.ai. Required confirming a triage table each time. Good for trust-building; not good for consistency.

**Phase 2 — Python upload script**
Separated the upload step into `daily_brief.py` — a Python script that finds today's notebooks, waits for audio readiness, downloads, converts M4A → MP3, and publishes to Element.fm. Could run headlessly.

**Phase 3 — Full automation**
Wired Phase 1 and Phase 2 together via `run-reading-list.sh`, scheduled via launchd at 6am. Added:
- Gmail label system replacing starred triage (labels applied by filter at receipt)
- MCP OAuth tokens registered at user scope for `claude -p` (non-interactive) compatibility
- Automation instruction appended to skill prompt to bypass the confirmation step
- Magic-byte MP3 validation before upload (NotebookLM emits M4A despite `.mp3` extension)
- Paginated Element.fm episode listing (API returns 10/page)
- Per-date manifest for full idempotency

---

## Current state (March 2026)

The pipeline runs unattended. On a day with labeled newsletters, it produces 2–3 published podcast episodes with no human involvement. The episodes are available in Apple Podcasts within minutes of the pipeline completing.

Known gaps:
- `nlm` authentication expires every few weeks — requires running `nlm login` to refresh
- The skill's triage table still appears in the log even in automated mode (cosmetic; doesn't block execution)
- No alerting when the pipeline fails — currently requires checking `~/logs/reading-list/YYYY-MM-DD.log`

---

## Design reference

For the full technical specification — phases, parameters, file locations, MCP tools — see [process-overview.md](../process-overview.md).

For the principles behind the design decisions, see [key-ideas.md](key-ideas.md).
