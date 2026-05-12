"""Build H3 hex features from raw_records using DuckDB and h3."""

from datetime import datetime
from pathlib import Path

import duckdb
import h3

DB_PATH = Path(__file__).parent.parent / "data" / "familiar_places.duckdb"


def _conn() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def build_hex_features(city: str, resolution: int = 9) -> int:
    """Aggregate raw points into normalized feature vectors by H3 cell."""
    con = _conn()
    rows = con.execute(
        "SELECT lat, lon, source FROM raw_records WHERE city = ?", [city]
    ).fetchall()
    if not rows:
        print(f"  No raw records for {city}")
        return 0

    hex_buckets = {}
    for lat, lon, source in rows:
        h = h3.latlng_to_cell(lat, lon, resolution)
        if h not in hex_buckets:
            hex_buckets[h] = {}
        hex_buckets[h][source] = hex_buckets[h].get(source, 0) + 1

    total_records = len(rows)
    n_hexes = len(hex_buckets)
    crime_max = max((v.get("crime", 0) for v in hex_buckets.values()), default=1) or 1
    permit_max = max((v.get("permits", 0) for v in hex_buckets.values()), default=1) or 1
    now = datetime.utcnow()

    con.execute("DELETE FROM hex_features WHERE city = ?", [city])
    con.executemany(
        """
        INSERT INTO hex_features
            (h3_index, city, crime_rate, permit_rate, transit_cnt, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                h3_idx,
                city,
                round(counts.get("crime", 0) / crime_max, 6),
                round(counts.get("permits", 0) / permit_max, 6),
                counts.get("transit", 0),
                now,
            )
            for h3_idx, counts in hex_buckets.items()
        ],
    )
    con.close()
    print(f"  {city}: {total_records:,} records -> {n_hexes:,} hexagons (res={resolution})")
    return n_hexes

