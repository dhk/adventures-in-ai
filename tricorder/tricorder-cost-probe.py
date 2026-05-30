#!/usr/bin/env python3
"""
tricorder-cost-probe.py

Scan a GitHub repository, sample text files, count tokens, and report
projected Claude API costs across Haiku / Sonnet / Opus.

Usage:
    python tricorder-cost-probe.py owner/repo [--limit N] [--ext .py .md ...]
                                              [--output-csv FILE]

Requires: GITHUB_TOKEN env var, requests library.
"""

import argparse
import base64
import csv
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

# Claude API pricing per 1M tokens (input / output), as of 2025
MODELS = {
    "claude-haiku-4-5":  {"input": 0.80,  "output": 1.00,  "label": "Haiku 4.5"},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "label": "Sonnet 4.6"},
    "claude-opus-4-8":   {"input": 15.00, "output": 75.00, "label": "Opus 4.8"},
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".gz", ".tar", ".pdf",
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".parquet", ".db", ".sqlite", ".arrow",
    ".lock",  # package-lock.json, poetry.lock, etc.
}

SKIP_PATH_SEGMENTS = {
    "node_modules", ".git", "__pycache__", ".mypy_cache",
    "dist", "build", "venv", ".venv", "vendor", ".tox",
    "site-packages",
}


def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_tree(owner: str, repo: str, token: str) -> list[dict]:
    """Return flat blob list for the default branch (recursive tree walk)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    resp = requests.get(url, headers=gh_headers(token), timeout=30)
    if resp.status_code == 404:
        print(f"ERROR: repo {owner}/{repo} not found or not accessible.", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 401:
        print("ERROR: GitHub token invalid or expired.", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    data = resp.json()
    if data.get("truncated"):
        print(
            "WARNING: repo tree was truncated by GitHub (very large repo). "
            "Sample may not be representative.",
            file=sys.stderr,
        )
    return [item for item in data.get("tree", []) if item["type"] == "blob"]


def is_scannable(path: str, allowed_exts: list[str] | None) -> bool:
    p = Path(path)
    if p.suffix.lower() in SKIP_EXTENSIONS:
        return False
    if any(seg in SKIP_PATH_SEGMENTS for seg in p.parts):
        return False
    if allowed_exts and p.suffix.lower() not in allowed_exts:
        return False
    return True


def fetch_content(owner: str, repo: str, path: str, token: str) -> str | None:
    """Fetch raw text content of a file via GitHub contents API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(url, headers=gh_headers(token), timeout=30)
    if resp.status_code != 200:
        return None
    data = resp.json()
    encoding = data.get("encoding", "")
    raw = data.get("content", "")
    if encoding == "base64":
        try:
            return base64.b64decode(raw).decode("utf-8", errors="replace")
        except Exception:
            return None
    return raw if isinstance(raw, str) else None


