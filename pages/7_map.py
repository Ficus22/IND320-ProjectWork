# streamlit_app/pages/2_map.py
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from shapely.geometry import Point, shape
from pymongo import MongoClient
from streamlit_plotly_events2 import plotly_events

# ============================================================
# Page setup
# ============================================================
st.set_page_config(page_title="Price Area Map", layout="wide")
st.title("🗺️ Norwegian Price Areas Map (NO1–NO5)")

# ============================================================
# Cache Mongo + data loading (like teacher does w/ geojson)
# ============================================================
@st.cache_data
def load_elhub_data():
    MONGO_URI = st.secrets["MONGO_URI"]
    client = MongoClient(MONGO_URI)
    db = client["elhub_data"]
    coll = db["production_data"]
    df = pd.DataFrame(list(coll.find({})))
    df["start_time"] = pd.to_datetime(df["start_time"])
    return df

if "df_elhub" not in st.session_state:
    st.session_state.df_elhub = load_elhub_data()

df = st.session_state.df_elhub

# ============================================================
# Load GeoJSON (cached)
# ============================================================
@st.cache_data
def load_geojson():
    with open("data/price_zones.geojson", "r") as f:
        return json.load(f)

geojson_data = load_geojson()

# ============================================================
# Build shapely polygons once (cached in session)
# ============================================================
if "polygons" not in st.session_state:
    polys = []
    for feat in geojson_data.get("features", []):
        try:
            geom = shape(feat["geometry"])
            name = feat.get("properties", {}).get("name")
            polys.append((name, geom))  # store (areaName, geometry)
        except Exception:
            continue
    st.session_state.polygons = polys

def find_area_name(lon: float, lat: float):
    pt = Point(lon, lat)
    for area_name, geom in st.session_state.polygons:
        if geom.covers(pt):  # boundary-inclusive
            return area_name
    return None

# ============================================================
# Sidebar: time interval
# ============================================================
st.sidebar.header("⚙️ Settings")
days = st.sidebar.slider("Time interval (days)", 1, 30, 7)

date_max = df["start_time"].max()
date_min = date_max - pd.Timedelta(days=days)
df_period = df[(df["start_time"] >= date_min) & (df["start_time"] <= date_max)]

mean_df = df_period.groupby("price_area")["quantity_kwh"].mean().reset_index()
mean_df.columns = ["price_area", "mean_kwh"]

# ============================================================
# Init selected items same way teacher pre-selects last pin
# ============================================================
if "selected_area" not in st.session_state:
    st.session_state.selected_area = None
if "clicked_point" not in st.session_state:
    st.session_state.clicked_point = [64.5, 11.0]  # center of Norway

# Preselect initial area only once
if st.session_state.selected_area is None:
    lat, lon = st.session_state.clicked_point
    st.session_state.selected_area = find_area_name(lon, lat)

# ============================================================
# Build Plotly choropleth map
# ============================================================
fig = px.choropleth_mapbox(
    mean_df,
    geojson=geojson_data,
    locations="price_area",
    featureidkey="properties.name",
    color="mean_kwh",
    mapbox_style="carto-positron",
    zoom=4,
    center={"lat": 64.5, "lon": 11},
    opacity=0.5,
    labels={"mean_kwh": "Mean kWh"},
    color_continuous_scale="Oranges"
)

# Highlight selected area
if st.session_state.selected_area:
    fig.update_traces(marker_line_color="red", marker_line_width=4)

# ============================================================
# Capture clicks using teacher-style "single rerun"
# ============================================================
clicked = plotly_events(fig, click_event=True, hover_event=False)

if clicked:
    lat = clicked[0]["lat"]
    lon = clicked[0]["lon"]
    # Update exactly like teacher does
    st.session_state.clicked_point = [lat, lon]
    st.session_state.selected_area = find_area_name(lon, lat)
    st.rerun()

# Display map
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# Display selection
# ============================================================
st.subheader("📌 Selection")
st.write(f"Latitude:  {st.session_state.clicked_point[0]:.6f}")
st.write(f"Longitude: {st.session_state.clicked_point[1]:.6f}")

if st.session_state.selected_area:
    st.success(f"🏷️ Price Area: **{st.session_state.selected_area}**")
else:
    st.error("Outside known Price Areas ❌")

st.markdown("💡 Zoom and click inside a zone to highlight and display its average values.")