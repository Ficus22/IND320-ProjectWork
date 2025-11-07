# Streamlit_app/pages/5_plots.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.title("📈 Weather Visualizations")

# ==============================
# Vérification de la zone de prix choisie
# ==============================
if "selected_price_area" not in st.session_state:
    st.warning("Please select a Price Area on page 1 first.")
    st.stop()

price_area = st.session_state.selected_price_area

# ==============================
# Load data directly from API
# ==============================
@st.cache_data
def load_api_data(price_area: str):
    """
    Charge les données météo depuis l'API pour la zone de prix sélectionnée.
    """
    # Exemple d'URL API (à adapter selon votre API réelle)
    api_url = f"https://api.example.com/weather?price_area={price_area}&interval=hourly"
    resp = requests.get(api_url, timeout=10)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    # Conversion en datetime
    df['time'] = pd.to_datetime(df['time'])
    return df

try:
    df = load_api_data(price_area)

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

    month_range_labels = st.select_slider(
        "Select a month range",
        options=month_labels,
        value=(month_labels[0], month_labels[2])
    )

    month_range = [
        [k for k,v in month_names.items() if v == month_range_labels[0]][0],
        [k for k,v in month_names.items() if v == month_range_labels[1]][0]
    ]

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
    if "wind_direction_10m (°)" in df.columns:
        fig_polar = px.scatter_polar(
            filtered_df,
            r="wind_speed_10m (m/s)",
            theta="wind_direction_10m (°)",
            size="wind_speed_10m (m/s)",
            color="wind_speed_10m (m/s)",
            title="Wind Rose (Polar)"
        )
        st.plotly_chart(fig_polar, use_container_width=True)
    else:
        st.info("Wind direction data not available for this zone.")

except Exception as e:
    st.error(f"Error loading data or generating plots: {e}")