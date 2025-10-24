# streamlit_app/pages/4_elhub.py
import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt

# Connexion à MongoDB
uri = "mongodb+srv://ficus22_db_user:Nmbu2025@cluster0.my1f15s.mongodb.net/?appName=Cluster0"
USR, PWD = "ficus22_db_user", "Nmbu2025"
client = MongoClient(uri.format(USR, PWD))
db = client["elhub_data"]
collection = db["production_data"]

# Récupérer les données
data = list(collection.find({}))
df = pd.DataFrame(data)

# Page 4 : Visualisations
st.title("Production d'Énergie en 2022")

col1, col2 = st.columns(2)

with col1:
    price_area = st.selectbox("Zone de prix", df["price_area"].unique())
    df_filtered = df[df["price_area"] == price_area]
    production_by_group = df_filtered.groupby("production_group")["quantity_kwh"].sum()

    fig, ax = plt.subplots()
    ax.pie(production_by_group, labels=production_by_group.index, autopct='%1.1f%%')
    st.pyplot(fig)

with col2:
    production_groups = st.multiselect("Groupes de production", df["production_group"].unique())
    month = st.selectbox("Mois", range(1, 13))
    df_month = df_filtered[df_filtered["start_time"].dt.month == month]
    df_month_group = df_month[df_month["production_group"].isin(production_groups)]

    if not df_month_group.empty:
        pivot_df = df_month_group.pivot(index="start_time", columns="production_group", values="quantity_kwh")
        st.line_chart(pivot_df)
    else:
        st.write("Aucune donnée pour les filtres sélectionnés.")
