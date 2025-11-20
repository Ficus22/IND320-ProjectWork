# streamlit_app/app.py
import streamlit as st
import os
import importlib
from utils.data_loader import load_mongo_data, download_weather_data

# =========================================================
# Load data once at app launch
# =========================================================
if "df_production" not in st.session_state:
    st.session_state.df_production = load_mongo_data("production_data")
if "df_consumption" not in st.session_state:
    st.session_state.df_consumption = load_mongo_data("consumption_data")

# =========================================================
# Page configuration
# =========================================================
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌦️",
    layout="wide"
)

# =========================================================
# Functions to dynamically load sidebar pages
# =========================================================
PAGES_DIR = "pages"

def list_pages():
    pages = {}
    for folder in sorted(os.listdir(PAGES_DIR)):
        folder_path = os.path.join(PAGES_DIR, folder)
        if os.path.isdir(folder_path):
            files = [
                f for f in os.listdir(folder_path)
                if f.endswith(".py") and not f.startswith("_")
            ]
            pages[folder] = sorted(files)
    return pages

def sidebar_menu(pages_dict):
    st.sidebar.info("IND320 Project")

    selected_folder = st.sidebar.selectbox(
        "📁 Category", 
        list(pages_dict.keys())
    )

    selected_page = st.sidebar.radio(
        "📄 Select page", 
        pages_dict[selected_folder],
        format_func=lambda x: " ".join(x.split("_")[1:]).replace(".py", "")
    )
    return selected_folder, selected_page

def load_page(folder, file):
    module_path = f"{PAGES_DIR}.{folder}.{file.replace('.py', '')}"
    module = importlib.import_module(module_path)
    module.app()  # each page must have app() function

# =========================================================
# Sidebar + navigation logic
# =========================================================
pages_dict = list_pages()

# Load selected page OR show main homepage if none yet
folder, page = sidebar_menu(pages_dict)

# If the current page is the homepage (root), show intro
if folder is None or page is None:
    pass
else:
    load_page(folder, page)
    st.stop()

# =========================================================
# Main (Home) Page content
# =========================================================
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
st.markdown("""
- [GitHub Repository](https://github.com/Ficus22/IND320-ProjectWork)
- [Live Streamlit App](https://ind320-projectwork-esteban-carrasco.streamlit.app)
""")

# =========================
# Logo / Image
# =========================
st.image(
    "https://nobel.boku.ac.at/wp-content/uploads/2020/03/nmbu_logo_eng_rgb-768x348.jpg",
    width=500
)

st.markdown("---")
st.markdown("Use the sidebar menu to navigate through pages.")
st.markdown("© 2025 Esteban Carrasco - ESILV")
