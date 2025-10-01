"""
title: Tableau des Données
"""
import streamlit as st
import pandas as pd
import os

st.title("📊 Tableau des Données Météo")

@st.cache_data
def load_data():
    # Chemin absolu dans Streamlit Cloud
    csv_path = "data/open-meteo-subset.csv"

    # Vérifie si le fichier existe
    if not os.path.exists(csv_path):
        st.error(f"Fichier non trouvé à : {csv_path}")
        st.stop()  # Arrête l'exécution si le fichier est manquant

    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    return df

df = load_data()

# Tableau interactif natif
st.dataframe(
    df,
    height=500,
    column_config={
        "time": "Date/Heure",
        "temperature_2m (°C)": "Température (°C)",
        "precipitation (mm)": "Précipitations (mm)",
    },
    hide_index=True,
)

# Graphique
st.subheader("Température du Premier Mois")
first_month = df[df['time'].dt.month == 1]
st.line_chart(first_month.set_index('time')['temperature_2m (°C)'])
