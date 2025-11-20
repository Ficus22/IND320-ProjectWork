# streamlit_app/pages/9_sliding_window.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from pymongo import MongoClient
import requests

st.set_page_config(page_title="Meteorology & Energy — Sliding Window Correlation", layout="wide")

# -----------------------
# Helper: Mongo loader (uses your function style)
# -----------------------
@st.cache_data
def load_mongo(collection: str) -> pd.DataFrame:
    try:
        MONGO_URI = st.secrets.get("MONGO_URI")
        client = MongoClient(MONGO_URI)
        db = client["elhub_data"]
        coll = db[collection]
        df = pd.DataFrame(list(coll.find({}, {
            "_id": 0,
            "price_area": 1,
            "start_time": 1,
            "quantity_kwh": 1
        })))
        if "start_time" in df.columns:
            df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        return df
    except Exception as e:
        st.error(f"Failed to load Mongo collection '{collection}': {e}")
        return pd.DataFrame(columns=["price_area", "start_time", "quantity_kwh"])

# -----------------------
# Helper: download weather from Open-Meteo ERA5 archive
# -----------------------
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

@st.cache_data
def download_weather_data(latitude: float, longitude: float, start_date: str, end_date: str,
                          hourly=("temperature_2m","precipitation","wind_speed_10m","wind_gusts_10m","wind_direction_10m")) -> pd.DataFrame:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly),
        "timezone": "UTC"
    }
    response = requests.get(OPENMETEO_ERA5, params=params, timeout=30)
    response.raise_for_status()
    hourly_data = response.json().get("hourly", {})
    df = pd.DataFrame({"time": pd.to_datetime(hourly_data.get("time", []), utc=True)})
    for v in hourly:
        df[v] = pd.to_numeric(hourly_data.get(v, []), errors="coerce")
    df = df.set_index("time").sort_index()
    return df

# -----------------------
# Mapping price_area -> coords (you can extend or modify)
# These are approximate representative coordinates for each Norwegian bidding zone.
# -----------------------
PRICE_AREA_COORDS = {
    "NO1": (59.91, 10.75),   # Oslo region
    "NO2": (63.43, 10.39),   # Trondheim region
    "NO3": (58.97, 5.73),    # Bergen region
    "NO4": (61.47, 6.15),    # Kristiansand / Stavanger region (approx)
    "NO5": (70.67, 23.68),   # Tromsø / northern region (approx)
}

# -----------------------
# Utility: prepare energy time series from Mongo data
# -----------------------
@st.cache_data
def prepare_energy_series(df_energy: pd.DataFrame, price_area: str, resample_freq: str = "H") -> pd.Series:
    # Filter by price_area (user requested)
    if price_area is not None and price_area in df_energy["price_area"].unique():
        df_area = df_energy[df_energy["price_area"] == price_area].copy()
    else:
        df_area = df_energy.copy()

    if df_area.empty:
        return pd.Series(dtype=float)

    # Ensure start_time is datetime
    if "start_time" in df_area.columns:
        df_area["start_time"] = pd.to_datetime(df_area["start_time"], utc=True)
        df_area = df_area.set_index("start_time")
    else:
        st.warning("Energy dataframe has no 'start_time' column; result may be empty")

    # Aggregate per resample period using SUM (A = your choice)
    series = df_area["quantity_kwh"].resample(resample_freq).sum().sort_index()
    series.name = "quantity_kwh"
    return series

# -----------------------
# Sliding window correlation helpers
# -----------------------
@st.cache_data
def sliding_window_correlation(series_x: pd.Series, series_y: pd.Series, window: int) -> pd.Series:
    return series_x.rolling(window=window, min_periods=2).corr(series_y)


def compute_rolled_corr(series_met: pd.Series, series_eng: pd.Series, window_hours: int, lag_hours: int) -> pd.Series:
    # Both series assumed to be indexed by UTC datetime and share same frequency
    if lag_hours != 0:
        # Positive lag: meteorology leads energy by lag_hours -> shift energy backward so earlier energy aligns
        series_eng_shifted = series_eng.shift(-lag_hours)
    else:
        series_eng_shifted = series_eng

    df2 = pd.concat([series_met, series_eng_shifted], axis=1).dropna()
    if df2.shape[0] == 0:
        return pd.Series([], dtype=float)
    x = df2.iloc[:, 0]
    y = df2.iloc[:, 1]
    corr = sliding_window_correlation(x, y, window)
    return corr

# -----------------------
# Page UI
# -----------------------
st.title("Meteorology ↔ Energy — Sliding Window Correlation (MongoDB + Open-Meteo)")
st.write("Using energy data from your Mongo collections and weather from the Open‑Meteo ERA5 archive.")

