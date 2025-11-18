# streamlit_app/pages/5_new_B.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor
from pymongo import MongoClient

st.set_page_config(page_title="Anomaly & SPC Analysis", layout="wide")

# -------------------------
# Check if price area selected on page 2
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

st.title(f"🔍 Outliers and anomalies for {city}")

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
# Functions
# -------------------------
def high_pass_filter(data, cutoff_frequency=0.3):
    data_array = np.asarray(data)
    dct_coeffs = dct(data_array, type=2, norm='ortho')
    dct_coeffs[:int(cutoff_frequency*len(dct_coeffs))] = 0
    return idct(dct_coeffs, type=2, norm='ortho')

def calculate_spc_boundaries(data, n_std=3):
    """SPC boundaries using MAD converted to sigma."""
    data_array = np.asarray(data)
    median = np.median(data_array)
    mad = np.median(np.abs(data_array - median))

    sigma = 1.4826 * mad
    lower_bound = median - n_std * sigma
    upper_bound = median + n_std * sigma
    return lower_bound, upper_bound, median

def normalize_series(data):
    data = np.asarray(data)
    return (data - data.min()) / (data.max() - data.min())

def plot_temperature_spc_dct_plotly(
    temperature_data,
    time_data,
    cutoff_frequency=0.3,
    n_std=3,
    show_normalized=False
):
    """
    SPC with DCT filtering + optional normalized display only.
    """
    temp_array = np.asarray(temperature_data)

    # --------- DCT FILTER ----------
    dct_filtered = high_pass_filter(temp_array, cutoff_frequency)

    # --------- SPC BOUNDARIES ----------
    lower, upper, median = calculate_spc_boundaries(dct_filtered, n_std)

    fig = go.Figure()

    if show_normalized:
        # Normalized data
        temp_norm = normalize_series(temp_array)
        dct_norm = normalize_series(dct_filtered)

        fig.add_trace(go.Scatter(
            x=time_data,
            y=temp_norm,
            mode='lines',
            name='Original (normalized)',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=time_data,
            y=dct_norm,
            mode='lines',
            name='DCT filtered (normalized)',
            line=dict(color='orange')
        ))

        # SPC bounds on normalized scale
        fig.add_trace(go.Scatter(
            x=time_data,
            y=[1.0]*len(time_data),
            mode='lines',
            name='Upper Bound (SPC)',
            line=dict(color='green', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=time_data,
            y=[0.0]*len(time_data),
            mode='lines',
            name='Lower Bound (SPC)',
            line=dict(color='red', dash='dash')
        ))

        # Outliers
        outliers = (dct_norm < 0) | (dct_norm > 1)
        fig.add_trace(go.Scatter(
            x=np.array(time_data)[outliers],
            y=dct_norm[outliers],
            mode='markers',
            name='Outliers',
            marker=dict(color='red', size=7)
        ))

    else:
        # Real values
        fig.add_trace(go.Scatter(
            x=time_data,
            y=temp_array,
            mode='lines',
            name='Original (kWh)',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=time_data,
            y=dct_filtered,
            mode='lines',
            name='DCT filtered (kWh)',
            line=dict(color='orange')
        ))


        # Outliers
        outliers = (dct_filtered < lower) | (dct_filtered > upper)
        fig.add_trace(go.Scatter(
            x=np.array(time_data)[outliers],
            y=dct_filtered[outliers],
            mode='markers',
            name='Outliers',
            marker=dict(color='red', size=7)
        ))

    fig.update_layout(
        title=f"SPC + DCT Analysis (n_std={n_std})",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        yaxis=dict(title="Normalized" if show_normalized else "kWh (real values)")
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_precipitation_with_lof(precipitation, time, contamination=0.01):
    precip_array = np.asarray(precipitation)
    time_array = np.asarray(time)
    data_reshaped = precip_array.reshape(-1,1)
    lof = LocalOutlierFactor(contamination=contamination)
    outlier_flags = lof.fit_predict(data_reshaped) == -1

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_array, y=precip_array, mode='lines', name='Precipitation', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=time_array[outlier_flags], y=precip_array[outlier_flags], mode='markers', name='LOF Anomalies', marker=dict(color='red', size=6)))
    fig.update_layout(title=f"Precipitation with LOF Anomalies ({contamination*100:.1f}% outliers)", xaxis_title="Time", yaxis_title="Precipitation", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Tabs
# -------------------------
tab1, tab2 = st.tabs(["Outlier/SPC Analysis", "Anomaly/LOF Analysis"])

# --- Tab 1: Outlier/SPC ---
with tab1:
    st.header(f"Outlier / SPC Analysis for {city}")
    groups = df["production_group"].dropna().unique()
    selected_group = st.selectbox("Select Production Group", groups)
    cutoff_frequency = st.slider("DCT High-pass cutoff frequency", min_value=0.0, max_value=1.0, value=0.3)
    n_std = st.number_input("SPC sensitivity", value=3, step=1)

    show_normalized = st.checkbox(
    "Display normalized output", 
    value=False)

    df_tab1 = df[(df["price_area"]==price_area) & (df["production_group"]==selected_group)]
    if df_tab1.empty:
        st.info("No data available for this selection.")
    else:
        df_tab1["start_time"] = pd.to_datetime(df_tab1["start_time"]).dt.tz_localize(None)
        df_tab1 = df_tab1.set_index("start_time")
        numeric_cols = df_tab1.select_dtypes(include="number").columns
        df_tab1_resampled = df_tab1[numeric_cols].resample("H").sum().interpolate()
        plot_temperature_spc_dct_plotly(
            df_tab1_resampled["quantity_kwh"],
            df_tab1_resampled.index,
            cutoff_frequency=cutoff_frequency,
            n_std=n_std,
            show_normalized=show_normalized
        )


# --- Tab 2: Anomaly/LOF ---
with tab2:
    st.header(f"Anomaly Detection with LOF for {city}")
    selected_group_lof = st.selectbox("Select Production Group", groups, key="lof_group")
    contamination = st.slider("Expected outliers (%)", min_value=0.0, max_value=10.0, value=1.0)/100

    df_tab2 = df[(df["price_area"]==price_area) & (df["production_group"]==selected_group_lof)]
    if df_tab2.empty:
        st.info("No data available for this selection.")
    else:
        df_tab2["start_time"] = pd.to_datetime(df_tab2["start_time"]).dt.tz_localize(None)
        df_tab2 = df_tab2.set_index("start_time")
        numeric_cols = df_tab2.select_dtypes(include="number").columns
        df_tab2_resampled = df_tab2[numeric_cols].resample("H").sum().interpolate()
        plot_precipitation_with_lof(df_tab2_resampled["quantity_kwh"], df_tab2_resampled.index, contamination=contamination)