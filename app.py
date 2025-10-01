# streamlit_app/app.py
import streamlit as st

st.set_page_config(layout="wide", page_title="Dashboard Météo")
st.title("🌦️ Dashboard Météo - IND320")
st.markdown("""
Bienvenue sur le dashboard d'analyse des données météorologiques de 2020.

**Fonctionnalités :**
- Visualisation des températures, précipitations et vents
- Analyse des directions du vent avec flèches vectorielles
- Filtres par mois pour une analyse ciblée
""")

#st.sidebar.title("Navigation")
#st.sidebar.page_link("app.py", label="Accueil")
#st.sidebar.page_link("pages/1_data_tables.py", label="Tableau de données")
#st.sidebar.page_link("pages/2_plots.py", label="Visualisations")
#st.sidebar.page_link("pages/3_about.py", label="À propos")

st.image("https://kommunikasjon.ntb.no/data/images/00148/dee9f88e-8f69-42ee-aae0-ec20be9f2b7b.png", width=300) #NMBU image
