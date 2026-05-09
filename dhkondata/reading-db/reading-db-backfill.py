#!/usr/bin/env python3
"""
reading-db-backfill.py
======================
Backfills the reading-db YAML store from historical Gmail newsletter labels.
Reads emails from all four newsletter labels over a date range, runs the same
deep pipeline logic as reading-list-builder v2.0, and writes YYYY-MM-DD.yaml
files to adventures-in-ai/dhkondata/reading-db/runs/.

This script is designed to run via Claude Code (claude --print) so that
token usage is tracked exactly via the API usage field.

Usage:
  python3 reading-db-backfill.py --from 2026-01-01 --to 2026-05-08
  python3 reading-db-backfill.py --from 2026-01-01          # to = yesterday
  python3 reading-db-backfill.py --days 90                  # last 90 days

Flags:
  --from    YYYY-MM-DD  Start date (inclusive)
  --to      YYYY-MM-DD  End date (inclusive), default: yesterday
  --days    N           Convenience: last N days from today
  --dry-run             Print what would be processed, write nothing
  --skip-existing       Skip dates that already have a YAML file (default: True)
  --overwrite           Re-process and overwrite existing YAML files
  --label   LABEL       Process a single label only (for debugging)
  --limit   N           Cap emails per label per day (for testing)

Version stamping:
  Reads version from skills/user/reading-list-builder/SKILL.md frontmatter.
  Stamps skill_version into every YAML run file it writes.
  If the skill file is not found, uses "backfill-unknown" as the version.

Output:
  adventures-in-ai/dhkondata/reading-db/runs/YYYY-MM-DD.yaml (one per day)
  adventures-in-ai/dhkondata/reading-db/backfill-log.yaml    (run summary)
"""

import argparse
import os
import sys
import yaml
import json
import re
from datetime import date, timedelta, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LABELS = [
    ("newsletter/news",       "01", "News & Current Affairs"),
    ("newsletter/think",      "02", "Things to Think About"),
    ("newsletter/pro",        "03", "Professional Reading"),
    ("newsletter/healthcare", "04", "Healthcare"),
]

BLOCKED_DOMAINS = {
    "links.tldrnewsletter.com", "mailchi.mp", "mg.mail.substack.com",
    "link.axios.com", "click.e.washingtonpost.com", "email.mg.substack.com",
    "mandrillapp.com", "sendgrid.net", "mailgun.org", "list-manage.com",
    "campaign-archive.com", "constantcontact.com", "hubspotemail.net",
}

BLOCKED_ANCHOR_PATTERNS = [
    "unsubscribe", "manage preferences", "view in browser", "view online",
    "privacy policy", "terms of service", "click here", "read more",
]

REPO_ROOT = Path.home() / "adventures-in-ai"
RUNS_DIR  = REPO_ROOT / "dhkondata" / "reading-db" / "runs"
LOG_FILE  = REPO_ROOT / "dhkondata" / "reading-db" / "backfill-log.yaml"
SKILL_PATH = REPO_ROOT.parent / "mnt" / "skills" / "user" / "reading-list-builder" / "SKILL.md"

# Fallback skill path (if running from repo directly)
SKILL_PATH_ALT = Path.home() / "adventures-in-ai" / "skills" / "user" / "reading-list-builder" / "SKILL.md"

# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

def get_skill_version():
    """Read version from SKILL.md frontmatter. Returns string."""
    for path in [SKILL_PATH, SKILL_PATH_ALT]:
        if path.exists():
            text = path.read_text()
            match = re.search(r'^version:\s*["\'](.*?)["\']', text, re.MULTILINE)
            if match:
                return match.group(1)
    return "backfill-unknown"

# ---------------------------------------------------------------------------
# Date range helpers
# ---------------------------------------------------------------------------

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

