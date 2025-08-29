# src/dashboard/pages/04_Live_Game.py
import json
import streamlit as st
from src.dashboard.utils.riot import (
    live_game_by_summoner_id,
    summoner_by_puuid,
    RiotError,
    NotFound,
)

st.set_page_config(page_title="Live Game", layout="wide")
st.title("Live Game  ↪")

summ = st.session_state.get("summoner")
if not summ:
    st.info("Primero busca un invocador; se guardará en la sesión.")
    st.stop()

region = (summ.get("region") or "").lower().strip()
puuid = summ.get("puuid")
enc_id = summ.get("id")

if not region:
    st.error("No tengo la plataforma (p. ej., euw1). Repite la búsqueda.")
    st.stop()

# 1) Siempre refrescamos el ID desde summoner-v4 usando el PUUID (plataforma correcta)
def refresh_id_from_puuid() -> str | None:
    """Refrescar el ID del invocador desde su PUUID en la región correcta."""
    try:
        if not puuid:
            st.error("No se encuentra el PUUID.")
            return None
        st.write(f"Recuperando el ID del invocador desde el PUUID: {puuid}")  # Depuración
        summoner = summoner_by_puuid(region, puuid)
        if not summoner:
            st.error(f"No se pudo encontrar al invocador con PUUID: {puuid}.")
            return None
        st.write(f"ID del invocador actualizado: {summoner.get('id')}")  # Depuración
        return summoner.get("id")
    except RiotError as e:
        st.error(f"Error al obtener el ID del invocador: {str(e)}")
        return None


# Refrescamos el ID si es necesario
fresh_id = refresh_id_from_puuid()
if fresh_id:
    enc_id = fresh_id
    summ["id"] = enc_id
    st.session_state["summoner"] = summ

if not enc_id:
    st.warning("No pude resolver el ID (encryptedSummonerId). Vuelve a buscar al invocador.")
    st.stop()

def is_decrypt_error(e: RiotError) -> bool:
    msg = str(e).lower()
    return "exception decrypting" in msg and "spectator" in msg

# 2) Llamada a Spectator con un reintento inteligente si Riot devuelve “Exception decrypting…”
def fetch_live_game(_id: str):
    try:
        st.write(f"Intentando obtener el juego en vivo para el ID: {_id}")  # Depuración
        game = live_game_by_summoner_id(region, _id)
        if game:
            return game
        else:
            st.info("El invocador no está actualmente en una partida activa.")
            return None
    except RiotError as e:
        if is_decrypt_error(e):
            st.write(f"Error de desencriptado al intentar obtener el juego en vivo para el ID: {_id}")  # Depuración
            fresh_id = refresh_id_from_puuid()
            if fresh_id and fresh_id != _id:
                try:
                    return live_game_by_summoner_id(region, fresh_id)
                except NotFound:
                    return None
                except RiotError as e2:
                    st.error(f"Error en el nuevo ID: {str(e2)}")
                    return "err"
        st.error(f"Error al obtener el juego en vivo: {str(e)}")
        return "err"

# Intentamos obtener el juego en vivo
game = fetch_live_game(enc_id)

# Verificamos si hay un error en el juego
if game == "err":
    st.stop()

# Si no se obtiene el juego, mostramos que el invocador no está en partida
if not game:
    st.info("El invocador no está en partida ahora mismo, o no se pudo resolver su ID para esta plataforma.")
    st.stop()

st.success("Partida en curso encontrada.")
with st.expander("Ver JSON bruto", expanded=False):
    st.code(json.dumps(game, ensure_ascii=False, indent=2)[:4000] + " …")

players = game.get("participants", [])
c1, c2 = st.columns(2)
half = (len(players) + 1) // 2
for i, p in enumerate(players):
    col = c1 if i < half else c2
    with col:
        st.write(
            f"**{p.get('summonerName','?')}** — champId `{p.get('championId','?')}` — "
            f"spell1 `{p.get('spell1Id','?')}`, spell2 `{p.get('spell2Id','?')}`"
        )
