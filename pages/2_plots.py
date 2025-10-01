# Streamlit_app/pages/2_plots.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.title("📈 Visualisations Météo")

# ==============================
# Chargement des données
# ==============================
@st.cache_data
def load_data():
    csv_path = "data/open-meteo-subset.csv"
    df = pd.read_csv(csv_path)
    df['time'] = pd.to_datetime(df['time'])
    return df

try:
    df = load_data()

    # Liste des colonnes numériques à tracer
    numeric_cols = [
        "temperature_2m (°C)",
        "precipitation (mm)",
        "wind_speed_10m (m/s)",
        "wind_gusts_10m (m/s)"
    ]

    # ==============================
    # Widgets de sélection utilisateur
    # ==============================
    # Sélection d'une variable
    selected_col = st.selectbox("Choisir une variable :", numeric_cols + ["Toutes les colonnes"])

    # Liste des mois uniques et leurs noms
    month_names = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    months = sorted(df['time'].dt.month.unique())
    month_labels = [month_names[m] for m in months]

    # Sélection d'une plage de mois par noms
    month_range_labels = st.select_slider(
        "Sélectionnez une plage de mois",
        options=month_labels,
        value=(month_labels[0], month_labels[0])  # par défaut : premier mois
    )

    # Conversion des noms en chiffres
    month_range = [
        [k for k,v in month_names.items() if v == month_range_labels[0]][0],
        [k for k,v in month_names.items() if v == month_range_labels[1]][0]
    ]

    # Filtrage
    filtered_df = df[df['time'].dt.month.between(month_range[0], month_range[1])]


    # ==============================
    # Affichage du graphique
    # ==============================
    if selected_col == "Toutes les colonnes":
        fig = px.line(
            filtered_df,
            x="time",
            y=numeric_cols,
            title=f"Évolution des variables météo ({month_range[0]} → {month_range[1]})"
        )
    else:
        fig = px.line(
            filtered_df,
            x="time",
            y=selected_col,
            title=f"{selected_col} ({month_range[0]} → {month_range[1]})"
        )

    fig.update_layout(
        xaxis_title="Temps",
        yaxis_title="Valeurs",
        legend_title="Variables"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # Graphique polaire pour direction du vent
    # ==============================
    st.subheader("🌪️ Direction et intensité du vent")
    fig_polar = px.scatter_polar(
        filtered_df,
        r="wind_speed_10m (m/s)",
        theta="wind_direction_10m (°)",
        size="wind_speed_10m (m/s)",
        color="wind_speed_10m (m/s)",
        title="Rose des vents (polaire)"
    )
    st.plotly_chart(fig_polar, use_container_width=True)

except Exception as e:
    st.error(f"Erreur lors du chargement ou du tracé : {e}")
