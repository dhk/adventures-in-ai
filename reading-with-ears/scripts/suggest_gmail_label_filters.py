#!/usr/bin/env python3
"""
Suggest Gmail label-migration filters from newsletter sender registry.

Reads:
  reading-with-ears/data/newsletter_sender_registry.json

Outputs:
  - Top senders by score
  - Suggested Gmail filter query snippets
  - Optional full OR query for bulk testing in Gmail search
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[1] / "data" / "newsletter_sender_registry.json"
)


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "updated_at": None, "senders": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "updated_at": None, "senders": {}}
    if not isinstance(data, dict):
        return {"version": 1, "updated_at": None, "senders": {}}
    if not isinstance(data.get("senders"), dict):
        data["senders"] = {}
    return data


def sender_score(entry: dict[str, Any], preferred_category: str | None) -> float:
    count = int(entry.get("count", 0) or 0)
    categories = entry.get("categories", {}) if isinstance(entry.get("categories"), dict) else {}
    category_bonus = 0.0
    if preferred_category:
        category_bonus = float(categories.get(preferred_category, 0) or 0) * 0.5
    diversity_bonus = 0.2 * len([k for k, v in categories.items() if int(v or 0) > 0])
    return float(count) + category_bonus + diversity_bonus


def build_from_clause(entry: dict[str, Any], key: str) -> str:
    email = str(entry.get("email", "") or "").strip()
    name = str(entry.get("name", "") or "").strip()
    if email:
        return f"from:{email}"
    if name:
        # Quote sender names with spaces for Gmail query compatibility.
        if " " in name:
            return f'from:"{name}"'
        return f"from:{name}"
    return f'from:"{key}"'


def main() -> None:
    parser = argparse.ArgumentParser(description="Suggest Gmail label filters from newsletter sender registry")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="Path to sender registry JSON")
    parser.add_argument("--top", type=int, default=25, help="How many sender suggestions to print (default: 25)")
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Minimum seen count required for suggestions (default: 2)",
    )
    parser.add_argument(
        "--preferred-category",
        choices=["news", "think", "professional", "vital-signs"],
        default=None,
        help="Optional category preference to boost ranking",
    )
    parser.add_argument(
        "--emit-or-query",
        action="store_true",
        help="Also print one combined OR Gmail query for all suggested senders",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry).expanduser()
    data = load_registry(registry_path)
    senders = data.get("senders", {})
    if not senders:
        print(f"No senders found in: {registry_path}")
        return

    ranked: list[tuple[str, dict[str, Any], float]] = []
    for key, entry in senders.items():
        if not isinstance(entry, dict):
            continue
        count = int(entry.get("count", 0) or 0)
        if count < args.min_count:
            continue
        ranked.append((key, entry, sender_score(entry, args.preferred_category)))

    if not ranked:
        print("No senders match your min-count threshold.")
        return

    ranked.sort(key=lambda x: x[2], reverse=True)
    top = ranked[: max(args.top, 1)]

    print("Suggested Gmail label filters")
    print(f"Registry: {registry_path}")
    print(f"Updated:  {data.get('updated_at')}")
    print("")
    print("Use these in Gmail filter creation (Create filter -> From):")
    print("")

    clauses: list[str] = []
    for idx, (key, entry, score) in enumerate(top, start=1):
        name = str(entry.get("name", "") or "").strip()
        email = str(entry.get("email", "") or "").strip()
        count = int(entry.get("count", 0) or 0)
        categories = entry.get("categories", {}) if isinstance(entry.get("categories"), dict) else {}
        clause = build_from_clause(entry, key)
        clauses.append(clause)
        ident = email if email else (name if name else key)
        print(f"{idx:2d}. {ident}")
        print(f"    filter: {clause}")
        print(f"    count: {count}  categories: {categories}  score: {score:.1f}")

    if args.emit_or_query:
        print("")
        print("Combined OR query for Gmail search testing:")
        # Gmail accepts OR operator; wrapping each clause is robust with quoted names.
        or_query = " OR ".join(f"({c})" for c in clauses)
        print(or_query)


if __name__ == "__main__":
    main()

