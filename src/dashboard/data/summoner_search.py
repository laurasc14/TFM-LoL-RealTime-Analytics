import json
import requests
import streamlit as st
import sys
import os

# Añadir el directorio src al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

# Ahora importa los módulos
from src.dashboard.utils.riot import lookup_summoner

from src.dashboard.utils.riot import (
    summoner_by_name,
    RiotError,
)

# Cargar el archivo JSON de campeones
def load_champions():
    with open("src/dashboard/data/champions.json", "r") as f:
        data = json.load(f)
        champions = {int(champ['key']): champ['id'] for champ in data['data'].values()}
    return champions

# Función para obtener la URL de la imagen del campeón
def get_champion_image(champion_id: int, champions: dict) -> str:
    champion_name = champions.get(champion_id)
    if champion_name:
        return f"http://ddragon.leagueoflegends.com/cdn/12.15.1/img/champion/{champion_name}.png"
    return None

# Cargar el diccionario de campeones
champions = load_champions()

# Lógica de búsqueda del invocador
st.set_page_config(page_title="Summoner Search", layout="wide")
st.title("Summoner Search")

summoner_name = st.text_input("Enter Summoner Name", "")

if summoner_name:
    try:
        summ = summoner_by_name("euw1", summoner_name)  # Cambia la región según corresponda
        champion_id = summ.get("championId")  # Asumiendo que championId está presente
        if champion_id:
            champion_image_url = get_champion_image(champion_id, champions)
            if champion_image_url:
                st.image(champion_image_url, width=200)  # Muestra la imagen del campeón

        st.write(f"Summoner Level: {summ.get('summonerLevel')}")
        st.write(f"Summoner ID: {summ.get('id')}")

    except RiotError as e:
        st.error(f"Error: {e}")
