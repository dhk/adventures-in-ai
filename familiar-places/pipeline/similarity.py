"""Neighborhood similarity engine: cosine similarity over H3 hex feature vectors."""

from pathlib import Path

import duckdb
import h3
import numpy as np
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "familiar_places.duckdb"
ALL_FEATURES = ["crime_rate", "permit_rate", "transit_norm"]
DEFAULT_FEATURE_WEIGHTS = {feature: 1.0 for feature in ALL_FEATURES}


def load_features() -> pd.DataFrame:
    """Load and normalize hex features for similarity search."""
    con = duckdb.connect(str(DB_PATH))
    df = con.execute(
        """
        SELECT h3_index, city, crime_rate, permit_rate, transit_cnt
        FROM hex_features
        ORDER BY city, h3_index
        """
    ).df()
    con.close()

    if df.empty:
        df.attrs["dead_features"] = []
        df.attrs["live_features"] = ALL_FEATURES
        return df

    t_max = df["transit_cnt"].max() or 1
    df["transit_norm"] = df["transit_cnt"] / t_max

    for col in ("crime_rate", "permit_rate", "transit_norm"):
        lo, hi = df[col].min(), df[col].max()
        df[col] = (df[col] - lo) / (hi - lo + 1e-9)

    dead = []
    for city in df["city"].unique():
        city_df = df[df["city"] == city]
        for col in ALL_FEATURES:
            if city_df[col].std() < 1e-6:
                dead.append(col)

    df.attrs["dead_features"] = list(set(dead))
    df.attrs["live_features"] = [f for f in ALL_FEATURES if f not in df.attrs["dead_features"]]
    return df


def _active_features(df: pd.DataFrame, cross_city: bool) -> list[str]:
    if cross_city:
        return df.attrs.get("live_features", ALL_FEATURES)
    return ALL_FEATURES


def _feature_weights(
    features: list[str],
    feature_weights: dict[str, float] | None = None,
) -> np.ndarray:
    weights = feature_weights or DEFAULT_FEATURE_WEIGHTS
    values = np.array(
        [max(float(weights.get(feature, 1.0)), 0.0) for feature in features],
        dtype=np.float32,
    )
    if not values.any():
        values = np.ones(len(features), dtype=np.float32)
    return values


def _feature_matrix(
    df: pd.DataFrame,
    features: list[str],
    feature_weights: dict[str, float] | None = None,
) -> np.ndarray:
    return df[features].to_numpy(dtype=np.float32) * _feature_weights(
        features, feature_weights
    )


def score_similarities(
    query_h3: str,
    df: pd.DataFrame | None = None,
    cross_city: bool = True,
    feature_weights: dict[str, float] | None = None,
    include_query: bool = True,
) -> pd.DataFrame:
    """Score all candidate H3 cells against a query cell."""
    if df is None:
        df = load_features()
    if query_h3 not in df["h3_index"].values:
        raise ValueError(f"H3 index {query_h3!r} not found in hex_features")

    query_city = df.loc[df["h3_index"] == query_h3, "city"].iloc[0]
    candidates = df if cross_city else df[df["city"] == query_city]
    features = _active_features(df, cross_city)

    mat = _feature_matrix(candidates, features, feature_weights)
    q_vec = _feature_matrix(df[df["h3_index"] == query_h3], features, feature_weights)
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)
    mat_norms = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    sims = (mat_norms @ q_norm.T).ravel()

    result = candidates[
        ["h3_index", "city", "crime_rate", "permit_rate", "transit_cnt"]
    ].copy()
    result["similarity"] = sims
    if not include_query:
        result = result[result["h3_index"] != query_h3]
    return result.sort_values("similarity", ascending=False).reset_index(drop=True)


def find_similar(
    query_h3: str,
    df: pd.DataFrame | None = None,
    top_n: int = 10,
    cross_city: bool = True,
    feature_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Find the most similar H3 cells to a query cell."""
    return (
        score_similarities(
            query_h3,
            df=df,
            cross_city=cross_city,
            feature_weights=feature_weights,
            include_query=False,
        )
        .head(top_n)
        .reset_index(drop=True)
    )


def hex_to_latlon(h3_index: str) -> tuple[float, float]:
    """Return the latitude/longitude center for an H3 cell."""
    lat, lon = h3.cell_to_latlng(h3_index)
    return lat, lon


def sample_hex(city: str, df: pd.DataFrame | None = None) -> str:
    """Pick a random H3 cell for a city."""
    if df is None:
        df = load_features()
    subset = df[df["city"] == city]
    if subset.empty:
        raise ValueError(f"No hexagons for city '{city}'")
    return subset.sample(1)["h3_index"].iloc[0]

