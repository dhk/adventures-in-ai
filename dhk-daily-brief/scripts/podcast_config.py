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


CONFIG_PATH = Path.home() / ".config" / "dhk-daily-brief" / "config.json"
STATE_DIR = Path.home() / ".local" / "state" / "dhk-daily-brief"


CATEGORY_SLUGS: dict[str, str] = {
    "📰 News & Current Affairs": "news",
    "🧠 Things to Think About": "think",
    "💼 Professional Reading": "professional",
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
      2) ~/.config/dhk-daily-brief/config.json (audio_dir)
      3) DEFAULT_AUDIO_DIR (iCloud Personal Podcast)
    """
    if cli_audio_dir:
        return Path(cli_audio_dir).expanduser()

    cfg = _read_json(CONFIG_PATH)
    audio_dir = cfg.get("audio_dir")
    if isinstance(audio_dir, str) and audio_dir.strip():
        return Path(audio_dir).expanduser()

    env_audio_dir = os.environ.get("DHK_DAILY_BRIEF_AUDIO_DIR")
    if isinstance(env_audio_dir, str) and env_audio_dir.strip():
        return Path(env_audio_dir).expanduser()

    return DEFAULT_AUDIO_DIR


def resolve_audio_format(*, cli_audio_format: Optional[str] = None) -> str:
    """
    Resolve output audio format precedence:
      1) CLI override (--audio-format)
      2) ~/.config/dhk-daily-brief/config.json (audio_format)
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
        return "DHK Daily Brief — personal reading-list audio overview."
    return f"DHK Daily Brief — {t}"


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
    Map NotebookLM notebook category segment (after date/nn) to news | think | professional.
    Handles minor title variations (e.g. 'and' vs '&', missing emoji).
    """
    if not category_title:
        return None
    ct = category_title.strip()
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
    # Emoji fallback — emoji in the notebook title is a reliable category signal
    if "📰" in ct:
        return "news"
    if "🧠" in ct:
        return "think"
    if "💼" in ct:
        return "professional"
    # Keyword fallbacks
    if "professional" in norm and "reading" in norm:
        return "professional"
    if "things to think" in norm:
        return "think"
    if "news" in norm:
        return "news"
    if "reading" in norm and ("weekend" in norm or "weekly" in norm or "today" in norm):
        return "news"
    return None


def slug_for_category_title(category_title: str) -> Optional[str]:
    """Backward-compatible name; use category_title_to_slug."""
    return category_title_to_slug(category_title)

