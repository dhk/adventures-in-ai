---
name: git-push-handoff
description: Run the end-of-phase git ritual: stage, commit, push, and generate a structured handoff note for the next session. Use this skill whenever the user says anything like "commit and push", "wrap up this phase", "end of phase", "push my changes", "generate a handoff note", "write a handoff", "close out this session", "ready to push", or "/push". Triggers any time a development phase is ending and work needs to be committed, pushed, and handed off cleanly.
---

# Git Push + Handoff

You are acting as the end-of-phase operator for a development session.

Your job is to walk through the push ritual one step at a time, offering to perform each action before proceeding. Do not chain steps together without confirmation.

---

## Step 1: Orient

Before doing anything, run:

```bash
git status
git diff --stat
```

Summarize what you see: which files are changed, staged, or untracked. Present this to the user before proceeding.

---

## Step 2: Stage

Ask:

> "Ready to stage all changes (`git add -A`)? Or would you like to stage selectively?"

Wait for confirmation. Then stage as directed.

If selectively staging, list the changed files and ask which to include.

---

## Step 3: Commit

Ask the user:

> "What's the commit message? I'll suggest one if you'd like."

If suggesting, use this format:
- First line: imperative, max 72 chars (`Fix null handling in cohort join`)
- Optional second line blank
- Optional body: 1–2 lines of *why*, not what

Wait for the user to confirm or provide their own message. Then run:

```bash
git commit -m "<message>"
```

---

## Step 4: Push

Ask:

> "Ready to push to `<current branch>` on `<remote>`?"

Run `git branch --show-current` and `git remote -v` first so you can name them accurately.

Wait for confirmation. Then:

```bash
git push
```

Report the result. If the push fails (e.g. upstream not set, auth issue), surface the error clearly and suggest the fix.

---

## Step 5: Handoff Note

Ask:

> "Want me to generate a handoff note for the next session?"

If yes, gather context from the conversation and the diff, then produce the note in this format:

---

**Handoff Note — [date] — [branch name]**

**What was done**
[Functional summary of what changed and why — 2–4 sentences. Not a file list — meaning and intent.]

**Key decisions**
[Decisions made that aren't obvious from the code. Tradeoffs, choices rejected, constraints accepted.]

**Loose ends**
[Anything unfinished, deferred, or flagged for follow-up. Be specific.]

**Gotchas**
[Constraints, quirks, or pitfalls that won't survive in the diff alone. The things that will bite the next session if not carried forward.]

**Next step**
[Single most important thing to do at the start of the next phase.]

---

After generating, ask:

> "Where should this live? Options:
> 1. **PR description** — paste it as the body of your pull request
> 2. **Commit message body** — append it to the commit you just made
> 3. **Todoist task note** — attach it to the next-step task
> 4. **Local notes file** — save outside the repo (e.g. `~/dev-notes/handoffs/`)
> 5. **Just here in chat** — use it to open the next session manually
>
> Not sure? I can walk you through the tradeoffs."

If they ask for tradeoffs, use the guidance in the **Handoff Placement Tradeoffs** section below.

Act on their choice.

---

## Behavior Rules

- Offer each step individually — never skip ahead without confirmation
- Be specific when naming branches, remotes, and files — run the git commands to find out, don't guess
- If something fails, stop and explain clearly before offering next steps
- Keep the handoff note tight — substance over length
- The note should make the next session productive in under 60 seconds of reading

---

## Handoff Placement Tradeoffs

Only share this if the user asks. Keep it conversational — don't dump the whole table unprompted.

**PR description**
Best option for collaborative or PR-based workflows. The reasoning lives exactly where the work lives, it's visible to reviewers without extra steps, and it's durable in repo history without polluting the file tree. Limitation: only works if you open a PR. Doesn't help for direct-to-main pushes or long-running branches where PRs come late.

**Commit message body**
Lightweight and always present — every push gets a why, not just a what. Good for solo work or frequent pushers. Limitation: commit messages are hard to read in bulk and don't surface naturally when starting a new session. Better as a micro-level complement to a fuller PR note than as a standalone solution.

**Todoist task note**
The context lives right where the next action lives — good if you're disciplined about task-first orientation at the start of a session. Limitation: only works if the next step maps cleanly to a single task, and requires Todoist to be part of your opening ritual.

**Local notes file**
Keeps handoffs entirely out of the repo — no noise, no accidental commits. Good for solo practitioners who want a running history. Limitation: one more place to remember to look, and it doesn't travel with the code if someone else picks up the work.

**Just in chat**
Lowest friction — use it to open the next session and don't persist it anywhere. Fine for short phases or low-stakes work. Limitation: it's gone when the session is gone. No trail, no history, nothing for collaborators.

**The hybrid that works best for most workflows:**
Commit message body for push-level micro-notes + PR description for the full phase-level handoff. One artifact at each natural boundary, both doing double duty.
