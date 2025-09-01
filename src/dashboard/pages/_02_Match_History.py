from typing import Optional, Dict, Any, List
import streamlit as st
from src.dashboard.utils.riot import (
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    QUEUES,
    load_champions,
    get_champion_image,
)

def main():
    st.set_page_config(page_title="Match History", layout="wide")
    st.title("Match History")

    # Obtener invocador
    summ = st.session_state.get("summoner")
    if not summ:
        st.info("Primero busca un invocador; se guardará en la sesión.")
        st.stop()

    region = summ.get("region")
    puuid = summ.get("puuid")

    # Selección de cola
    queue_label = st.selectbox("Cola a filtrar", list(QUEUES.keys()), index=0)
    queue_id = QUEUES[queue_label]

    n = st.slider("Número de partidas", min_value=1, max_value=10, value=5)

    # Obtener partidas
    ids = matches_by_puuid(puuid, region, count=n, queue=queue_id)
    champions_dict = load_champions()

    # CSS oscuro y filas
    st.markdown("""
    <style>
    .row-container {display: flex; justify-content: space-between; background-color: #1e1e2f; color: #f0f0f0; padding: 6px 12px; border-bottom: 1px solid #444; align-items: center;}
    .row-header {background-color: #0a0a1a; font-weight: bold;}
    .status-win {color: #00ff00; font-weight: bold;}
    .status-lose {color: #ff4444; font-weight: bold;}
    .status-remake {color: #ffa500; font-weight: bold;}
    .champ-img {width: 32px; height: 32px; vertical-align: middle; margin-right: 4px; border-radius: 4px;}
    .team-label {font-weight:bold; margin-top:10px; font-size:16px;}
    </style>
    """, unsafe_allow_html=True)

    # Cabecera
    col_names = ["Match ID", "Queue", "Champion", "KDA", "CS", "Gold", "Duration", "Status"]
    header_cols = st.columns([2,2,2,1,1,1,1,1])
    for h_col, h_name in zip(header_cols, col_names):
        h_col.markdown(f"<div class='row-container row-header'>{h_name}</div>", unsafe_allow_html=True)

    # Filas principales
    for mid in ids:
        match = match_by_id(region, mid)
        participant = find_participant_by_puuid(match, puuid)
        if not participant:
            continue

        # Estado de partida
        status = "Win" if participant.get("win") else "Lose"
        if match.get("info", {}).get("gameDuration", 0) < 300:
            status = "Remake"
        status_class = f"status-{status.lower()}"

        # Nombre de la cola
        match_queue_id = match.get("info", {}).get("queueId")
        match_queue_name = next((k for k,v in QUEUES.items() if v == match_queue_id), "Desconocida")

        # Imagen del campeón
        champ_key = participant.get("championId")
        champ_url = get_champion_image(champ_key, champions_dict)
        champ_html = f"<img class='champ-img' src='{champ_url}'>{participant.get('championName','-')}"

        # Columnas de fila
        cols = st.columns([2,2,2,1,1,1,1,1])
        col_vals = [
            mid,
            match_queue_name,
            champ_html,
            f"{participant.get('kills',0)}/{participant.get('deaths',0)}/{participant.get('assists',0)}",
            participant.get("totalMinionsKilled",0) + participant.get("neutralMinionsKilled",0),
            participant.get("goldEarned",0),
            match.get("info", {}).get("gameDuration",0),
            status
        ]
        for c, val in zip(cols, col_vals):
            c.markdown(f"<div class='row-container {status_class}'>{val}</div>", unsafe_allow_html=True)

        # Expander con equipos separados
        with st.expander(f"Detalles del Match {mid}", expanded=False):
            participants = match.get("info", {}).get("participants", [])
            team1 = [p for p in participants if p.get("teamId") == 100]
            team2 = [p for p in participants if p.get("teamId") == 200]

            for tname, team in [("Equipo 1", team1), ("Equipo 2", team2)]:
                st.markdown(f"<div class='team-label'>{tname}</div>", unsafe_allow_html=True)
                # Cabecera del equipo
                cols = st.columns([2,2,1,1,1,1])
                for h_col, h_name in zip(cols, ["Summoner", "Champion", "KDA", "CS", "Gold", "Status"]):
                    h_col.markdown(f"<div class='row-container row-header'>{h_name}</div>", unsafe_allow_html=True)

                for p in team:
                    # Resaltar invocador principal
                    extra_style = "background-color:#3333ff;" if p.get("puuid") == puuid else ""

                    p_champ_key = p.get("championId")
                    p_champ_url = get_champion_image(p_champ_key, champions_dict)
                    p_champ_html = f"<img class='champ-img' src='{p_champ_url}'>{p.get('championName','-')}"
                    p_status = "Win" if p.get("win") else "Lose"
                    if match.get("info", {}).get("gameDuration", 0) < 300:
                        p_status = "Remake"
                    status_class = f"status-{p_status.lower()}"

                    cols = st.columns([2,2,1,1,1,1])
                    vals = [
                        p.get("summonerName"),
                        p_champ_html,
                        f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                        p.get("totalMinionsKilled",0)+p.get("neutralMinionsKilled",0),
                        p.get("goldEarned",0),
                        p_status
                    ]
                    for c, v in zip(cols, vals):
                        c.markdown(f"<div class='row-container {status_class}' style='{extra_style}'>{v}</div>", unsafe_allow_html=True)
