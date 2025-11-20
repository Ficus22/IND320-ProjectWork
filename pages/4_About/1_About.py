# streamlit_app/pages/6_about.py
import streamlit as st

def app():
  st.title("🔍 About - IND320 Project")
  st.markdown("""
  **Author**: Esteban Carrasco
              
  **Link**: [GitHub Source Code](https://github.com/Ficus22/IND320-ProjectWork)
  """)

  # -------------------------
  # Tabs
  # -------------------------
  tab1, tab2, tab3, tab4 = st.tabs(["Assignment 1", "Assignment 2", "Assignment 3", "Assignment 4"])

  # --- Tab 1 ---
  with tab1:
      st.header("Weather Data Analysis")
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
      st.header("Energy Production Data Analysis")
      st.markdown("""
  **Objectives**:
  - Retrieve and analyze hourly energy production data from the Elhub API for Norway in 2021.
  - Store data in Cassandra and MongoDB for efficient querying and visualization.
  - Create interactive visualizations using Streamlit to explore energy production trends.
  - Include specific analyses of production groups and price areas.

  **Technologies Used**:
  - **Python** (Pandas, Matplotlib, Cassandra-driver, PyMongo)
  - **Cassandra** for data storage.
  - **MongoDB** for flexible querying and visualization.
  - **Streamlit** for the interactive dashboard.

  **Features Added**:
  - **Data Extraction**: Automated retrieval of energy production data from the Elhub API.
  - **Data Storage**: Integration with Cassandra and MongoDB for robust data management.
  - **Interactive Visualizations**:
    - **Pie charts** showing the distribution of energy production by group.
    - **Line plots** illustrating hourly production trends for selected months and price areas.
  - **User-Friendly Interface**: Filters to select specific price areas, production groups, and months.

  **Challenges and Adaptations**:
  - Originally planned with Apache Spark, but due to connection issues, switched to Cassandra Python driver for direct data extraction and insertion.
  - Simplified workflow and reduced dependency issues.

  ---

  ### **AI Usage**:
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
  **Objectives**:
  - Implement time series analyses and anomaly detection as per project guidelines.
  - Perform Seasonal-Trend decomposition using LOESS (STL) on energy production data.
  - Generate spectrograms to visualize frequency content over time.
  - Detect outliers in weather and production data using Statistical Process Control (SPC) and Direct Cosine Transform (DCT).
  - Detect anomalies using Local Outlier Factor (LOF).
  - Wrap all analyses in reusable functions with sensible default parameters.
  - Integrate results into Streamlit with interactive visualizations.

  **Technologies Used**:
  - **Python** (Pandas, NumPy, Matplotlib, Plotly, SciPy, Scikit-learn)
  - **Streamlit** for interactive visualization.
  - Statistical and signal processing methods:
    - **STL decomposition** (LOESS)
    - **DCT high-pass filtering**
    - **SPC boundaries with median and MAD**
    - **LOF anomaly detection**
    - **Spectrogram generation**

  **Features Added**:
  - **STL & Spectrogram Analysis**:
    - Decomposition of energy production data by price area, production group, and period.
    - Interactive plots for observed, trend, seasonal, and residual components.
    - Spectrograms illustrating frequency variations over time.
  - **Outlier & SPC Analysis**:
    - High-pass filtering of temperature or production data using DCT.
    - SPC boundary calculation and visualization of outliers.
  - **Anomaly Detection with LOF**:
    - Detection of anomalous points in hourly data.
    - Interactive visualizations highlighting LOF-detected anomalies.
  - **Reusable Functions**:
    - All analyses wrapped in functions with default parameters for reproducibility.
    - Functions return both plots and summaries/statistics of outliers or anomalies.

  **Challenges and Adaptations**:
  - Ensured compatibility with data retrieved via the **Open-Meteo API** for multiple locations (Oslo, Kristiansand, Trondheim, Tromsø, Bergen).
  - Adapted plots and analyses to dynamically handle user-selected years and price areas via Streamlit selectors.
  - Structured new pages in the Streamlit app to match project workflow (new A: STL/Spectrogram, new B: Outlier/SPC + LOF).
  - Verified consistency of DCT cut-offs, SPC thresholds, and LOF parameters across datasets.
  - Wrapped repetitive workflows in functions for modularity and easier testing.

  ---

  ### **AI Usage**:
  *Le Chat* ([Mistral AI](https://mistral.ai/)) assisted with:
  - Implementing STL decomposition and spectrogram visualizations.
  - Designing SPC and LOF analyses for time series data.
  - Troubleshooting parameter choices for DCT filtering and anomaly detection.
  - Switching from Matplotlib to Plotly.
  - Translating the project into English.
  """)

  # --- Tab 4 ---
  with tab4:
      st.header("Interactive Maps, Snow Drift, Correlations, and Forecasting")
      st.markdown("""
      **Objectives**:
      - Extend the Streamlit app with interactive map visualizations and user selectors.
      - Allow users to select Price areas, coordinates, production/consumption groups, and time intervals.
      - Implement snow drift calculations and visualizations per year and per month.
      - Enable meteorology-energy production correlations with sliding windows.
      - Add dynamic forecasting of energy production/consumption using SARIMAX.
      - Improve UX by reordering pages, caching, and adding spinners for long computations.

      **Technologies Used**:
      - **Python** (Pandas, NumPy, Plotly, Folium, Statsmodels)
      - **Streamlit** for interactive visualization.
      - Geospatial data handling:
          - **GeoJSON overlays** of Price areas (NO1–NO5)
          - Interactive choropleth mapping and coordinate selection
      - Statistical & forecasting methods:
          - **Sliding Window Correlation**
          - **SARIMAX forecasting**
          - Snow drift calculations and wind rose plots

      **Features Added**:

      - **Interactive Map & Selectors**:
          - Plotly/Folium map with GeoJSON overlays of Price areas NO1–NO5.
          - Downloaded and integrated GeoJSON data from NVE (Elspot areas).
          - Display outlines of all Price areas and highlight the selected area.
          - Store and mark any clicked coordinates interactively.
          - Allow users to choose an energy production/consumption group and time interval (days).
          - Transparent choropleth coloring of areas based on mean values of the selected group over the chosen interval.

      - **Snow Drift Calculation & Visualization**:
          - Year defined from July 1 of the selected year to June 30 of the following year.
          - Calculate snow drift per year for a selectable range of years.
          - Plot results with wind rose from Snow_drift.py.
          - Handle gracefully if no coordinate selection is made.
          - Added monthly snow drift plots, adjusting the x-axis for semesters and months.

      - **Meteorology & Energy Production**:
          - Sliding Window Correlation integrated into Streamlit with Plotly visuals.
          - Selectable lag and window length.
          - Independent selectors for meteorological properties and energy production/consumption.
          - Interactive exploration allows detection of correlation changes during normal vs. extreme weather.

      - **Forecasting Energy Production & Consumption**:
          - Dynamic SARIMAX interface with selectable parameters.
          - User-defined training timeframe and forecast horizon.
          - Forecasts of selected energy property with optional exogenous variables.
          - Interactive plotting with confidence intervals.

      - **UX Improvements**:
          - Reordered pages to improve navigation and workflow for users.
          - Added caching of heavy computations for faster interaction.
          - Spinners during long calculations to indicate progress.
          
      **Challenges and Adaptations**:
      - Ensured map interactions work smoothly with coordinate selections and Price area highlighting.
      - Adapted Snow_drift.py code to integrate into Streamlit with dynamic year selection and monthly plotting.
      - Maintained consistent color scales and axes across choropleth maps.
      - Verified compatibility between meteorological and production datasets for correlation analysis.
      - Streamlined forecasting interface for non-expert users, including validation of parameter inputs.

      ---

      ### **AI Usage**:
      *Le Chat* ([Mistral AI](https://mistral.ai/)) assisted with:
      - Designing the interactive map interface and GeoJSON overlays.
      - Integrating snow drift calculations into Streamlit with dynamic plotting.
      - Converting Sliding Window Correlation to Streamlit with Plotly.
      - Implementing the SARIMAX forecasting interface and visualizations.
      - Optimizing app UX with caching, spinners, and page reordering.
      """)
