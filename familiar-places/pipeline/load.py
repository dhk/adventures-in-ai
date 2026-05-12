"""DuckDB operations: init schema, load raw NDJSON, query status."""

from pathlib import Path

import duckdb

DB_PATH = Path(__file__).parent.parent / "data" / "familiar_places.duckdb"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def _conn() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def init_db() -> None:
    """Create the app tables if they do not already exist."""
    con = _conn()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_records (
            city        VARCHAR NOT NULL,
            source      VARCHAR NOT NULL,
            lat         DOUBLE  NOT NULL,
            lon         DOUBLE  NOT NULL,
            fetched_at  TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS hex_features (
            h3_index    VARCHAR PRIMARY KEY,
            city        VARCHAR NOT NULL,
            crime_rate  DOUBLE,
            permit_rate DOUBLE,
            transit_cnt INTEGER,
            updated_at  TIMESTAMP DEFAULT current_timestamp
        )
        """
    )
    con.close()


def load_raw(city: str, source: str, ndjson_path: Path) -> int:
    """Replace raw records for one city/source from an NDJSON file."""
    init_db()
    con = _conn()
    con.execute("DELETE FROM raw_records WHERE city = ? AND source = ?", [city, source])
    n = con.execute(
        f"""
        INSERT INTO raw_records (city, source, lat, lon, fetched_at)
        SELECT
            '{city}'                           AS city,
            '{source}'                         AS source,
            CAST(_lat AS DOUBLE)               AS lat,
            CAST(_lon AS DOUBLE)               AS lon,
            TRY_CAST(_fetched_at AS TIMESTAMP) AS fetched_at
        FROM read_ndjson_auto('{ndjson_path}')
        """
    ).fetchone()[0]
    con.close()
    return n


def get_db_status() -> list[dict]:
    """Return counts for loaded raw records by city/source."""
    if not DB_PATH.exists():
        return []
    con = _conn()
    try:
        rows = con.execute(
            """
            SELECT
                city,
                source,
                COUNT(*)        AS records,
                MAX(fetched_at) AS last_fetched
            FROM raw_records
            GROUP BY city, source
            ORDER BY city, source
            """
        ).fetchall()
    except duckdb.CatalogException:
        rows = []
    finally:
        con.close()
    return [
        {"city": r[0], "source": r[1], "records": r[2], "last_fetched": r[3]}
        for r in rows
    ]


def get_raw_file_status() -> list[dict]:
    """Return counts and sizes for cached raw NDJSON files."""
    results = []
    for f in sorted(RAW_DIR.glob("*.ndjson")):
        parts = f.stem.split("__", 1)
        city = parts[0] if len(parts) > 1 else "?"
        source = parts[1] if len(parts) > 1 else parts[0]
        size_kb = f.stat().st_size // 1024
        with open(f) as fh:
            line_count = sum(1 for _ in fh)
        results.append(
            {
                "file": f.name,
                "city": city,
                "source": source,
                "records": line_count,
                "size_kb": size_kb,
            }
        )
    return results

