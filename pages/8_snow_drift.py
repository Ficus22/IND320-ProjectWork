# streamlit_app/pages/8_snow_drift.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

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
PRICE_AREAS = {
    "8": "Oslo",
    "6": "Kristiansand",
    "9": "Trondheim",
    "10": "Tromsø",
    "7": "Bergen"
}

if "selected_feature_id" not in st.session_state or st.session_state.selected_feature_id is None:
    st.warning("Please select a location on the map first!")
    st.stop()

lat, lon = st.session_state.last_pin
fid = st.session_state.selected_feature_id
st.write(f"Selected location: ID={fid}, Lat={lat:.3f}, Lon={lon:.3f}, city={type(fid)}")

# ---------------------------
# Year range selector
# ---------------------------
start_year, end_year = st.slider(
    "Select year range",
    min_value=2021,
    max_value=2024,
    value=(2021, 2024)
)

# ---------------------------
# Download weather data function
# ---------------------------
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

@st.cache_data
def download_weather_data(latitude: float, longitude: float, year: int,
                          hourly=("temperature_2m","precipitation",
                                  "wind_speed_10m","wind_gusts_10m","wind_direction_10m")) -> pd.DataFrame:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(hourly),
        "timezone": "UTC"
    }
    response = requests.get(OPENMETEO_ERA5, params=params, timeout=30)
    response.raise_for_status()
    hourly_data = response.json().get("hourly", {})
    df = pd.DataFrame({"time": pd.to_datetime(hourly_data.get("time", []), utc=True)})
    for v in hourly:
        df[v] = pd.to_numeric(hourly_data.get(v, []), errors="coerce")
    return df

# ---------------------------
# Snow drift calculation functions
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
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1
        )
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
            df_year = download_weather_data(
                st.session_state.last_pin[0], st.session_state.last_pin[1], year
            )
            df_year['season'] = df_year['time'].apply(lambda dt: dt.year if dt.month >= 7 else dt.year - 1)
            dfs.append(df_year)
        except Exception as e:
            st.error(f"Error loading data for year {year}: {e}")

if not dfs:
    st.stop()

df_all = pd.concat(dfs, ignore_index=True)
df_all['time'] = pd.to_datetime(df_all['time'], errors='coerce', utc=True)

# ---------------------------
# Snow drift parameters
# ---------------------------
T = 3000
F = 30000
theta = 0.5

# ---------------------------
# Yearly snow drift
# ---------------------------
yearly_df = compute_yearly_results(df_all, T, F, theta)
if yearly_df.empty:
    st.warning("No snow drift data available for the selected year range.")
    st.stop()

yearly_df["Qt_tonnes"] = yearly_df["Qt (kg/m)"] / 1000

# ---------------------------
# Monthly snow drift
# ---------------------------
df_all['month'] = df_all['time'].dt.month
monthly_results_list = []

for season, group in df_all.groupby('season'):
    for month, month_group in group.groupby('month'):
        month_group = month_group.copy()
        month_group['Swe_hourly'] = month_group.apply(
            lambda row: row['precipitation'] if row['temperature_2m'] < 1 else 0, axis=1
        )
        total_Swe = month_group['Swe_hourly'].sum()
        wind_speeds = month_group["wind_speed_10m"].tolist()
        result = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
        result['season'] = f"{season}"
        result['month'] = month
        monthly_results_list.append(result)

monthly_df = pd.DataFrame(monthly_results_list)
monthly_df["Qt_tonnes"] = monthly_df["Qt (kg/m)"] / 1000

# ---------------------------
# Plot yearly + monthly Qt (shared x-axis)
# ---------------------------
st.subheader("Snow Drift Qt Over Seasons")
st.markdown("Monthly Qt (orange) is plotted **per season** for comparison with yearly Qt (blue).")

fig_combined = go.Figure()

# Yearly Qt
fig_combined.add_trace(go.Scatter(
    x=yearly_df['season'],
    y=yearly_df['Qt_tonnes'],
    mode='lines+markers',
    name='Yearly Qt (tonnes/m)',
    line=dict(color='blue', width=3)
))

# Monthly Qt per season
fig_combined.add_trace(go.Scatter(
    x=monthly_df['season'],
    y=monthly_df['Qt_tonnes'],
    mode='markers',
    name='Monthly Qt (tonnes/m)',
    marker=dict(color='orange', size=8, symbol='circle')
))

fig_combined.update_layout(
    title="Snow Drift Transport (Qt) per Season",
    xaxis_title="Season",
    yaxis_title="Qt (tonnes/m)",
    legend=dict(x=0.01, y=0.99),
    template="plotly_white"
)

st.plotly_chart(fig_combined, use_container_width=True)

# ---------------------------
# Wind rose (reverted to original)
# ---------------------------
st.subheader("Average Wind Rose")
st.markdown("The wind rose shows the **directional distribution of snow transport** (Qt).")

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
r = avg_sectors / 1000  # tonnes/m

fig_rose = go.Figure(go.Barpolar(
    r=r,
    theta=angles,
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