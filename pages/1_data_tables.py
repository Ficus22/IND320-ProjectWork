import streamlit as st
import pandas as pd
import os

st.title("📊 Weather Data Table")

@st.cache_data
def load_data():
    csv_path = "data/open-meteo-subset.csv"

    # Check if the file exists
    if not os.path.exists(csv_path):
        st.error(f"File not found at: {csv_path}")
        st.stop()  # Stop execution if the file is missing

    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    return df

df = load_data()

# Native interactive table
st.dataframe(
    df,
    height=500,
    column_config={
        "time": "Date/Time",
        "temperature_2m (°C)": "Temperature (°C)",
        "precipitation (mm)": "Precipitation (mm)",
    },
    hide_index=True,
)

# Chart
st.subheader("Temperature for the First Month")
first_month = df[df['time'].dt.month == 1]
st.line_chart(first_month.set_index('time')['temperature_2m (°C)'])
