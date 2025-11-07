# streamlit_app/pages/2_new_A.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram
import numpy as np
from pymongo import MongoClient

st.set_page_config(page_title="📊 Elhub Analysis", layout="wide")

# -------------------------
# Check if a price area was selected
# -------------------------
if "selected_price_area" not in st.session_state:
    st.warning("Please select a Price Area on page 2 (elhub) first.")
    st.stop()

price_area = st.session_state.selected_price_area

# -------------------------
# Price area info
# -------------------------
PRICE_AREAS = {
    "NO1": {"city": "Oslo", "lat": 59.9139, "lon": 10.7522},
    "NO2": {"city": "Kristiansand", "lat": 58.1467, "lon": 7.9956},
    "NO3": {"city": "Trondheim", "lat": 63.4305, "lon": 10.3951},
    "NO4": {"city": "Tromsø", "lat": 69.6492, "lon": 18.9553},
    "NO5": {"city": "Bergen", "lat": 60.3913, "lon": 5.3221},
}

if price_area not in PRICE_AREAS:
    st.error(f"Unknown price area: {price_area}")
    st.stop()

city = PRICE_AREAS[price_area]["city"]

st.title(f"📊 Elhub Time Series Analysis for {city}")

# -------------------------
# Load data (MongoDB / Elhub)
# -------------------------
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["elhub_data"]
collection = db["production_data"]

data = list(collection.find({}))
df = pd.DataFrame(data)
if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)

# -------------------------
# Tabs for STL and Spectrogram
# -------------------------
tab1, tab2 = st.tabs(["STL Decomposition", "Spectrogram"])

# -------------------------
# --- TAB 1: STL Decomposition ---
# -------------------------
with tab1:
    st.header(f"STL Decomposition for {city}")
    
    # Select production group
    production_groups = df["production_group"].dropna().unique()
    selected_group = st.selectbox("Select Production Group", production_groups)
    
    # STL parameters
    period = st.number_input("Period (hours)", value=24*7, step=1)
    seasonal = st.number_input("Seasonal Smoother", value=13, step=1)
    trend = st.number_input("Trend Smoother", value=201, step=1)
    robust = st.checkbox("Robust fitting", value=True)
    
    # Filter data by selected price area and production group
    df_area_group = df[(df["price_area"] == price_area) & (df["production_group"] == selected_group)]
    
    if df_area_group.empty:
        st.info("No data available for this selection.")
    else:
        df_area_group["start_time"] = pd.to_datetime(df_area_group["start_time"]).dt.tz_localize(None)
        df_area_group = df_area_group.set_index("start_time")
        numeric_cols = df_area_group.select_dtypes(include="number").columns
        df_area_group = df_area_group[numeric_cols].resample("H").sum().interpolate()

        stl = STL(df_area_group["quantity_kwh"], period=period, seasonal=seasonal, trend=trend, robust=robust)
        result = stl.fit()
        
        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_area_group.index, y=result.observed, mode='lines', name='Observed'))
        fig.add_trace(go.Scatter(x=df_area_group.index, y=result.trend, mode='lines', name='Trend'))
        fig.add_trace(go.Scatter(x=df_area_group.index, y=result.seasonal, mode='lines', name='Seasonal'))
        fig.add_trace(go.Scatter(x=df_area_group.index, y=result.resid, mode='lines', name='Residual'))

        fig.update_layout(
            title=f"STL Decomposition — {city} · Group {selected_group}",
            xaxis_title="Time",
            yaxis_title="kWh",
            legend_title="Components",
            height=700
        )
        st.plotly_chart(fig, use_container_width=True)

# -------------------------
# --- TAB 2: Spectrogram ---
# -------------------------
with tab2:
    st.header(f"Spectrogram for {city}")
    
    # Select production group
    selected_group_spec = st.selectbox("Select Production Group for Spectrogram", production_groups, key="spec_group")
    
    # Spectrogram parameters
    window_length = st.number_input("Window length (hours)", value=24*7, step=1)
    window_overlap = st.slider("Window overlap (%)", min_value=0.0, max_value=0.9, value=0.5, step=0.05)
    colorscale = st.selectbox("Colorscale", ["Viridis", "Cividis", "Plasma", "Inferno", "Magma"])
    
    # Filter data
    df_spec = df[(df["price_area"] == price_area) & (df["production_group"] == selected_group_spec)]
    
    if df_spec.empty:
        st.info("No data available for this selection.")
    else:
        df_spec["start_time"] = pd.to_datetime(df_spec["start_time"]).dt.tz_localize(None)
        df_spec = df_spec.set_index("start_time")
        numeric_cols = df_spec.select_dtypes(include="number").columns
        df_spec_resampled = df_spec[numeric_cols].resample("H").sum().interpolate()

        y = df_spec_resampled["quantity_kwh"].to_numpy()
        nperseg = int(window_length)
        noverlap = int(nperseg * window_overlap)
        fs = 1.0

        freqs, times, Sxx = spectrogram(y, fs=fs, nperseg=nperseg, noverlap=noverlap, scaling="density", detrend="linear", mode="psd")
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        freqs_per_day = freqs * 24

        fig = go.Figure(go.Heatmap(
            z=Sxx_db,
            x=times,
            y=freqs_per_day,
            colorscale=colorscale,
            colorbar=dict(title="Power (dB)"),
            zsmooth="best"
        ))
        fig.update_layout(
            title=f"Spectrogram — {city} · Group {selected_group_spec}",
            xaxis_title="Time (hours)",
            yaxis_title="Frequency (cycles/day)",
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig, use_container_width=True)