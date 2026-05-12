"""Fetch raw data from open data portals using the Socrata API."""

import json
import time
from datetime import datetime
from pathlib import Path

import httpx

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
SOCRATA_LIMIT = 1000


def fetch_source(city: str, source: str, cfg: dict) -> Path:
    """Fetch one configured Socrata source and cache normalized NDJSON."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{city}__{source}.ndjson"

    url = cfg["url"]
    limit = cfg.get("limit", 10000)
    extra_params = cfg.get("params", {})
    coord_format = cfg.get("coord_format", "columns")
    coord_col = cfg.get("coord_col")
    lat_col = cfg.get("lat_col")
    lon_col = cfg.get("lon_col")

    print(f"  Fetching {city}/{source} from {url}")
    print(f"  Target: up to {limit:,} records")

    records = _socrata_fetch(
        url, limit, extra_params, lat_col, lon_col, coord_format, coord_col
    )
    with open(out_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"  Saved {len(records):,} records -> {out_path.name}")
    return out_path


def _socrata_fetch(
    url: str,
    limit: int,
    extra_params: dict,
    lat_col: str | None,
    lon_col: str | None,
    coord_format: str,
    coord_col: str | None = None,
) -> list[dict]:
    records = []
    offset = 0
    page_size = min(SOCRATA_LIMIT, limit)

    with httpx.Client(timeout=30) as client:
        while len(records) < limit:
            params = {"$limit": page_size, "$offset": offset}
            params.update(extra_params)

            resp = client.get(url, params=params)
            resp.raise_for_status()
            page = resp.json()
            if not page:
                break

            for rec in page:
                lat, lon = _extract_coords(rec, coord_format, lat_col, lon_col, coord_col)
                if lat is not None and lon is not None:
                    rec["_lat"] = lat
                    rec["_lon"] = lon
                    rec["_fetched_at"] = datetime.utcnow().isoformat()
                    records.append(rec)

            offset += len(page)
            print(f"    page offset={offset}, collected={len(records)}", end="\r")
            if len(page) < page_size:
                break
            time.sleep(0.1)

    print()
    return records


def _extract_coords(
    rec: dict,
    coord_format: str,
    lat_col: str | None,
    lon_col: str | None,
    coord_col: str | None,
) -> tuple[float | None, float | None]:
    try:
        if coord_format == "geojson_point":
            pt = rec.get(coord_col)
            if pt and isinstance(pt, dict) and pt.get("type") == "Point":
                lon, lat = pt["coordinates"]
                return float(lat), float(lon)
        else:
            lat = rec.get(lat_col)
            lon = rec.get(lon_col)
            if lat and lon:
                return float(lat), float(lon)
    except (TypeError, ValueError, KeyError, IndexError):
        pass
    return None, None

