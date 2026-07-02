#!/usr/bin/env python3
"""
Reading with Ears — "The Week That Was"
Mechanical stages of the weekly synthesis pipeline (see
reading-with-ears/docs/week-that-was-design.md).

Builds the pre-flight, zeitgeist tag-counting, per-section synthesis, and
document-assembly stages (design doc §9 build-order item 3). Does NOT include
the zeitgeist narrative (stage 4) or the ideation/article-ideas layer (stage
5, gated on a writer profile that doesn't exist yet) or the NotebookLM/
Element.fm publish steps (7-8) — those are later build-order items.

Usage:
    python3 week_that_was.py                    # current ISO week
    python3 week_that_was.py --week 2026-W26    # specific ISO week
    python3 week_that_was.py --dry-run          # skip Anthropic API calls

Safe to re-run: each stage (and each section within section_synthesis) is
recorded in manifest.yaml and skipped once complete, so a re-run only retries
what previously failed or is still pending.
"""

import argparse
import json
import re
import sys
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

# ── Paths ──────────────────────────────────────────────────────────────────
#
# Prefer RWE_REPO if set — bin/rwe-weekly exports it after resolving the repo root
# via rwe-common.sh's rwe_repo_root() (which honors RWE_REPO / ~/.config/reading-with-
# ears/config.json / relative-to-caller, in that order). Falling back to
# Path(__file__).resolve() only works when scripts/ is a symlink into the repo
# (install-local.sh's default SYNC_MODE); under SYNC_MODE=copy this file is a real
# copy under ~/.local/share with nothing to resolve back to the repo, so RWE_REPO
# must be trusted when present rather than always re-deriving from __file__.
_env_repo = os.environ.get("RWE_REPO", "").strip()
if _env_repo:
    REPO_ROOT = Path(_env_repo).expanduser().resolve()
    RWE_ROOT = REPO_ROOT / "reading-with-ears"
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    RWE_ROOT = SCRIPT_DIR.parent
    REPO_ROOT = RWE_ROOT.parent

RUNS_DIR = REPO_ROOT / "dhkondata" / "reading-db" / "runs"
ZEITGEIST_DIR = REPO_ROOT / "dhkondata" / "reading-db" / "zeitgeist"
THEMES_PATH = ZEITGEIST_DIR / "themes.yaml"
WEEKLY_DIR = REPO_ROOT / "dhkondata" / "reading-db" / "weekly"
WEEKLY_CONFIG_PATH = RWE_ROOT / "config" / "weekly.json"
FEEDS_CONFIG_PATH = RWE_ROOT / "config" / "feeds.json"
FEEDS_CONFIG_OVERRIDE_PATH = Path.home() / ".config" / "reading-with-ears" / "feeds.json"

# Rough public per-token pricing for manifest cost estimates. Not billing-accurate
# — just enough to give the cost guardrail (design doc §7) something to compare
# against a ceiling.
PRICING_PER_MTOK = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}

WEEK_LABEL_RE = re.compile(r"^(\d{4})-W(\d{1,2})$")

TREND_PRIORITY = {"emerging": 0, "growing": 1, "dipping": 2, "steady": 3, "low-volume": 4}


# ── ISO week helpers ─────────────────────────────────────────────────────────

def week_label(iso_year, iso_week):
    return f"{iso_year}-W{iso_week:02d}"


def parse_week_label(label):
    m = WEEK_LABEL_RE.match(label.strip())
    if not m:
        raise ValueError(f"invalid ISO week label: {label!r} (expected YYYY-Www)")
    return int(m.group(1)), int(m.group(2))


def today_iso_week():
    y, w, _ = date.today().isocalendar()
    return y, w


def week_dates(iso_year, iso_week):
    return [date.fromisocalendar(iso_year, iso_week, d) for d in range(1, 8)]


def shift_week(iso_year, iso_week, weeks_back):
    """Return the (iso_year, iso_week) that is `weeks_back` weeks before the given week."""
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    shifted = monday.fromordinal(monday.toordinal() - 7 * weeks_back)
    y, w, _ = shifted.isocalendar()
    return y, w


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Reading-db loading ───────────────────────────────────────────────────────

