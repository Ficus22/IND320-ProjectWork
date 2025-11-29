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
        # --- Separate trend and SATV (high-pass) ---
        satv = high_pass_filter(temperature_series.values, cutoff_frequency=cutoff_frequency)
        trend = temperature_series.values - satv  # estimated trend

        # --- SPC boundaries are computed from SATV only ---
        lower_satv, upper_satv = calculate_spc_boundaries(satv, n_std=n_std)

        # --- Transform SATV bounds back to curves following the real data ---
        upper_curve = trend + upper_satv
        lower_curve = trend + lower_satv

        # --- Detect outliers in SATV (NOT in raw temperature) ---
        outliers_mask = (satv < lower_satv) | (satv > upper_satv)


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
            y=upper_curve, 
            name='Upper Bound',
            line=dict(color='green', dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=temperature_series.index, 
            y=lower_curve, name='Lower Bound',
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
        n_neighbors = st.slider("Number of LOF neighbors", 5, 100, 20)
        lof = LocalOutlierFactor(contamination=contamination, n_neighbors=n_neighbors)
        outlier_flags = lof.fit_predict(data_reshaped) == -1
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_array, y=precip_array, mode='lines', name='Precipitation Data', line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=time_array[outlier_flags], y=precip_array[outlier_flags],
            mode='markers', name='LOF Anomalies', marker=dict(color='red', size=6)
        ))
        fig.update_layout(
            title=f"Precipitation LOF Anomalies ({contamination*100:.1f}% expected outliers)",
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
        st.markdown('''
        This section performs an Outlier and SPC (Statistical Process Control) Analysis on hourly weather data. SPC methods evaluate how stable the process is over time, using control charts to identify abnormal fluctuations compared to expected variability.

        **Purpose of this tab :**
        - Detect unusual values within each weather variable separately
        - Highlight points outside statistical control limits
         - Reveal measurement errors, abnormal weather, or rare events

        SPC helps determine whether variations in weather data are part of normal behavior or represent potential outliers.
        
        ---
                    
        ''')

        year = st.number_input("Year", min_value=MIN_YEAR, max_value=MAX_YEAR, value=DEFAULT_YEAR, step=1)
        cutoff_frequency = st.slider("DCT high-pass cutoff frequency", 0.0, 0.1, 0.01)
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
        st.markdown('''
        This section applies Anomaly Detection using Local Outlier Factor (LOF) on hourly precipitation data.  
        LOF compares each value to its neighbors and highlights unusual spikes or drops in rainfall intensity.

        **Purpose of this tab :**
        - Detect precipitation anomalies based on local deviations in the dataset
        - Capture abnormal rainfall events not visible through SPC control limits alone
        - Identify rare weather events such as extreme rain peaks or unexpected dry periods

        Unlike SPC, LOF does not rely on global thresholds but detects anomalies based on local behavior, making it useful for rainfall outlier detection.
        
        ---
                    
        ''')

        # Select year and contamination
        year_lof = st.number_input("Year (for precipitation)", min_value=MIN_YEAR, max_value=MAX_YEAR, value=DEFAULT_YEAR, step=1)
        contamination = st.slider("Expected outliers (%)", 0.0, 10.0, 1.0) / 100

        # Load precipitation data
        try:
            df_weather = load_weather_data(price_area, year_lof)
        except Exception as e:
            st.error(f"Failed to load weather data: {e}")
            st.stop()

        if df_weather.empty or "precipitation" not in df_weather.columns:
            st.error("Precipitation data not available for LOF analysis.")
        else:
            df_weather["time"] = pd.to_datetime(df_weather["time"]).dt.tz_localize(None)
            df_weather = df_weather.set_index("time")
            precipitation_series = df_weather["precipitation"].resample("H").sum().interpolate()

            # Plot LOF anomalies on precipitation
            plot_precipitation_with_lof(precipitation_series, precipitation_series.index, contamination=contamination)
