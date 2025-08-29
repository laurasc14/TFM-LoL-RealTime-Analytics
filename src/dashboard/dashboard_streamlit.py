import streamlit as st

st.set_page_config(page_title="LoL Dashboard", page_icon="🎮", layout="wide")

st.sidebar.title("lol dashboard streamlit")
st.sidebar.page_link("pages/01_Summoner_Search.py", label="Summoner Search", icon="🔎")
st.sidebar.page_link("pages/02_Match_History.py", label="Match History", icon="🕒")
st.sidebar.page_link("pages/03_Champion_Stats.py", label="Champion Stats", icon="📊")
st.sidebar.page_link("pages/04_Live_Game.py", label="Live Game", icon="🟢")

st.title("LoL Dashboard")
st.write("Usa el menú de la izquierda para navegar.")
