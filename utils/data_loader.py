# utils/data_loader.py
import streamlit as st
import pandas as pd
from pymongo import MongoClient
import requests
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
