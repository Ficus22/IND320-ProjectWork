# streamlit_app/app.py
import streamlit as st

# =========================
# Page configuration
# =========================
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌦️",
    layout="wide"
)

# =========================
# Sidebar
# =========================

st.sidebar.info("IND320 Project")


# =========================
# Main Page
# =========================
st.title("🌦️ Weather Dashboard - IND320")

st.markdown("""
Welcome to the **IND320 Weather Data Analysis Dashboard**.  
This dashboard provides interactive visualizations and tables for the hourly weather data of January 2020.

You can explore the following pages:  
- **Data Table**: View the dataset in an interactive table and see line charts for the first month.  
- **Visualizations**: Plot different weather variables with selectable columns and month ranges.  
- **About**: Learn about the project, the author, technologies used, and AI assistance.

Check out the project resources below:
""")

# =========================
# Links
# =========================
st.markdown(
    """
- [GitHub Repository](https://github.com/Ficus22/IND320-ProjectWork)
- [Live Streamlit App](https://ind320-projectwork-esteban-carrasco.streamlit.app)
"""
)

# =========================
# Logo / Image
# =========================
st.image(
    "https://nobel.boku.ac.at/wp-content/uploads/2020/03/nmbu_logo_eng_rgb-768x348.jpg",
    width=500
)

st.markdown("---")
st.markdown("Use the sidebar menu to navigate to Data Table, Visualizations, or About pages.")
st.markdown("© 2025 Esteban Carrasco - NMBU")