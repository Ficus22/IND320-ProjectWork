# streamlit_app/pages/4_elhub.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

# MongoDB connection
MONGO_URI = "mongodb+srv://ficus22_db_user:Nmbu2025@cluster0.my1f15s.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["elhub_data"]
collection = db["production_data"]

data = list(collection.find({}))
df = pd.DataFrame(data)

if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
    df["start_time"] = pd.to_datetime(df["start_time"])

st.title("Energy Production in 2022")
st.markdown("Explore production data by price area and production group.")

col1, col2 = st.columns(2)

with col1:
    st.header("Production Share by Group")
    price_area = st.selectbox("Select Price Area", df["price_area"].unique())
    df_area = df[df["price_area"] == price_area]
    production_by_group = df_area.groupby("production_group")["quantity_kwh"].sum()

    fig, ax = plt.subplots()
    ax.pie(production_by_group, labels=production_by_group.index, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"Energy Production by Group in {price_area}")
    st.pyplot(fig)

with col2:
    st.header("Monthly Production Trends")
    selected_groups = st.multiselect("Select Production Groups", df["production_group"].unique())
    selected_month = st.selectbox("Select Month", range(1, 13))
    df_month = df_area[df_area["start_time"].dt.month == selected_month]
    df_month_group = df_month[df_month["production_group"].isin(selected_groups)]

    if not df_month_group.empty:
        pivot_df = df_month_group.pivot(index="start_time", columns="production_group", values="quantity_kwh")
        st.line_chart(pivot_df)
    else:
        st.info("No data available for the selected filters.")
