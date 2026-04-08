from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


DEFAULT_AUDIO_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Personal Podcast"
)

AUDIO_FORMAT_DEFAULT = "mp3"
ALLOWED_AUDIO_FORMATS = {"mp3", "m4a"}


CONFIG_PATH = Path.home() / ".config" / "reading-with-ears" / "config.json"
FEEDS_CONFIG_PATH = Path.home() / ".config" / "reading-with-ears" / "feeds.json"
STATE_DIR = Path.home() / ".local" / "state" / "reading-with-ears"


CATEGORY_SLUGS: dict[str, str] = {
    "📰 News & Current Affairs": "news",
    "🧠 Things to Think About": "think",
    "💼 Professional Reading": "professional",
    "🏥 Healthcare Reading": "vital-signs",
}

CATEGORY_TITLES: dict[str, str] = {v: k for k, v in CATEGORY_SLUGS.items()}


FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>[a-z0-9_-]+)\.(?P<ext>[A-Za-z0-9]+)$"
)


READING_LIST_NOTEBOOK_RE = re.compile(
    r"^reading-list-(?P<date>\d{4}-\d{2}-\d{2})-(?P<nn>\d{2})\s+(?P<category>.+)$"
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def ensure_dirs() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_audio_dir(*, cli_audio_dir: Optional[str] = None) -> Path:
    """
    Resolve audio directory precedence:
      1) CLI override
      2) ~/.config/reading-with-ears/config.json (audio_dir)
      3) DEFAULT_AUDIO_DIR (iCloud Personal Podcast)
    """
    if cli_audio_dir:
        return Path(cli_audio_dir).expanduser()

    cfg = _read_json(CONFIG_PATH)
    audio_dir = cfg.get("audio_dir")
    if isinstance(audio_dir, str) and audio_dir.strip():
        return Path(audio_dir).expanduser()

    env_audio_dir = os.environ.get("RWE_AUDIO_DIR")
    if isinstance(env_audio_dir, str) and env_audio_dir.strip():
        return Path(env_audio_dir).expanduser()

    return DEFAULT_AUDIO_DIR


def resolve_audio_format(*, cli_audio_format: Optional[str] = None) -> str:
    """
    Resolve output audio format precedence:
      1) CLI override (--audio-format)
      2) ~/.config/reading-with-ears/config.json (audio_format)
      3) default 'mp3'
    """
    candidate = (cli_audio_format or "").strip().lower()
    if candidate:
        if candidate in ALLOWED_AUDIO_FORMATS:
            return candidate
        return AUDIO_FORMAT_DEFAULT

    cfg = _read_json(CONFIG_PATH)
    cfg_format = str(cfg.get("audio_format", "")).strip().lower()
    if cfg_format in ALLOWED_AUDIO_FORMATS:
        return cfg_format

    return AUDIO_FORMAT_DEFAULT


def manifest_path_for_date(target_date: str) -> Path:
    ensure_dirs()
    return STATE_DIR / f"manifest-{target_date}.json"


def parse_episode_title_from_filename(filename: str) -> str:
    """
    Turn '2026-03-21-news.mp3' into 'reading list - news - 2026-03-21'.
    Falls back to a humanized stem.
    """
    stem = Path(filename).stem
    parts = stem.split("-")
    if len(parts) >= 4:
        try:
            datetime.strptime(f"{parts[0]}-{parts[1]}-{parts[2]}", "%Y-%m-%d")
            date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            slug = parts[3].lower()
            return f"reading list - {slug} - {date_str}"
        except ValueError:
            pass
    return stem.replace("-", " ").replace("_", " ").title()


@dataclass(frozen=True)
class NotebookMatch:
    notebook_id: str
    date: str
    nn: int
    title: str
    category_title: str


def parse_reading_list_notebook_title(title: str) -> Optional[tuple[str, int, str]]:
    """
    Parse 'reading-list-YYYY-MM-DD-NN <CATEGORY>' into (date, nn, category).
    Returns None if not matched.
    """
    m = READING_LIST_NOTEBOOK_RE.match(title.strip())
    if not m:
        return None
    return (m.group("date"), int(m.group("nn")), m.group("category"))


def parse_audio_filename(filename: str) -> Optional[tuple[str, str, str]]:
    """
    Parse '<YYYY-MM-DD>-<slug>.<ext>' into (date, slug, ext).
    Returns None if the filename doesn't match the expected pattern.
    """
    m = FILENAME_RE.match(Path(filename).name)
    if not m:
        return None
    dt = m.group("date")
    slug = m.group("slug")
    ext = m.group("ext").lower()
    return (dt, slug, ext)


def elementfm_episode_description(title: str, rich_description: Optional[str] = None) -> str:
    """
    Episode description for element.fm. Uses the rich Phase 1 description (NotebookLM
    title + bullets + sources) if available; otherwise falls back to a simple string.
    """
    if rich_description and rich_description.strip():
        return rich_description.strip()
    t = (title or "").strip()
    if not t:
        return "Reading with Ears — personal reading-list audio overview."
    return f"Reading with Ears — {t}"


def _strip_leading_non_letters(s: str) -> str:
    """Strip leading emoji / punctuation until first letter or digit (category labels)."""
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):
            break
        i += 1
    return s[i:].strip()


