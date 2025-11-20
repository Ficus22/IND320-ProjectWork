import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import statsmodels.api as sm
from datetime import datetime, timedelta
from pymongo import MongoClient
from scipy.stats import zscore

# -------------------------------------------------------
# Page configuration
# -------------------------------------------------------
st.set_page_config(
    page_title="Energy Forecasting ↔ SARIMAX",
    layout="wide"
)

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
# Mongo loader (reuse from previous page)
# -------------------------------------------------------
@st.cache_data
def load_mongo(collection: str) -> pd.DataFrame:
    try:
        MONGO_URI = st.secrets.get("MONGO_URI")
        client = MongoClient(MONGO_URI)
        db = client["elhub_data"]
        coll = db[collection]
        df = pd.DataFrame(list(coll.find({}, {"_id":0})))
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
collection_name = "production_data" if mode=="Production" else "consumption_data"
if f"df_{collection_name}" not in st.session_state:
    st.session_state[f"df_{collection_name}"] = load_mongo(collection_name)
df_energy = st.session_state[f"df_{collection_name}"]

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
    df_area = df[df["price_area"]==price_area].copy()
    if df_area.empty:
        return pd.Series(dtype=float)
    df_area = df_area.set_index("start_time").sort_index()
    s = df_area["quantity_kwh"].resample(freq).sum()
    s.name = "quantity_kwh"
    return s

freq = st.selectbox("Resample frequency", ["H","3H","6H","12H","D"])
series_energy = prepare_energy_series(df_energy, price_area, freq)

# -------------------------------------------------------
# Exogenous variables (weather)
# -------------------------------------------------------
st.subheader("🌡 Exogenous variables (optional)")
st.write("You can include weather features as exogenous variables in the SARIMAX model.")
met_options = ["temperature_2m","precipitation","wind_speed_10m","wind_gusts_10m","wind_direction_10m"]
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

with col2:
    P = st.number_input("Seasonal AR (P)", min_value=0, value=1)
    D = st.number_input("Seasonal I (D)", min_value=0, value=1)
    Q = st.number_input("Seasonal MA (Q)", min_value=0, value=1)
    s = st.number_input("Seasonal length (s)", min_value=1, value=24)

trend = st.selectbox("Trend component", ["n", "c", "t", "ct"], index=1)
run_button = st.button("▶️ Run Forecast")

# -------------------------------------------------------
# Run forecast
# -------------------------------------------------------
if run_button:
    st.header("📈 Forecast results")
    train_series = series_energy.loc[str(start_date):str(end_date)]
    exog_train = None
    exog_forecast = None

    if exog_vars:
        df_exog = df_energy.copy()
        # Filter for the selected price area
        df_exog = df_exog[df_exog["price_area"]==price_area]
        
        # Select only numeric columns (exogenous vars)
        df_exog_numeric = df_exog[exog_vars].apply(pd.to_numeric, errors='coerce')
        
        # Resample and fill missing values
        df_exog_resampled = df_exog_numeric.set_index(df_exog["start_time"]).resample(freq).mean().fillna(method="ffill")
        
        exog_train = df_exog_resampled.loc[str(start_date):str(end_date)]
        exog_forecast = df_exog_resampled.loc[str(end_date)+":"]

    # Fit SARIMAX
    mod = sm.tsa.statespace.SARIMAX(train_series,
                                    exog=exog_train,
                                    order=(p,d,q),
                                    seasonal_order=(P,D,Q,s),
                                    trend=trend)
    res = mod.fit(disp=False)
    st.write(res.summary())

    # Forecast
    forecast_index = pd.date_range(start=train_series.index[-1]+pd.Timedelta(freq),
                                   periods=forecast_horizon, freq=freq)
    forecast_res = res.get_forecast(steps=forecast_horizon, exog=exog_forecast.iloc[:forecast_horizon] if exog_forecast is not None else None)
    forecast_mean = forecast_res.predicted_mean
    forecast_ci = forecast_res.conf_int()

    # Plot results
    df_plot = pd.DataFrame({
        "Observed": series_energy,
        "Forecast": forecast_mean
    })
    fig = px.line(df_plot, labels={"index":"Time"})
    fig.add_traces([
        px.scatter(x=forecast_ci.index, y=forecast_ci.iloc[:,0], opacity=0.2).data[0],
        px.scatter(x=forecast_ci.index, y=forecast_ci.iloc[:,1], opacity=0.2).data[0]
    ])
    st.plotly_chart(fig, use_container_width=True)
    st.success("🎉 Forecast complete!")
else:
    st.info("Set your options above and press **Run Forecast**.")