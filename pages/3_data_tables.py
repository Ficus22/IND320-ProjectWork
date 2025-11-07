import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# --- API fetch ---
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

def download_weather_data(latitude: float, longitude: float, year: int, 
                          hourly=("temperature_2m","precipitation",
                                  "wind_speed_10m","wind_gusts_10m","wind_direction_10m")) -> pd.DataFrame:
    """
    Downloads weather data from the Open-Meteo API for a given location and year.
    """
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

# --- Price area to location mapping ---
PRICE_AREAS = {
    "NO1": {"city": "Oslo", "lat": 59.9139, "lon": 10.7522},
    "NO2": {"city": "Kristiansand", "lat": 58.1467, "lon": 7.9956},
    "NO3": {"city": "Trondheim", "lat": 63.4305, "lon": 10.3951},
    "NO4": {"city": "Tromsø", "lat": 69.6492, "lon": 18.9553},
    "NO5": {"city": "Bergen", "lat": 60.3913, "lon": 5.3221},
}



# --- Retrieve selected price area from another page ---
if "selected_price_area" not in st.session_state:
    st.error("No price area selected. Please select a Price Area on page 2 (elhub) first.")
    st.stop()

price_area = st.session_state.selected_price_area
location = PRICE_AREAS.get(price_area, None)
if location is None:
    st.error(f"Unknown price area: {price_area}")
    st.stop()


st.title(f"📊 Weather Data Table for {PRICE_AREAS[price_area].get('city')}")

# --- Year selection ---
year = st.number_input("Select year:", min_value=2000, max_value=datetime.now().year, value=2021)

# --- Load data ---
@st.cache_data
def load_data(price_area_code: str, year: int):
    loc = PRICE_AREAS[price_area_code]
    df = download_weather_data(latitude=loc["lat"], longitude=loc["lon"], year=year)
    return df

df = load_data(price_area, year)

# --- Display table ---
st.dataframe(
    df,
    height=500,
    column_config={
        "time": "Date/Time",
        "temperature_2m": "Temperature (°C)",
        "precipitation": "Precipitation (mm)",
        "wind_speed_10m": "Wind Speed (m/s)",
        "wind_gusts_10m": "Wind Gusts (m/s)",
        "wind_direction_10m": "Wind Direction (°)",
    },
    hide_index=True,
)

# --- Plot temperature for January ---
st.subheader(f"Temperature for January {year} in {location['city']}")
first_month = df[df['time'].dt.month == 1]
st.line_chart(first_month.set_index('time')['temperature_2m'])