def _normalize_category_label(s: str) -> str:
    t = unicodedata.normalize("NFKC", s).strip()
    t = _strip_leading_non_letters(t)
    t = t.lower().replace(" and ", " & ")
    t = re.sub(r"\s+", " ", t)
    return t


def category_title_to_slug(category_title: str) -> Optional[str]:
    """
    Map NotebookLM notebook category segment (after date/nn) to feed slug.
    Uses config/feeds.json (all feeds with slugs, including disabled) first, then legacy CATEGORY_SLUGS.
    """
    if not category_title:
        return None
    ct = category_title.strip()

    for feed in all_feeds_with_slug():
        slug = str(feed.get("slug") or "").strip()
        nc = str(feed.get("notebook_category") or "").strip()
        em = str(feed.get("notebook_emoji") or "").strip()
        if slug and nc and (ct == nc or nc in ct or ct in nc):
            return slug
        if slug and em and em in ct:
            return slug

    if ct in CATEGORY_SLUGS:
        return CATEGORY_SLUGS[ct]
    for expected_title, slug in CATEGORY_SLUGS.items():
        if expected_title in ct or ct in expected_title:
            return slug
    norm = _normalize_category_label(ct)
    for expected_title, slug in CATEGORY_SLUGS.items():
        exp = _normalize_category_label(expected_title)
        if norm == exp or exp in norm or norm in exp:
            return slug
    # Emoji fallback — match any feed emoji from config
    for feed in all_feeds_with_slug():
        em = str(feed.get("notebook_emoji") or "").strip()
        slug = str(feed.get("slug") or "").strip()
        if em and slug and em in ct:
            return slug
    if "📰" in ct:
        return "news"
    if "🧠" in ct:
        return "think"
    if "💼" in ct:
        return "professional"
    if "🏥" in ct:
        return "vital-signs"
    if "🎙️" in ct:
        return "ai-everybody"
    # Keyword fallbacks
    if "healthcare" in norm and "reading" in norm:
        return "vital-signs"
    if "professional" in norm and "reading" in norm:
        return "professional"
    if "things to think" in norm:
        return "think"
    if "news" in norm:
        return "news"
    if "reading" in norm and ("weekend" in norm or "weekly" in norm or "today" in norm):
        return "news"
    if "ai is for everybody" in norm or ("everybody" in norm and "ai" in norm):
        return "ai-everybody"
    return None


def slug_for_category_title(category_title: str) -> Optional[str]:
    """Backward-compatible name; use category_title_to_slug."""
    return category_title_to_slug(category_title)


def _feeds_config_candidate_paths() -> list[Path]:
    paths: list[Path] = []
    if FEEDS_CONFIG_PATH.is_file():
        paths.append(FEEDS_CONFIG_PATH)
    bundled = Path(__file__).resolve().parent.parent / "config" / "feeds.json"
    if bundled.is_file():
        paths.append(bundled)
    return paths


