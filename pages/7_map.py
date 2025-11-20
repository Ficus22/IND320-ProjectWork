# streamlit_app/pages/2_map.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
from shapely.geometry import shape, Point
from pymongo import MongoClient

# -----------------------
# Page config
# -----------------------
st.set_page_config(page_title="Price Areas", layout="wide")
st.title("Choropleth + Single Click Pin (NO1–NO5)")

# -----------------------
# Load GeoJSON (cached)
# -----------------------
@st.cache_data
def load_geojson(path="data/price_zones.geojson"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

geojson_data = load_geojson()

# -----------------------
# Build id -> name mapping (cached)
# -----------------------
@st.cache_data
def build_id_to_name(gj):
    out = {}
    for f in gj.get("features", []):
        fid = f.get("id") or (f.get("properties") or {}).get("id")
        if fid is None:
            continue
        # Try several common property names
        props = f.get("properties") or {}
        name = props.get("ElSpotOmr") or props.get("ElSpotOmråde") or props.get("name") or props.get("navn") or props.get("ElSpot_omraade")
        if name is None:
            # fallback: check for any property that looks like a code (NO1..NO5)
            # join values and look for NO1..NO5
            for v in props.values():
                if isinstance(v, str) and v.strip().upper().startswith("NO"):
                    name = v.strip().upper()
                    break
        if name is None:
            # last fallback: use stringified id
            name = str(fid)
        out[fid] = str(name)
    return out

id_to_name = build_id_to_name(geojson_data)

# -----------------------
# Build shapely polygons once and store in session_state
# -----------------------
if "polygons" not in st.session_state:
    polys = []
    for feat in geojson_data.get("features", []):
        fid = feat.get("id") or (feat.get("properties") or {}).get("id")
        if fid is None:
            continue
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        polys.append((fid, geom))
    st.session_state.polygons = polys

def find_feature_id(lon: float, lat: float):
    """Return the feature id that covers the given lon/lat (or None)."""
    pt = Point(lon, lat)
    for fid, geom in st.session_state.polygons:
        # use covers for boundary-inclusive test (matches teacher)
        if geom.covers(pt):
            return fid
    return None

# -----------------------
# Load production/consumption data (from session_state or Mongo)
# -----------------------
# If you already loaded df elsewhere, put it in st.session_state['df_elhub'] before opening this page,
# otherwise this will connect to Mongo to fetch it.
if "df_elhub" not in st.session_state:
    # Try to fetch from Mongo (will require st.secrets["MONGO_URI"])
    try:
        MONGO_URI = st.secrets["MONGO_URI"]
        client = MongoClient(MONGO_URI)
        db = client["elhub_data"]
        coll = db["production_data"]
        df = pd.DataFrame(list(coll.find({})))
        if "start_time" in df.columns:
            df["start_time"] = pd.to_datetime(df["start_time"])
        st.session_state.df_elhub = df
    except Exception:
        # If Mongo fails, create an empty df to avoid crashes
        st.session_state.df_elhub = pd.DataFrame(columns=["price_area", "start_time", "quantity_kwh"])

df = st.session_state.df_elhub

# -----------------------
# Sidebar filters
# -----------------------
st.sidebar.header("Settings")
days = st.sidebar.slider("Time interval (days)", 1, 30, 7)

# if df has no start_time or quantity_kwh, produce empty values map
if "start_time" in df.columns and "quantity_kwh" in df.columns and "price_area" in df.columns and not df.empty:
    date_max = df["start_time"].max()
    date_min = date_max - pd.Timedelta(days=days)
    df_period = df[(df["start_time"] >= date_min) & (df["start_time"] <= date_max)]
    # compute mean quantity_kwh per price_area (price_area should be codes like NO1..NO5)
    mean_df = df_period.groupby("price_area")["quantity_kwh"].mean().reset_index()
else:
    mean_df = pd.DataFrame(columns=["price_area", "quantity_kwh"])

# -----------------------
# Build value_map keyed by feature id (fid)
# We map feature names (id_to_name[fid]) to price_area codes in mean_df
# -----------------------
value_map = {}
for fid, name in id_to_name.items():
    # try direct match: name equals price_area (NO1..NO5)
    matched = mean_df[mean_df["price_area"].astype(str).str.upper() == str(name).upper()]
    if not matched.empty:
        value = float(matched["quantity_kwh"].iloc[0])
        value_map[fid] = value
        continue
    # else try if name appears inside price_area or vice versa
    matched2 = mean_df[mean_df["price_area"].astype(str).str.upper().str.contains(str(name).upper())]
    if not matched2.empty:
        value_map[fid] = float(matched2["quantity_kwh"].iloc[0])
        continue
    # fallback: try matching by numeric id (if price_area stored as id in df)
    try:
        if int(fid) in list(map(int, mean_df["price_area"].dropna().astype(str).tolist())):
            # map by numeric id string match
            val = mean_df[mean_df["price_area"].astype(str) == str(fid)]["quantity_kwh"]
            if not val.empty:
                value_map[fid] = float(val.iloc[0])
                continue
    except Exception:
        pass
    # default: NaN (will be shown as missing)
    value_map[fid] = None

# -----------------------
# Session state for pin + selected feature
# -----------------------
if "last_pin" not in st.session_state:
    # default center on Norway
    st.session_state.last_pin = [64.5, 11.0]
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None

# Preselect area for initial pin (teacher logic)
if st.session_state.selected_feature_id is None:
    lat, lon = st.session_state.last_pin
    st.session_state.selected_feature_id = find_feature_id(lon, lat)

# -----------------------
# Layout: map left, info right
# -----------------------
map_col, info_col = st.columns([2.4, 1])

with map_col:
    # Build Folium map
    m = folium.Map(location=st.session_state.last_pin, zoom_start=5, tiles="OpenStreetMap")

    # Prepare df for folium.Choropleth: must be two columns matching feature id
    # Create a DataFrame with id and value (value may be None)
    df_vals = pd.DataFrame({"id": list(value_map.keys()), "value": [v if v is not None else 0 for v in value_map.values()]})

    # Add Choropleth. NOTE: folium.Choropleth doesn't show NaN; we feed 0 for missing
    choropleth = folium.Choropleth(
        geo_data=geojson_data,
        data=df_vals,
        columns=["id", "value"],
        key_on="feature.id",
        fill_color="YlOrRd",
        fill_opacity=0.5,
        line_opacity=0.6,
        line_color="white",
        legend_name="Mean kWh (over selected interval)",
        highlight=True
    )
    choropleth.add_to(m)

    # Highlight the selected polygon outline (red)
    if st.session_state.selected_feature_id is not None:
        sel_id = st.session_state.selected_feature_id
        sel_feats = [
            f for f in geojson_data.get("features", [])
            if f.get("id") == sel_id or (f.get("properties") or {}).get("id") == sel_id
        ]
        if sel_feats:
            folium.GeoJson(
                {"type": "FeatureCollection", "features": sel_feats},
                style_function=lambda f: {"fillOpacity": 0, "color": "red", "weight": 3},
                name="selection"
            ).add_to(m)

    # Single pin (last clicked)
    folium.Marker(
        location=st.session_state.last_pin,
        icon=folium.Icon(color="red"),
        popup=f"{st.session_state.last_pin[0]:.5f}, {st.session_state.last_pin[1]:.5f}"
    ).add_to(m)

    # Render map with st_folium and capture interactions
    out = st_folium(m, key="choropleth_map", height=650)

    # Process click: update pin and polygon ID, then rerun (teacher pattern)
    if out and out.get("last_clicked"):
        lat = out["last_clicked"]["lat"]
        lon = out["last_clicked"]["lng"]
        new_coord = [lat, lon]
        if new_coord != st.session_state.last_pin:
            st.session_state.last_pin = new_coord
            st.session_state.selected_feature_id = find_feature_id(lon, lat)
            st.rerun()

with info_col:
    st.subheader("Selection")
    st.write(f"Lat: {st.session_state.last_pin[0]:.6f}")
    st.write(f"Lon: {st.session_state.last_pin[1]:.6f}")

    if st.session_state.selected_feature_id is None:
        st.write("Outside known features.")
    else:
        fid = st.session_state.selected_feature_id
        # read value_map (handle int/str)
        try:
            val = value_map.get(fid, value_map.get(int(fid), "n/a"))
        except Exception:
            val = value_map.get(fid, "n/a")
        area_name = id_to_name.get(fid, f"ID {fid}")
        st.write(f"Area: {area_name}")
        st.write(f"Value (mean kWh): {val if val is not None else 'n/a'}")

st.markdown("---")
st.markdown("💡 Tip: Click inside a zone to pin it and highlight the zone outline.")