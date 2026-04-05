from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ElementFmConfig:
    api_key: str
    workspace_id: str
    show_id: str
    base_url: str


def _json_loads_safe(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


class ElementFmClient:
    def __init__(
        self,
        cfg: ElementFmConfig,
        *,
        timeout_s: float = 30.0,
        upload_timeout_s: float | None = None,
        retries: int = 3,
        initial_backoff_s: float = 1.0,
        backoff_mult: float = 2.0,
    ):
        self.cfg = cfg
        self.timeout_s = timeout_s
        # Large MP3 multipart uploads need a much higher ceiling than JSON calls.
        self.upload_timeout_s = upload_timeout_s if upload_timeout_s is not None else max(600.0, timeout_s * 5)
        self.retries = retries
        self.initial_backoff_s = initial_backoff_s
        self.backoff_mult = backoff_mult

    def request(
        self,
        method: str,
        path: str,
        *,
        data: Any | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to element.fm API and return a dict.
        Retries on transient errors (HTTP 5xx, 429, URLError).
        """
        url = self.cfg.base_url + path
        headers = {"Authorization": f"Token {self.cfg.api_key}"}
        body: bytes | None = None

        if files:
            boundary = "----ElementFMBoundary"
            parts: list[bytes] = []
            for name, (filename, filedata, content_type) in files.items():
                parts.append(f"--{boundary}\r\n".encode())
                parts.append(
                    (
                        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                        f"Content-Type: {content_type}\r\n\r\n"
                    ).encode()
                )
                parts.append(filedata)
                parts.append(b"\r\n")
            parts.append(f"--{boundary}--\r\n".encode())
            body = b"".join(parts)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if files:
            effective_timeout = timeout_s if timeout_s is not None else self.upload_timeout_s
        else:
            effective_timeout = timeout_s if timeout_s is not None else self.timeout_s

        max_attempts = self.retries + 1
        if files:
            max_attempts = max(max_attempts, 6)

        backoff = self.initial_backoff_s
        for i in range(max_attempts):
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                    parsed = _json_loads_safe(resp.read())
                    return parsed if isinstance(parsed, dict) else {"error": "Non-JSON response"}
            except urllib.error.HTTPError as e:
                raw = e.read()
                parsed = _json_loads_safe(raw)
                if isinstance(parsed, dict):
                    # Handle rate limiting / transient failures with retries
                    if e.code in (429,) or (500 <= e.code <= 599):
                        if i < max_attempts - 1:
                            time.sleep(backoff)
                            backoff *= self.backoff_mult
                            continue
                    return parsed
                msg = raw.decode("utf-8", errors="replace")
                if e.code in (429,) or (500 <= e.code <= 599):
                    if i < max_attempts - 1:
                        time.sleep(backoff)
                        backoff *= self.backoff_mult
                        continue
                return {"error": f"HTTP {e.code}: {msg[:500]}"}
            except urllib.error.URLError as e:
                if i < max_attempts - 1:
                    time.sleep(backoff)
                    backoff *= self.backoff_mult
                    continue
                return {"error": f"URL error: {e}"}
            except Exception as e:
                if i < max_attempts - 1:
                    time.sleep(backoff)
                    backoff *= self.backoff_mult
                    continue
                return {"error": f"Request error: {e}"}

        return {"error": "Request failed after retries"}

    def list_episodes(self) -> list[dict[str, Any]]:
        """
        Returns all episodes, handling pagination (API returns 10 per page).
        """
        all_episodes: list[dict[str, Any]] = []
        page = 1
        while True:
            result = self.request("GET", f"/episodes?page={page}")
            batch: list[dict[str, Any]] = []
            for key in ("episodes", "results", "items", "data"):
                value = result.get(key)
                if isinstance(value, list):
                    batch = [e for e in value if isinstance(e, dict)]
                    break
            if not batch:
                if isinstance(result.get("episodes"), dict):
                    inner = result["episodes"].get("results")
                    if isinstance(inner, list):
                        batch = [e for e in inner if isinstance(e, dict)]
            if not batch:
                break
            all_episodes.extend(batch)
            total = result.get("total_episodes", 0)
            if len(all_episodes) >= total:
                break
            page += 1
        return all_episodes

    def total_episodes(self) -> int:
        result = self.request("GET", "/episodes")
        val = result.get("total_episodes")
        return int(val) if isinstance(val, int) else 0

    def find_episode_by_title(self, title: str) -> Optional[dict[str, Any]]:
        title_norm = title.strip()
        for ep in self.list_episodes():
            if str(ep.get("title", "")).strip() == title_norm:
                return ep
        return None

    def get_next_episode_number(self) -> int:
        # Best-effort: keep existing behavior if total_episodes is exposed.
        return self.total_episodes() + 1

    def create_episode(
        self,
        *,
        title: str,
        season_number: int,
        episode_number: int,
        description: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "season_number": season_number,
            "episode_number": episode_number,
        }
        if description:
            payload["description"] = description
        return self.request("POST", "/episodes", data=payload)

    def patch_episode(self, *, episode_id: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/episodes/{episode_id}", data=data)

    def upload_audio(self, *, episode_id: str, mp3_path: Path) -> dict[str, Any]:
        audio_data = mp3_path.read_bytes()
        size = len(audio_data)
        # Rough floor from file size: assume ~200 KiB/s effective upload; cap 1 hour.
        size_based = max(300.0, min(3600.0, (size / (200 * 1024)) * 8))
        upload_timeout = max(self.upload_timeout_s, size_based)
        return self.request(
            "POST",
            f"/episodes/{episode_id}/audio",
            files={"audio": (mp3_path.name, audio_data, "audio/mpeg")},
            timeout_s=upload_timeout,
        )

    def publish_episode(self, *, episode_id: str) -> dict[str, Any]:
        return self.request("POST", f"/episodes/{episode_id}/publish")

