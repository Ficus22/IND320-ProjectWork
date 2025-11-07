# streamlit_app/pages/1_elhub.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# -------------------------
# MongoDB connection
# -------------------------
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["elhub_data"]
collection = db["production_data"]

# -------------------------
# Load data
# -------------------------
data = list(collection.find({}))
df = pd.DataFrame(data)

# Convert start_time to datetime if necessary
if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"])

st.title("⚡Energy Production in 2021")
st.markdown("Analyze monthly production trends and energy distribution by production group.")

# -------------------------
# Price area to city mapping
# -------------------------
PRICE_AREAS = {
    "NO1": "Oslo",
    "NO2": "Kristiansand",
    "NO3": "Trondheim",
    "NO4": "Tromsø",
    "NO5": "Bergen"
}

# -------------------------
# Price area selection
# -------------------------
price_areas = list(df["price_area"].unique())  # Removed "ALL"

# Add city name in parentheses
price_area_options = []
for pa in price_areas:
    if pa in PRICE_AREAS:
        price_area_options.append(f"{pa} ({PRICE_AREAS[pa]})")
    else:
        price_area_options.append(pa)

# Default selection: N=1
default_price_area = "NO1"
default_idx = price_areas.tolist().index(default_price_area) if default_price_area in price_areas else 0

selected_option = st.selectbox("Select Price Area", price_area_options, index=default_idx)

# Extract price area code from selection
price_area = selected_option.split(" ")[0]

# Store selection in session_state for access on other pages
st.session_state.selected_price_area = price_area

# -------------------------
# Production groups selection
# -------------------------
production_groups = df["production_group"].dropna().unique()
selected_groups = st.multiselect("Select Production Groups", production_groups)

# -------------------------
# Month range selection using names
# -------------------------
month_names = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# Available months in the data
months_in_data = sorted(df["start_time"].dt.month.unique())
month_labels = [month_names[m] for m in months_in_data]

# Select a range of months by name
month_range_labels = st.select_slider(
    "Select a month range",
    options=month_labels,
    value=(month_labels[0], month_labels[-1])  # default: first to last available month
)

# Convert month names back to numbers
month_range = [
    [k for k,v in month_names.items() if v == month_range_labels[0]][0],
    [k for k,v in month_names.items() if v == month_range_labels[1]][0]
]

# -------------------------
# Filter data based on selections
# -------------------------
if price_area == "ALL":
    df_filtered = df.copy()
else:
    df_filtered = df[df["price_area"] == price_area]

df_month = df_filtered[df_filtered["start_time"].dt.month.between(month_range[0], month_range[1])]
df_month_group = df_month[df_month["production_group"].isin(selected_groups)]

if not df_month_group.empty:
    pivot_df = df_month_group.pivot_table(
        index="start_time",
        columns="production_group",
        values="quantity_kwh",
        aggfunc="sum"
    )
    st.line_chart(pivot_df)
else:
    st.info("No data available for the selected filters.")

# -------------------------
# Production Share by Group (Interactive Pie)
# -------------------------
st.header("Production Share by Group")

# Aggregate production by group (all months for the selected price area)
production_by_group = df_filtered.groupby("production_group")["quantity_kwh"].sum().reset_index()

# Interactive pie chart with Plotly
fig = px.pie(
    production_by_group,
    names="production_group",
    values="quantity_kwh",
    title=f"Energy Production Distribution in {price_area}",
    hole=0.3
)
st.plotly_chart(fig, use_container_width=True)