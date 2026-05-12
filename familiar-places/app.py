"""Streamlit app for finding familiar-feeling neighborhoods."""

from typing import Any

import h3
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from demo_data import seed_demo_data
from pipeline.load import get_db_status, get_raw_file_status, init_db
from pipeline.similarity import find_similar, hex_to_latlon, load_features, score_similarities

st.set_page_config(page_title="Familiar Places", page_icon="FP", layout="wide")

SIMILARITY_PALETTE = [
    [49, 54, 149, 210],
    [69, 117, 180, 210],
    [116, 173, 209, 210],
    [171, 217, 233, 210],
    [224, 243, 248, 210],
    [254, 224, 144, 220],
    [253, 174, 97, 225],
    [244, 109, 67, 230],
    [215, 48, 39, 235],
    [165, 0, 38, 240],
]
DEFAULT_FILL = [148, 163, 184, 90]
MATCH_FILL = [255, 145, 77, 220]
QUERY_FILL = [34, 197, 94, 240]
FEATURE_CONTROLS = [
    ("crime_rate", "Crime"),
    ("permit_rate", "Permits"),
    ("transit_norm", "Transit"),
]


def _hex_polygon(h3_index: str) -> list[list[float]]:
    return [[lon, lat] for lat, lon in h3.cell_to_boundary(h3_index)]


def _style_hexes(
    map_df: pd.DataFrame,
    query_h3: str,
    matches: pd.DataFrame,
    color_mode: str,
) -> pd.DataFrame:
    styled = map_df.copy()
    styled["polygon"] = styled["h3_index"].map(_hex_polygon)
    styled["fill_color"] = [DEFAULT_FILL for _ in range(len(styled))]
    styled["bucket"] = "not in top matches"

    if color_mode == "Similarity stack":
        ranks = styled["similarity"].rank(pct=True, method="first")
        bucket_idx = np.clip(np.ceil(ranks * 10).astype(int) - 1, 0, 9)
        styled["fill_color"] = [SIMILARITY_PALETTE[i] for i in bucket_idx]
        styled["bucket"] = bucket_idx.map(lambda i: f"{int(i) * 10}-{int(i + 1) * 10}%")
    else:
        match_hexes = set(matches["h3_index"])
        match_mask = styled["h3_index"].isin(match_hexes)
        styled.loc[match_mask, "fill_color"] = [MATCH_FILL] * match_mask.sum()
        styled.loc[match_mask, "bucket"] = "top match"

    query_mask = styled["h3_index"] == query_h3
    styled.loc[query_mask, "fill_color"] = [QUERY_FILL] * query_mask.sum()
    styled.loc[query_mask, "bucket"] = "selected hex"
    styled["similarity_label"] = styled["similarity"].map(lambda x: f"{x:.3f}")
    return styled


def _deck_for_hexes(map_df: pd.DataFrame) -> pdk.Deck:
    if map_df.empty:
        return pdk.Deck(layers=[])

    center_lat = map_df["lat"].mean()
    center_lon = map_df["lon"].mean()
    layer = pdk.Layer(
        "PolygonLayer",
        data=map_df,
        get_polygon="polygon",
        get_fill_color="fill_color",
        get_line_color=[15, 23, 42, 160],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )
    return pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10,
            pitch=0,
        ),
        map_style=None,
        tooltip={
            "html": "<b>{city}</b><br/>Similarity: {similarity_label}<br/>{bucket}<br/><small>{h3_index}</small>",
            "style": {"backgroundColor": "#111827", "color": "white"},
        },
    )


