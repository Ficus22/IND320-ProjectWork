# streamlit_app/pages/4_plots.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# -------------------------
# Check if a price area was selected on page 2
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
latitude = PRICE_AREAS[price_area]["lat"]
longitude = PRICE_AREAS[price_area]["lon"]

st.title(f"📈 Weather Visualizations for {city}")
st.markdown("*Open-Meteo ERA5 data*")

# ==============================
# Function to download Open-Meteo ERA5 data
# ==============================
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

# Year selection (default 2021)
selected_year = st.number_input(
    "Select year (below 2025):",
    min_value=1979,
    max_value=datetime.utcnow().year,
    value=2021,
    step=1
)

# ==============================
# Load data
# ==============================
try:
    df = download_weather_data(latitude, longitude, selected_year)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

numeric_cols = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m"
]

# ==============================
# User selection widgets
# ==============================
selected_col = st.selectbox("Choose a variable:", numeric_cols + ["All columns"])

months = sorted(df['time'].dt.month.unique())
month_names = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}
month_labels = [month_names[m] for m in months]

month_range_labels = st.select_slider(
    "Select a month range",
    options=month_labels,
    value=(month_labels[0], month_labels[min(2, len(month_labels)-1)])
)

month_range = [
    [k for k,v in month_names.items() if v == month_range_labels[0]][0],
    [k for k,v in month_names.items() if v == month_range_labels[1]][0]
]

filtered_df = df[df['time'].dt.month.between(month_range[0], month_range[1])]

# ==============================
# Line chart
# ==============================
if selected_col == "All columns":
    fig = px.line(
        filtered_df,
        x="time",
        y=numeric_cols,
        title=f"Weather variables over time ({month_names[month_range[0]]} → {month_names[month_range[1]]})"
    )
else:
    fig = px.line(
        filtered_df,
        x="time",
        y=selected_col,
        title=f"{selected_col} ({month_names[month_range[0]]} → {month_names[month_range[1]]})"
    )

fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Values",
    legend_title="Variables"
)
st.plotly_chart(fig, use_container_width=True)

# ==============================
# Polar plot for wind direction
# ==============================
st.subheader("🌪️ Wind Direction and Intensity")
if "wind_direction_10m" in df.columns:
    fig_polar = px.scatter_polar(
        filtered_df,
        r="wind_speed_10m",
        theta="wind_direction_10m",
        size="wind_speed_10m",
        color="wind_speed_10m",
        title="Wind Rose (Polar)"
    )
    st.plotly_chart(fig_polar, use_container_width=True)
else:
    st.info("Wind direction data not available for this zone.")