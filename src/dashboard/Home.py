# src/dashboard/pages/Home.py
import streamlit as st

def render():
    st.title("🏠 Bienvenido al Dashboard LoL")
    st.write("Usa el menú de la izquierda para navegar entre las distintas secciones:")
    st.markdown("""
    - 🔎 **Summoner Search**: busca un jugador por su Riot ID.  
    - 📜 **Match History**: explora partidas recientes del jugador cargado.  
    - 📊 **Champion Stats**: estadísticas detalladas por campeón.  
    - 🎮 **Live Game**: información de la partida en curso.
    """)

render()