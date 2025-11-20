import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from pymongo import MongoClient
import requests
from scipy.stats import ttest_ind
from scipy.stats import zscore

# -------------------------------------------------------
# Page configuration
# -------------------------------------------------------
st.set_page_config(
    page_title="Meteorology ↔ Energy — Sliding Window Correlation",
    layout="wide"
)

st.title("🌦⚡ Meteorology ↔ Energy — Sliding Window Correlation Explorer")

st.write("""
This tool explores how **meteorology influences energy production or consumption over time.**
You can:
- Select **meteorological variables and energy signals**
- Study **time-varying correlations** using a sliding window
- Test **delayed effects** using a lag
- Highlight **extreme weather periods**
- Compare correlations **during extreme vs normal conditions**
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
# Helper: Mongo loader
# -------------------------------------------------------
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

# -------------------------------------------------------
# Weather loader (Open-Meteo ERA5)
# -------------------------------------------------------
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

@st.cache_data
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

# -------------------------------------------------------
# Price area → coordinates (keep internally)
# -------------------------------------------------------
PRICE_AREA_COORDS = {
    "NO1": (59.9139, 10.7522),   # Oslo
    "NO2": (58.1467, 7.9956),    # Kristiansand
    "NO3": (63.4305, 10.3951),   # Trondheim
    "NO4": (69.6496, 18.9560),   # Tromsø
    "NO5": (60.39299, 5.32415),  # Bergen
}

# -------------------------------------------------------
# Energy data preparation
# -------------------------------------------------------
@st.cache_data
def prepare_energy_series(df_energy: pd.DataFrame, price_area: str, resample_freq: str="H") -> pd.Series:
    df = df_energy[df_energy["price_area"] == price_area].copy()
    if df.empty:
        return pd.Series(dtype=float)
    df = df.set_index("start_time").sort_index()
    s = df["quantity_kwh"].resample(resample_freq).sum()
    s.name = "quantity_kwh"
    return s

# -------------------------------------------------------
# Correlation utilities
# -------------------------------------------------------
def sliding_window_correlation(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
    return x.rolling(window=window).corr(y)

def compute_rolled_corr(series_met: pd.Series, series_eng: pd.Series, window_hours: int, lag_hours: int) -> pd.Series:
    if lag_hours != 0:
        series_eng = series_eng.shift(-lag_hours)
    df = pd.concat([series_met, series_eng], axis=1).dropna()
    if df.empty:
        return pd.Series([], dtype=float)
    return sliding_window_correlation(df.iloc[:,0], df.iloc[:,1], window_hours)

# -------------------------------------------------------
# USER SETTINGS
# -------------------------------------------------------
st.subheader("🔧 Analysis settings")

with st.expander("Click to configure settings", expanded=True):

    mode = st.radio("Energy dataset", ["Production", "Consumption"])

    collection_name = "production_data" if mode == "Production" else "consumption_data"
    if f"df_{collection_name}" not in st.session_state:
        st.session_state[f"df_{collection_name}"] = load_mongo(collection_name)
    df_energy = st.session_state[f"df_{collection_name}"]

    price_area = st.selectbox(
        "Price area (region + city)",
        options=list(PRICE_AREAS.keys()),
        format_func=lambda x: f"{x} — {PRICE_AREAS[x]}"
    )

    st.markdown("""
**📌 Resample frequency**  
Energy and meteorological data do not always share the same timestamps.  
Resampling aligns them to a common time step (e.g., hourly or daily) to make comparison possible.
""")
    freq = st.selectbox("Time resolution", ["H","3H","6H","12H","D"])

    st.markdown("""
**🌡⚡ Meteorological & Signal Parameters**  
- **Variable**: Chooses the weather feature affecting energy  
- **Sliding window**: Groups consecutive time points to compute one correlation (smooth vs reactive)  
- **Lag**: Tests whether weather impacts energy with delay (e.g. heating reaction to cold)
""")
    met_col = st.selectbox("Meteorological variable", ["temperature_2m","precipitation","wind_speed_10m","wind_gusts_10m","wind_direction_10m"])
    window_len = st.slider("Sliding window (in periods)", 3, 24*30, 24)
    lag = st.slider("Lag (periods) — positive = weather leads", -168, 168, 0)

    st.markdown("""
**🌪 Highlight extreme events**  
This highlights periods where the chosen weather variable is unusually high/low or within a selected date range.  
The tool compares correlation *during these extreme periods vs the rest of the time* to see if weather influence changes.
""")
    event_mode = st.radio("Highlight method", ["None", "By threshold", "By date range"])
    thr_val = None
    if event_mode == "By threshold":
        thr_dir = st.selectbox("Direction", ["Above", "Below"])
        thr_val = st.number_input("Threshold value", value=0.0)
    if event_mode == "By date range":
        date_range = st.date_input("Range (start, end)")

    normalize_plot = st.checkbox("Normalize series for plotting (z-score)", value=False)
    run_button = st.button("▶️ Run Analysis")

# -------------------------------------------------------
# RUN COMPUTATION
# -------------------------------------------------------
if run_button:
    st.header("📈 Results")

    # --- Retrieve and align the data ---
    series_energy = prepare_energy_series(df_energy, price_area, freq)
    lat, lon = PRICE_AREA_COORDS[price_area]

    start_date, end_date = "2018-01-01", "2024-12-31"
    df_weather = download_weather_data(lat, lon, start_date, end_date)
    series_met = df_weather[met_col].resample(freq).mean()

    corr_series = compute_rolled_corr(series_met, series_energy, window_len, lag)

   

    series_energy_plot = series_energy
    series_met_plot = series_met

    if normalize_plot:
        # Align both series
        df_align = pd.concat([series_energy, series_met], axis=1).dropna()
        series_energy_plot = pd.Series(zscore(df_align["quantity_kwh"]), index=df_align.index, name="quantity_kwh")
        series_met_plot = pd.Series(zscore(df_align[met_col]), index=df_align.index, name=met_col)


    # ===================== PLOTS =========================

    st.subheader("📌 Aligned time-series (normalized)" if normalize_plot else "📌 Aligned time-series")
    fig = px.line(pd.concat([series_met_plot, series_energy_plot], axis=1))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔄 Sliding-window correlation")
    fig_corr = px.line(x=corr_series.index, y=corr_series.values,
                       labels={"x":"Time", "y":"Correlation"},
                       title="Correlation over time")
    fig_corr.update_layout(yaxis=dict(range=[-1,1]))
    st.plotly_chart(fig_corr, use_container_width=True)

    # 3) Extreme event comparison
    if event_mode != "None" and not corr_series.empty:
        st.subheader("🌪 Effect of extreme weather on correlation")

        if event_mode == "By threshold":
            mask = (df_weather[met_col] > thr_val) if thr_dir=="Above" else (df_weather[met_col] < thr_val)
            mask = mask.resample(freq).max().reindex(corr_series.index).fillna(False)
        else:
            mask = pd.Series(False, index=corr_series.index)
            if len(date_range)==2:
                mask[(corr_series.index >= pd.to_datetime(date_range[0])) &
                     (corr_series.index <= pd.to_datetime(date_range[1]))] = True

        r_event = corr_series[mask].dropna()
        r_normal = corr_series[~mask].dropna()

        if len(r_event)>2 and len(r_normal)>2:
            stat, p = ttest_ind(r_event, r_normal, equal_var=False)
            st.write(f"**Mean correlation (extreme): {r_event.mean():.3f}**")
            st.write(f"**Mean correlation (normal): {r_normal.mean():.3f}**")
            st.write(f"**p-value = {p:.4f}** *(p<0.05 → significantly different)*")
            fig_compare = px.box(pd.DataFrame({"Extreme":r_event, "Normal":r_normal}), title="Correlation distribution")
            st.plotly_chart(fig_compare, use_container_width=True)
        else:
            st.info("Not enough event data to compare statistically.")

    # 4) Lag scan
    st.subheader("⏳ Lag effect scan")
    lags = range(-72, 73)
    mean_corrs = [compute_rolled_corr(series_met, series_energy, window_len, L).mean() for L in lags]
    fig_lag = px.line(x=list(lags), y=mean_corrs,
                      labels={"x":"Lag (periods)", "y":"Mean correlation"})
    st.plotly_chart(fig_lag, use_container_width=True)

    st.success("🎉 Analysis completed!")

else:
    st.info("Set your options above and press **Run Analysis**.")