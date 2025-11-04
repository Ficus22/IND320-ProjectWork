import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from datetime import datetime
import numpy as np


st.title("🌬️ Wind and Weather Analysis")

# ==============================
# Load Data
# ==============================
@st.cache_data
def load_data():
    csv_path = "data/open-meteo-subset.csv"
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    # Calculate wind components for wind roses
    df['u'] = df['wind_speed_10m (m/s)'] * (-np.sin(np.radians(df['wind_direction_10m (°)'])))
    df['v'] = df['wind_speed_10m (m/s)'] * (-np.cos(np.radians(df['wind_direction_10m (°)'])))
    return df

try:
    df = load_data()
    numeric_cols = [
        "temperature_2m (°C)",
        "precipitation (mm)",
        "wind_speed_10m (m/s)",
        "wind_gusts_10m (m/s)"
    ]

    # ==============================
    # User selection widgets
    # ==============================
    st.sidebar.header("Filters")

    # Select variable
    selected_col = st.sidebar.selectbox(
        "Choose a variable:",
        numeric_cols + ["All columns"]
    )

    # Select month range
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    months = sorted(df['time'].dt.month.unique())
    month_labels = [month_names[m] for m in months]
    month_range_labels = st.sidebar.select_slider(
        "Select a month range:",
        options=month_labels,
        value=(month_labels[0], month_labels[-1])
    )
    month_range = [
        [k for k, v in month_names.items() if v == month_range_labels[0]][0],
        [k for k, v in month_names.items() if v == month_range_labels[1]][0]
    ]
    filtered_df = df[df['time'].dt.month.between(month_range[0], month_range[1])]

    # Add resample selector for time series
    resample_option = st.sidebar.selectbox(
        "Time aggregation:",
        ["Raw", "Daily", "Weekly", "Monthly"]
    )

    # Resample data based on selection
    if resample_option != "Raw":
        resample_rule = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[resample_option]
        resampled_df = filtered_df.set_index('time').resample(resample_rule).mean().reset_index()
    else:
        resampled_df = filtered_df

    # ==============================
    # Time Series Plot
    # ==============================
    st.header("📈 Time Series Analysis")
    if selected_col == "All columns":
        fig = px.line(
            resampled_df,
            x="time",
            y=numeric_cols,
            title=f"Weather variables over time ({month_names[month_range[0]]} to {month_names[month_range[1]]})"
        )
    else:
        fig = px.line(
            resampled_df,
            x="time",
            y=selected_col,
            title=f"{selected_col} ({month_names[month_range[0]]} to {month_names[month_range[1]]})"
        )
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Values",
        legend_title="Variables"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # Wind Analysis Section
    # ==============================
    st.header("🌪️ Wind Analysis")

    # Option 1: Polar Scatter Plot (existing)
    st.subheader("Polar Scatter Plot")
    fig_polar = px.scatter_polar(
        resampled_df,
        r="wind_speed_10m (m/s)",
        theta="wind_direction_10m (°)",
        size="wind_speed_10m (m/s)",
        color="wind_speed_10m (m/s)",
        title="Wind Direction and Intensity (Polar Scatter)"
    )
    st.plotly_chart(fig_polar, use_container_width=True)

    # Option 2: Small Multiples of Monthly Wind Roses (using Altair)
    st.subheader("Monthly Wind Roses")
    wind_roses = alt.Chart(resampled_df).transform_calculate(
        direction_bins="floor(datum['wind_direction_10m (°)'] / 30) * 30"
    ).transform_aggregate(
        speed_mean='mean(wind_speed_10m (m/s))',
        groupby=['direction_bins', 'time']
    ).transform_joinaggregate(
        total_speed='sum(speed_mean)',
        groupby=['time']
    ).transform_calculate(
        percentage='datum.speed_mean / datum.total_speed'
    ).mark_bar().encode(
        theta=alt.Theta('direction_bins:Q', scale=alt.Scale(domain=[0, 360])),
        radius=alt.Radius('percentage:Q', scale=alt.Scale(type='sqrt', zero=True)),
        color=alt.Color('speed_mean:Q', legend=alt.Legend(title="Avg Wind Speed (m/s)")),
        column=alt.Column('month(time):O', title="Month")
    ).properties(
        width=200,
        height=200
    ).configure_view(
        strokeWidth=0
    ).properties(
        title="Monthly Wind Roses (Small Multiples)"
    )
    st.altair_chart(wind_roses, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data or generating plots: {e}")
