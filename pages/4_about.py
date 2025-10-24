# streamlit_app/pages/4_about.py
import streamlit as st

st.title("🔍 About")
st.markdown("""
## IND320 Project - Weather Data Analysis
**Author**: Esteban Carrasco

**Objectives**:
- Analyze hourly weather data from January 2020
- Create interactive visualizations using Streamlit
- Include specific analyses of wind directions

**Technologies Used**:
- Python (Pandas, Plotly, NumPy)
- Streamlit for the interactive dashboard

---

## IND320 Project - Energy Production Data Analysis (New Addition)
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

---

### Features Added (New Addition)
- **Data Extraction**: Automated retrieval of energy production data from the Elhub API.
- **Data Storage**: Integration with **Cassandra** and **MongoDB** for robust data management.
- **Interactive Visualizations**:
  - **Pie charts** showing the distribution of energy production by group.
  - **Line plots** illustrating hourly production trends for selected months and price areas.
- **User-Friendly Interface**: Filters to select specific price areas, production groups, and months.

---

### Challenges and Adaptations (New Addition)
Initially, the project was designed to use **Apache Spark** for data processing. However, due to **multiple connection issues** between Spark and Cassandra, I decided to abandon Spark. Instead, I used the **Cassandra Python driver** to directly extract and insert data, simplifying the workflow.

---

**Links**:
- [GitHub Source Code](https://github.com/Ficus22/IND320-ProjectWork)

**AI Usage**:
*Le Chat* ([Mistral AI](https://mistral.ai/)) helps me in this project by:
- Assist with advanced visualizations
- Translating the project into English
- Assisting with **troubleshooting compatibility issues** between Cassandra, MongoDB, and Python libraries.
- Providing **step-by-step guidance** for installation and configuration of Java, Cassandra, and MongoDB.
- Helping to **resolve data type conversion errors** and optimize data processing.
- Offering **alternative solutions** when initial attempts with Spark proved challenging.


**Note**: This project is a demonstration of data analysis and visualization skills and is not intended for commercial use. For more details, please refer to the associated Jupyter Notebook.
""")
