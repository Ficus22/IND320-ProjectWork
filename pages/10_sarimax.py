import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statsmodels.api as sm
from datetime import datetime, timedelta
from pymongo import MongoClient
from scipy.stats import zscore
import requests
import time
import os

# -------------------------------------------------------
# Page configuration
# -------------------------------------------------------
st.set_page_config(page_title="Energy Forecasting ↔ SARIMAX", layout="wide")
st.title("🔮 Energy Production & Consumption Forecasting — SARIMAX")
st.write("""
This tool allows you to forecast energy production or consumption using **SARIMAX** models.
You can select:
- **Target variable** from your energy dataset
- **Exogenous variables** (weather)
- **Training timeframe** and **forecast horizon**
- **SARIMAX parameters** (AR, I, MA, seasonal AR, seasonal I, seasonal MA, season length)
""")

# -------------------------------------------------------
# Price area → city names
# -------------------------------------------------------
PRICE_AREAS = {
    "NO1": "Oslo",
    "NO2": "Kristiansand",
    "NO3": "Trondheim",
    "NO4": "Tromsø",
    "NO5": "Bergen"
}

# -------------------------------------------------------
# Mongo loader
# -------------------------------------------------------
@st.cache_data
def load_mongo(collection: str) -> pd.DataFrame:
    try:
        MONGO_URI = st.secrets.get("MONGO_URI")
        if not MONGO_URI:
            st.error("MongoDB URI not configured.")
            return pd.DataFrame()
        client = MongoClient(MONGO_URI)
        db = client["elhub_data"]
        coll = db[collection]
        df = pd.DataFrame(list(coll.find({}, {"_id": 0})))
        if "start_time" in df.columns:
            df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        return df
    except Exception as e:
        st.error(f"Failed to load Mongo collection '{collection}': {e}")
        return pd.DataFrame()

# -------------------------------------------------------
# Data selection
# -------------------------------------------------------
st.subheader("🔧 Dataset selection")
mode = st.radio("Energy dataset", ["Production", "Consumption"])
collection_name = "production_data" if mode == "Production" else "consumption_data"
if f"df_{collection_name}" not in st.session_state:
    st.session_state[f"df_{collection_name}"] = load_mongo(collection_name)
df_energy = st.session_state[f"df_{collection_name}"]

if df_energy.empty:
    st.error("No data loaded. Please check your MongoDB connection and data.")
    st.stop()

price_area = st.selectbox(
    "Price area",
    options=list(PRICE_AREAS.keys()),
    format_func=lambda x: f"{x} — {PRICE_AREAS[x]}"
)

# -------------------------------------------------------
# Energy series preparation
# -------------------------------------------------------
@st.cache_data
def prepare_energy_series(df, price_area, freq="H"):
    if "price_area" not in df.columns or "start_time" not in df.columns or "quantity_kwh" not in df.columns:
        st.error("Required columns not found in the dataset.")
        return pd.Series(dtype=float)
    df_area = df[df["price_area"] == price_area].copy()
    if df_area.empty:
        st.error(f"No data available for price area: {price_area}")
        return pd.Series(dtype=float)
    df_area = df_area.set_index("start_time").sort_index()
    s = df_area["quantity_kwh"].resample(freq).sum()
    s.name = "quantity_kwh"
    return s

freq = st.selectbox("Resample frequency", ["H", "3H", "6H", "12H", "D"])
series_energy = prepare_energy_series(df_energy, price_area, freq)

if series_energy.empty:
    st.error("No energy data available for the selected price area and frequency.")
    st.stop()

# -------------------------------------------------------
# Weather loader (Open-Meteo ERA5) with chunking and caching
# -------------------------------------------------------
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

def download_weather_data(lat: float, lon: float, start_date: str, end_date: str,
                          hourly=("temperature_2m","precipitation","wind_speed_10m","wind_gusts_10m","wind_direction_10m")) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly),
        "timezone": "UTC"
    }
    try:
        response = requests.get(OPENMETEO_ERA5, params=params, timeout=30)
        response.raise_for_status()
    except Exception as e:
        st.error(f"Failed to fetch weather data: {e}")
        return pd.DataFrame()
    hourly_data = response.json().get("hourly", {})
    df = pd.DataFrame({"time": pd.to_datetime(hourly_data.get("time", []), utc=True)})
    for v in hourly:
        df[v] = pd.to_numeric(hourly_data.get(v, []), errors="coerce")
    return df.set_index("time").sort_index()

@st.cache_data
def download_weather_data_chunked(lat, lon, start_date, end_date, hourly):
    """Download weather in 3-month chunks to avoid 429 errors."""
    df_list = []
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    chunk_size = pd.Timedelta(days=90)

    while start <= end:
        chunk_end = min(start + chunk_size, end)
        df_chunk = download_weather_data(
            lat=lat, lon=lon,
            start_date=start.date().isoformat(),
            end_date=chunk_end.date().isoformat(),
            hourly=hourly
        )
        if not df_chunk.empty:
            df_list.append(df_chunk)
        start = chunk_end + pd.Timedelta(days=1)
        time.sleep(1)  # optional delay to reduce request frequency

    if df_list:
        return pd.concat(df_list).sort_index()
    return pd.DataFrame()

