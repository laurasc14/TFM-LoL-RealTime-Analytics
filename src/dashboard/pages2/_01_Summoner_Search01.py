import streamlit as st
import requests
import time
import os
from src.dashboard.utils.riot import region_for_platform

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8081")

st.set_page_config(page_title="Summoner Search", layout="wide")

st.title("🔎 Buscar invocador")

# --- formulario de búsqueda ---
with st.form("search_summoner"):
    name = st.text_input("Nombre del invocador")
    tag = st.text_input("Tag (por ejemplo EUW)", value="EUW")
    platform = st.selectbox("Plataforma", ["EUW1", "NA1", "KR", "BR1", "JP1"], index=0)
    submitted = st.form_submit_button("Buscar")

if submitted and name:
    try:
        url = f"{BACKEND_URL}/summoner/by-name/{platform}/{name}"
        resp = requests.get(url)
        resp.raise_for_status()
        info = resp.json()

        # guardamos invoker_ctx (más completo)
        st.session_state["invoker_ctx"] = {
            "summoner": info.get("name") or name,
            "tag": tag,
            "summoner_id": info.get("id") or "",
            "account_id": info.get("accountId") or "",
            "puuid": info.get("puuid") or "",
            "platform": platform,
            "region": region_for_platform(platform),
            "saved_at": int(time.time()),
        }

        # guardamos summoner (lo que espera Match History)
        st.session_state["summoner"] = {
            "gameName": info.get("name") or name,
            "tagLine": tag,
            "puuid": info.get("puuid") or "",
        }

        st.success(f"Invocador **{name}#{tag}** guardado en sesión.")
    except Exception as e:
        st.error(f"Error al buscar invocador: {e}")

# mostrar el contexto actual
if "summoner" in st.session_state:
    summ = st.session_state["summoner"]
    st.info(
        f"Jugador en sesión: **{summ.get('gameName','')}#{summ.get('tagLine','')}**"
    )
