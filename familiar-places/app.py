"""Streamlit app for finding familiar-feeling neighborhoods."""

import pandas as pd
import streamlit as st

from demo_data import seed_demo_data
from pipeline.load import get_db_status, get_raw_file_status, init_db
from pipeline.similarity import find_similar, hex_to_latlon, load_features

st.set_page_config(page_title="Familiar Places", page_icon="FP", layout="wide")

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

left, right = st.columns([0.34, 0.66], gap="large")

with left:
    cities = sorted(df["city"].unique())
    city = st.selectbox("Query city", cities)
    city_df = df[df["city"] == city].copy()
    query_h3 = st.selectbox("Query hex", city_df["h3_index"].tolist())
    cross_city = st.toggle("Compare across cities", value=True)
    top_n = st.slider("Matches", 3, 25, 10)

    query_lat, query_lon = hex_to_latlon(query_h3)
    st.metric("Available hexes", f"{len(df):,}")
    st.metric("Query center", f"{query_lat:.4f}, {query_lon:.4f}")

matches = find_similar(query_h3, df=df, top_n=top_n, cross_city=cross_city)
matches[["lat", "lon"]] = matches["h3_index"].apply(
    lambda h: pd.Series(hex_to_latlon(h))
)
query_point = pd.DataFrame(
    [{"lat": query_lat, "lon": query_lon, "city": city, "similarity": 1.0}]
)

with right:
    st.subheader("Most Familiar Matches")
    st.map(
        pd.concat([query_point, matches[["lat", "lon", "city", "similarity"]]], ignore_index=True),
        latitude="lat",
        longitude="lon",
        size=90,
        color="#1677ff",
    )

    display = matches.copy()
    display["similarity"] = display["similarity"].map(lambda x: f"{x:.3f}")
    st.dataframe(
        display[
            ["city", "similarity", "crime_rate", "permit_rate", "transit_cnt", "h3_index"]
        ],
        use_container_width=True,
        hide_index=True,
    )

