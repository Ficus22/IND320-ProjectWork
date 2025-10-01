# streamlit_app/pages/about.py
import streamlit as st

st.title("🔍 À propos")
st.markdown("""
## Projet IND320 - Analyse de données météorologiques

**Auteur** : Esteban Carrasco

**Objectifs** :
- Analyser les données météorologiques horaires de janvier 2020
- Créer des visualisations interactives avec Streamlit
- Intégrer des analyses spécifiques sur les directions du vent

**Technologies utilisées** :
- Python (Pandas, Matplotlib, NumPy)
- Streamlit pour le dashboard interactif
- AgGrid pour les tableaux avancés

**Liens** :
- [Code source GitHub](https://github.com/ton-pseudo/IND320-Streamlit-esteban)
- [Données source](https://open-meteo.com/)

**Remerciements** :
- À l'équipe enseignante pour son accompagnement
- À Le Chat (Mistral AI) pour son aide sur les visualisations avancées
""")
