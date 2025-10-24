# streamlit_app/pages/4_elhub.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# MongoDB connection
MONGO_URI = "mongodb+srv://ficus22_db_user:Nmbu2025@cluster0.my1f15s.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["elhub_data"]
collection = db["production_data"]

# Load data
data = list(collection.find({}))
df = pd.DataFrame(data)

if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"])

st.title("Energy Production in 2022")
st.markdown("Analyze monthly production trends and energy distribution by production group.")

# -------------------------
# Monthly Production Trends
# -------------------------
st.header("Monthly Production Trends")

# Add 'ALL' option for price area
price_areas = ["ALL"] + list(df["price_area"].unique())
price_area = st.selectbox("Select Price Area", price_areas)

selected_groups = st.multiselect("Select Production Groups", df["production_group"].unique())
selected_month = st.selectbox("Select Month", range(1, 13))

# Filter data
if price_area == "ALL":
    df_filtered = df.copy()
else:
    df_filtered = df[df["price_area"] == price_area]

df_month = df_filtered[df_filtered["start_time"].dt.month == selected_month]
df_month_group = df_month[df_month["production_group"].isin(selected_groups)]

if not df_month_group.empty:
    pivot_df = df_month_group.pivot(index="start_time", columns="production_group", values="quantity_kwh")
    st.line_chart(pivot_df)
else:
    st.info("No data available for the selected filters.")

# -------------------------
# Production Share by Group (Interactive Pie)
# -------------------------
st.header("Production Share by Group")

# Aggregate production by group
production_by_group = df_filtered.groupby("production_group")["quantity_kwh"].sum().reset_index()

# Plot interactive pie chart
fig = px.pie(production_by_group, names="production_group", values="quantity_kwh",
             title=f"Energy Production Distribution in {price_area}", hole=0.3)
st.plotly_chart(fig, use_container_width=True)
