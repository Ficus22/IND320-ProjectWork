import streamlit as st
import pandas as pd

st.title("Mon projet IND320 🚀")
st.write("Bienvenue dans mon app Streamlit hébergée sur streamlit.app")

# Charger un CSV
df = pd.read_csv("open-meteo-subset.csv")
st.write("Aperçu des données :")
st.dataframe(df.head())

# Petit graphique
st.line_chart(df)
