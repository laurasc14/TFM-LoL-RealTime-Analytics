import streamlit as st

from src.dashboard.pages import _01_Summoner_Search as summoner_search
from src.dashboard.pages import _02_Match_History as match_history
from src.dashboard.pages import _03_Champion_Stats as champion_stats
from src.dashboard.pages import _04_Live_Game as live_game


# Configuración general de la página
st.set_page_config(
    page_title="LoL Dashboard",
    page_icon="🎮",
    layout="wide"
)

# Selector de páginas
page = st.sidebar.radio(
    "Selecciona una página:",
    ["Dashboard", "Summoner Search", "Match History", "Champion Stats", "Live Game"],
    index=0
)

# Mostrar solo la página seleccionada
if page == "Dashboard":
    st.title("LoL Dashboard")
    st.write("Usa el menú de la izquierda para navegar.")
elif page == "Summoner Search":
    summoner_search.main()
elif page == "Match History":
    match_history.main()
elif page == "Champion Stats":
    champion_stats.main()
elif page == "Live Game":
    live_game.main()

def main():
    st.title("League of Legends Dashboard")

# Estilo general para el dashboard
st.markdown("""
    <style>
        /* Estilo para las tablas */
        .dataframe {
            border-radius: 10px;
            border: 1px solid #ddd;
            padding: 10px;
            background-color: #f5f5f5;
        }
        .dataframe th {
            background-color: #005A9C;
            color: white;
            font-weight: bold;
        }
        .dataframe td {
            color: #333;
            padding: 10px;
        }
        .stButton>button {
            background-color: #005A9C;
            color: white;
            border-radius: 8px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #007ACC;
        }
        /* Títulos y secciones */
        .title {
            font-size: 24px;
            font-weight: bold;
            color: #005A9C;
        }
    </style>
""", unsafe_allow_html=True)