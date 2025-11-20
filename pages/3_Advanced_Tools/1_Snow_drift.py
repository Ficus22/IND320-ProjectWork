# streamlit_app/pages/8_snow_drift.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import download_weather_data
from utils.config import PRICE_AREAS

def app():
    # ---------------------------
    # Page configuration
    # ---------------------------
    st.set_page_config(page_title="Snow Drift Analysis", layout="wide")
    st.title("❄️ Snow Drift Analysis and Wind Rose")
    st.markdown("""
    This page calculates **snow drift transport (Qt)** based on ERA5 weather data.
    Qt represents the **snow mass transported by wind per meter**. We show **yearly and monthly trends**, and a **wind rose** for directional distribution.
    """)

    # ---------------------------
    # Map selection check
    # ---------------------------
    if "selected_feature_id" not in st.session_state or st.session_state.selected_feature_id is None:
        st.warning("Please select a location on the map first!")
        st.stop()

    lat, lon = st.session_state.last_pin
    fid = st.session_state.selected_feature_id

    # Use PRICE_AREAS from config.py
    price_areas = {
        8: "NO1",
        6: "NO2",
        9: "NO3",
        10: "NO4",
        7: "NO5"
    }

    if fid not in price_areas:
        st.error(f"Unknown feature ID: {fid}")
        st.stop()

    price_area = price_areas[fid]
    city = PRICE_AREAS[price_area]["city"]
    st.write(f"Selected location: {city}")

    # ---------------------------
    # Year range selector
    # ---------------------------
    start_year, end_year = st.slider(
        "Select year range",
        min_value=2018,
        max_value=2024,
        value=(2018, 2021)
    )

    # ---------------------------
    # Snow drift functions
    # ---------------------------
    def compute_Qupot(hourly_wind_speeds, dt=3600):
        return sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847

    def sector_index(direction):
        return int(((direction + 11.25) % 360) // 22.5)

    def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
        sectors = [0.0] * 16
        for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
            idx = sector_index(d)
            sectors[idx] += ((u ** 3.8) * dt) / 233847
        return sectors

    def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds, dt=3600):
        Qupot = compute_Qupot(hourly_wind_speeds, dt)
        Qspot = 0.5 * T * Swe
        Srwe = theta * Swe
        if Qupot > Qspot:
            Qinf = 0.5 * T * Srwe
            control = "Snowfall controlled"
        else:
            Qinf = Qupot
            control = "Wind controlled"
        Qt = Qinf * (1 - 0.14 ** (F / T))
        return {"Qupot (kg/m)": Qupot, "Qspot (kg/m)": Qspot, "Srwe (mm)": Srwe,
                "Qinf (kg/m)": Qinf, "Qt (kg/m)": Qt, "Control": control}

    def compute_yearly_results(df, T, F, theta):
        seasons = sorted(df['season'].unique())
        results_list = []
        for s in seasons:
            season_start = pd.Timestamp(year=s, month=7, day=1, tz='UTC')
            season_end = pd.Timestamp(year=s+1, month=6, day=30, hour=23, minute=59, second=59, tz='UTC')
            df_season = df[(df['time'] >= season_start) & (df['time'] <= season_end)]
            if df_season.empty:
                continue
            df_season = df_season.copy()
            df_season['Swe_hourly'] = df_season.apply(
                lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1)
            total_Swe = df_season['Swe_hourly'].sum()
            wind_speeds = df_season["wind_speed_10m"].tolist()
            result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
            result["season"] = f"{s}-{s+1}"
            results_list.append(result)
        return pd.DataFrame(results_list)

    # ---------------------------
    # Download weather data per year
    # ---------------------------
    dfs = []
    with st.spinner("Downloading weather data..."):
        for year in range(start_year, end_year + 1):
            try:
                df_year = download_weather_data(lat, lon, year)
                df_year['season'] = df_year['time'].apply(lambda dt: dt.year if dt.month >= 7 else dt.year - 1)
                dfs.append(df_year)
            except Exception as e:
                st.error(f"Error loading data for year {year}: {e}")
    if not dfs:
        st.stop()

    df_all = pd.concat(dfs, ignore_index=True)

    # ---------------------------
    # Compute yearly snow drift
    # ---------------------------
    T = 3000
    F = 30000
    theta = 0.5
    yearly_df = compute_yearly_results(df_all, T, F, theta)
    if yearly_df.empty:
        st.warning("No snow drift data available for the selected year range.")
        st.stop()

    yearly_df["Qt_tonnes"] = yearly_df["Qt (kg/m)"] / 1000

    # Assign a datetime for plotting: first month of the season (July)
    yearly_df['plot_time'] = yearly_df['season'].apply(lambda s: pd.Timestamp(int(s.split('-')[0]), 7, 1))

    # ---------------------------
    # Compute monthly snow drift
    # ---------------------------
    df_all['year_month'] = df_all['time'].dt.to_period('M')
    monthly_results_list = []
    for ym, group in df_all.groupby('year_month'):
        group = group.copy()
        group['Swe_hourly'] = group.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1
        )
        total_Swe = group['Swe_hourly'].sum()
        wind_speeds = group["wind_speed_10m"].tolist()
        result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
        result['year_month'] = ym.to_timestamp()
        monthly_results_list.append(result)

    monthly_df = pd.DataFrame(monthly_results_list)
    monthly_df["Qt_tonnes"] = monthly_df["Qt (kg/m)"] / 1000

    # ---------------------------
    # Plot both yearly and monthly Qt
    # ---------------------------
    fig = go.Figure()
    # Yearly Qt (July-June season, one point per season)
    fig.add_trace(go.Scatter(
        x=yearly_df['plot_time'],
        y=yearly_df['Qt_tonnes'],
        mode='lines+markers',
        name='Yearly Qt (July-June)',
        line=dict(color='blue', width=3),
        marker=dict(size=8)
    ))
    # Monthly Qt (calendar months)
    fig.add_trace(go.Scatter(
        x=monthly_df['year_month'],
        y=monthly_df['Qt_tonnes'],
        mode='lines+markers',
        name='Monthly Qt',
        line=dict(color='orange', width=2),
        marker=dict(size=6)
    ))
    fig.update_layout(
        title="Snow Drift Transport (Qt): Yearly vs Monthly",
        xaxis_title="Time",
        yaxis_title="Qt (tonnes/m)",
        legend=dict(x=0.01, y=0.99),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # Compute average wind rose
    # ---------------------------
    st.subheader("Average Wind Rose")
    sectors_list = []
    for s, group in df_all.groupby('season'):
        group = group.copy()
        group['Swe_hourly'] = group.apply(lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1)
        ws = group["wind_speed_10m"].tolist()
        wdir = group["wind_direction_10m"].tolist()
        sectors = compute_sector_transport(ws, wdir)
        sectors_list.append(sectors)

    avg_sectors = np.mean(sectors_list, axis=0)
    overall_avg = yearly_df['Qt (kg/m)'].mean()
    angles = np.linspace(0, 360, 16, endpoint=False)
    directions = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
                'S','SSW','SW','WSW','W','WNW','NW','NNW']
    theta = angles
    r = avg_sectors / 1000  # tonnes/m
    fig_rose = go.Figure(go.Barpolar(
        r=r,
        theta=theta,
        width=[22.5]*16,
        marker_color=r,
        marker_line_color="black",
        marker_line_width=1,
        opacity=0.8
    ))
    fig_rose.update_layout(
        polar=dict(
            radialaxis=dict(title="Qt (tonnes/m)"),
            angularaxis=dict(direction="clockwise", rotation=90, tickmode='array', tickvals=angles, ticktext=directions)
        ),
        title=f"Average Directional Distribution of Snow Transport<br>Overall Qt: {overall_avg/1000:.1f} tonnes/m"
    )
    st.plotly_chart(fig_rose, use_container_width=True)