def load_week_runs(runs_dir, dates):
    """Load whatever daily run YAMLs exist for this week's dates. Missing days
    are not an error — see design doc §6.1."""
    runs, found, missing = [], [], []
    for d in dates:
        p = runs_dir / f"{d.isoformat()}.yaml"
        if p.is_file():
            with p.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            runs.append((d, data))
            found.append(d.isoformat())
        else:
            missing.append(d.isoformat())
    return runs, found, missing


def load_feeds_config():
    """Merge-first, same precedence as podcast_config.load_feeds_json(): prefer
    ~/.config/reading-with-ears/feeds.json, else the bundled repo config."""
    for path in (FEEDS_CONFIG_OVERRIDE_PATH, FEEDS_CONFIG_PATH):
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            if data.get("feeds"):
                return data
    return {"feeds": []}


def build_label_to_slug(feeds_cfg):
    """Map every spelling of a feed's label seen in daily run YAMLs to its slug.

    The daily YAML's `emails[].label` field has drifted over time between the raw
    Gmail label (e.g. "newsletter/pro") and the feed slug (e.g. "professional") —
    both forms exist in real run files. weekly.json's taxonomy `feeds` lists use
    slugs, so every other spelling must normalize to the slug before filtering."""
    mapping = {}
    for feed in feeds_cfg.get("feeds") or []:
        slug = feed.get("slug")
        if not slug:
            continue
        mapping[slug] = slug
        for gl in feed.get("gmail_labels") or []:
            mapping[gl] = slug
            if "/" in gl:
                mapping[gl.split("/", 1)[1]] = slug
    return mapping


def _synthesis_bullets_and_note(art):
    """Some older run files (e.g. reading-db-backfill.py's "deep-email-body"
    pipeline_mode) store `synthesis` as a flat list of bullet strings rather than
    the current `{bullets: [...], confidence_note: ...}` dict — handle both."""
    synthesis = art.get("synthesis")
    if isinstance(synthesis, list):
        return synthesis, None
    if isinstance(synthesis, dict):
        return synthesis.get("bullets") or [], synthesis.get("confidence_note")
    return [], None


def iter_articles(runs, label_to_slug):
    for d, data in runs:
        for email in data.get("emails") or []:
            label = label_to_slug.get(email.get("label"), email.get("label"))
            for art in email.get("articles") or []:
                bullets, confidence_note = _synthesis_bullets_and_note(art)
                yield {
                    "date": d.isoformat(),
                    "label": label,
                    "subject": email.get("subject"),
                    "sender_name": email.get("sender_name"),
                    "thread_id": email.get("thread_id"),
                    "url_canonical": (art.get("source") or {}).get("url_canonical") or art.get("canonical_url"),
                    "bullets": bullets,
                    "confidence_note": confidence_note,
                    "tags": art.get("tags") or [],
                }


def articles_for_section(all_articles, feeds):
    feeds = set(feeds)
    return [a for a in all_articles if a["label"] in feeds]


# ── Zeitgeist counting (deterministic, no model — design doc §6.3) ─────────

def count_tags(all_articles):
    counts = {}
    for a in all_articles:
        for t in a["tags"]:
            counts[t] = counts.get(t, 0) + 1
    return counts


def trailing_avg(weekly_counts, iso_year, iso_week):
    weeks = [shift_week(iso_year, iso_week, d) for d in (1, 2, 3, 4)]
    vals = [weekly_counts.get(week_label(*w), 0) for w in weeks]
    return sum(vals) / 4.0


def first_seen_weeks_ago(weekly_counts, iso_year, iso_week):
    if not weekly_counts:
        return None
    earliest = min(weekly_counts, key=lambda w: parse_week_label(w))
    ey, ew = parse_week_label(earliest)
    cur_monday = date.fromisocalendar(iso_year, iso_week, 1)
    earliest_monday = date.fromisocalendar(ey, ew, 1)
    return (cur_monday - earliest_monday).days // 7


