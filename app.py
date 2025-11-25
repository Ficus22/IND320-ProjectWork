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

def load_page(folder, file):
    module_path = f"{PAGES_DIR}.{folder}.{file.replace('.py', '')}"
    module = importlib.import_module(module_path)
    module.app()

# =========================================================
# Initialize session state
# =========================================================
if "current_folder" not in st.session_state:
    st.session_state["current_folder"] = None
if "current_page" not in st.session_state:
    st.session_state["current_page"] = None

# =========================================================
# Sidebar
# =========================================================
pages_dict = list_pages()


# ---- HOME BUTTON ----
if st.sidebar.button("🏠"):
    st.session_state["current_page"] = None
    st.session_state["current_folder"] = None
    st.rerun()

st.sidebar.info("IND320 Project")

# ---- Folder selectbox ----
folder_list = list(pages_dict.keys())
folder_clean_list = [clean_name(f) for f in folder_list]

folder_clean_list_with_home = ["Home"] + folder_clean_list
selected_clean = st.sidebar.selectbox("📂 Section", folder_clean_list_with_home)

if selected_clean == "Home":
    st.session_state["current_folder"] = None
else:
    st.session_state["current_folder"] = folder_list[folder_clean_list.index(selected_clean)]


# ---- Page selectbox ----
if st.session_state["current_folder"]:
    page_clean_list = [clean_name(f) for f in pages_dict[st.session_state["current_folder"]]]

    selected_page_clean = st.sidebar.selectbox(f"📄 Pages in {selected_clean}", page_clean_list)
    
    st.session_state["current_page"] = pages_dict[st.session_state["current_folder"]][page_clean_list.index(selected_page_clean)]

else:
    st.session_state["current_page"] = None

# ---- Load page if selected ----
if st.session_state["current_page"]:
    load_page(st.session_state["current_folder"], st.session_state["current_page"])
    st.stop()

# =========================================================
# HOME PAGE CONTENT
# =========================================================
st.title("🌦️ Weather Dashboard - IND320")

st.markdown("""
Welcome to the **IND320 Weather Data Analysis Dashboard**.  
This dashboard provides interactive visualizations and tables for the hourly weather data of January 2020.

**You can explore the different pages through the different sections.**  

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
