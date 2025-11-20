# streamlit_app/pages/10_sarimax.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statsmodels.api as sm
from datetime import datetime, timedelta
from scipy.stats import zscore
import time
from utils.data_loader import load_mongo_data, download_weather_data_chunked
from config import PRICE_AREAS, DEFAULT_HOURLY_VARIABLES

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
# Data selection
# -------------------------------------------------------
st.subheader("🔧 Dataset selection")
mode = st.radio("Energy dataset", ["Production", "Consumption"])
collection_name = "production_data" if mode == "Production" else "consumption_data"
if f"df_{collection_name}" not in st.session_state:
    st.session_state[f"df_{collection_name}"] = load_mongo_data(collection_name)
df_energy = st.session_state[f"df_{collection_name}"]
if df_energy.empty:
    st.error("No data loaded. Please check your MongoDB connection and data.")
    st.stop()

price_area = st.selectbox(
    "Price area",
    options=list(PRICE_AREAS.keys()),
    format_func=lambda x: f"{x} — {PRICE_AREAS[x]['city']}"
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
# Exogenous variables (weather)
# -------------------------------------------------------
st.subheader("🌡 Exogenous variables (optional)")
st.write("You can include weather features as exogenous variables in the SARIMAX model.")
exog_vars = st.multiselect("Select exogenous variables", options=DEFAULT_HOURLY_VARIABLES)

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
# Helper functions
# -------------------------------------------------------
@st.cache_data
def freq_to_timedelta(freq_str):
    if freq_str == "H":
        return pd.Timedelta(hours=1)
    elif freq_str == "D":
        return pd.Timedelta(days=1)
    elif freq_str.endswith("H"):
        return pd.Timedelta(hours=int(freq_str[:-1]))
    elif freq_str.endswith("D"):
        return pd.Timedelta(days=int(freq_str[:-1]))
    else:
        return pd.Timedelta(hours=1)

@st.cache_data
def freq_to_dateoffset(freq_str):
    if freq_str == "H":
        return pd.DateOffset(hours=1)
    elif freq_str == "D":
        return pd.DateOffset(days=1)
    elif freq_str.endswith("H"):
        hours = int(freq_str[:-1])
        return pd.DateOffset(hours=hours)
    elif freq_str.endswith("D"):
        days = int(freq_str[:-1])
        return pd.DateOffset(days=days)
    else:
        return pd.DateOffset(hours=1)

# -------------------------------------------------------
# Run forecast
# -------------------------------------------------------
if run_button:
    st.header("📈 Forecast results")
    status_placeholder = st.empty()
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
            lat, lon = PRICE_AREAS[price_area]["lat"], PRICE_AREAS[price_area]["lon"]
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

            # Prepare forecast start
            forecast_start = pd.to_datetime(end_date) + freq_to_timedelta(freq)
            forecast_start = pd.Timestamp(forecast_start, tz='UTC')

            # Check data consistency
            if df_exog.empty:
                st.error("No exogenous data available.")
                exog_forecast = None
            else:
                if forecast_start < df_exog.index.min() or forecast_start > df_exog.index.max():
                    st.warning(f"forecast_start ({forecast_start}) is outside the range of exogenous data index ({df_exog.index.min()} to {df_exog.index.max()}).")
                    exog_forecast = None
                else:
                    exog_forecast = df_exog.loc[df_exog.index >= forecast_start, exog_vars].iloc[:forecast_horizon]
                    if exog_forecast.empty:
                        st.warning("No exogenous data available for the forecast period. Forecast will run without exogenous variables.")
                        exog_forecast = None
            exog_train = df_exog.loc[str(start_date):str(end_date), exog_vars]

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
                start=train_series.index[-1] + freq_to_dateoffset(freq),
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