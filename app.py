import streamlit as st

st.set_page_config(page_title="IND320 Project", page_icon="📊")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à :", ["Accueil", "Données", "Graphiques", "Autres"])

# Pages
if page == "Accueil":
    st.title("🏠 Page d’accueil")
    st.write("Bienvenue dans mon application Streamlit !")

elif page == "Données":
    st.title("📊 Tableau des Données")
    st.write("Ici on affichera le CSV et les colonnes.")

elif page == "Graphiques":
    st.title("📈 Visualisation des Données")
    st.write("Ici on affichera les graphiques avec selectbox et slider.")

elif page == "Autres":
    st.title("⚙️ Page supplémentaire")
    st.write("Contenu test/dummy.")
