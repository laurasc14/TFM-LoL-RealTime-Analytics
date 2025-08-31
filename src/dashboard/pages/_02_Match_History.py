import json
from typing import Optional, Dict, Any, List
from collections import defaultdict

import pandas as pd
import streamlit as st

from src.dashboard.utils.riot import (
    matches_by_puuid,
    match_by_id,
    queue_label_to_id,
    QUEUES,
    NotFound,
    RiotError,
    season_to_date_start_timestamp,
    load_champions,
    get_champion_image,
)

def main():
    st.set_page_config(page_title="Match History", layout="wide")
    st.title("Match History  ↪")

    summ = st.session_state.get("summoner")
    if not summ:
        st.info("Primero busca un invocador; se guardará en la sesión.")
        st.stop()

    region = summ.get("region")
    puuid = summ.get("puuid")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        queue_label = st.selectbox("Cola", list(QUEUES.keys()), index=0)
    with col_b:
        use_s2d = st.checkbox("Usar temporada (Season-to-date)", value=False)

    n = st.slider("Número de partidas", min_value=1, max_value=100, value=10)

    queue_id = queue_label_to_id(queue_label)
    start_time = season_to_date_start_timestamp() if use_s2d else None

    champions_dict = load_champions()

    @st.cache_data(show_spinner=False, ttl=300)
    def _cached_ids(region: str, puuid: str, count: int, queue: Optional[int], start_time: Optional[int]) -> List[str]:
        return matches_by_puuid(puuid, region, count=count, queue=queue, start_time=start_time)

    @st.cache_data(show_spinner=False, ttl=600)
    def _cached_match(region: str, match_id: str) -> Dict[str, Any]:
        return match_by_id(region, match_id)

    try:
        ids = _cached_ids(region, puuid, n, queue_id, start_time)
    except RiotError as e:
        st.error(str(e))
        st.stop()

    if not ids:
        st.info("No hay partidas para los filtros seleccionados.")
        st.stop()

    rows = []
    prog = st.progress(0.0, text="Descargando partidas…")
    for i, mid in enumerate(ids, start=1):
        try:
            m = _cached_match(region, mid)
            participant = next((p for p in m.get("info", {}).get("participants", []) if p["puuid"] == puuid), None)
            if not participant:
                continue

            champ_id = participant.get("championId")
            champ_name = participant.get("championName")
            champ_img = get_champion_image(champ_id, champions_dict)

            # Estado de la partida
            if participant.get("win") is True:
                result = "Win"
            elif participant.get("win") is False:
                result = "Lose"
            else:
                result = "Remake"

            rows.append({
                "Match ID": mid,
                "Champion": f'<img src="{champ_img}" width="32"> {champ_name}',
                "Queue": next((k for k, v in QUEUES.items() if v == m.get("info", {}).get("queueId")), "Desconocida"),
                "Duration": m.get("info", {}).get("gameDuration"),
                "Patch": m.get("info", {}).get("gameVersion"),
                "Result": result
            })
        except NotFound:
            pass
        except RiotError:
            pass
        prog.progress(i / len(ids))

    df = pd.DataFrame(rows)

    # CSS tabla dark full-width
    st.markdown("""
        <style>
            table {
                width: 100% !important;
                border-collapse: collapse;
            }
            table thead th {
                background-color: #003366;  /* Azul más oscuro */
                color: #f5f5f5;            /* Letras más visibles */
                padding: 10px;
                text-align: center;
            }
            table tbody tr:nth-child(odd) {
                background-color: #1a1a1a;
            }
            table tbody tr:nth-child(even) {
                background-color: #222222;
            }
            table tbody td {
                color: #f5f5f5;
                padding: 8px;
                text-align: center;
            }
            table tbody tr:hover {
                background-color: #333333;
            }
            .win { color: #00ff00; font-weight: bold; }
            .lose { color: #ff4444; font-weight: bold; }
            .remake { color: #ffcc00; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # Pintar resultado con color
    def color_result(r):
        if r == "Win":
            return f'<span class="win">{r}</span>'
        elif r == "Lose":
            return f'<span class="lose">{r}</span>'
        else:
            return f'<span class="remake">{r}</span>'

    if not df.empty:
        df["Result"] = df["Result"].apply(color_result)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
