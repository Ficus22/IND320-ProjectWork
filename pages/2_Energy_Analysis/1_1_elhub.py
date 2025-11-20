# streamlit_app/pages/1_elhub.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_mongo_data
from utils.config import PRICE_AREAS, DEFAULT_YEAR, DEFAULT_PRICE_AREA, MONTH_NAMES

# --- Load Data ---
df = load_mongo_data("production_data")

# Convert start_time to datetime if necessary
if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"])

# Extract year from start_time
df["year"] = df["start_time"].dt.year

# --- Page Layout ---
st.title("⚡ Energy Production Dashboard")
st.markdown("Analyze monthly production trends and energy distribution by production group.")

# --- Year Selection ---
available_years = sorted(df["year"].unique())
selected_year = st.selectbox(
    "Select Year",
    available_years,
    index=available_years.index(DEFAULT_YEAR) if DEFAULT_YEAR in available_years else 0
)

# --- Price Area Selection ---
price_areas = list(df["price_area"].unique())
price_area_options = [
    f"{pa} ({PRICE_AREAS[pa]['city']})" if pa in PRICE_AREAS else pa
    for pa in price_areas
]

default_idx = price_areas.index(DEFAULT_PRICE_AREA) if DEFAULT_PRICE_AREA in price_areas else 0
selected_option = st.selectbox("Select Price Area", price_area_options, index=default_idx)

# Extract price area code from selection
price_area = selected_option.split(" ")[0]

# Store selection in session_state for access on other pages
st.session_state.selected_price_area = price_area

# --- Production Groups Selection ---
production_groups = df["production_group"].dropna().unique()
selected_groups = st.multiselect("Select Production Groups", production_groups)

# --- Month Range Selection ---
month_names = MONTH_NAMES

months_in_data = sorted(df[df["year"] == selected_year]["start_time"].dt.month.unique())
month_labels = [month_names[m] for m in months_in_data]

if len(month_labels) >= 2:
    month_range_labels = st.select_slider(
        "Select a month range",
        options=month_labels,
        value=(month_labels[0], month_labels[-1])
    )
    # Convert month names back to numbers
    month_range = [
        [k for k, v in month_names.items() if v == month_range_labels[0]][0],
        [k for k, v in month_names.items() if v == month_range_labels[1]][0]
    ]
else:
    st.warning("Not enough months available for the selected year.")
    month_range = [1, 12]  # Default to all months if not enough data

# --- Filter Data ---
df_filtered = df[df["price_area"] == price_area] if price_area != "ALL" else df.copy()
df_filtered = df_filtered[df_filtered["year"] == selected_year]
df_month = df_filtered[df_filtered["start_time"].dt.month.between(month_range[0], month_range[1])]
df_month_group = df_month[df_month["production_group"].isin(selected_groups)]

# --- Line Chart ---
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

# --- Production Share by Group (Interactive Pie) ---
st.header("Production Share by Group")
production_by_group = df_filtered.groupby("production_group")["quantity_kwh"].sum().reset_index()

fig = px.pie(
    production_by_group,
    names="production_group",
    values="quantity_kwh",
    title=f"Energy Production Distribution in {price_area} for {selected_year}",
    hole=0.3
)
st.plotly_chart(fig, use_container_width=True)
