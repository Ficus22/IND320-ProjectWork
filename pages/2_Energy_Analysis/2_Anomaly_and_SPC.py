# streamlit_app/pages/5_anomaly_and_SPC.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.fftpack import dct, idct
from sklearn.neighbors import LocalOutlierFactor
from utils.data_loader import load_mongo_data, load_weather_data
from utils.config import PRICE_AREAS, DEFAULT_YEAR, MAX_YEAR, MIN_YEAR

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
    # Load production data
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
        dct_coeffs[:int(cutoff_frequency * len(dct_coeffs))] = 0
        return idct(dct_coeffs, type=2, norm='ortho')

    def calculate_spc_boundaries(data, n_std=3):
        """Calculate SPC bounds using MAD converted to sigma"""
        data_array = np.asarray(data)
        median = np.median(data_array)
        mad = np.median(np.abs(data_array - median))
        sigma = 1.4826 * mad
        lower_bound = median - n_std * sigma
        upper_bound = median + n_std * sigma
        return lower_bound, upper_bound

    def plot_temperature_spc(
        temperature_series: pd.Series,
        cutoff_frequency: float = 0.3,
        n_std: float = 3
    ):
        """
        Plot raw temperature data with SPC bounds (calculated from SATV) and highlight outliers.
        Returns:
            fig: Plotly Figure
            outlier_summary: dict with count, times, and values
        """
        # High-pass filter (SATV) for SPC bounds calculation
        satv = high_pass_filter(temperature_series.values, cutoff_frequency=cutoff_frequency)
        # Calculate SPC boundaries from SATV
        lower, upper = calculate_spc_boundaries(satv, n_std=n_std)
        # Identify outliers on raw temperature data
        outliers_mask = (temperature_series < lower) | (temperature_series > upper)

        # Plot raw temperature data and SPC bounds
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temperature_series.index,
            y=temperature_series.values,
            mode='lines',
            name='Temperature (°C)',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=temperature_series.index,
            y=[upper] * len(temperature_series),
            mode='lines',
            name='Upper Bound (SPC)',
            line=dict(color='green', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=temperature_series.index,
            y=[lower] * len(temperature_series),
            mode='lines',
            name='Lower Bound (SPC)',
            line=dict(color='red', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=temperature_series.index[outliers_mask],
            y=temperature_series.values[outliers_mask],
            mode='markers',
            name='Outliers',
            marker=dict(color='red', size=7)
        ))
        fig.update_layout(
            title=f"Temperature SPC Analysis (n_std={n_std}, cutoff={cutoff_frequency})",
            hovermode="x unified",
            yaxis=dict(title="Temperature (°C)")
        )

        # Summarize outliers
        outlier_summary = {
            "count": outliers_mask.sum(),
            "times": temperature_series.index[outliers_mask].tolist(),
            "values": temperature_series.values[outliers_mask].tolist()
        }
        return fig, outlier_summary


    def plot_precipitation_with_lof(precipitation, time, contamination=0.01):
        precip_array = np.asarray(precipitation)
        time_array = np.asarray(time)
        data_reshaped = precip_array.reshape(-1,1)
        lof = LocalOutlierFactor(contamination=contamination)
        outlier_flags = lof.fit_predict(data_reshaped) == -1
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_array, y=precip_array, mode='lines', name='Production Data', line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=time_array[outlier_flags], y=precip_array[outlier_flags],
            mode='markers', name='LOF Anomalies', marker=dict(color='red', size=6)
        ))
        fig.update_layout(
            title=f"Production LOF Anomalies ({contamination*100:.1f}% expected outliers)",
            xaxis_title="Time",
            yaxis_title="Quantity",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # Tabs
    # -------------------------
    tab1, tab2 = st.tabs(["Outlier/SPC Analysis", "Anomaly/LOF Analysis"])

    # --- Tab 1: Outlier/SPC ---
    with tab1:
        st.header(f"Outlier / SPC Analysis for {city}")

        year = st.number_input("Year", min_value=MIN_YEAR, max_value=MAX_YEAR, value=DEFAULT_YEAR, step=1)
        cutoff_frequency = st.slider("DCT high-pass cutoff frequency", 0.0, 1.0, 0.01)
        n_std = st.number_input("SPC sensitivity (n_std)", value=3, step=1)

        try:
            df_temp = load_weather_data(price_area, year)
        except Exception as e:
            st.error(f"Failed to load temperature data: {e}")
            df_temp = pd.DataFrame()

        if df_temp.empty or "temperature_2m" not in df_temp.columns:
            st.error("Temperature data not available for SPC analysis.")
        else:
            df_temp["time"] = pd.to_datetime(df_temp["time"]).dt.tz_localize(None)
            df_temp = df_temp.set_index("time")
            df_temp_resampled = df_temp["temperature_2m"].resample("H").mean().interpolate()

            fig, summary = plot_temperature_spc(
                df_temp_resampled,
                cutoff_frequency=cutoff_frequency,
                n_std=n_std
            )
            st.plotly_chart(fig, use_container_width=True)
            st.write(f"Number of outliers detected: {summary['count']}")

    # --- Tab 2: Anomaly/LOF ---
    with tab2:
        st.header(f"Anomaly Detection with LOF for {city}")

        # Get all production groups
        groups = df["production_group"].dropna().unique()
        selected_group_lof = st.selectbox("Select Production Group", groups, key="lof_group")
        contamination = st.slider("Expected outliers (%)", 0.0, 10.0, 1.0) / 100

        df_tab2 = df[(df["price_area"] == price_area) & (df["production_group"] == selected_group_lof)]
        if df_tab2.empty:
            st.info("No data available for this selection.")
        else:
            df_tab2["start_time"] = pd.to_datetime(df_tab2["start_time"]).dt.tz_localize(None)
            df_tab2 = df_tab2.set_index("start_time")
            numeric_cols = df_tab2.select_dtypes(include="number").columns
            df_tab2_resampled = df_tab2[numeric_cols].resample("H").sum().interpolate()
            plot_precipitation_with_lof(df_tab2_resampled["quantity_kwh"], df_tab2_resampled.index, contamination=contamination)
