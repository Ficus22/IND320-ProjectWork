# streamlit_app/pages/2_map.py
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from shapely.geometry import Point, shape
from pymongo import MongoClient
import streamlit.components.v1 as components
from streamlit_plotly_events import plotly_events


# ============================================================
# Page title
# ============================================================
st.set_page_config(page_title="Price Area Map", layout="wide")
st.title("🗺️ Norwegian Price Areas Map (NO1–NO5)")

# ============================================================
# MongoDB connection
# ============================================================
if "df_elhub" not in st.session_state:
    MONGO_URI = st.secrets["MONGO_URI"]
    client = MongoClient(MONGO_URI)
    db = client["elhub_data"]
    collection = db["production_data"]
    data = list(collection.find({}))
    df = pd.DataFrame(data)
    df["start_time"] = pd.to_datetime(df["start_time"])
    st.session_state.df_elhub = df
else:
    df = st.session_state.df_elhub

# ============================================================
# Load GeoJSON in repo
# ============================================================
with open("data/price_zones.geojson", "r") as f:
    geojson = json.load(f)

# ============================================================
# UI Filters
# ============================================================
st.sidebar.header("⚙️ Settings")

days = st.sidebar.slider("Time interval (days)", 1, 30, 7)

date_max = df["start_time"].max()
date_min = date_max - pd.Timedelta(days=days)

df_period = df[(df["start_time"] >= date_min) & (df["start_time"] <= date_max)]

mean_df = df_period.groupby("price_area")["quantity_kwh"].mean().reset_index()
mean_df.columns = ["price_area", "mean_kwh"]

# ============================================================
# Click storage in session state
# ============================================================
if "clicked_point" not in st.session_state:
    st.session_state.clicked_point = None
if "selected_area" not in st.session_state:
    st.session_state.selected_area = None

# Function to detect area from lon/lat
def detect_area(lon, lat):
    pt = Point(lon, lat)
    for feat in geojson["features"]:
        geom = shape(feat["geometry"])
        if geom.contains(pt):
            return feat["properties"].get("name", None)
    return None

# ============================================================
# Create Plotly Map
# ============================================================
fig = px.choropleth_mapbox(
    mean_df,
    geojson=geojson,
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

# Highlight selected area if exists
if st.session_state.selected_area:
    fig.update_traces(marker_line_color="red", marker_line_width=4)

clicked_points = plotly_events(fig, click_event=True, hover_event=False)

if clicked_points:
    lat = clicked_points[0]["lat"]
    lon = clicked_points[0]["lon"]
    st.session_state.clicked_point = (lat, lon)
    st.session_state.selected_area = detect_area(lon, lat)


# ============================================================
# Inject JS to capture Plotly click
# ============================================================
components.html("""
<script>
const plot = window.parent.document.querySelector('iframe[title="Plotly Chart"]');
function sendData(lat, lon){
    window.parent.postMessage({type: "map_click", lat: lat, lon: lon}, "*");
}
if(plot){
  plot.onload = function(){
    const plotDoc = plot.contentWindow.document.querySelector('div.js-plotly-plot');
    plotDoc.on('plotly_click', function(data){
      const point = data.points[0];
      sendData(point.lat, point.lon);
    });
  };
}
</script>
""", height=0)

# ============================================================
# Listen to messages from JS
# ============================================================
msg = st.experimental_get_query_params()

if "lat" in msg and "lon" in msg:
    lat = float(msg["lat"][0])
    lon = float(msg["lon"][0])
    st.session_state.clicked_point = (lat, lon)
    st.session_state.selected_area = detect_area(lon, lat)

# ============================================================
# Display results
# ============================================================
st.write("### 📌 Clicked coordinates:", st.session_state.clicked_point)
st.write("### 🏷️ Detected Price Area:", st.session_state.selected_area)
st.markdown("---")
st.markdown("💡 Tip: Zoom and click inside a zone to highlight and get its average values.")