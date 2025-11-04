# Streamlit_app/pages/2_plots.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.title("📈 Weather Visualizations")
# ==============================
# Load Data
# ==============================
@st.cache_data
def load_data():
    csv_path = "data/open-meteo-subset.csv"
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
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
    selected_col = st.selectbox("Choose a variable:", numeric_cols + ["All columns"])
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    months = sorted(df['time'].dt.month.unique())
    month_labels = [month_names[m] for m in months]
    # Select a range of months by name
    month_range_labels = st.select_slider(
        "Select a month range",
        options=month_labels,
        value=(month_labels[0], month_labels[2])  # default: January to March
    )
    # Convert month names back to numbers
    month_range = [
        [k for k,v in month_names.items() if v == month_range_labels[0]][0],
        [k for k,v in month_names.items() if v == month_range_labels[1]][0]
    ]
    # Filter data by selected month range
    filtered_df = df[df['time'].dt.month.between(month_range[0], month_range[1])]
    # ==============================
    # Display line chart
    # ==============================
    if selected_col == "All columns":
        fig = px.line(
            filtered_df,
            x="time",
            y=numeric_cols,
            title=f"Weather variables over time ({month_range[0]} → {month_range[1]})"
        )
    else:
        fig = px.line(
            filtered_df,
            x="time",
            y=selected_col,
            title=f"{selected_col} ({month_range[0]} → {month_range[1]})"
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
    fig_polar = px.scatter_polar(
        filtered_df,
        r="wind_speed_10m (m/s)",
        theta="wind_direction_10m (°)",
        size="wind_speed_10m (m/s)",
        color="wind_speed_10m (m/s)",
        title="Wind Rose (Polar)"
    )
    st.plotly_chart(fig_polar, use_container_width=True)


except Exception as e:
    st.error(f"Error loading data or generating plots: {e}")