col_left, col_right = st.columns([1, 2])
with col_left:
    mode = st.radio("Energy dataset type", options=["Production", "Consumption"], index=0)
    collection_name = "production_data" if mode == "Production" else "consumption_data"

    # Load energy dataframe from Mongo and cache in session_state for snappiness
    if f"df_{collection_name}" not in st.session_state:
        st.session_state[f"df_{collection_name}"] = load_mongo(collection_name)
    df_energy = st.session_state[f"df_{collection_name}"]

    st.markdown(f"Loaded **{len(df_energy)}** energy records from collection `{collection_name}`.")

    # Price area selector (user chose option 1: single price area dropdown)
    price_areas = sorted(df_energy["price_area"].dropna().unique()) if not df_energy.empty else []
    price_area = st.selectbox("Price area", options=[None] + price_areas, format_func=lambda x: "All areas" if x is None else x)

    # Determine coordinates for weather request based on chosen price_area (option Z: infer mapping)
    lat, lon = None, None
    if price_area in PRICE_AREA_COORDS:
        lat, lon = PRICE_AREA_COORDS[price_area]
        st.markdown(f"Using coordinates for {price_area}: lat={lat}, lon={lon}")
    else:
        st.info("No mapped coordinates for selected price area — please supply coordinates below or pick 'All areas' and choose coordinates manually.")

    # Allow manual override of coordinates
    with st.expander("Weather location / override coordinates"):
        col_lat, col_lon = st.columns(2)
        manual_lat = col_lat.number_input("Latitude (override)", value=float(lat) if lat is not None else 59.91)
        manual_lon = col_lon.number_input("Longitude (override)", value=float(lon) if lon is not None else 10.75)
        lat = manual_lat
        lon = manual_lon

    # Year / date range for weather
    years = st.slider("Year range for weather data (start year, end year)", min_value=2015, max_value= pd.Timestamp.utcnow().year, value=(2021, 2021), step=1)
    start_date = f"{years[0]}-01-01"
    end_date = f"{years[1]}-12-31"

    # Resample frequency
    freq = st.selectbox("Resample frequency", options=["H", "3H", "6H", "12H", "D"], index=0)

    # Meteorological and energy column selectors
    # We'll fetch weather hourly variables list from Open-Meteo default set
    met_options = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
    met_col = st.selectbox("Meteorological property", options=met_options, index=0)

    eng_series_label = "quantity_kwh"

    window_len = st.slider("Window length (in resample periods)", min_value=3, max_value=24*30, value=24, step=1)
    lag = st.slider("Lag (in resample periods) — positive means meteorology leads", min_value=-168, max_value=168, value=0, step=1)

    # Event highlighting
    st.markdown("**Highlight extreme-event periods**")
    event_mode = st.radio("Event selection method", options=["None", "By threshold on selected meteorological", "By date range"], index=0)
    event_mask = None
    thr_dir = None
    thr_val = None
    if event_mode == "By threshold on selected meteorological":
        thr_dir = st.selectbox("Threshold direction", options=["Above", "Below"], index=0)
        thr_val = st.number_input("Threshold value", value=0.0)
    elif event_mode == "By date range":
        date_range = st.date_input("Event date range (start, end)", [])
        if len(date_range) == 2:
            event_start = pd.to_datetime(date_range[0]).tz_localize("UTC")
            event_end = pd.to_datetime(date_range[1]).tz_localize("UTC")
            # we'll build mask later after merging

    run_button = st.button("Compute & Plot")

with col_right:
    out = st.empty()

