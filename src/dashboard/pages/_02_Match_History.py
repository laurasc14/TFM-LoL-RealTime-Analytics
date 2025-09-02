from typing import Optional, Dict, Any, List
import streamlit as st
from src.dashboard.utils.riot import (
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    QUEUES,
    load_champions,
    get_champion_image,
    resolve_summoner_name,  # <- usamos esto para mostrar el nombre real
)


def main():
    st.set_page_config(page_title="Match History", layout="wide")
    st.title("Match History")

    # Invocador de la sesión
    summ = st.session_state.get("summoner")
    if not summ:
        st.info("Primero busca un invocador; se guardará en la sesión.")
        st.stop()

    region = summ.get("region")
    puuid = summ.get("puuid")

    # Filtros
    queue_label = st.selectbox("Cola a filtrar", list(QUEUES.keys()), index=0)
    queue_id = QUEUES[queue_label]
    n = st.slider("Número de partidas", min_value=1, max_value=10, value=5)

    # Datos
    ids = matches_by_puuid(puuid, region, count=n, queue=queue_id)
    champions_dict = load_champions()

    # Estilos (mismo layout que la captura)
    st.markdown("""
    <style>
    .row-container {
        display: flex;
        justify-content: space-between;
        background-color: #1e1e2f;
        color: #f0f0f0;
        padding: 6px 12px;
        border-bottom: 1px solid #444;
        align-items: center;
    }
    .row-header {
        background-color: #0a0a1a;
        font-weight: bold;
    }
    .status-win   { color: #00D46A; font-weight: 700; }
    .status-lose  { color: #FF5252; font-weight: 700; }
    .status-remake{ color: #FFB020; font-weight: 700; }
    .champ-img    { width: 28px; height: 28px; vertical-align: middle; margin-right: 6px; border-radius: 4px; }
    .team-label   { font-weight: 700; margin-top: 14px; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

    # Cabecera
    head = ["Match ID", "Queue", "Champion", "KDA", "CS", "Gold", "Duration", "Status"]
    cols_head = st.columns([2, 2, 2, 1, 1, 1, 1, 1])
    for c, h in zip(cols_head, head):
        c.markdown(f"<div class='row-container row-header'>{h}</div>", unsafe_allow_html=True)

    # Filas de cada partida
    for mid in ids:
        match = match_by_id(region, mid)
        me = find_participant_by_puuid(match, puuid)
        if not me:
            continue

        # status de la partida
        status = "Win" if me.get("win") else "Lose"
        if match.get("info", {}).get("gameDuration", 0) < 300:
            status = "Remake"
        status_cls = f"status-{status.lower()}"

        # Nombre de la cola
        qid = match.get("info", {}).get("queueId")
        qname = next((k for k, v in QUEUES.items() if v == qid), "Desconocida")

        # Campeón jugado
        champ_key = me.get("championId")
        champ_url = get_champion_image(champ_key, champions_dict)
        champ_html = f"<img class='champ-img' src='{champ_url}'>{me.get('championName', '-')}"

        # Fila principal
        cols = st.columns([2, 2, 2, 1, 1, 1, 1, 1])
        vals = [
            mid,
            qname,
            champ_html,
            f"{me.get('kills',0)}/{me.get('deaths',0)}/{me.get('assists',0)}",
            me.get("totalMinionsKilled", 0) + me.get("neutralMinionsKilled", 0),
            me.get("goldEarned", 0),
            match.get("info", {}).get("gameDuration", 0),
            status,
        ]
        for c, v in zip(cols, vals):
            c.markdown(f"<div class='row-container {status_cls}'>{v}</div>", unsafe_allow_html=True)

        # Expander con equipos
        with st.expander(f"Detalles del Match {mid}", expanded=False):
            parts = match.get("info", {}).get("participants", [])
            team1 = [p for p in parts if p.get("teamId") == 100]
            team2 = [p for p in parts if p.get("teamId") == 200]

            for label, team in [("Equipo 1", team1), ("Equipo 2", team2)]:
                st.markdown(f"<div class='team-label'>{label}</div>", unsafe_allow_html=True)

                # Cabecera de la tabla de equipo
                cols_t = st.columns([2, 2, 1, 1, 1, 1])
                for c, h in zip(cols_t, ["Summoner", "Champion", "KDA", "CS", "Gold", "Status"]):
                    c.markdown(f"<div class='row-container row-header'>{h}</div>", unsafe_allow_html=True)

                # Filas por jugador
                for p in team:
                    # Campeón del jugador
                    p_key = p.get("championId")
                    p_url = get_champion_image(p_key, champions_dict)
                    p_champ = f"<img class='champ-img' src='{p_url}'>{p.get('championName','-')}"

                    # status por jugador
                    p_status = "Win" if p.get("win") else "Lose"
                    if match.get("info", {}).get("gameDuration", 0) < 300:
                        p_status = "Remake"
                    p_cls = f"status-{p_status.lower()}"

                    # <<< AQUÍ se pinta el NOMBRE REAL >>>
                    display_name = resolve_summoner_name(region, p)

                    # resaltar mi fila
                    style_me = "background-color:#2a2aff;" if p.get("puuid") == puuid else ""

                    cols_row = st.columns([2, 2, 1, 1, 1, 1])
                    vals_row = [
                        display_name,                                       # <- nombre real
                        p_champ,
                        f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                        p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                        p.get("goldEarned", 0),
                        p_status,
                    ]
                    for c, v in zip(cols_row, vals_row):
                        c.markdown(
                            f"<div class='row-container {p_cls}' style='{style_me}'>{v}</div>",
                            unsafe_allow_html=True
                        )
