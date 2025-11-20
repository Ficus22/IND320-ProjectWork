# streamlit_app/pages/5_anomaly_and_SPC.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor
from utils.data_loader import load_mongo_data
from utils.config import PRICE_AREAS

def app():
    st.set_page_config(page_title="Anomaly & SPC Analysis", layout="wide")

    # -------------------------
    # Check if price area selected
    # -------------------------
    if "selected_price_area" not in st.session_state:
        st.warning("Please select a Price Area on the Elhub API page first.")
        st.stop()

    price_area = st.session_state.selected_price_area

    # -------------------------
    # Price area info
    # -------------------------
    if price_area not in PRICE_AREAS:
        st.error(f"Unknown price area: {price_area}")
        st.stop()

    city = PRICE_AREAS[price_area]["city"]
    st.title(f"🔍 Outliers and Anomalies for {city}")

    # -------------------------
    # Load data
    # -------------------------
    df = load_mongo_data("production_data")
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
        SPC with DCT filtering + optional normalized display.
        """
        temp_array = np.asarray(temperature_data)
        # DCT FILTER
        dct_filtered = high_pass_filter(temp_array, cutoff_frequency)
        # SPC BOUNDARIES
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
            # SPC bounds
            fig.add_trace(go.Scatter(
                x=time_data,
                y=[upper]*len(time_data),
                mode='lines',
                name='Upper Bound (SPC)',
                line=dict(color='green', dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=time_data,
                y=[lower]*len(time_data),
                mode='lines',
                name='Lower Bound (SPC)',
                line=dict(color='red', dash='dash')
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
        
        # Use only temperature data for SPC
        if "temperature_c" not in df.columns:
            st.error("Temperature data not available for SPC analysis.")
        else:
            df_temp = df[df["price_area"] == price_area].copy()
            df_temp["start_time"] = pd.to_datetime(df_temp["start_time"]).dt.tz_localize(None)
            df_temp = df_temp.set_index("start_time")
            df_temp_resampled = df_temp["temperature_c"].resample("H").mean().interpolate()

            n_std = st.number_input("SPC sensitivity", value=3, step=1)

            # Calculate SPC bounds based on DCT (SATV)
            dct_filtered = high_pass_filter(df_temp_resampled.values)
            lower, upper, median = calculate_spc_boundaries(dct_filtered, n_std=n_std)

            # Identify outliers based on SPC bounds
            outliers = (df_temp_resampled < lower) | (df_temp_resampled > upper)

            # Plot raw temperature with SPC bounds and outliers
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_temp_resampled.index,
                y=df_temp_resampled.values,
                mode='lines',
                name='Temperature (°C)',
                line=dict(color='blue')
            ))
            fig.add_trace(go.Scatter(
                x=df_temp_resampled.index,
                y=[upper]*len(df_temp_resampled),
                mode='lines',
                name='Upper Bound (SPC)',
                line=dict(color='green', dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=df_temp_resampled.index,
                y=[lower]*len(df_temp_resampled),
                mode='lines',
                name='Lower Bound (SPC)',
                line=dict(color='red', dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=df_temp_resampled.index[outliers],
                y=df_temp_resampled.values[outliers],
                mode='markers',
                name='Outliers',
                marker=dict(color='red', size=7)
            ))

            fig.update_layout(
                title=f"Temperature SPC Analysis (n_std={n_std})",
                hovermode="x unified",
                yaxis=dict(title="Temperature (°C)")
            )
            st.plotly_chart(fig, use_container_width=True)
