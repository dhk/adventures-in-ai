#!/usr/bin/env python3
"""
Tidy Element.fm shows: normalize episode titles (drop legacy "reading list - " and
NotebookLM-style labels) and move episodes to the show that matches their category
(all enabled slugs in feeds.json, e.g. news / think / professional / vital-signs).

Uses the same API + feeds.json mapping as publish_episodes.py.

  export CLAUDE_ELEMENT_FM_KEY=…   # see docs/install.md

  python3 tidy_elementfm_shows.py              # dry-run
  python3 tidy_elementfm_shows.py --apply      # execute
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional

from elementfm_client import ElementFmClient, ElementFmConfig
from podcast_config import (
    elementfm_base_url,
    elementfm_episode_description,
    enabled_slugs_ordered,
    load_feeds_publish_config,
)


TITLE_RE = re.compile(
    r"^reading\s+list\s*-\s*(?P<slug>[a-z0-9_-]+)\s*-\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$",
    re.IGNORECASE,
)

DAILY_NEWS_RE = re.compile(r"^Daily\s+News\s+(?P<date>\d{4}-\d{2}-\d{2})\s*$", re.IGNORECASE)

NOTEBOOK_DATE_RE = re.compile(
    r"—\s*(?P<mon>[A-Za-z]{3,9})\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\s*$"
)


def clean_title(slug: str, date: str) -> str:
    return f"{slug} - {date}"


def _parse_us_short_date(mon: str, day: str, year: str) -> Optional[str]:
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(f"{mon} {int(day)}, {year}", fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def slug_date_from_title(title: str) -> Optional[tuple[str, str]]:
    raw = (title or "").strip()
    m = TITLE_RE.match(raw)
    if m:
        return m.group("slug").lower(), m.group("date")

    m2 = DAILY_NEWS_RE.match(raw)
    if m2:
        return "news", m2.group("date")

    m3 = NOTEBOOK_DATE_RE.search(raw)
    if m3:
        date_iso = _parse_us_short_date(m3.group("mon"), m3.group("day"), m3.group("year"))
        if not date_iso:
            return None
        if "Professional Reading" in raw:
            return "professional", date_iso
        if "Healthcare Reading" in raw:
            return "vital-signs", date_iso
        if "Things to Think About" in raw:
            return "think", date_iso
        if "News & Current Affairs" in raw:
            return "news", date_iso
        return None

    return None


def api_request(
    api_key: str,
    method: str,
    url: str,
    *,
    data: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    headers = {"Authorization": f"Token {api_key}"}
    body: bytes | None = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return {}
            parsed = json.loads(raw.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")[:800]
        return {"error": f"HTTP {e.code}: {msg}"}


def try_move_episode(
    api_key: str,
    workspace_id: str,
    from_show_id: str,
    episode_id: str,
    to_show_id: str,
) -> dict[str, Any]:
    base = f"https://app.element.fm/api/workspaces/{workspace_id}/shows/{from_show_id}/episodes/{episode_id}"
    attempts: list[dict[str, Any]] = [
        {"show": to_show_id},
        {"show_id": to_show_id},
        {"podcast_show": to_show_id},
        {"podcast_show_id": to_show_id},
    ]
    last: dict[str, Any] = {}
    for payload in attempts:
        last = api_request(api_key, "PATCH", base.rstrip("/") + "/", data=payload)
        if "error" not in last:
            return last
    return last


def client_for_show(api_key: str, workspace_id: str, show_id: str) -> ElementFmClient:
    return ElementFmClient(
        ElementFmConfig(
            api_key=api_key,
            workspace_id=workspace_id,
            show_id=show_id,
            base_url=elementfm_base_url(workspace_id=workspace_id, show_id=show_id),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Tidy Element.fm titles and show placement.")
    parser.add_argument("--apply", action="store_true", help="Perform PATCH/move calls (default is dry-run)")
    args = parser.parse_args()
    dry = not args.apply

    api_key = (os.environ.get("CLAUDE_ELEMENT_FM_KEY") or "").strip()
    if not api_key:
        print("CLAUDE_ELEMENT_FM_KEY is not set.", file=sys.stderr)
        return 1

    workspace_id, slug_to_show = load_feeds_publish_config()
    feed_slugs = [s for s in enabled_slugs_ordered() if s in slug_to_show]
    if not feed_slugs:
        print("No enabled feed slugs with elementfm_show_id in feeds config.", file=sys.stderr)
        return 1

    moves_ok = 0
    titles_ok = 0
    skipped = 0
    move_fail = 0

    for current_slug in feed_slugs:
        show_id = slug_to_show[current_slug]
        client = client_for_show(api_key, workspace_id, show_id)
        episodes = client.list_episodes()
        print(f"\n=== Show {current_slug!r} ({show_id[:8]}…) — {len(episodes)} episode(s) ===")

        for ep in episodes:
            eid = str(ep.get("id") or "")
            title = str(ep.get("title") or "")
            if not eid:
                continue

            parsed = slug_date_from_title(title)
            if not parsed:
                print(f"  skip  {eid[:8]}…  unrecognized title: {title!r}")
                skipped += 1
                continue

            title_slug, date = parsed
            new_t = clean_title(title_slug, date)
            need_title = new_t != title.strip()

            if title_slug not in slug_to_show:
                print(f"  skip  {eid[:8]}…  unknown slug {title_slug!r}: {title!r}")
                skipped += 1
                continue

            need_move = title_slug != current_slug
            rich = str(ep.get("description") or "").strip() or None

            if need_move:
                print(f"  move  {eid[:8]}…  {title!r}  → show {title_slug!r}  title→ {new_t!r}")
                if not dry:
                    r = try_move_episode(api_key, workspace_id, show_id, eid, slug_to_show[title_slug])
                    if "error" in r:
                        print(f"        FAILED move: {r.get('error')}")
                        move_fail += 1
                        continue
                    moves_ok += 1
                    tclient = client_for_show(api_key, workspace_id, slug_to_show[title_slug])
                    desc = elementfm_episode_description(new_t, rich)
                    pr = tclient.patch_episode(
                        episode_id=eid,
                        data={"title": new_t, "description": desc},
                    )
                    if "error" in pr:
                        print(f"        title patch after move: {pr.get('error')}")
                    else:
                        titles_ok += 1
                continue

            if need_title:
                print(f"  title {eid[:8]}…  {title!r}  →  {new_t!r}")
                if not dry:
                    desc = elementfm_episode_description(new_t, rich)
                    pr = client.patch_episode(
                        episode_id=eid,
                        data={"title": new_t, "description": desc},
                    )
                    if "error" in pr:
                        print(f"        FAILED: {pr.get('error')}")
                        continue
                    titles_ok += 1
            else:
                print(f"  ok    {eid[:8]}…  {title!r}")

    print(f"\nSummary ({'dry-run' if dry else 'applied'}): moves_ok={moves_ok}, titles_ok={titles_ok}, move_fail={move_fail}, skipped={skipped}")
    if dry:
        print("Re-run with --apply to execute.")
    elif move_fail:
        print(
            "\nSome moves failed: Element.fm may not expose show transfers via API. "
            "Move those episodes in the dashboard, then re-run with --apply to fix titles.",
            file=sys.stderr,
        )
    return 0 if move_fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