def classify_tag(week_str, count_this_week, prior_weekly_counts):
    """Trend label with a noise floor — see design doc §6.3 ("Review comment:
    noise floor"). Ratio math only applies once a tag has enough trailing
    volume to make a ratio meaningful."""
    iso_year, iso_week = parse_week_label(week_str)
    avg = trailing_avg(prior_weekly_counts, iso_year, iso_week)
    weeks_ago = first_seen_weeks_ago(prior_weekly_counts, iso_year, iso_week)
    is_new = weeks_ago is None or weeks_ago <= 1

    if is_new and count_this_week >= 2:
        return "emerging"
    if avg < 3:
        return "low-volume"
    if count_this_week > 1.5 * avg:
        return "growing"
    if count_this_week < 0.5 * avg:
        return "dipping"
    return "steady"


def update_themes(themes, week_str, counts):
    """Mutates `themes` in place with this week's counts; returns the mover list."""
    themes.setdefault("themes", {})

    def has_recent_signal(tag):
        rec = themes["themes"].get(tag)
        if not rec:
            return False
        iso_year, iso_week = parse_week_label(week_str)
        return trailing_avg(rec.get("weekly_counts", {}), iso_year, iso_week) > 0

    all_tags = set(counts) | {t for t in themes["themes"] if has_recent_signal(t)}

    movers = []
    for tag in sorted(all_tags):
        rec = themes["themes"].setdefault(tag, {"weekly_counts": {}})
        prior_hist = dict(rec["weekly_counts"])  # snapshot before writing this week
        count_this_week = counts.get(tag, 0)
        trend = classify_tag(week_str, count_this_week, prior_hist)
        movers.append({"tag": tag, "count": count_this_week, "trend": trend})
        if count_this_week > 0:
            rec["weekly_counts"][week_str] = count_this_week
    return movers


def load_themes(path):
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {"themes": {}}
    return {"themes": {}}


def save_themes(path, themes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(themes, f, sort_keys=False, allow_unicode=True)


# ── Section synthesis (Sonnet x 6, direct API — design doc §6.2) ───────────
#
# Note: article HTML briefs (dhkondata/reading-db/briefs/) are rendered *from*
# `synthesis.bullets` by the daily pipeline's infographic step (see SKILL.md
# STEP 7) — they don't carry any content the bullets don't already have, just
# a nicer layout. So section synthesis reads `bullets` directly from the daily
# YAML rather than re-reading and stripping brief HTML; there's no fidelity
# gain to justify the extra I/O.

def estimate_cost(model, input_tokens, output_tokens):
    rates = PRICING_PER_MTOK.get(model, DEFAULT_PRICING)
    return (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]


def build_section_prompt(section_label, articles):
    lines = [
        f'You are writing the "{section_label}" section of a weekly newsletter/podcast roundup.',
        "Write 2-4 short paragraphs of connected narrative prose synthesizing this week's "
        "developments in this section. Do not restate the bullets as a list — note where "
        "sources agree, disagree, or build on each other, and what the throughline is.",
        "",
        f'This week\'s articles in "{section_label}":',
    ]
    for a in articles:
        lines.append(f"\n### {a['subject']} ({a['sender_name']})")
        for b in a["bullets"]:
            lines.append(f"- {b}")
        if a.get("confidence_note"):
            lines.append(f"(confidence: {a['confidence_note']})")
    return "\n".join(lines)


def call_with_retries(fn, attempts=3, base_delay=2):
    # Broad except is intentional: this is a bounded retry for transient API
    # errors (rate limits, 5xx) per design doc §8 — not meant to distinguish
    # error types, just to retry a few times before giving up.
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i == attempts - 1:
                break
            time.sleep(base_delay * (2 ** i))
    raise last_exc


def make_anthropic_client():
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "the 'anthropic' package is required for section synthesis "
            "(pip install anthropic, or re-run with --dry-run)"
        ) from exc
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


def synthesize_section(client, model, section_label, articles):
    prompt = build_section_prompt(section_label, articles)

    def _call():
        return client.messages.create(
            model=model,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )

    resp = call_with_retries(_call)
    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    cost = estimate_cost(model, resp.usage.input_tokens, resp.usage.output_tokens)
    return text, tokens, cost


# ── Manifest / config I/O ────────────────────────────────────────────────────

def load_manifest(path, week_str):
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("week", week_str)
        data.setdefault("stages", {})
        return data
    return {"week": week_str, "started_at": now_iso(), "stages": {}}


def save_manifest(path, manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)


