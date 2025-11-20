# streamlit_app/app.py
import streamlit as st
import os
import importlib
from utils.data_loader import load_mongo_data

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
# Constants
# =========================================================
PAGES_DIR = "pages"

# =========================================================
# Utilities for cleaning names
# =========================================================
def clean_name(name: str) -> str:
    """Remove prefix numbers/underscore and clean formatting."""
    name = name.replace(".py", "")
    parts = name.split("_")[1:]  # remove first block: 1_, 2_, etc.
    return " ".join(parts).strip()

# =========================================================
# Load all pages by folder
# =========================================================
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

# =========================================================
# Sidebar Navigation UI
# =========================================================
def sidebar_menu(pages_dict):
    st.sidebar.title("Navigation")

    # ---- HOME BUTTON ----
    if st.sidebar.button("🏠 Home"):
        st.session_state["current_page"] = None
        st.session_state["current_folder"] = None
        st.rerun()

    st.sidebar.markdown("---")

    # ---- Folder selectbox ----
    folder_list = list(pages_dict.keys())
    folder_clean_list = [clean_name(f) for f in folder_list]

    selected_clean = st.sidebar.selectbox("📁 Section", folder_clean_list)
    selected_folder = folder_list[folder_clean_list.index(selected_clean)]
    st.session_state["current_folder"] = selected_folder

    st.sidebar.markdown(f"### 📂 {clean_name(selected_folder)}")

    # ---- Buttons for pages ----
    for file in pages_dict[selected_folder]:
        label = f"🔹 {clean_name(file)}"
        if st.sidebar.button(label):
            st.session_state["current_page"] = file
            st.rerun()

# =========================================================
# Load current page
# =========================================================
def load_page(folder, file):
    module_path = f"{PAGES_DIR}.{folder}.{file.replace('.py', '')}"
    module = importlib.import_module(module_path)
    module.app()

# =========================================================
# Sidebar + logic
# =========================================================
pages_dict = list_pages()
sidebar_menu(pages_dict)

# If a user selected a page, load it
if st.session_state.get("current_page"):
    load_page(st.session_state["current_folder"], st.session_state["current_page"])
    st.stop()

# =========================================================
# HOME PAGE CONTENT
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