# -------------------------------------------------------
# Exogenous variables (weather)
# -------------------------------------------------------
st.subheader("🌡 Exogenous variables (optional)")
st.write("You can include weather features as exogenous variables in the SARIMAX model.")
met_options = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
exog_vars = st.multiselect("Select exogenous variables", options=met_options)

# -------------------------------------------------------
# Training & forecast period
# -------------------------------------------------------
st.subheader("📅 Training & Forecast Settings")
start_date = st.date_input("Training start date", value=series_energy.index.min().date())
end_date = st.date_input("Training end date", value=(series_energy.index.max() - timedelta(days=30)).date())
forecast_horizon = st.number_input("Forecast horizon (periods)", min_value=1, max_value=365, value=24)

# -------------------------------------------------------
# SARIMAX parameters
# -------------------------------------------------------
st.subheader("⚙️ SARIMAX Parameters")
col1, col2 = st.columns(2)
with col1:
    p = st.number_input("AR (p)", min_value=0, value=1)
    d = st.number_input("I (d)", min_value=0, value=1)
    q = st.number_input("MA (q)", min_value=0, value=1)
    trend = st.selectbox("Trend component", ["n", "c", "t", "ct"], index=1)
with col2:
    P = st.number_input("Seasonal AR (P)", min_value=0, value=1)
    D = st.number_input("Seasonal I (D)", min_value=0, value=1)
    Q = st.number_input("Seasonal MA (Q)", min_value=0, value=1)
    s = st.number_input("Seasonal length (s)", min_value=1, value=24)

run_button = st.button("▶️ Run Forecast")

# -------------------------------------------------------
# Run forecast
# -------------------------------------------------------
if run_button:
    st.header("📈 Forecast results")
    status_placeholder = st.empty()  # messages to user

    with st.spinner("SARIMAX is training... ⏳"):
        # --- Training data ---
        status_placeholder.info("📊 Preparing training data...")
        train_series = series_energy.loc[str(start_date):str(end_date)]
        if train_series.empty:
            st.error("No training data available for the selected date range.")
            st.stop()

        # --- Exogenous variables ---
        exog_train = None
        exog_forecast = None
        if exog_vars:
            status_placeholder.info("☁️ Downloading weather data...")
            lat_lon_map = {
                "NO1": (59.91, 10.75),
                "NO2": (58.15, 8.00),
                "NO3": (63.43, 10.39),
                "NO4": (69.65, 18.95),
                "NO5": (60.39, 5.33)
            }
            lat, lon = lat_lon_map[price_area]
            df_weather = download_weather_data_chunked(
                lat=lat,
                lon=lon,
                start_date=series_energy.index.min().date().isoformat(),
                end_date=series_energy.index.max().date().isoformat(),
                hourly=exog_vars
            )
            if df_weather.empty:
                st.error("No weather data available.")
                st.stop()
            df_exog = series_energy.to_frame().join(df_weather, how="left")
            df_exog.fillna(method="ffill", inplace=True)
            exog_train = df_exog.loc[str(start_date):str(end_date), exog_vars]
            exog_forecast = df_exog.loc[str(end_date)+":", exog_vars].iloc[:forecast_horizon]

        # --- Fit SARIMAX ---
        status_placeholder.info("⚙️ Training SARIMAX model...")
        try:
            mod = sm.tsa.statespace.SARIMAX(
                train_series,
                exog=exog_train,
                order=(p, d, q),
                seasonal_order=(P, D, Q, s),
                trend=trend
            )
            res = mod.fit(disp=False)
        except Exception as e:
            st.error(f"Failed to fit SARIMAX model: {e}")
            st.stop()

        # --- Forecast ---
        status_placeholder.info("📈 Generating forecast...")
        try:
            forecast_index = pd.date_range(
                start=train_series.index[-1] + pd.Timedelta(freq),
                periods=forecast_horizon,
                freq=freq
            )
            forecast_res = res.get_forecast(steps=forecast_horizon, exog=exog_forecast)
            forecast_mean = forecast_res.predicted_mean
            forecast_ci = forecast_res.conf_int()
        except Exception as e:
            st.error(f"Failed to generate forecast: {e}")
            st.stop()

        # --- Display results ---
        status_placeholder.success("🎉 Forecast complete!")
        df_plot = pd.DataFrame({
            "Observed": series_energy,
            "Forecast": forecast_mean
        })
        fig = px.line(df_plot, labels={"index": "Time"})
        fig.add_traces([
            px.scatter(x=forecast_ci.index, y=forecast_ci.iloc[:, 0], opacity=0.2).data[0],
            px.scatter(x=forecast_ci.index, y=forecast_ci.iloc[:, 1], opacity=0.2).data[0]
        ])
        st.plotly_chart(fig, use_container_width=True)
        st.write(res.summary())
else:
    st.info("Set your options above and press **Run Forecast**.")