def _find_h3(value: Any) -> str | None:
    if hasattr(value, "selection"):
        return _find_h3(value.selection)
    if isinstance(value, dict):
        if isinstance(value.get("h3_index"), str):
            return value["h3_index"]
        for child in value.values():
            found = _find_h3(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_h3(child)
            if found:
                return found
    return None


def _render_hex_map(title: str, map_df: pd.DataFrame, key: str) -> str | None:
    st.caption(title)
    event = st.pydeck_chart(
        _deck_for_hexes(map_df),
        key=key,
        on_select="rerun",
        selection_mode="single-object",
        use_container_width=True,
    )
    return _find_h3(event)


def _default_weights() -> dict[str, float]:
    return {feature: 1.0 for feature, _label in FEATURE_CONTROLS}


st.title("Familiar Places")
st.caption("Compare neighborhoods by the shape of nearby civic signals.")

init_db()

with st.sidebar:
    st.header("Data")
    if st.button("Seed demo data", use_container_width=True):
        with st.spinner("Building demo city features..."):
            seed_demo_data()
        st.success("Demo data loaded")

    db_status = pd.DataFrame(get_db_status())
    raw_status = pd.DataFrame(get_raw_file_status())
    st.subheader("Loaded records")
    st.dataframe(db_status if not db_status.empty else pd.DataFrame(), use_container_width=True)
    with st.expander("Raw files"):
        st.dataframe(raw_status if not raw_status.empty else pd.DataFrame(), use_container_width=True)

try:
    df = load_features()
except Exception as exc:
    df = pd.DataFrame()
    st.info("No feature database yet. Use Seed demo data to create a local dataset.")
    st.caption(str(exc))

if df.empty:
    st.stop()

cities = sorted(df["city"].unique())
control_cols = st.columns([0.22, 0.3, 0.22, 0.14, 0.12], gap="medium")
with control_cols[0]:
    default_city = st.session_state.get("query_city")
    city_index = cities.index(default_city) if default_city in cities else 0
    city = st.selectbox("Query city", cities, index=city_index)
city_df = df[df["city"] == city].copy()

if (
    st.session_state.get("query_h3") not in set(city_df["h3_index"])
    or st.session_state.get("query_city") != city
):
    if st.session_state.get("query_city") != city and st.session_state.get("query_city"):
        st.session_state["has_selected_hex"] = True
    st.session_state["query_h3"] = city_df["h3_index"].iloc[0]
    st.session_state["query_city"] = city

with control_cols[1]:
    query_h3 = st.selectbox(
        "Query hex",
        city_df["h3_index"].tolist(),
        index=city_df["h3_index"].tolist().index(st.session_state["query_h3"]),
    )
with control_cols[2]:
    color_mode = st.selectbox("Map mode", ["Top matches", "Similarity stack"])
with control_cols[3]:
    cross_city = st.toggle("Across cities", value=True)
with control_cols[4]:
    top_n = st.slider("Matches", 3, 25, 10)

if query_h3 != st.session_state["query_h3"]:
    st.session_state["query_h3"] = query_h3
    st.session_state["has_selected_hex"] = True

if "applied_weights" not in st.session_state:
    st.session_state["applied_weights"] = _default_weights()

st.write("Dimension weights")
weight_cols = st.columns(len(FEATURE_CONTROLS), gap="medium")
pending_weights = {}
for idx, (feature, label) in enumerate(FEATURE_CONTROLS):
    with weight_cols[idx]:
        pending_weights[feature] = (
            st.slider(
                label,
                min_value=0,
                max_value=100,
                value=int(st.session_state["applied_weights"].get(feature, 1.0) * 100),
                step=5,
                format="%d%%",
                key=f"weight_{feature}",
            )
            / 100
        )

weights_changed = pending_weights != st.session_state["applied_weights"]
if not st.session_state.get("has_selected_hex"):
    st.session_state["applied_weights"] = pending_weights
elif weights_changed:
    apply_cols = st.columns([0.2, 0.8])
    with apply_cols[0]:
        if st.button("Apply weights", type="primary", use_container_width=True):
            st.session_state["applied_weights"] = pending_weights
            st.rerun()
    with apply_cols[1]:
        st.caption("Pending weights will redraw the maps around the current selected hex.")

active_weights = st.session_state["applied_weights"]

query_lat, query_lon = hex_to_latlon(st.session_state["query_h3"])
summary_cols = st.columns(3)
summary_cols[0].metric("Available hexes", f"{len(df):,}")
summary_cols[1].metric("Query center", f"{query_lat:.4f}, {query_lon:.4f}")
summary_cols[2].metric("Color bands", "10% deciles" if color_mode == "Similarity stack" else "Top matches")

matches = find_similar(
    st.session_state["query_h3"],
    df=df,
    top_n=top_n,
    cross_city=cross_city,
    feature_weights=active_weights,
)
scores = score_similarities(
    st.session_state["query_h3"],
    df=df,
    cross_city=cross_city,
    feature_weights=active_weights,
)
scores[["lat", "lon"]] = scores["h3_index"].apply(lambda h: pd.Series(hex_to_latlon(h)))
styled_scores = _style_hexes(scores, st.session_state["query_h3"], matches, color_mode)

query_map = styled_scores[styled_scores["city"] == city].copy()
comparison_map = styled_scores[styled_scores["city"] != city].copy()
if comparison_map.empty:
    comparison_map = styled_scores.copy()

if color_mode == "Similarity stack":
    st.info(
        "Similarity stack uses 10% decile bands across the current comparison set: deep red is most similar, deep blue is least similar. Click any hex on either map to restack both maps around that hex."
    )
else:
    st.caption("Click any hex on either map to use it as the query cell.")

map_cols = st.columns(2, gap="large")
with map_cols[0]:
    clicked_h3 = _render_hex_map(f"{city} query map", query_map, "query-map")
with map_cols[1]:
    compared_title = "Comparison map" if cross_city else f"{city} comparison map"
    clicked_comparison_h3 = _render_hex_map(compared_title, comparison_map, "comparison-map")

new_query_h3 = clicked_h3 or clicked_comparison_h3
if new_query_h3 and new_query_h3 != st.session_state["query_h3"]:
    selected_city = df.loc[df["h3_index"] == new_query_h3, "city"].iloc[0]
    st.session_state["query_h3"] = new_query_h3
    st.session_state["query_city"] = selected_city
    st.session_state["has_selected_hex"] = True
    st.rerun()

st.subheader("Most Familiar Matches")
display = matches.copy()
display["similarity"] = display["similarity"].map(lambda x: f"{x:.3f}")
st.dataframe(
    display[["city", "similarity", "crime_rate", "permit_rate", "transit_cnt", "h3_index"]],
    use_container_width=True,
    hide_index=True,
)