def load_weekly_config(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ── Document assembly (step 6) ──────────────────────────────────────────────

def assemble_document(week_str, manifest, weekly_cfg, section_texts, movers):
    lines = [f"# The Week That Was — {week_str}", ""]

    if manifest.get("days_missing"):
        lines.append(f"_Missing daily runs: {', '.join(manifest['days_missing'])}_")
        lines.append("")

    lines.append("## Zeitgeist")
    lines.append("")
    lines.append("_Narrative synthesis not yet built (stage 4) — raw movers below._")
    lines.append("")
    notable = [m for m in movers if not (m["trend"] == "low-volume" and m["count"] == 0)]
    notable.sort(key=lambda m: (TREND_PRIORITY.get(m["trend"], 5), -m["count"]))
    if notable:
        lines.append("| Theme | Mentions this week | Trend |")
        lines.append("|---|---|---|")
        for m in notable[:20]:
            lines.append(f"| {m['tag']} | {m['count']} | {m['trend']} |")
    else:
        lines.append("_No tagged themes this week._")
    lines.append("")

    for section in weekly_cfg["taxonomy"]:
        text = section_texts.get(section["key"])
        if not text:
            continue
        lines.append(f"## {section['label']}")
        lines.append("")
        lines.append(text.strip())
        lines.append("")

    lines.append("## Ideas for articles")
    lines.append("")
    lines.append(
        "_Not yet built — requires `writer-profile.yaml` "
        "(see `docs/week-that-was-design.md` §9)._"
    )
    lines.append("")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--week", help="ISO week, e.g. 2026-W26 (default: current week)")
    p.add_argument("--dry-run", action="store_true", help="Skip Anthropic API calls; sections are marked skipped")
    args = p.parse_args(argv)
    args.iso_year, args.iso_week = parse_week_label(args.week) if args.week else today_iso_week()
    return args


def main(argv=None):
    args = parse_args(argv)
    week_str = week_label(args.iso_year, args.iso_week)
    dates = week_dates(args.iso_year, args.iso_week)

    weekly_dir = WEEKLY_DIR / week_str
    manifest_path = weekly_dir / "manifest.yaml"
    manifest = load_manifest(manifest_path, week_str)

    # Checked unconditionally, independent of preflight's resume state: a prior
    # --dry-run can leave preflight marked complete without ever having checked
    # for a key, and a real run must still fail fast rather than inherit that.
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        stage = manifest["stages"].setdefault("preflight", {"status": "pending"})
        stage.update(status="failed", reason="ANTHROPIC_API_KEY not set", at=now_iso())
        save_manifest(manifest_path, manifest)
        print(
            "ERROR: ANTHROPIC_API_KEY not set — aborting before any paid stage runs "
            "(see docs/week-that-was-design.md §4.1). Re-run with --dry-run to test "
            "the mechanical pipeline without a key.",
            file=sys.stderr,
        )
        return 1

    # ── Stage: preflight ──
    stage = manifest["stages"].setdefault("preflight", {"status": "pending"})
    if stage.get("status") != "complete":
        runs, found, missing = load_week_runs(RUNS_DIR, dates)
        manifest["days_found"] = found
        manifest["days_missing"] = missing
        if not found:
            stage.update(status="failed", reason="no daily runs found for this week", at=now_iso())
            save_manifest(manifest_path, manifest)
            print(f"ERROR: no daily runs found for {week_str} in {RUNS_DIR}. Nothing to synthesize.", file=sys.stderr)
            return 1
        stage.update(status="complete", at=now_iso())
        save_manifest(manifest_path, manifest)
    else:
        runs, _, _ = load_week_runs(RUNS_DIR, dates)

    label_to_slug = build_label_to_slug(load_feeds_config())
    all_articles = list(iter_articles(runs, label_to_slug))

    # ── Stage: zeitgeist_counts ──
    stage = manifest["stages"].setdefault("zeitgeist_counts", {"status": "pending"})
    if stage.get("status") != "complete":
        themes = load_themes(THEMES_PATH)
        counts = count_tags(all_articles)
        movers = update_themes(themes, week_str, counts)
        save_themes(THEMES_PATH, themes)
        stage.update(status="complete", at=now_iso(), movers=movers)
        save_manifest(manifest_path, manifest)
    movers = stage.get("movers", [])

    # ── Stage: section_synthesis (per-section resume granularity — §8) ──
    weekly_cfg = load_weekly_config(WEEKLY_CONFIG_PATH)
    stage = manifest["stages"].setdefault("section_synthesis", {"status": "pending", "sections": {}})
    stage.setdefault("sections", {})

    if args.dry_run:
        client = None
    else:
        try:
            client = make_anthropic_client()
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    section_texts = {}
    for section in weekly_cfg["taxonomy"]:
        key, label, feeds = section["key"], section["label"], section["feeds"]
        sec_state = stage["sections"].setdefault(key, {"status": "pending"})

        if sec_state.get("status") == "complete":
            section_texts[key] = sec_state.get("text", "")
            continue
        if sec_state.get("status") == "skipped":
            continue
        # "dry_run_skipped" is only terminal for another dry run. A real invocation
        # must still attempt synthesis even if an earlier --dry-run already touched
        # this section — otherwise a dry run permanently blocks real synthesis for
        # every section it ran (same class of bug already fixed for preflight above).
        if sec_state.get("status") == "dry_run_skipped" and args.dry_run:
            continue

        articles = articles_for_section(all_articles, feeds)
        if not articles:
            sec_state.update(status="skipped", reason="no articles this week")
            save_manifest(manifest_path, manifest)
            continue

        if args.dry_run:
            sec_state.update(status="dry_run_skipped", reason="dry-run")
            save_manifest(manifest_path, manifest)
            continue

        try:
            text, tokens, cost = synthesize_section(client, weekly_cfg["section_model"], label, articles)
        except Exception as exc:  # noqa: BLE001 — recorded per-section, not fatal to other sections
            sec_state.update(status="failed", reason=str(exc), at=now_iso())
            save_manifest(manifest_path, manifest)
            continue

        sec_state.update(status="complete", at=now_iso(), tokens=tokens, cost_usd=round(cost, 4), text=text)
        section_texts[key] = text
        save_manifest(manifest_path, manifest)

    # "dry_run_skipped" only counts as done for a dry run. A real invocation must
    # still treat those sections as unfinished so it actually retries them.
    terminal_statuses = {"complete", "skipped"} | ({"dry_run_skipped"} if args.dry_run else set())
    section_statuses = [s.get("status") for s in stage["sections"].values()]
    if section_statuses and all(s in terminal_statuses for s in section_statuses):
        section_tokens = sum(s.get("tokens", 0) for s in stage["sections"].values())
        section_cost = sum(s.get("cost_usd", 0) for s in stage["sections"].values())
        stage.update(status="complete", at=now_iso(), tokens=section_tokens, cost_usd=round(section_cost, 4))
    else:
        stage["status"] = "failed" if "failed" in section_statuses else "pending"
    save_manifest(manifest_path, manifest)

    if stage["status"] != "complete":
        print(f"section_synthesis incomplete for {week_str} — re-run to retry failed/pending sections.", file=sys.stderr)
        return 1

    max_cost = weekly_cfg.get("max_cost_usd", 5.0)
    running_cost = sum(
        s.get("cost_usd", 0) for s in manifest["stages"].values() if isinstance(s, dict)
    )
    if running_cost > max_cost:
        print(
            f"WARNING: estimated cost ${running_cost:.2f} exceeds configured ceiling "
            f"${max_cost:.2f} for {week_str} — continuing (signal only, not enforced; "
            "see design doc §7)."
        )

    # ── Stage: assemble_doc ──
    stage = manifest["stages"].setdefault("assemble_doc", {"status": "pending"})
    if stage.get("status") != "complete":
        doc = assemble_document(week_str, manifest, weekly_cfg, section_texts, movers)
        weekly_dir.mkdir(parents=True, exist_ok=True)
        synthesis_path = weekly_dir / "synthesis.md"
        synthesis_path.write_text(doc, encoding="utf-8")
        stage.update(status="complete", at=now_iso(), path=str(synthesis_path))
        save_manifest(manifest_path, manifest)

    manifest["total_cost_usd"] = round(running_cost, 4)
    save_manifest(manifest_path, manifest)

    print(f"Week {week_str}: wrote {weekly_dir / 'synthesis.md'}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
