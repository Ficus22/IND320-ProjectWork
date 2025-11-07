# streamlit_app/pages/5_new_B.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor

st.set_page_config(page_title="🔍 Anomaly & SPC Analysis", layout="wide")
st.title("🔍 Outlier & Anomaly Analysis")

# -------------------------
# Check if price area selected on page 1
# -------------------------
if "selected_price_area" not in st.session_state:
    st.warning("Please select a Price Area on page 1 first.")
    st.stop()

price_area = st.session_state.selected_price_area

# -------------------------
# Load data (MongoDB / Elhub)
# -------------------------
from pymongo import MongoClient
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["elhub_data"]
collection = db["production_data"]

data = list(collection.find({}))
df = pd.DataFrame(data)
if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)

# -------------------------
# Helper functions
# -------------------------
def high_pass_filter(data, cutoff_frequency=0.3):
    data_array = np.asarray(data)
    dct_coeffs = dct(data_array, type=2, norm='ortho')
    dct_coeffs[:int(cutoff_frequency*len(dct_coeffs))] = 0
    return idct(dct_coeffs, type=2, norm='ortho')

def calculate_spc_boundaries(data, n_std=3):
    data_array = np.asarray(data)
    median = np.median(data_array)
    mad = np.median(np.abs(data_array - median))
    lower_bound = median - n_std*mad
    upper_bound = median + n_std*mad
    return lower_bound, upper_bound

def normalize_series(data):
    data = np.asarray(data)
    return (data - data.min()) / (data.max() - data.min())

def plot_temperature_spc_dct_plotly(temperature_data, time_data, cutoff_frequency=0.3, n_std=3):
    temp_array = np.asarray(temperature_data)
    dct_filtered = high_pass_filter(temp_array, cutoff_frequency)
    temp_norm = normalize_series(temp_array)
    dct_norm = normalize_series(dct_filtered)
    lower_bound, upper_bound = calculate_spc_boundaries(dct_norm, n_std)
    outliers = (dct_norm < lower_bound) | (dct_norm > upper_bound)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_data, y=temp_norm, mode='lines', name='Original', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=time_data, y=dct_norm, mode='lines', name='DCT Filtered', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=time_data, y=[upper_bound]*len(time_data), mode='lines', name='Upper Bound', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=time_data, y=[lower_bound]*len(time_data), mode='lines', name='Lower Bound', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=np.array(time_data)[outliers], y=dct_norm[outliers], mode='markers', name='Outliers', marker=dict(color='red', size=6)))
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
    st.header("Outlier / SPC Analysis")
    groups = df["production_group"].dropna().unique()
    selected_group = st.selectbox("Select Production Group", groups)
    cutoff_frequency = st.slider("DCT High-pass cutoff frequency", min_value=0.0, max_value=1.0, value=0.3)
    n_std = st.number_input("SPC n_std", value=3, step=1)

    df_tab1 = df[(df["price_area"]==price_area) & (df["production_group"]==selected_group)]
    if df_tab1.empty:
        st.info("No data available for this selection.")
    else:
        df_tab1 = df_tab1.set_index("start_time").resample("H").sum().interpolate()
        plot_temperature_spc_dct_plotly(df_tab1["quantity_kwh"], df_tab1.index, cutoff_frequency=cutoff_frequency, n_std=n_std)

# --- Tab 2: Anomaly/LOF ---
with tab2:
    st.header("Anomaly Detection with LOF")
    selected_group_lof = st.selectbox("Select Production Group", groups, key="lof_group")
    contamination = st.slider("Expected outliers (%)", min_value=0.0, max_value=10.0, value=1.0)/100

    df_tab2 = df[(df["price_area"]==price_area) & (df["production_group"]==selected_group_lof)]
    if df_tab2.empty:
        st.info("No data available for this selection.")
    else:
        df_tab2 = df_tab2.set_index("start_time").resample("H").sum().interpolate()
        plot_precipitation_with_lof(df_tab2["quantity_kwh"], df_tab2.index, contamination=contamination)