# -----------------------
# Run computation
# -----------------------
if run_button:
    if df_energy.empty:
        st.error("No energy data available. Check your MongoDB connection and collection content.")
    else:
        # Prepare energy series (sum aggregation per resample period) — Q1 = A
        series_energy = prepare_energy_series(df_energy, price_area, resample_freq=freq)

        if series_energy.empty:
            st.error("Energy series is empty after resampling. Check date ranges and selection.")
        else:
            # Download weather for chosen coords and date range
            with st.spinner("Downloading weather data (Open-Meteo ERA5)..."):
                try:
                    df_weather = download_weather_data(float(lat), float(lon), start_date, end_date)
                except Exception as e:
                    st.error(f"Failed to download weather data: {e}")
                    df_weather = pd.DataFrame()

            if df_weather.empty:
                st.error("No weather data available for selected coords/date range")
            else:
                # Resample weather to chosen freq by mean
                series_met = df_weather[met_col].resample(freq).mean()
                series_met.name = met_col

                # Align/merge the two series
                # Reindex to union of indices and then dropna in compute_rolled_corr
                common_idx = series_met.index.intersection(series_energy.index)
                # If empty intersection, try aligning by reindexing to union and forward/backfill? We'll use inner join behavior
                if len(common_idx) == 0:
                    st.warning("No overlapping timestamps between weather and energy series. Attempting to align by resampling to hourly and intersecting.")
                    # try resampling both to hourly
                    series_energy_h = series_energy.resample("H").sum()
                    series_met_h = df_weather[met_col].resample("H").mean()
                    series_met = series_met_h
                    series_energy = series_energy_h

                # Final compute
                corr_series = compute_rolled_corr(series_met, series_energy, window_hours=window_len, lag_hours=lag)

                # If event mask by threshold requested, build it now using original weather index
                if event_mode == "By threshold on selected meteorological":
                    if thr_dir == "Above":
                        event_mask_full = df_weather[met_col] > thr_val
                    else:
                        event_mask_full = df_weather[met_col] < thr_val
                    # resample mask to chosen freq (any True in period -> True)
                    event_mask = event_mask_full.resample(freq).max().astype(bool)
                elif event_mode == "By date range" and len(date_range) == 2:
                    event_mask = pd.Series(False, index=series_met.index)
                    event_mask[(series_met.index >= event_start) & (series_met.index <= event_end)] = True

                # Plot 1: time series of meteorology and energy (aligned)
                fig_ts = go.Figure()
                # align series for plotting: trim to common index after shift performed in correlation
                # For plotting, show raw aligned series (apply lag visually by shifting energy)
                series_energy_for_plot = series_energy.copy()
                if lag != 0:
                    series_energy_for_plot = series_energy.shift(-lag)

                # Trim to overlapping index
                df_plot = pd.concat([series_met, series_energy_for_plot], axis=1).dropna()
                if df_plot.empty:
                    st.warning("No overlapping data to plot after alignment.")
                else:
                    fig_ts.add_trace(go.Scatter(x=df_plot.index, y=df_plot.iloc[:, 0].values, name=met_col, yaxis="y1"))
                    fig_ts.add_trace(go.Scatter(x=df_plot.index, y=df_plot.iloc[:, 1].values, name=eng_series_label, yaxis="y2"))
                    fig_ts.update_layout(
                        title=f"Time series — {met_col} and {eng_series_label} (lag={lag}, window={window_len})",
                        xaxis_title="Time",
                        yaxis={"title": met_col},
                        yaxis2=dict(title=eng_series_label, overlaying="y", side="right")
                    )

                    # add event shading
                    if event_mask is not None and event_mask.any():
                        # reindex event_mask to df_plot index
                        event_bool = event_mask.reindex(df_plot.index, method="nearest").fillna(False)
                        starts = []
                        ends = []
                        prev_ts = None
                        in_event = False
                        for ts, val in event_bool.items():
                            if val and not in_event:
                                starts.append(ts)
                                in_event = True
                            elif not val and in_event:
                                ends.append(prev_ts)
                                in_event = False
                            prev_ts = ts
                        if in_event:
                            ends.append(prev_ts)
                        for s, e in zip(starts, ends):
                            fig_ts.add_vrect(x0=s, x1=e, fillcolor="LightSalmon", opacity=0.25, layer="below", line_width=0)

                    out.plotly_chart(fig_ts, use_container_width=True)

                # Plot 2: rolling correlation over time
                if corr_series.empty:
                    st.warning("No rolling correlation computed (not enough overlapping data after shifting).")
                else:
                    fig_corr = px.line(x=corr_series.index, y=corr_series.values, labels={"x": "Time", "y": "Rolling correlation"}, title="Sliding-window correlation over time")
                    fig_corr.update_layout(yaxis=dict(range=[-1, 1]))
                    out.plotly_chart(fig_corr, use_container_width=True)

                # Plot 3: scatter of last window
                try:
                    last_idx = corr_series.dropna().index
                    if len(last_idx) > 0:
                        last_time = last_idx[-1]
                        last_window_start = last_time - pd.Timedelta(hours=window_len)
                        last_df = pd.concat([series_met, series_energy_for_plot], axis=1).loc[last_window_start:last_time].dropna()
                        if not last_df.empty and last_df.shape[0] >= 2:
                            r_last = last_df.iloc[:, 0].corr(last_df.iloc[:, 1])
                            fig_scatter = px.scatter(last_df, x=last_df.columns[0], y=last_df.columns[1], trendline="ols", title=f"Scatter in last window ending {last_time.date()} (corr={r_last:.2f})")
                            out.plotly_chart(fig_scatter, use_container_width=True)
                except Exception:
                    pass

                # Bonus: mean correlation vs lag heatmap/line
                st.markdown("### Mean sliding-window correlation vs lag (quick scan)")
                lag_range = st.slider("Lag range (hours) for scan", min_value=1, max_value=168, value=48)
                lags = list(range(-lag_range, lag_range + 1, max(1, int(max(1, lag_range / 24)))))
                mean_corrs = []
                with st.spinner("Computing lag scan..."):
                    for L in lags:
                        corr_L = compute_rolled_corr(series_met, series_energy, window_len, L)
                        mean_corrs.append(corr_L.mean(skipna=True))
                lag_df = pd.DataFrame({"lag": lags, "mean_corr": mean_corrs})
                fig_lag = px.line(lag_df, x="lag", y="mean_corr", title="Mean rolling correlation vs lag (positive = met leads)")
                out.plotly_chart(fig_lag, use_container_width=True)

                st.success("Done — explore different price areas, lags and windows. Use event selection to compare in-event vs out-of-event behavior.")

else:
    st.info("Choose options on the left and click 'Compute & Plot' to run the analysis.")