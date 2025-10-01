# streamlit_app/app.py
import streamlit as st

st.set_page_config(layout="wide", page_title="Dashboard Météo")

# =========================
# Sidebar
# =========================
st.sidebar.title("🧭 Navigation")
st.sidebar.write("Choisissez une page ci-dessous :")

# (le menu natif multipage s’affichera juste en dessous)
# Tu peux aussi ajouter d'autres éléments si tu veux
st.sidebar.markdown("---")
st.sidebar.info("Projet IND320 - Données météo")

# =========================
# Page principale
# =========================
st.title("🌦️ Dashboard Météo - IND320")
st.markdown("""
Bienvenue sur le dashboard d'analyse des données météorologiques de 2020.

**Fonctionnalités :**
- Visualisation des températures, précipitations et vents
- Analyse des directions du vent avec flèches vectorielles
- Filtres par mois pour une analyse ciblée
""")


st.image("https://kommunikasjon.ntb.no/data/images/00148/dee9f88e-8f69-42ee-aae0-ec20be9f2b7b.png", width=300) #NMBU image
