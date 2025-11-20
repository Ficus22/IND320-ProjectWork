# streamlit_app/pages/4_plots.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils.data_loader import load_weather_data
from utils.config import PRICE_AREAS, MONTH_NAMES, MAX_YEAR, MIN_YEAR, DEFAULT_YEAR


def app():
    # -------------------------
    # Check if a price area was selected
    # -------------------------
    if "selected_price_area" not in st.session_state:
        st.warning("Please select a Price Area on the Data tables page first.")
        st.stop()

    price_area = st.session_state.selected_price_area

    # -------------------------
    # Price area info
    # -------------------------
    if price_area not in PRICE_AREAS:
        st.error(f"Unknown price area: {price_area}")
        st.stop()

    city = PRICE_AREAS[price_area]["city"]
    latitude = PRICE_AREAS[price_area]["lat"]
    longitude = PRICE_AREAS[price_area]["lon"]

    st.title(f"📈 Weather Visualizations for {city}")
    st.markdown("*Open-Meteo ERA5 data*")

    # -------------------------
    # Year selection
    # -------------------------
    selected_year = st.number_input(
        "Select year (below 2025):",
        min_value=MIN_YEAR,
        max_value=MAX_YEAR,
        value=DEFAULT_YEAR,
        step=1
    )

    # -------------------------
    # Load data
    # -------------------------
    try:
        df = load_weather_data(price_area, selected_year)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    numeric_cols = [
        "temperature_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_gusts_10m"
    ]

    # -------------------------
    # User selection widgets
    # -------------------------
    selected_col = st.selectbox("Choose a variable:", numeric_cols + ["All columns"])

    month_names = MONTH_NAMES

    months = sorted(df['time'].dt.month.unique())
    month_labels = [month_names[m] for m in months]

    month_range_labels = st.select_slider(
        "Select a month range",
        options=month_labels,
        value=(month_labels[0], month_labels[min(2, len(month_labels)-1)])
    )

    month_range = [
        [k for k, v in month_names.items() if v == month_range_labels[0]][0],
        [k for k, v in month_names.items() if v == month_range_labels[1]][0]
    ]

    filtered_df = df[df['time'].dt.month.between(month_range[0], month_range[1])]

    # -------------------------
    # Line chart
    # -------------------------
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

    # -------------------------
    # Polar plot for wind direction
    # -------------------------
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