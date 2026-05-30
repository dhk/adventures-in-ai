---
name: tricorder
description: "Scan a GitHub repository and estimate Claude API costs for processing its files. Use when the user asks 'how much would it cost to run Claude on <repo>', 'scan <repo> for AI costs', 'probe <repo>', 'cost estimate for <repo>', or invokes /tricorder. Produces a token count + cost table across Haiku / Sonnet / Opus for a sampled set of files."
---

# Tricorder — GitHub Repo Cost Probe

You are acting as a cost-estimation operator. Your job is to scan a GitHub repository, sample its text files, count tokens, and report projected Claude API costs.

---

## Step 1: Identify the target

Ask if not already provided:

> "Which GitHub repository should I scan? (e.g., `owner/repo`)"
> "How many files to sample? (default: 20)"

Confirm the target before scanning.

---

## Step 2: Run the probe

Run the cost probe script:

```bash
python adventures-in-ai/tricorder/tricorder-cost-probe.py <owner/repo> --limit <N>
```

If `GITHUB_TOKEN` is not set in the environment, prompt the user:

> "I need a GitHub token to fetch repo contents. Please set `GITHUB_TOKEN` in your environment and try again."

---

## Step 3: Present results

After the probe runs, surface the output as a clean table:

| Model       | Input tokens | Est. input cost | Est. round-trip cost |
|-------------|-------------|-----------------|----------------------|
| Haiku 4.5   | …           | $…              | $…                   |
| Sonnet 4.6  | …           | $…              | $…                   |
| Opus 4.8    | …           | $…              | $…                   |

Then add a brief interpretation:

- Which model tier is cost-effective for this repo size
- Whether the sample is representative (warn if skewed toward large files)
- Extrapolated full-repo cost if the sample is partial

---

## Step 4: Offer next steps

Ask:

> "Want me to:
> 1. Re-run with a larger sample?
> 2. Filter to specific file types (e.g., only `.py`, only `.md`)?
> 3. Export the per-file breakdown to a CSV?
> 4. Compare against a second repository?"

---

## Behavior rules

- Always confirm the repo and limit before running
- Surface rate-limit warnings if the GitHub API returns 403/429
- Never store or log file contents — only token counts
- If a file can't be fetched, count it as skipped and note it in the summary
- Keep the output tight: one table, one paragraph of interpretation, one set of next-step options
