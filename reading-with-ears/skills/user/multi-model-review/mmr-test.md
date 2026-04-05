# Proof of Concept Test

## Input

Paste this into a Claude Code session with the skill installed and Codex MCP configured:

```
Red team the following proposal using both your own judgment and Codex via MCP.

PROPOSAL:
We should migrate our data pipeline from batch processing to real-time streaming
using Kafka. This will reduce latency from hours to seconds and allow us to
react to events as they happen. The migration can be completed in one sprint.
```

A working setup returns two distinct critiques and a synthesis. Codex should surface at least one issue Claude didn't lead with — if both outputs are identical, something is wrong with the independence of the calls.

---

## Output

**Red Team: Kafka Migration Proposal**

Verdict: Do not approve as written.

The proposal is technology-first, underspecified, and contains a critical timeline misrepresentation. Below are the major failure vectors.

---

### 1. The "One Sprint" Estimate Is Not Credible

This is the most immediately dangerous claim. A safe streaming migration requires:

- Event schema and topic design
- Producer changes at source systems
- Consumer rewrites (not just re-wiring)
- Idempotency and deduplication logic
- Schema registry and versioning
- Shadow/dual-run validation
- Observability (lag, DLQ, end-to-end latency)
- Load, failure, and replay testing
- Cutover and rollback plan

A one-sprint estimate might describe a narrow pilot on one pipeline. Calling it a migration sets a false expectation with stakeholders that almost guarantees a rushed, correctness-unsafe cutover.

A credible timeline:
- Sprint 1: Discovery, use case selection, architecture decision, success metrics
- Sprints 2–3: Pilot with dual-run on one pipeline
- Beyond: Phased domain-by-domain rollout

---

### 2. Streaming Is a Systems Redesign, Not an Infrastructure Swap

Batch and streaming have fundamentally different semantics. Many batch transforms do not translate cleanly:

- Full-table aggregations
- Late-arriving corrections
- Cross-source joins with batch completeness assumptions
- Slowly changing dimensions
- Dedup over large time horizons

Moving to Kafka changes delivery semantics, failure handling, replay strategy, schema evolution, and downstream consumer behavior. Every one of these must be explicitly designed.

---

### 3. "Hours to Seconds" Is an Assumption, Not an Outcome

End-to-end latency may still be dominated by factors Kafka doesn't control:

- Source-system commit timing
- Upstream extraction frequency
- Stateful join/window processing time
- Downstream warehouse ingestion cadence
- Exactly-once overhead

The actual achievable SLA may be "near real-time with bounded lag" — not seconds. This distinction matters for downstream systems, SLAs promised to stakeholders, and whether the project delivers its stated value.

---

### 4. Key Failure Modes in Production

| Failure Mode | Root Cause |
|---|---|
| Duplicate processing | At-least-once delivery + non-idempotent consumers |
| Out-of-order events | Cross-partition ordering, late arrivals |
| Hot partitions | Poor key strategy, skewed entity distribution |
| Silent data loss | DLQ mishandling, retention expiry, sink failures |
| Side effects on replay | Re-triggering alerts, billing, external writes |
| State corruption | Windowed jobs failing during restart/recovery |
| Batch consumers broken | Downstream systems expecting complete snapshots |
| Scope creep on "exactly-once" | Kafka's guarantee doesn't extend to external sinks |

---

### 5. Missing Considerations

The proposal does not address:

- **Why Kafka specifically?** CDC, micro-batching, managed pub/sub, or reduced batch intervals may solve the latency problem with lower operational risk.
- **Which use cases actually need sub-minute freshness?** Real-time infrastructure is expensive — the business case needs to justify the cost and complexity.
- **Who owns Kafka operations?** Broker sizing, partition planning, ISR behavior, ACLs, upgrades, and on-call. If the team lacks streaming ops experience, production incidents are likely.
- **Schema governance.** No schema registry = producer changes silently break consumers.
- **Security/compliance.** If events carry PII, encryption, access control, and retention requirements must be designed up front.
- **Rollback strategy.** Once downstream systems consume event streams, reverting is complex — especially if side effects have already fired.

---

### 6. Questions That Must Be Answered Before Proceeding

1. What specific business outcome requires real-time data, and what freshness SLA is actually needed?
2. Which pipeline(s) are in scope first — all of them, or a pilot?
3. What percentage of current transforms are stateful, join-heavy, or batch-completeness-dependent?
4. What delivery guarantee is required, and where is idempotency enforced?
5. How will late, corrected, or deleted data be represented in the event model?
6. How will old and new pipelines run in parallel before cutover, and how will outputs be compared?
7. Who owns Kafka ops and on-call?
8. Why Kafka over lower-risk alternatives?

---

### Bottom Line

The direction (lower latency) may be correct. The approach (full Kafka migration in one sprint) is not. The proposal needs a narrowed scope, a phased timeline, explicit data semantics, and an operational ownership model before it is ready to approve.