def load_feeds_json() -> dict[str, Any]:
    """Merge-first: prefer ~/.config/feeds.json, else bundled repo `config/feeds.json`."""
    for path in _feeds_config_candidate_paths():
        data = _read_json(path)
        if data.get("feeds"):
            return data
    return {}


def _feed_sort_key(feed: dict[str, Any]) -> int:
    try:
        return int(feed.get("notebook_order"))
    except (TypeError, ValueError):
        return 999


def enabled_feeds_ordered() -> list[dict[str, Any]]:
    """Feeds with enabled != false, non-empty slug, sorted by notebook_order."""
    data = load_feeds_json()
    feeds: list[dict[str, Any]] = []
    for f in data.get("feeds") or []:
        if not isinstance(f, dict):
            continue
        if f.get("enabled") is False:
            continue
        slug = str(f.get("slug") or "").strip()
        if not slug:
            continue
        feeds.append(f)
    feeds.sort(key=_feed_sort_key)
    return feeds


def enabled_slugs_ordered() -> list[str]:
    """Slugs for enabled feeds only — drives Phase 2 and launchd skip guard."""
    return [str(f.get("slug")).strip() for f in enabled_feeds_ordered()]


def all_feeds_with_slug() -> list[dict[str, Any]]:
    """
    Every feed entry that has a slug (including disabled), sorted by notebook_order.
    Used to map NotebookLM notebook titles → slug for existing notebooks.
    """
    data = load_feeds_json()
    out: list[dict[str, Any]] = []
    for f in data.get("feeds") or []:
        if not isinstance(f, dict):
            continue
        slug = str(f.get("slug") or "").strip()
        if not slug:
            continue
        out.append(f)
    out.sort(key=_feed_sort_key)
    return out


def load_feeds_publish_config() -> tuple[str, dict[str, str]]:
    """
    Return (workspace_id, slug -> elementfm_show_id) for each enabled feed that has a show id.
    """
    data = load_feeds_json()
    ws = str(data.get("workspace_id") or "").strip()
    if not ws:
        raise ValueError(
            "Missing feeds config: add ~/.config/reading-with-ears/feeds.json "
            "or keep reading-with-ears/config/feeds.json in the repo / sync clone."
        )
    out: dict[str, str] = {}
    for feed in data.get("feeds") or []:
        if not isinstance(feed, dict):
            continue
        if feed.get("enabled") is False:
            continue
        slug = str(feed.get("slug") or "").strip()
        sid = str(feed.get("elementfm_show_id") or "").strip()
        if slug and sid:
            out[slug] = sid
    if not out:
        raise ValueError("feeds.json has no enabled feeds with elementfm_show_id")
    return ws, out


def elementfm_base_url(*, workspace_id: str, show_id: str) -> str:
    return f"https://app.element.fm/api/workspaces/{workspace_id}/shows/{show_id}"


def _clear_elementfm_upload_state(entry: dict[str, Any]) -> None:
    for k in (
        "episode_id",
        "episode_number",
        "audio_uploaded",
        "published",
        "found_existing_by_title",
        "create_error",
        "upload_error",
        "publish_error",
    ):
        entry.pop(k, None)


def migrate_manifest_episodes_for_per_show_uploads(
    manifest: dict[str, Any],
    slug_to_show: dict[str, str],
    relevant_slugs: list[str],
) -> None:
    """
    Each slug uploads to its own Element.fm show. Legacy manifests stored all episode_ids
    on the news show; clear think/professional state when migrating so episodes are created
    on the correct show.
    """
    eps = manifest.setdefault("episodes", {})
    for slug in relevant_slugs:
        expected = slug_to_show.get(slug)
        if not expected:
            continue
        entry = eps.setdefault(slug, {})
        if not isinstance(entry, dict):
            entry = {}
            eps[slug] = entry
        stored_show = entry.get("elementfm_show_id")
        if stored_show == expected:
            continue
        if stored_show is None:
            if slug != "news" and entry.get("episode_id"):
                _clear_elementfm_upload_state(entry)
            entry["elementfm_show_id"] = expected
        else:
            _clear_elementfm_upload_state(entry)
            entry["elementfm_show_id"] = expected

