# streamlit_app/pages/1_3_data_tables.py
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_loader import load_weather_data
from utils.config import PRICE_AREAS

def app():
    # --- Retrieve selected price area from another page ---
    if "selected_price_area" not in st.session_state:
        st.error("No price area selected. Please select a Price Area on the Energy Production Dashboard first.")
        st.stop()

    price_area = st.session_state.selected_price_area

    if price_area not in PRICE_AREAS:
        st.error(f"Unknown price area: {price_area}")
        st.stop()

    city = PRICE_AREAS[price_area]["city"]
    st.title(f"📊 Weather Data Table for {city}")

    # --- Year selection ---
    year = st.number_input(
        "Select year:",
        min_value=2000,
        max_value=datetime.now().year,
        value=2021
    )

    # --- Load weather data ---
    df = load_weather_data(price_area, year)

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
    st.line_chart(first_month.set_index('time')['temperature_2m'])