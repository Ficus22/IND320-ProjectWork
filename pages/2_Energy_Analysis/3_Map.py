# streamlit_app/pages/7_map.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
from shapely.geometry import shape, Point
from utils.data_loader import load_mongo_data

def app():
    # -----------------------
    # Page config
    # -----------------------
    st.set_page_config(page_title="Price Areas", layout="wide")
    st.title("🗺️ Price Areas & Energy Analysis")

    # -----------------------
    # Load GeoJSON (cached)
    # -----------------------
    @st.cache_data
    def load_geojson(path="data/price_zones.geojson"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    geojson_data = load_geojson()

    # Normalize GeoJSON names (remove spaces: "NO 2" -> "NO2")
    for f in geojson_data["features"]:
        if "ElSpotOmr" in f["properties"]:
            f["properties"]["ElSpotOmr"] = f["properties"]["ElSpotOmr"].replace(" ", "").upper()

    # Assign a proper feature.id using OBJECTID (or fallback index)
    for i, f in enumerate(geojson_data["features"]):
        props = f.get("properties", {})
        f["id"] = props.get("OBJECTID", i)

    # -----------------------
    # Build id -> name mapping (cached)
    # -----------------------
    @st.cache_data
    def build_id_to_name(gj):
        out = {}
        for f in gj.get("features", []):
            fid = f.get("id")
            props = f.get("properties", {})
            name = props.get("ElSpotOmr") or props.get("ElSpot_omraade") or props.get("name")
            out[fid] = (name or str(fid)).replace(" ", "").upper()
        return out

    id_to_name = build_id_to_name(geojson_data)

    # -----------------------
    # Build shapely polygons once
    # -----------------------
    if "polygons" not in st.session_state:
        st.session_state.polygons = [
            (f.get("id"), shape(f["geometry"]))
            for f in geojson_data["features"]
        ]

    def find_feature_id(lon: float, lat: float):
        pt = Point(lon, lat)
        for fid, geom in st.session_state.polygons:
            if geom.covers(pt):
                return fid
        return None

    # -----------------------
    # Sidebar: choose Production or Consumption
    # -----------------------
    st.sidebar.header("Settings")
    mode = st.sidebar.radio("Select data type", ["Production", "Consumption"])
    days = st.sidebar.slider("Time interval (days)", 1, 30, 7)

    # -----------------------
    # Load selected dataset
    # -----------------------
    collection_name = "production_data" if mode == "Production" else "consumption_data"
    df = load_mongo_data(collection_name)

    # -----------------------
    # Compute mean per area
    # -----------------------
    if not df.empty and all(col in df.columns for col in ["price_area", "start_time", "quantity_kwh"]):
        date_max = df["start_time"].max()
        date_min = date_max - pd.Timedelta(days=days)
        df_period = df[(df["start_time"] >= date_min) & (df["start_time"] <= date_max)]
        mean_df = df_period.groupby("price_area")["quantity_kwh"].mean().round(2).reset_index()
    else:
        mean_df = pd.DataFrame(columns=["price_area", "quantity_kwh"])

    # -----------------------
    # Map mean values to features
    # -----------------------
    value_map = {}
    for f in geojson_data["features"]:
        name = f["properties"].get("ElSpotOmr")
        fid = f.get("id")
        match = mean_df[mean_df["price_area"].str.upper() == name]
        value_map[fid] = float(match["quantity_kwh"].iloc[0]) if not match.empty else None

    # -----------------------
    # Session state for pin + selected feature
    # -----------------------
    if "last_pin" not in st.session_state:
        st.session_state.last_pin = [64.5, 11.0]
    if "selected_feature_id" not in st.session_state:
        st.session_state.selected_feature_id = None
    if st.session_state.selected_feature_id is None:
        lat, lon = st.session_state.last_pin
        st.session_state.selected_feature_id = find_feature_id(lon, lat)

    # -----------------------
    # Layout: map + info
    # -----------------------
    map_col, info_col = st.columns([2.4, 1])
    with map_col:
        m = folium.Map(location=st.session_state.last_pin, zoom_start=5, tiles="OpenStreetMap")
        df_vals = pd.DataFrame({"id": list(value_map.keys()),
                                "value": [v if v is not None else 0 for v in value_map.values()]})
        choropleth = folium.Choropleth(
            geo_data=geojson_data,
            data=df_vals,
            columns=["id", "value"],
            key_on="feature.id",
            fill_color="YlOrRd",
            fill_opacity=0.5,
            line_opacity=0.6,
            line_color="white",
            legend_name=f"Mean {mode} kWh (last {days} days)",
            highlight=True
        )
        choropleth.add_to(m)
        # Highlight selected polygon
        if st.session_state.selected_feature_id is not None:
            sel_id = st.session_state.selected_feature_id
            sel_feats = [f for f in geojson_data["features"] if f.get("id") == sel_id]
            if sel_feats:
                folium.GeoJson(
                    {"type": "FeatureCollection", "features": sel_feats},
                    style_function=lambda f: {"fillOpacity": 0, "color": "red", "weight": 3}
                ).add_to(m)
        # Pin marker
        folium.Marker(
            location=st.session_state.last_pin,
            icon=folium.Icon(color="red")
        ).add_to(m)
        # Capture click
        out = st_folium(m, key="map", height=650)
        if out and out.get("last_clicked"):
            lat = out["last_clicked"]["lat"]
            lon = out["last_clicked"]["lng"]
            st.session_state.last_pin = [lat, lon]
            st.session_state.selected_feature_id = find_feature_id(lon, lat)
            st.rerun()

    with info_col:
        st.subheader("Selection")
        st.write(f"Lat: {st.session_state.last_pin[0]:.6f}")
        st.write(f"Lon: {st.session_state.last_pin[1]:.6f}")
        fid = st.session_state.selected_feature_id
        if fid is None:
            st.write("Outside known features.")
        else:
            area_name = id_to_name.get(fid, f"ID {fid}")
            val = value_map.get(fid)
            st.write(f"Area: **{area_name}**")
            st.write(f"Mean {mode} (kWh): **{val if val is not None else 'n/a'}**")

    st.markdown("---")
    st.markdown("💡 Tip: Click inside a zone to pin it and highlight the outline.")