"""Small deterministic dataset for trying Familiar Places locally."""

import json
import random
from datetime import datetime

from pipeline.load import RAW_DIR, init_db, load_raw
from pipeline.score import build_hex_features

CITIES = {
    "Oakland": (37.8044, -122.2712),
    "Portland": (45.5152, -122.6784),
    "Chicago": (41.8781, -87.6298),
}
SOURCES = ("crime", "permits", "transit")


def _points(lat: float, lon: float, source: str, count: int, rng: random.Random) -> list[dict]:
    spread = {"crime": 0.045, "permits": 0.035, "transit": 0.025}[source]
    bias = {"crime": (-0.012, 0.006), "permits": (0.014, -0.014), "transit": (0.0, 0.0)}[source]
    rows = []
    for i in range(count):
        rows.append(
            {
                "id": f"{source}-{i}",
                "_lat": lat + bias[0] + rng.uniform(-spread, spread),
                "_lon": lon + bias[1] + rng.uniform(-spread, spread),
                "_fetched_at": datetime.utcnow().isoformat(),
            }
        )
    return rows


def seed_demo_data(records_per_source: int = 120, resolution: int = 8) -> None:
    """Create demo NDJSON, load DuckDB, and build hex features."""
    rng = random.Random(42)
    init_db()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for city, (lat, lon) in CITIES.items():
        for source in SOURCES:
            out = RAW_DIR / f"{city}__{source}.ndjson"
            with open(out, "w") as f:
                for row in _points(lat, lon, source, records_per_source, rng):
                    f.write(json.dumps(row) + "\n")
            load_raw(city, source, out)
        build_hex_features(city, resolution)


if __name__ == "__main__":
    seed_demo_data()

