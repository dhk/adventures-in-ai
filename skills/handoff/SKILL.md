---
name: handoff
aliases:
  - continue-in-new-session
description: >
  Generates a self-contained handoff prompt for continuing the current
  session's work in a new Claude Code session — typically because the
  work requires a repo that isn't in scope for the current session.
  Produces a context snapshot + first-message you can paste directly
  into the new session. Use when you hit a scope wall and need to
  switch repos without losing thread.
---

# Continue in New Session

You are generating a **handoff prompt** — a self-contained message that
a new Claude Code session (with no memory of this conversation) can
receive and immediately act on, without asking clarifying questions.

## What to produce

Output two clearly labelled blocks:

---

### 1. Open this session

A one-liner telling the user which repo to open and how:

```
Open a Claude Code session scoped to: <owner>/<repo>
```

---

### 2. Paste this as your first message

A single fenced code block (so the user can copy it cleanly) containing
the complete handoff prompt. The prompt must be self-contained — the
receiving agent will have zero context from this conversation.

Structure the prompt as follows:

```
## Context handoff from previous session

**What we were working on:**
<1–3 sentences: the task, the goal, why it matters>

**What's already done:**
<bullet list of completed work — be specific: file paths, commit SHAs,
issue numbers, branch names, PR URLs. Anything the new agent needs to
not repeat work>

**The specific blocker that caused this handoff:**
<one sentence: which repo was needed but out of scope, and why>

**What to do next — in order:**
<numbered steps, specific enough that the agent can execute without
asking questions. Include exact file paths, target branches, source
locations, URL patterns, commit message formats>

**Files to carry over / reference:**
<list any files the new agent should read first, with their locations
and what they contain>

**Constraints and guard rails:**
<anything the new agent must NOT do — don't overwrite X, don't touch Y,
stay on branch Z, cap at N issues, etc.>

**Done when:**
<one sentence describing the terminal state — what "finished" looks like>
```

---

## How to gather the context

Before writing the handoff, review:

1. **This conversation** — what was asked, what was built, what's pending
2. **Git state** — run `git log --oneline -10` and `git status` in any
   repos that were modified; include branch names and recent commit SHAs
3. **Open issues / PRs** — note any issue numbers or PR URLs created
4. **Blocked work** — identify exactly what couldn't be done and why
   (usually: repo X not in session scope)

Do not ask the user for any of this — derive it from the conversation
and tool call history. If something is genuinely ambiguous, make the
most reasonable assumption and note it in the handoff.

---

## Standing defaults

These apply to every handoff unless the user has explicitly said otherwise
in this session:

- **Always work on a branch** — never commit directly to `main`. The branch
  name should follow the pattern `claude/<short-slug>`. Include the target
  branch name explicitly in the "What to do next" steps.

---

## Tone

The handoff prompt is written to another Claude instance, not to the
user. Be precise and dense — no pleasantries, no hedging. The receiving
agent should be able to read it once and start working.