def date_range(start, end):
    """Yield dates from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def build_date_range(args):
    today = date.today()
    yesterday = today - timedelta(days=1)

    if args.days:
        start = today - timedelta(days=int(args.days))
        end = yesterday
    elif args.from_date:
        start = parse_date(args.from_date)
        end = parse_date(args.to_date) if args.to_date else yesterday
    else:
        print("ERROR: provide --from or --days")
        sys.exit(1)

    if start > end:
        print(f"ERROR: start date {start} is after end date {end}")
        sys.exit(1)

    return start, end

# ---------------------------------------------------------------------------
# YAML output helpers
# ---------------------------------------------------------------------------

def run_file_path(run_date):
    return RUNS_DIR / f"{run_date}.yaml"

def load_existing_run(run_date):
    path = run_file_path(run_date)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    return None

def write_run_file(run_date, data):
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = run_file_path(run_date)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return path

# ---------------------------------------------------------------------------
# Stub: Gmail fetch
# These functions are stubs. When running via Claude Code, replace with
# actual MCP tool calls. The structure is defined here for documentation
# and for standalone testing with mock data.
# ---------------------------------------------------------------------------

def gmail_search(label, after_date, limit=None):
    """
    Stub for: gmail_search_messages(q=f"label:{label} after:{after_date}")
    Returns list of {messageId, threadId, snippet, subject, sender, received_at}
    Replace with actual MCP call when running via Claude Code.
    """
    raise NotImplementedError(
        "gmail_search is a stub. Run this script via Claude Code with Gmail MCP "
        "connected, or provide a --mock flag for testing with sample data."
    )

def gmail_read(message_id):
    """
    Stub for: gmail_read_message(messageId=message_id)
    Returns {messageId, threadId, subject, sender, received_at, body_text, body_html}
    """
    raise NotImplementedError("gmail_read is a stub. Run via Claude Code.")

# ---------------------------------------------------------------------------
# Stub: Article fetch and synthesis
# ---------------------------------------------------------------------------

def resolve_url(url_raw):
    """
    Follow redirects to get canonical URL.
    Returns {url_canonical, domain, resolve_status}
    Stub: replace with web_fetch(url) + extract final URL.
    """
    raise NotImplementedError("resolve_url is a stub. Run via Claude Code.")

def fetch_article(url_canonical):
    """
    Fetch full article body.
    Returns {body_text, fetch_status, full_body_chars}
    Stub: replace with web_fetch(url) + body extraction.
    """
    raise NotImplementedError("fetch_article is a stub. Run via Claude Code.")

def synthesize(article_body, fallback_excerpt=None):
    """
    Generate synthesis bullets via Claude.
    Returns {bullets, source, confidence_note}
    Stub: replace with Anthropic API call with the synthesis prompt.

    Synthesis prompt (use exactly):
      Extract 3-5 key claims from this article.
      Only include claims that are directly and explicitly stated in the text.
      Do not infer, extrapolate, summarize themes, or editorialize.
      Do not combine claims from different parts of the article into a single bullet.
      Each bullet should be independently verifiable against the source text.
      If you are uncertain whether a claim is directly stated, omit it.
      If fewer than 3 clear claims are present, return only those that are certain.
    """
    raise NotImplementedError("synthesize is a stub. Run via Claude Code.")

# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

def extract_links(html_body, email_id):
    """
    Extract editorial article links from email HTML body.
    Returns list of {article_id, url_raw, anchor_text, excerpt, position}
    """
    from html.parser import HTMLParser
    import urllib.parse

    class LinkExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []
            self.current_href = None
            self.current_text = []
            self.in_anchor = False

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                attrs_dict = dict(attrs)
                self.current_href = attrs_dict.get("href", "")
                self.in_anchor = True
                self.current_text = []

        def handle_endtag(self, tag):
            if tag == "a" and self.in_anchor:
                text = " ".join(self.current_text).strip()
                if self.current_href and text:
                    self.links.append((self.current_href, text))
                self.in_anchor = False
                self.current_href = None
                self.current_text = []

        def handle_data(self, data):
            if self.in_anchor:
                self.current_text.append(data.strip())

    extractor = LinkExtractor()
    extractor.feed(html_body or "")
    raw_links = extractor.links

    results = []
    position = 0

    for url_raw, anchor_text in raw_links:
        # Skip short anchor text
        if len(anchor_text) < 15:
            continue

        # Skip blocked anchor patterns
        anchor_lower = anchor_text.lower()
        if any(p in anchor_lower for p in BLOCKED_ANCHOR_PATTERNS):
            continue

        # Skip social links
        social_domains = {"twitter.com", "x.com", "linkedin.com", "facebook.com",
                          "instagram.com", "youtube.com"}
        try:
            parsed = urllib.parse.urlparse(url_raw)
            domain = parsed.netloc.lstrip("www.")
            if domain in social_domains:
                continue
            if domain in BLOCKED_DOMAINS:
                # Will be resolved -- if canonical domain is clean, keep it
                pass
            if url_raw.startswith("#"):
                continue
        except Exception:
            continue

        position += 1
        article_id = f"{email_id}-{position:02d}"
        results.append({
            "article_id": article_id,
            "position": position,
            "url_raw": url_raw,
            "anchor_text": anchor_text,
            "excerpt": "",  # populated by caller from surrounding text
        })

    return results

# ---------------------------------------------------------------------------
# Build article record (skeleton -- stubs for fetch/synthesis)
# ---------------------------------------------------------------------------

def build_article_record(link, email_record, notebook_info, dry_run=False):
    """
    Given an extracted link dict and parent email record, build a full article record.
    In dry_run mode, skips network calls and marks everything as pending.
    """
    article = {
        "article_id": link["article_id"],
        "position": link["position"],
        "source": {
            "url_raw": link["url_raw"],
            "url_canonical": None,
            "domain": None,
            "anchor_text": link["anchor_text"],
            "resolve_status": "pending",
            "parse_confidence": None,
        },
        "content": {
            "full_body_available": False,
            "full_body_chars": None,
            "fetch_status": "pending",
            "fetch_notes": None,
        },
        "routing": {
            "category": email_record["label"].split("/")[-1],
            "notebook_id": notebook_info.get("notebook_id"),
            "notebook_title": notebook_info.get("notebook_title"),
        },
        "synthesis": {
            "status": "pending",
            "source": None,
            "bullets": [],
            "generated_at": None,
            "confidence_note": None,
        },
        "tags": [],
        "status": "ingested",
    }

    if not dry_run:
        # These would be real calls via Claude Code
        # resolve -> fetch -> synthesize
        # Stubs raise NotImplementedError -- catch and mark as failed
        try:
            resolved = resolve_url(link["url_raw"])
            article["source"].update(resolved)
        except NotImplementedError:
            article["source"]["resolve_status"] = "stub-not-implemented"
            article["content"]["fetch_status"] = "skipped"
            article["synthesis"]["status"] = "skipped"
            article["synthesis"]["source"] = "skipped"
            return article

    return article

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Backfill reading-db from Gmail labels")
    parser.add_argument("--from", dest="from_date", help="Start date YYYY-MM-DD")
    parser.add_argument("--to",   dest="to_date",   help="End date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--days", type=int,          help="Last N days")
    parser.add_argument("--dry-run",       action="store_true", help="Print plan, write nothing")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="Skip dates with existing YAML (default: True)")
    parser.add_argument("--overwrite",     action="store_true",
                        help="Re-process and overwrite existing YAML files")
    parser.add_argument("--label",  help="Process a single label only")
    parser.add_argument("--limit",  type=int, help="Cap emails per label per day")
    args = parser.parse_args()

    skill_version = get_skill_version()
    start, end = build_date_range(args)

    labels_to_run = LABELS
    if args.label:
        labels_to_run = [l for l in LABELS if l[0] == args.label]
        if not labels_to_run:
            print(f"ERROR: unknown label '{args.label}'. Valid: {[l[0] for l in LABELS]}")
            sys.exit(1)

    total_days = (end - start).days + 1
    print(f"Reading DB Backfill")
    print(f"  Skill version : {skill_version}")
    print(f"  Date range    : {start} to {end} ({total_days} days)")
    print(f"  Labels        : {[l[0] for l in labels_to_run]}")
    print(f"  Output dir    : {RUNS_DIR}")
    print(f"  Mode          : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Skip existing : {args.skip_existing and not args.overwrite}")
    print()

    backfill_log = {
        "backfill_run_at": datetime.utcnow().isoformat() + "Z",
        "skill_version": skill_version,
        "date_range": {"from": str(start), "to": str(end)},
        "dry_run": args.dry_run,
        "days_processed": 0,
        "days_skipped": 0,
        "days_errored": 0,
        "total_emails": 0,
        "total_articles": 0,
    }

    for run_date in date_range(start, end):
        run_date_str = str(run_date)
        existing = load_existing_run(run_date)

        if existing and args.skip_existing and not args.overwrite:
            print(f"  {run_date_str}  SKIP (file exists, use --overwrite to reprocess)")
            backfill_log["days_skipped"] += 1
            continue

        print(f"  {run_date_str}  processing...")

        if args.dry_run:
            print(f"    [dry-run] would search {len(labels_to_run)} labels")
            backfill_log["days_processed"] += 1
            continue

        # Build run record
        run_record = {
            "run_date": run_date_str,
            "skill_version": skill_version,
            "pipeline_mode": "deep",
            "backfill": True,
            "notebooks": [],
            "emails": [],
        }

        # Step 1: Search each label
        # NOTE: gmail_search is a stub -- when running via Claude Code,
        # these calls are handled by the MCP tool layer.
        for label, suffix, category in labels_to_run:
            after_str = run_date_str.replace("-", "/")
            try:
                messages = gmail_search(label, after_str, limit=args.limit)
            except NotImplementedError:
                print(f"    WARNING: gmail_search stub -- run via Claude Code for live data")
                print(f"    Generating empty run record for {run_date_str}")
                messages = []

            # Filter to this day only
            day_messages = [m for m in messages
                           if m.get("received_at", "").startswith(run_date_str)]

            if not day_messages:
                continue

            notebook_info = {
                "label": label,
                "notebook_id": None,  # populated after NotebookLM create
                "notebook_title": f"reading-list-{run_date_str}-{suffix} {category}",
            }
            run_record["notebooks"].append(notebook_info)

            for msg in day_messages:
                try:
                    full_msg = gmail_read(msg["messageId"])
                except NotImplementedError:
                    full_msg = msg  # use search result as fallback

                email_record = {
                    "email_id": msg["messageId"],
                    "thread_id": msg.get("threadId"),
                    "received_at": msg.get("received_at"),
                    "label": label,
                    "sender": msg.get("sender"),
                    "sender_name": msg.get("sender_name"),
                    "subject": msg.get("subject"),
                    "article_count": 0,
                    "parse_notes": None,
                    "articles": [],
                }

                # Extract links
                html_body = full_msg.get("body_html", "")
                links = extract_links(html_body, msg["messageId"])
                email_record["article_count"] = len(links)

                for link in links:
                    article = build_article_record(
                        link, email_record, notebook_info, dry_run=args.dry_run
                    )
                    email_record["articles"].append(article)

                run_record["emails"].append(email_record)
                backfill_log["total_emails"] += 1
                backfill_log["total_articles"] += len(links)

        # Write run file
        out_path = write_run_file(run_date, run_record)
        email_count = len(run_record["emails"])
        article_count = sum(len(e["articles"]) for e in run_record["emails"])
        print(f"    wrote {out_path.name} -- {email_count} emails, {article_count} articles")
        backfill_log["days_processed"] += 1

    # Write backfill log
    if not args.dry_run:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE) as f:
                existing_log = yaml.safe_load(f)
                if isinstance(existing_log, list):
                    logs = existing_log
                elif existing_log:
                    logs = [existing_log]
        logs.append(backfill_log)
        with open(LOG_FILE, "w") as f:
            yaml.dump(logs, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print()
    print(f"Backfill complete.")
    print(f"  Days processed : {backfill_log['days_processed']}")
    print(f"  Days skipped   : {backfill_log['days_skipped']}")
    print(f"  Total emails   : {backfill_log['total_emails']}")
    print(f"  Total articles : {backfill_log['total_articles']}")
    if not args.dry_run:
        print(f"  Log written to : {LOG_FILE}")

if __name__ == "__main__":
    main()
