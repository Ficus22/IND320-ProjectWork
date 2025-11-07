# streamlit_app/pages/6_about.py
import streamlit as st

st.title("🔍 About")
st.markdown("""
**Author**: Esteban Carrasco
""")

# -------------------------
# Tabs
# -------------------------
tab1, tab2, tab3 = st.tabs(["Assignement 1", "Assignement 2", "Assignement 3"])

# --- Tab 1 ---
with tab1:
    st.header("IND320 Project - Weather Data Analysis")
    st.markdown("""
**Objectives**:
- Analyze hourly weather data from January 2020
- Create interactive visualizations using Streamlit
- Include specific analyses of wind directions

**Technologies Used**:
- Python (Pandas, Plotly, NumPy)
- Streamlit for the interactive dashboard
""")

# --- Tab 2 ---
with tab2:
    st.header("IND320 Project - Energy Production Data Analysis")
    st.markdown("""
**Objectives**:
- Retrieve and analyze hourly energy production data from the **Elhub API** for Norway in 2022.
- Store data in **Cassandra** and **MongoDB** for efficient querying and visualization.
- Create interactive visualizations using **Streamlit** to explore energy production trends.
- Include specific analyses of production groups and price areas.

**Technologies Used**:
- **Python** (Pandas, Matplotlib, Cassandra-driver, PyMongo)
- **Cassandra** for data storage.
- **MongoDB** for flexible querying and visualization.
- **Streamlit** for the interactive dashboard.

**Features Added**:
- **Data Extraction**: Automated retrieval of energy production data from the Elhub API.
- **Data Storage**: Integration with **Cassandra** and **MongoDB** for robust data management.
- **Interactive Visualizations**:
  - **Pie charts** showing the distribution of energy production by group.
  - **Line plots** illustrating hourly production trends for selected months and price areas.
- **User-Friendly Interface**: Filters to select specific price areas, production groups, and months.

**Challenges and Adaptations**:
- Originally planned with **Apache Spark**, but due to **connection issues**, switched to **Cassandra Python driver** for direct data extraction and insertion.
- Simplified workflow and reduced dependency issues.

**Links**:
- [GitHub Source Code](https://github.com/Ficus22/IND320-ProjectWork)

**AI Usage**:
*Le Chat* ([Mistral AI](https://mistral.ai/)) assisted with:
- Advanced visualizations
- Translating the project into English
- Troubleshooting compatibility issues between Cassandra, MongoDB, and Python
- Step-by-step guidance for Java, Cassandra, and MongoDB setup
- Resolving data type conversion errors and optimizing data processing
- Suggesting alternatives when Spark proved challenging
""")

# --- Tab 3 ---
with tab3:
    st.header("Advanced Analyses (STL, Spectrogram, SPC, LOF)")
    st.markdown("""
This section demonstrates the **time series and anomaly detection analyses** implemented in pages 2 and 5:

**STL & Spectrogram Analysis**:
- Performed **STL decomposition** for selected price areas and production groups.
- Generated interactive plots for **observed, trend, seasonal, and residual components**.
- Spectrograms visualize the **frequency content over time** for energy production.

**Outlier & SPC Analysis**:
- Applied **DCT high-pass filtering** to highlight rapid fluctuations in production.
- Used **Statistical Process Control (SPC)** with median and MAD to detect unusual deviations.
- Interactive charts show **original vs filtered data** with SPC boundaries and detected outliers.

**Anomaly Detection with LOF**:
- Used **Local Outlier Factor (LOF)** to detect anomalies in hourly production.
- Visualizations display LOF-detected anomalies as red markers on time series.

These analyses allow users to **explore patterns, trends, and anomalies** in energy production data in an interactive way.
""")
