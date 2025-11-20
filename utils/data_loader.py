# utils/data_loader.py
import streamlit as st
import pandas as pd
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
from .config import PRICE_AREAS, OPENMETEO_ERA5, DEFAULT_HOURLY_VARIABLES


# --- MongoDB Data Loader (Cached + Session State) ---
@st.cache_data
def load_mongo_data(collection_name: str) -> pd.DataFrame:
    """Load data from MongoDB and store in session_state."""
    if f"df_{collection_name}" not in st.session_state:
        with st.spinner(f"Loading {collection_name} from MongoDB..."):
            MONGO_URI = st.secrets["MONGO_URI"]
            client = MongoClient(MONGO_URI)
            db = client["elhub_data"]
            collection = db[collection_name]
            st.session_state[f"df_{collection_name}"] = pd.DataFrame(list(collection.find({})))
    return st.session_state[f"df_{collection_name}"]

# --- Weather Data Loader (Cached + Session State) ---
@st.cache_data
def download_weather_data(
    latitude: float,
    longitude: float,
    year: int,
    hourly=DEFAULT_HOURLY_VARIABLES
) -> pd.DataFrame:
    """Download weather data from Open-Meteo API."""
    cache_key = f"weather_{latitude}_{longitude}_{year}"
    if cache_key not in st.session_state:
        with st.spinner(f"Downloading weather data for {year}..."):
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
            st.session_state[cache_key] = df
    return st.session_state[cache_key]

# --- Load Weather Data by Price Area ---
@st.cache_data
def load_weather_data(price_area_code: str, year: int) -> pd.DataFrame:
    """Load weather data for a specific price area."""
    loc = PRICE_AREAS[price_area_code]
    return download_weather_data(latitude=loc["lat"], longitude=loc["lon"], year=year)

def download_weather_data_chunked(lat, lon, start_date, end_date, hourly):
    """
    Download weather data from Open-Meteo API in chunks.

    Args:
        lat (float): Latitude.
        lon (float): Longitude.
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        hourly (list): List of hourly variables to download.

    Returns:
        pd.DataFrame: Weather data.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    df_list = []

    # Convert dates to datetime objects
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    # Loop through date ranges in chunks (e.g., 30 days at a time)
    chunk_size = timedelta(days=30)
    current_start = start

    while current_start <= end:
        current_end = min(current_start + chunk_size, end)

        # Request data for the current chunk
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": current_start.strftime("%Y-%m-%d"),
            "end_date": current_end.strftime("%Y-%m-%d"),
            "hourly": hourly,
            "timezone": "UTC"
        }

        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch weather data: {response.text}")

        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame(data["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df_list.append(df)

        current_start = current_end + timedelta(days=1)

    # Concatenate all chunks
    if not df_list:
        return pd.DataFrame()

    df_weather = pd.concat(df_list)
    return df_weather