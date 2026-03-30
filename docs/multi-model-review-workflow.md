# Multi-Model Review: Workflow Reference

This document covers the architecture, design decisions, and extension patterns behind the `multi-model-review` skill. It's the companion to `SKILL.md` (which Claude reads) and `README.md` (quick start).

---

## Why multi-model review?

Single-model review has a structural problem: you're asking the same system that generated the content (or a system trained similarly) to evaluate it. The model shares blind spots with itself.

Multi-model review adds genuine diversity when:
- Models are trained on different data distributions
- Models have different RLHF tuning (what they're rewarded for)
- Models are prompted with different adversarial framings

The result isn't perfect — all frontier models share significant training overlap — but the divergence rate is meaningful. Expect Codex to catch things Claude misses roughly 20-30% of the time on technical content, and vice versa.

**The frame to hold:** multi-model review surfaces *questions to investigate*, not final verdicts. Two models agreeing doesn't mean they're right. Two models disagreeing is a flag, not a resolution.

---

## Architecture

```
Claude Code session
│
├── Claude (orchestrator)
│   ├── Reads SKILL.md at trigger time
│   ├── Runs its own review first (independent)
│   └── Calls Codex via MCP tool
│
└── Codex MCP server (subprocess)
    ├── Started by: npx codex mcp-server
    ├── Exposes: codex() — start session
    │           codex-reply() — continue thread
    └── Returns: full critique, thread ID for follow-up
```

Claude always reviews before calling Codex. Order matters: if Claude saw Codex's output first, it would anchor on it, defeating the independence that makes the comparison valuable.

---

## The four review modes

### Red Team (`/review-redteam`)
**Purpose:** Find failure modes before they find you.

Both models receive an adversarial prompt: find problems, not strengths. Each flags severity (High/Med/Low). The synthesis looks for consensus failures (confirmed risks) and divergent findings (model-specific blind spots).

Best used on: proposals with strong claims, architecture decisions, anything being presented to stakeholders.

### Steelman (`/review-steelman`)
**Purpose:** Find the strongest version of an idea before critiquing it.

Both models are asked to assume the proposal is directionally correct and identify: the core insight, ways to strengthen it, and the condition that makes it succeed. Useful before red teaming — if you can't steelman something, you don't understand it well enough to critique it.

Best used on: early-stage drafts, Substack pieces before publication, strategy memos.

### Debate (`/review-debate`)
**Purpose:** Stress-test a claim by running both sides.

Claude argues FOR. Codex argues AGAINST. Then one round of rebuttal each. The synthesis identifies what held under pressure and what didn't. This is the most expensive mode (4 calls total) but produces the sharpest output on contested claims.

Best used on: anything you're about to publish or present where someone will push back.

### Code Review (`/review-code`)
**Purpose:** Multi-pass technical review with division of labor.

Claude focuses on logic, edge cases, and maintainability. Codex focuses on security, performance, and production failures. The prompts are deliberately different to avoid both models reviewing the same surface.

Best used on: pre-commit review, PR review, code you're shipping to production.

---

## Signal vs. noise

The synthesis output is only as useful as your ability to read it correctly.

| What you see | What it means |
|---|---|
| Both models flag the same issue | Confirmed risk — address it |
| Only Claude flags something | Worth checking — may be Claude's training bias |
| Only Codex flags something | High value — this is why you called a second model |
| Both models validate | Weakest signal — shared blind spot is likely |
| Models disagree on severity | The crux — investigate before deciding |

**The most valuable output is always a Codex-only finding.** That's the thing Claude would have missed if you hadn't run this workflow.

---

## Prompting tips

**Force independence.** Don't show Claude what Codex said before Claude reviews. Don't show Codex what Claude said. The value collapses if one model anchors on the other.

**Force adversarial framing.** "Is this good?" produces validation. "What breaks first?" produces critique. The prompts in SKILL.md are engineered for the latter.

**Follow up if Codex validates.** If Codex's response reads like a compliment, use `codex-reply` immediately:
```
Assume the proposal is wrong. What breaks first?
```
This almost always produces a more useful response.

**Use the crux.** The synthesis surfaces THE CRUX — the single most important unresolved question. This is the thing to take to a human expert, not the full list of findings.

---

## Setup reference

### One-time setup

```bash
# Install Codex CLI
npm install -g @openai/codex

# Authenticate (pick one)
codex login                          # ChatGPT subscription
export OPENAI_API_KEY=your-key       # API key

# Register with Claude Code
claude mcp add codex -- npx codex mcp-server

# Verify
claude mcp list
```

### Per-project setup (optional)

Scope Codex to a specific project:

```bash
# In your project directory
claude mcp add codex --scope local -- npx codex mcp-server
```

### Verify end-to-end

In a Claude Code session:
```
Red team the following using both your own judgment and Codex via MCP:

PROPOSAL:
We should migrate our data pipeline from batch to real-time streaming using Kafka.
The migration can be completed in one sprint.
```

Expected: two distinct critiques, a synthesis, at least one Codex-only finding.

---

## Extending to more models

### PAL-MCP-Server (recommended next step)

PAL adds Gemini, GPT-4o, Grok, and others behind a single MCP interface:

```bash
git clone https://github.com/BeehiveInnovations/pal-mcp-server.git
cd pal-mcp-server
./run-server.sh   # auto-configures Claude Code
```

Once PAL is running, you can fan out to 3+ models in a single session. A `/review-consensus` workflow requiring 2/3 agreement before confirming an issue becomes practical.

### mcp-agent (for durable pipelines)

For automated review pipelines (e.g., review every Substack draft before publishing), `mcp-agent` provides orchestrator/evaluator patterns that persist across sessions:

```
pip install mcp-agent
```

See: https://github.com/lastmile-ai/mcp-agent

### OpenAI Agents SDK

Codex CLI can also be exposed to the OpenAI Agents SDK directly:

```python
async with MCPServerStdio(
    name="Codex CLI",
    params={"command": "npx", "args": ["-y", "codex", "mcp-server"]},
) as codex_mcp_server:
    # orchestrate multi-agent review workflows
```

See: https://developers.openai.com/codex/guides/agents-sdk

---

## Security note

Keep Codex CLI updated — a vulnerability (CVE-2025-61260) was patched in v0.23.0 that allowed malicious MCP configs in cloned repos to execute on startup. Run `npm update -g @openai/codex` to ensure you're on a safe version.

---

## Related files

```
adventures-in-ai/
├── dhk-daily-brief/
│   └── skills/user/
│       └── multi-model-review/
│           ├── SKILL.md       — Claude's runtime instructions
│           └── README.md      — Quick start
└── docs/
    └── multi-model-review-workflow.md   — this file
```
