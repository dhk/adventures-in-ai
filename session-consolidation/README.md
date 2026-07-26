# session-consolidation

Sweeps local Claude Code session transcripts (`~/.claude/projects/*/*.jsonl`),
clusters related ones, classifies each (active / completed / stale / orphaned /
superseded), and proposes a tiered action list — safe to archive, needs a
decision, keep as-is. Nothing is archived without explicit approval, and
"archive" always means *move*, never delete. See
[`docs/session-consolidation-design.md`](../docs/session-consolidation-design.md)
in the repo root for the full design.

## Layout

- `session_consolidation/core.py` — all logic (sweep/cluster/classify/propose/archive).
  No dependencies beyond the standard library.
- `session_consolidation/cli.py` — CLI, imports `core.py` directly. No server needed.
- `session_consolidation/mcp_server.py` — MCP server wrapping the same core
  functions as tools, for any MCP host (Claude Desktop, another agent, or this
  Claude Code skill via MCP instead of shelling out). Requires the `mcp` package.
- `web/viewer.html` — static, dependency-free viewer. Open it directly or drop
  a report JSON onto the page; no server process.
- `tests/test_core.py` — pytest suite over `core.py`.
- `../skills/user/session-consolidation/SKILL.md` — the Claude Code skill,
  shells out to the CLI.

## CLI usage

```bash
cd session-consolidation
python3 -m session_consolidation.cli report --since 30d --out report.json
```

Prints a human-readable tiered summary to stderr and writes the full JSON to
`report.json` (drop that file onto `web/viewer.html` to browse it visually).

Archiving is always a separate, explicit step:

```bash
# dry run -- shows what would move, moves nothing
python3 -m session_consolidation.cli archive --report report.json --approve-tier safe_to_archive

# actually move the safe-to-archive sessions (reversible: they land under ~/.claude/projects-archive/)
python3 -m session_consolidation.cli archive --report report.json --approve-tier safe_to_archive --yes

# approve specific sessions individually (works for any tier, e.g. needs_a_decision after you've looked)
python3 -m session_consolidation.cli archive --report report.json --approve <session_id> --yes
```

Bulk-approval (`--approve-tier`) only accepts `safe_to_archive` — sessions in
`needs_a_decision` must be approved one at a time via `--approve <id>`.

## MCP server (optional)

Only needed if something other than this CLI should call the same logic —
Claude Desktop, another agent, etc. Requires the `mcp` package:

```bash
pip install -r requirements.txt
claude mcp add session-consolidation -- python3 -m session_consolidation.mcp_server
```

Exposes `sweep_sessions`, `propose_actions`, and `archive_sessions` as MCP tools.

## Running tests

```bash
pip install pytest
python3 -m pytest session-consolidation/tests/
```
