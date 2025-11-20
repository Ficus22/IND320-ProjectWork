# streamlit_app/pages/1_3_data_tables.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_weather_data
from utils.config import PRICE_AREAS, DEFAULT_PRICE_AREA, DEFAULT_YEAR, MIN_YEAR, MAX_YEAR

def app():
    st.title("📊 Weather Data Table")

    # --- Price Area Selection ---
    price_area_options = [
        f"{pa} ({PRICE_AREAS[pa]['city']})" for pa in PRICE_AREAS
    ]
    default_idx = list(PRICE_AREAS.keys()).index(DEFAULT_PRICE_AREA)
    selected_option = st.selectbox("Select Price Area", price_area_options, index=default_idx)

    # Extract price area code from selection
    price_area = selected_option.split(" ")[0]

    # Store selection in session_state for access on other pages
    st.session_state.selected_price_area = price_area

    # --- Year selection ---
    year = st.number_input(
        "Select year:",
        min_value=MIN_YEAR,
        max_value=MAX_YEAR,
        value=DEFAULT_YEAR
    )

    city = PRICE_AREAS[price_area]["city"]
    st.subheader(f"Weather Data for {city} in {year}")

    # --- Load weather data ---
    df = load_weather_data(price_area, year)

    if df.empty:
        st.warning("No data available for this selection.")
        return

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
    st.subheader(f"Temperature for January {year} in {city}")
    first_month = df[df['time'].dt.month == 1]
    if not first_month.empty:
        st.line_chart(first_month.set_index('time')['temperature_2m'])
    else:
        st.info("No data for January.")