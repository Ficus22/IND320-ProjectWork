# streamlit_app/pages/8_snow_drift.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

from Snow_drift import compute_yearly_results, compute_average_sector, compute_sector_transport

st.set_page_config(page_title="Snow Drift Calculation", layout="wide")
st.title("❄️ Snow Drift Calculation and Wind Rose")

# ---------------------------
# Check map selection
# ---------------------------
if "selected_feature_id" not in st.session_state or st.session_state.selected_feature_id is None:
    st.warning("Please select a location on the map first!")
    st.stop()

lat, lon = st.session_state.last_pin
fid = st.session_state.selected_feature_id
st.write(f"Selected location: ID={fid}, Lat={lat:.3f}, Lon={lon:.3f}")

# ---------------------------
# Year range selector
# ---------------------------
current_year = datetime.utcnow().year
start_year, end_year = st.slider(
    "Select year range",
    min_value=1979,
    max_value=current_year,
    value=(2018, 2022)
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
# Load weather data for each year
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
# Snow drift calculation parameters
# ---------------------------
T = 3000      # Maximum transport distance in meters
F = 30000     # Fetch distance in meters
theta = 0.5   # Relocation coefficient

# ---------------------------
# Compute yearly snow drift
# ---------------------------
yearly_df = compute_yearly_results(df_all, T, F, theta)
if yearly_df.empty:
    st.warning("No snow drift data available for the selected year range.")
    st.stop()

# Convert Qt to tonnes/m
yearly_df["Qt_tonnes"] = yearly_df["Qt (kg/m)"] / 1000

# ---------------------------
# Plot Qt over seasons using Plotly
# ---------------------------
st.subheader("Yearly Snow Drift (Qt)")

fig_qt = px.line(
    yearly_df,
    x='season',
    y='Qt_tonnes',
    markers=True,
    labels={"season": "Season", "Qt_tonnes": "Qt (tonnes/m)"},
    title="Snow Drift Qt Over Seasons"
)
st.plotly_chart(fig_qt, use_container_width=True)

# ---------------------------
# Compute and plot average wind rose
# ---------------------------
st.subheader("Average Wind Rose")

# Compute average sector values across all seasons
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

# Prepare Plotly polar chart
angles = np.linspace(0, 360, 16, endpoint=False)
directions = ['N','NNE','NE','ENE','E','ESE','SE','SSE',
              'S','SSW','SW','WSW','W','WNW','NW','NNW']
theta = angles
r = avg_sectors / 1000  # Convert to tonnes/m

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