# streamlit_app/pages/9_sliding_windows.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from scipy.stats import ttest_ind, zscore
from utils.data_loader import load_mongo_data, download_weather_data
from utils.config import PRICE_AREAS, DEFAULT_YEAR, DEFAULT_PRICE_AREA

def app():
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
    # USER SETTINGS
    # -------------------------------------------------------
    st.subheader("🔧 Analysis settings")
    with st.expander("Click to configure settings", expanded=True):
        mode = st.radio("Energy dataset", ["Production", "Consumption"])
        collection_name = "production_data" if mode == "Production" else "consumption_data"
        if f"df_{collection_name}" not in st.session_state:
            st.session_state[f"df_{collection_name}"] = load_mongo_data(collection_name)
        df_energy = st.session_state[f"df_{collection_name}"]

        price_area = st.selectbox(
            "Price area (region + city)",
            options=list(PRICE_AREAS.keys()),
            format_func=lambda x: f"{x} — {PRICE_AREAS[x]['city']}",
            index=list(PRICE_AREAS.keys()).index(DEFAULT_PRICE_AREA)
        )

        st.markdown("""
    #### 📌 Resample frequency
    Energy and meteorological data do not always share the same timestamps.
    Resampling aligns them to a common time step (e.g., hourly or daily) to make comparison possible.
    """)
        freq = st.selectbox("Time resolution", ["H", "3H", "6H", "12H", "D"])

        st.markdown("""
    #### 🌡️ Meteorological & Signal Parameters
    Choose the weather feature affecting energy.
    """)

        met_col = st.selectbox(
            "Meteorological variable",
            ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
        )
        st.caption("This is the meteorological factor whose influence you want to study.")

        window_len = st.slider("Sliding window (in hours)", 3, 24*30, 24)
        st.caption("Groups consecutive time points to compute one correlation. Larger window → smoother correlation; smaller window → more reactive to short-term changes.")

        lag = st.slider("Lag (in hours)", -168, 168, 0)
        st.caption("Tests whether weather impacts energy with a delay. Positive lag → weather leads, energy responds later; Negative lag → energy leads. Helps identify the delay at which weather most strongly affects energy.")

        st.markdown("""
    #### 🌪 Highlight extreme events
    This highlights periods where the chosen weather variable is unusually high/low or within a selected date range. The tool compares correlation during these extreme periods vs the rest of the time to see if weather influence changes.
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
    @st.cache_data
    def sliding_window_correlation(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
        return x.rolling(window=window).corr(y)

    @st.cache_data
    def compute_rolled_corr(series_met: pd.Series, series_eng: pd.Series, window_hours: int, lag_hours: int) -> pd.Series:
        if lag_hours != 0:
            series_eng = series_eng.shift(-lag_hours)
        df = pd.concat([series_met, series_eng], axis=1).dropna()
        if df.empty:
            return pd.Series([], dtype=float)
        return sliding_window_correlation(df.iloc[:,0], df.iloc[:,1], window_hours)

    # -------------------------------------------------------
    # RUN COMPUTATION
    # -------------------------------------------------------
    if run_button:
        st.header("📈 Results")
        with st.spinner("Running analysis..."):
            # --- Retrieve and align the data ---
            series_energy = prepare_energy_series(df_energy, price_area, freq)
            lat, lon = PRICE_AREAS[price_area]["lat"], PRICE_AREAS[price_area]["lon"]

            # Download weather data
            df_weather = download_weather_data(lat, lon, DEFAULT_YEAR)
            for year in range(2018, 2025):
                if year != DEFAULT_YEAR:
                    df_year = download_weather_data(lat, lon, year)
                    df_weather = pd.concat([df_weather, df_year], ignore_index=True)

            # Set 'time' as the index and sort
            if "time" not in df_weather.columns:
                st.error("Weather data does not contain a 'time' column.")
                st.stop()

            df_weather["time"] = pd.to_datetime(df_weather["time"])
            df_weather = df_weather.set_index("time").sort_index()

            # Check if the selected meteorological column exists
            if met_col not in df_weather.columns:
                st.error(f"Meteorological variable '{met_col}' not found in weather data.")
                st.stop()

            # Resample weather data
            series_met = df_weather[met_col].resample(freq).mean()

            # Check if resampling worked
            if series_met.empty:
                st.error("Resampled weather data is empty. Check the frequency and data range.")
                st.stop()

            # Compute correlation
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
            st.markdown("""
            The **correlation over time** shows how strongly the selected meteorological variable and energy series are related during each sliding window.
            - **Positive correlation (~1)**: When the weather variable increases, energy also increases.
            - **Negative correlation (~-1)**: When the weather variable increases, energy decreases.
            - **Near zero (~0)**: Little to no linear relationship in that period.
            Use this to detect periods when the weather has the most impact on energy production or consumption.
            """)
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
            st.markdown("""
            The **lag scan** explores delayed effects of weather on energy.
            - The x-axis is the lag (in periods) between weather and energy.
            - The y-axis is the **mean correlation** for each lag.
            - Peaks indicate the lag at which the weather most strongly affects energy.
            For example, if the highest correlation occurs at lag = 3 hours, it means changes in the weather influence energy about 3 hours later.
            """)
            lags = range(-72, 73)
            mean_corrs = [compute_rolled_corr(series_met, series_energy, window_len, L).mean() for L in lags]
            fig_lag = px.line(x=list(lags), y=mean_corrs,
                            labels={"x":"Lag (periods)", "y":"Mean correlation"})
            st.plotly_chart(fig_lag, use_container_width=True)
            st.success("🎉 Analysis completed!")
    else:
        st.info("Set your options above and press **Run Analysis**.")