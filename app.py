# streamlit_app/app.py
import streamlit as st

st.set_page_config(layout="wide", page_title="Weather Dashboard")

# =========================
# Sidebar
# =========================
st.sidebar.markdown("---")
st.sidebar.info("IND320 Project")

# =========================
# Main Page
# =========================
st.title("🌦️ Weather Dashboard - IND320")
st.markdown("""
Welcome to the 2020 weather data analysis dashboard.
""")

st.image("https://nobel.boku.ac.at/wp-content/uploads/2020/03/nmbu_logo_eng_rgb-768x348.jpg", width=300)  # NMBU image
