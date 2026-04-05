---
name: multi-model-review
description: >
  Orchestrates a multi-model review workflow using Claude as orchestrator and Codex
  (via MCP) as a second-opinion reviewer. Produces adversarial, constructive, or
  debate-style critiques with a synthesis that highlights where the models diverge —
  which is where the real signal is. Use this skill whenever the user says anything
  like "review this with Codex", "get a second opinion", "red team this", "have Codex
  critique this", "multi-model review", "ask Codex what it thinks", "steelman this
  proposal", "debate this", or "review this code with another model". Triggers any
  time the user wants two AI perspectives on a proposal, draft, design, or codebase.
compatibility: "Requires: Codex registered as MCP server (claude mcp add codex -- npx codex mcp-server)"
---

# Multi-Model Review

Uses Claude as orchestrator and Codex as a second-opinion reviewer via MCP.
The value is in the *divergence* — where models disagree is where you should investigate.

---

## Prerequisites

Codex must be registered as an MCP server. Verify with:
```
claude mcp list
```

If `codex` is not listed, ask the user to run:
```bash
claude mcp add codex -- npx codex mcp-server
```

---

## Choosing a Workflow

Ask the user which review mode they want, or infer from context:

| Mode | Use when |
|------|----------|
| `/review-redteam` | Proposal, plan, design doc — find what breaks |
| `/review-steelman` | Draft or idea — find the strongest version |
| `/review-debate` | Claim or argument — stress-test both sides |
| `/review-code` | Code — correctness, security, edge cases |

If unclear, default to `/review-redteam`.

---

## Step 1: Run Both Reviews in Parallel

Call the Codex MCP tool AND complete Claude's own review at the same time.
Do NOT wait for Codex before forming your own view — parallel execution preserves independence.
Do NOT show the user anything until both reviews are complete.

### Red Team prompt (Claude's own)
Find at least 5 failure modes. Label each High / Med / Low severity.
Format:
```
[HIGH] <finding title>
Why it fails: ...
Consequence if ignored: ...
```
End with: "Top 3 things that must be addressed before proceeding:"

### Steelman prompt (Claude's own)
Identify: core insight (one sentence), 3 ways to strengthen, the single condition
that makes this succeed.

### Debate prompt (Claude's own)
Argue FOR the proposal — steelman it as strongly as possible.

### Code Review prompt (Claude's own)
Focus on: logic errors, edge cases, maintainability. Do not comment on style.

---

## Step 2: Codex Prompt (runs in parallel with Step 1)

Call the `codex` MCP tool with the appropriate prompt below.
Pass the original content verbatim — do not summarize or pre-process it.

### Red Team prompt for Codex
```
You are an adversarial reviewer. Your job is to find problems, not validate.

For the following content, identify:
- At least 5 specific failure modes or weaknesses (label each High/Med/Low severity)
- Unstated assumptions that could break this
- The single most critical issue that must be addressed

Do not praise or validate. Only critique.

CONTENT:
{content}
```

### Steelman prompt for Codex
```
You are a constructive strategic reviewer. Assume this proposal is directionally correct.

Identify:
- The core insight that makes this valuable (one sentence)
- 3 concrete ways to make this significantly stronger
- The single condition that, if true, makes this succeed

CONTENT:
{content}
```

### Debate prompt for Codex
```
You are arguing AGAINST the following proposal. Find every reason it fails.
Be specific. Be relentless. Do not hedge.

PROPOSAL:
{content}
```

### Code Review prompt for Codex
```
Review the following code. Focus specifically on:
- Security vulnerabilities
- Performance bottlenecks
- Missing error handling or edge cases
- Anything that would fail in production

Do not comment on style. Only flag substantive issues with severity (Critical/High/Med/Low).

CODE:
{content}
```

If Codex validates without critique, follow up via `codex-reply` with:
```
Assume the proposal is wrong. What breaks first?
```

---

## Step 3: Show Raw Outputs, Then Synthesize

**CRITICAL: Always show both raw reviews separately before synthesizing.**
Do not collapse them into a single pre-synthesized response. The user needs to see
what each model contributed independently — that visibility is the whole point.

Output in this exact order:

```
## Claude's [Mode] Review
[Claude's full findings, unmerged]

---

## Codex's [Mode] Review
[Codex's full findings, verbatim or closely paraphrased — do not filter]

---

## Synthesis

CONSENSUS (both flagged):
- ...

DIVERGENT — Claude only:
- ...

DIVERGENT — Codex only:
- ...

THE CRUX: [the single most important unresolved question]

RECOMMENDED NEXT STEP: [one concrete action]
```

The DIVERGENT — Codex only section is the highest-value output. If it is empty,
something went wrong — re-prompt Codex with "What did Claude likely miss?"

### Signal vs. Noise

| Signal | Noise |
|--------|-------|
| Claude flags X, Codex doesn't | Both say "looks good" |
| Codex raises issue Claude missed | Both list the same generic risks |
| Models disagree on severity | One model echoes the other's framing |

Two models agreeing does not mean they are right — it may mean they share a blind spot.
Genuine divergence is what to investigate.

---

## Edge Cases

- **Codex MCP not available**: Tell user to run `claude mcp add codex -- npx codex mcp-server` and restart the session
- **Codex validates without critique**: Follow up with the "Assume the proposal is wrong" prompt via `codex-reply`
- **Models fully agree**: Note the consensus but flag that shared training data may explain agreement; suggest a human domain expert review
- **Content too long for single call**: Summarize to key claims before sending to Codex; note the truncation in the synthesis
- **No mode specified**: Default to red team and confirm with user before proceeding
