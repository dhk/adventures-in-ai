> **Archived** — 5 April 2026. The active architecture and principles live in **[`../current-design.md`](../current-design.md)**.

---

# Key Ideas — DHK Daily Brief (prior revision)

The design decisions behind the pipeline, and why they were made that way.

---

## 1. AI as workflow orchestrator, not chatbot

The Claude skill isn't a Q&A interface — it's an autonomous agent that runs a multi-step workflow: fetch, classify, create, generate, title, download. The prompt is a specification. The MCPs are the I/O layer. The output is real artifacts in real systems.

This is the model: **prompts as programs, MCP tools as system calls**.

---

## 2. Phase separation with clean handoffs

The pipeline splits at a natural seam:

- **Phase 1** (Claude skill) — everything that requires intelligence: triage, classification, content synthesis, audio generation
- **Phase 2** (Python script) — everything that's mechanical: polling, conversion, upload, publish

Each phase can run independently. Phase 2 doesn't need to know how Phase 1 worked — only that certain files exist and certain notebooks are named correctly. This makes debugging, retrying, and iterating on each phase cheap.

---

## 3. Idempotency as a first-class constraint

Every step that touches external state checks before acting:

- Manifest tracks what's been uploaded and published per date
- Downloads skip files that already exist
- Episode creation looks up by title before creating a new one
- launchd script exits immediately if all episodes are already published

Re-running is always safe. This matters because the pipeline runs unattended — failures need to be recoverable without human coordination.

---

## 4. Labels over stars

The original design triaged starred Gmail. Labels are better:

- **Intent is captured at receipt**, not at triage time
- **Zero manual work** — Gmail filters auto-label as newsletters arrive
- **Cleaner signal** — the label is explicit category intent, not just "I meant to read this"

The label system (`newsletter/news`, `newsletter/think`, `newsletter/pro`) maps directly onto the three podcast categories. The classifier still runs, but it has strong priors to work from.

---

## 5. launchd over cron

macOS launchd wakes the machine from sleep to run scheduled jobs. Cron doesn't. For a 6am pipeline on a laptop that might be sleeping, this is the difference between "runs every day" and "runs when I remember to leave it open."

launchd also handles TCC (Transparency, Consent, and Control) differently — the workaround of caching scripts to `~/.local` and `~/.config` exists because launchd agents can't read `~/Documents` without Full Disk Access.

---

## 6. Insight-first audio

The focus prompt isn't "summarize these newsletters." It's:

> *Open with the 3–5 most important ideas across all sources — give me the signal first. Then go deeper on each piece. Close with commentary and open questions. Prioritize insight over summary.*

This produces audio that's worth listening to, not a reading of bullet points. The goal is to match the density of a good podcast, not a book report.

---

## 7. Rich episode titles as memory

After audio is generated, the pipeline uses `notebook_describe` to get an AI summary of the content, then renames the artifact with:

- A NotebookLM-generated title (usually excellent)
- 3–5 punchy insight bullets
- A sources line

This becomes the episode description in the podcast feed. It also serves as a searchable record of what was in each episode — useful weeks later when you remember "there was something about SpaceX" but not which date.
