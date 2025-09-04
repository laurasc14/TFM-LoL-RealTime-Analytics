import streamlit as st

# --- Importa las páginas ---
from src.dashboard.pages import _00_Home as home
from src.dashboard.pages import _01_Summoner_Search as summoner_search
from src.dashboard.pages import _02_Match_History as match_history
from src.dashboard.pages import _03_Champion_Stats as champion_stats
from src.dashboard.pages import _04_Live_Game as live_game

# --- Configuración general de la app ---
st.set_page_config(page_title="LoL Dashboard", page_icon="🎮", layout="wide")

# --- Estado inicial global ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"  # "dark" | "light"
if "dd_version" not in st.session_state:
    st.session_state["dd_version"] = "14.18.1"

# --- Navegación ---
page = st.sidebar.radio(
    "Selecciona una página:",
    ["Home", "Summoner Search", "Match History", "Champion Stats", "Live Game"],
    index=["Home", "Summoner Search", "Match History", "Champion Stats", "Live Game"].index(st.session_state["current_page"]),
    key="current_page",
)

# --- Router ---
if page == "Home":
    home.main()
elif page == "Summoner Search":
    summoner_search.main()
elif page == "Match History":
    match_history.main()
elif page == "Champion Stats":
    champion_stats.main()
elif page == "Live Game":
    live_game.main()

# --- Estilos globales suaves ---
st.markdown("""
    <style>
        .dataframe {
            border-radius: 10px;
            border: 1px solid #2a2a2a;
            padding: 10px;
            background-color: rgba(255,255,255,.02);
        }
        .dataframe th {
            background-color: #0b5aa3;
            color: white;
            font-weight: 600;
        }
        .dataframe td {
            color: #e7e7e7;
            padding: 8px 10px;
        }
        .stButton>button {
            background-color: #0b5aa3;
            color: white;
            border-radius: 10px;
            font-weight: 600;
            border: 0;
        }
        .stButton>button:hover { background-color: #0f73d1; }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar / navegación ---
#page = st.sidebar.radio(
 #   "Selecciona una página:",
  #  ["Home", "Summoner Search", "Match History", "Champion Stats", "Live Game"],
   # index=["Home", "Summoner Search", "Match History", "Champion Stats", "Live Game"]
    #      .index(st.session_state["current_page"]),
  #  key="current_page",
#)
