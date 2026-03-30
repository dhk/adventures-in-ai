# Multi-Model Review Workflow

This project uses Claude as the orchestrator and Codex as a second-opinion reviewer via MCP.
The goal is adversarial, multi-perspective critique — not validation.

---

## Setup

Codex must be registered as an MCP server before using these workflows:

```bash
claude mcp add codex -- npx codex mcp-server
claude mcp list  # verify it appears
```

---

## Review Workflows

### `/review-redteam <content>`

Run an adversarial red team review using both Claude and Codex.

**Steps:**
1. Claude performs a red team review of the content (find failure modes, not strengths)
2. Claude sends the same content to Codex via MCP with the red team prompt
3. Claude compares both critiques and identifies: consensus concerns, divergent findings, and the single most important issue

**Prompt to send Codex:**
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

**Output format:**
```
## Claude's Red Team
[findings]

## Codex's Red Team
[findings]

## Synthesis
CONSENSUS (both flagged): ...
DIVERGENT (only one flagged): ...
THE CRUX: [single most important issue]
RECOMMENDED NEXT STEP: [one concrete action]
```

---

### `/review-steelman <content>`

Generate the strongest possible version of a proposal, from two perspectives.

**Steps:**
1. Claude identifies the core insight and 3 ways to strengthen the proposal
2. Codex does the same independently
3. Claude synthesizes: where do they agree on what's valuable? Where do they diverge?

**Prompt to send Codex:**
```
You are a constructive strategic reviewer. Assume this proposal is directionally correct.

Identify:
- The core insight that makes this valuable (one sentence)
- 3 concrete ways to make this significantly stronger
- The single condition that, if true, makes this succeed

CONTENT:
{content}
```

---

### `/review-debate <content>`

Run a structured debate: Claude takes one position, Codex takes the opposite.

**Steps:**
1. Claude argues FOR the proposal (steelman it)
2. Claude sends to Codex with instruction to argue AGAINST (red team it)
3. Claude runs one rebuttal round from each side
4. Claude delivers a verdict: what changed, what held, what remains unresolved

**Prompt to send Codex:**
```
You are arguing AGAINST the following proposal. Find every reason it fails.
Be specific. Be relentless. Do not hedge.

PROPOSAL:
{content}
```

---

### `/review-code <file_or_description>`

Multi-model code review focused on correctness, security, and edge cases.

**Steps:**
1. Claude reviews for: logic errors, edge cases, maintainability
2. Codex reviews for: security issues, performance, missing error handling
3. Synthesize into a prioritized fix list

**Prompt to send Codex:**
```
Review the following code. Focus specifically on:
- Security vulnerabilities
- Performance bottlenecks  
- Missing error handling or edge cases
- Anything that would fail in production

Do not comment on style. Only flag substantive issues with severity (Critical/High/Med/Low).

CODE:
{code}
```

---

## How to Invoke Codex via MCP

In a Claude Code session, after Codex is registered as an MCP server:

```
Use the codex MCP tool to send the following prompt: [prompt]
Then return the full response so I can synthesize.
```

Claude will call the `codex` tool, get a response, and you can chain the `codex-reply` 
tool to continue the thread if you want a back-and-forth.

---

## Orchestration Tips

- **Claude orchestrates, Codex executes** — Claude decides when to call Codex and how to weight its response
- **Send identical content** — Both models should see the same input for the comparison to be meaningful
- **Force disagreement** — If both models agree immediately, prompt Codex explicitly: "What is Claude likely missing here?"
- **Watch for sycophancy** — If Codex validates without critique, re-prompt: "Assume the proposal is wrong. What breaks first?"
- **Context isolation** — Each Codex call starts fresh. If you want continuity, use `codex-reply` with the thread ID from the first response

---

## Signal vs. Noise

The value of multi-model review is in the *divergence*, not the consensus.

| Signal | Noise |
|--------|-------|
| Claude flags X, Codex doesn't | Both say "looks good" |
| Codex raises issue Claude missed | Both list the same generic risks |
| Models disagree on severity | One model echoes the other's framing |

When you see genuine divergence, that's the question worth investigating — not resolving automatically.

---

## Extending This Workflow

To add more models (Gemini, GPT-4o via PAL-MCP-Server):

1. Install PAL: `git clone https://github.com/BeehiveInnovations/pal-mcp-server && ./run-server.sh`
2. PAL auto-registers with Claude Code
3. Add a `/review-consensus` workflow that fans out to 3+ models and requires 2/3 agreement before flagging an issue as confirmed

---

## Proof of Concept Test

To verify the setup works end-to-end, run this in a Claude Code session:

```
Review the following proposal using both your own judgment and Codex via MCP.
Use the /review-redteam workflow.

PROPOSAL:
We should migrate our data pipeline from batch processing to real-time streaming 
using Kafka. This will reduce latency from hours to seconds and allow us to 
react to events as they happen. The migration can be completed in one sprint.
```

A working setup will return two distinct critiques and a synthesis.
The Codex critique should surface at least one thing Claude didn't lead with.