def count_tokens(text: str) -> int:
    """Approximate token count at ~4 chars/token (GPT/Claude rule of thumb)."""
    return max(1, len(text) // 4)


def cost_usd(tokens: int, price_per_million: float) -> float:
    return tokens / 1_000_000 * price_per_million


def format_cost(usd: float) -> str:
    if usd < 0.0001:
        return f"${usd:.6f}"
    if usd < 0.01:
        return f"${usd:.4f}"
    return f"${usd:.2f}"


def print_table(rows: list[dict], total_tokens: int, total_bytes: int) -> None:
    print()
    print(f"  Sampled files : {len(rows)}")
    print(f"  Total tokens  : {total_tokens:,}")
    print(f"  Total bytes   : {total_bytes:,}")
    print()
    col_w = [14, 14, 18, 22]
    header = (
        f"  {'Model':<{col_w[0]}}  {'Input $/1M':<{col_w[1]}}"
        f"  {'Est. input cost':<{col_w[2]}}  {'Est. round-trip cost'}"
    )
    sep = "  " + "-" * (sum(col_w) + 8)
    print(header)
    print(sep)
    for model_id, info in MODELS.items():
        input_cost = cost_usd(total_tokens, info["input"])
        # Assume a 1:4 output-to-input token ratio as a conservative estimate
        output_tokens = total_tokens // 4
        round_trip = input_cost + cost_usd(output_tokens, info["output"])
        print(
            f"  {info['label']:<{col_w[0]}}  "
            f"  ${info['input']:.2f}/1M       "
            f"  {format_cost(input_cost):<{col_w[2]}}  "
            f"  {format_cost(round_trip)}"
        )
    print()


def write_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["path", "size_bytes", "tokens", "skipped"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Per-file breakdown saved to: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate Claude API costs for a GitHub repository."
    )
    parser.add_argument("repo", help="GitHub repo in owner/repo format")
    parser.add_argument(
        "--limit", type=int, default=20,
        help="Max number of files to sample (default: 20)"
    )
    parser.add_argument(
        "--ext", nargs="+", metavar="EXT",
        help="Only scan files with these extensions (e.g. --ext .py .md)"
    )
    parser.add_argument(
        "--output-csv", metavar="FILE",
        help="Write per-file breakdown to a CSV file"
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print(
            "ERROR: GITHUB_TOKEN is not set. "
            "Export it before running:\n  export GITHUB_TOKEN=ghp_...",
            file=sys.stderr,
        )
        sys.exit(1)

    if "/" not in args.repo:
        print("ERROR: repo must be in owner/repo format.", file=sys.stderr)
        sys.exit(1)

    owner, repo = args.repo.split("/", 1)
    allowed_exts = [e if e.startswith(".") else f".{e}" for e in args.ext] if args.ext else None

    print(f"\nTricorder scanning: {owner}/{repo}")
    print(f"  Limit          : {args.limit} files")
    if allowed_exts:
        print(f"  Extensions     : {', '.join(allowed_exts)}")
    print("  Fetching file tree…")

    blobs = get_tree(owner, repo, token)
    scannable = [b for b in blobs if is_scannable(b["path"], allowed_exts)]

    print(f"  Files in tree  : {len(blobs):,} total, {len(scannable):,} scannable")

    # Sample up to --limit files, spread across the tree alphabetically
    step = max(1, len(scannable) // args.limit) if len(scannable) > args.limit else 1
    sample = scannable[::step][: args.limit]

    print(f"  Sampling       : {len(sample)} files")
    print()

    rows: list[dict] = []
    total_tokens = 0
    total_bytes = 0
    skipped = 0

    for i, blob in enumerate(sample, 1):
        path = blob["path"]
        size = blob.get("size", 0)
        print(f"  [{i:>3}/{len(sample)}] {path}", end="  ", flush=True)

        content = fetch_content(owner, repo, path, token)
        if content is None:
            print("(skipped — binary or fetch failed)")
            rows.append({"path": path, "size_bytes": size, "tokens": 0, "skipped": True})
            skipped += 1
            time.sleep(0.1)
            continue

        tokens = count_tokens(content)
        byte_len = len(content.encode("utf-8"))
        total_tokens += tokens
        total_bytes += byte_len
        print(f"{tokens:,} tokens")
        rows.append({"path": path, "size_bytes": byte_len, "tokens": tokens, "skipped": False})
        # Be gentle with the API
        time.sleep(0.05)

    scanned = len(sample) - skipped
    print(f"\n  Scanned {scanned} files, skipped {skipped}.")

    if total_tokens == 0:
        print("\n  No tokens counted — all files were binary or unreadable.")
        return

    print_table(rows, total_tokens, total_bytes)

    # Extrapolate to full repo
    if len(scannable) > len(sample):
        ratio = len(scannable) / max(1, len(sample))
        est_full = int(total_tokens * ratio)
        print(
            f"  Full-repo extrapolation ({len(scannable):,} scannable files):\n"
            f"    ~{est_full:,} tokens  "
            f"(Sonnet input: {format_cost(cost_usd(est_full, 3.00))})\n"
        )

    if args.output_csv:
        write_csv(args.output_csv, rows)


if __name__ == "__main__":
    main()
