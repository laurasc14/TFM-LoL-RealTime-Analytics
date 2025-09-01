from __future__ import annotations
from typing import Dict, Any, List, Optional
import streamlit as st
import math
from collections import defaultdict

from src.dashboard.utils.riot import (
    matches_by_puuid,
    match_by_id,
    QUEUES,
    load_champions,
    get_champion_image,
    season_to_date_start_timestamp,
)

def _safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else a / b

def _fmt2(x: float) -> float:
    # Para dataframe, mejor número plano (Streamlit ya formatea)
    return round(x, 2)

def main():
    st.set_page_config(page_title="Champion Stats", layout="wide")
    st.title("Champion Stats")

    # --- CSS para legibilidad (tema oscuro) ---
    st.markdown("""
    <style>
    /* Más contraste en tablas y textos */
    [data-testid="stTable"] thead tr th,
    [data-testid="stTable"] tbody tr td {
        color: #f0f4f8 !important;
        font-size: 14px !important;
    }
    .stDataFrame, .stTable, .stMarkdown {
        color: #f0f4f8 !important;
    }
    .divider {height: 6px; background: linear-gradient(90deg,#0b2239,#143d5c); border-radius: 4px; margin: 8px 0 12px;}
    </style>
    """, unsafe_allow_html=True)

    # --- Comprobar invocador en sesión ---
    summ = st.session_state.get("summoner")
    if not summ:
        st.info("Primero busca un invocador en la página **Summoner Search**.")
        st.stop()

    region: str = summ.get("region")
    puuid: str = summ.get("puuid")
    if not (region and puuid):
        st.warning("Faltan datos del invocador (region/puuid). Vuelve a buscarlo en Summoner Search.")
        st.stop()

    # --- Filtros ---
    top = st.columns([3, 1, 1])
    with top[0]:
        queue_label = st.selectbox("Cola", list(QUEUES.keys()), index=1)  # por defecto Solo/Dúo
        queue_id = QUEUES[queue_label]
    with top[1]:
        use_season = st.checkbox("Usar temporada (Season-to-date)", value=False)
    with top[2]:
        n_matches = st.slider("Nº de partidas a analizar", min_value=10, max_value=100, value=50, step=10)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # --- Obtener IDs de partidas ---
    start_ts: Optional[int] = season_to_date_start_timestamp() if use_season else None
    try:
        match_ids: List[str] = matches_by_puuid(
            puuid, region, count=n_matches, queue=queue_id, start_time=start_ts
        )
    except Exception as e:
        st.error(f"No se pudieron obtener partidas: {e}")
        st.stop()

    if not match_ids:
        st.info("No hay partidas para los filtros seleccionados.")
        st.stop()

    # --- Cargar diccionario de campeones ---
    champions_dict = load_champions()

    # --- Agregación por campeón ---
    agg: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "games": 0,
        "wins": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "cs": 0,
        "gold": 0,
        "name": "",
    })

    for mid in match_ids:
        try:
            match = match_by_id(region, mid)
        except Exception:
            continue

        participants = match.get("info", {}).get("participants", [])
        # Buscar al jugador
        me = next((p for p in participants if p.get("puuid") == puuid), None)
        if not me:
            continue

        champ_id = me.get("championId")
        entry = agg[champ_id]
        entry["games"] += 1
        entry["wins"] += 1 if me.get("win") else 0
        entry["kills"] += me.get("kills", 0)
        entry["deaths"] += me.get("deaths", 0)
        entry["assists"] += me.get("assists", 0)
        entry["cs"] += me.get("totalMinionsKilled", 0) + me.get("neutralMinionsKilled", 0)
        entry["gold"] += me.get("goldEarned", 0)
        entry["name"] = me.get("championName", str(champ_id))

    # --- Construir DataFrame (sin pandas import explícito arriba para no romper cold start) ---
    import pandas as pd

    rows = []
    for cid, e in agg.items():
        games = e["games"]
        if games == 0:
            continue
        kills = e["kills"]; deaths = e["deaths"]; assists = e["assists"]
        kda = (kills + assists) / (deaths if deaths > 0 else 1)
        rows.append({
            "Icon": get_champion_image(cid, champions_dict),
            "Champion": e["name"],
            "Games": int(games),
            "Win%": _fmt2(100.0 * _safe_div(e["wins"], games)),
            "KDA": _fmt2(kda),
            "Avg K": _fmt2(_safe_div(kills, games)),
            "Avg D": _fmt2(_safe_div(deaths, games)),
            "Avg A": _fmt2(_safe_div(assists, games)),
            "Avg CS": _fmt2(_safe_div(e["cs"], games)),
            "Avg Gold": int(round(_safe_div(e["gold"], games))),
        })

    if not rows:
        st.info("No hay datos agregables para mostrar.")
        st.stop()

    df = pd.DataFrame(rows).sort_values(["Games", "Win%"], ascending=[False, False]).reset_index(drop=True)

    # --- Mostrar DataFrame con columna de imagen real ---
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Icon": st.column_config.ImageColumn(""),
            "Champion": st.column_config.TextColumn("Champion", help="Campeón jugado"),
            "Games": st.column_config.NumberColumn(format="%d"),
            "Win%": st.column_config.NumberColumn(format="%.2f%%"),
            "KDA": st.column_config.NumberColumn(format="%.2f"),
            "Avg K": st.column_config.NumberColumn(format="%.2f"),
            "Avg D": st.column_config.NumberColumn(format="%.2f"),
            "Avg A": st.column_config.NumberColumn(format="%.2f"),
            "Avg CS": st.column_config.NumberColumn(format="%.1f"),
            "Avg Gold": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True,
    )

if __name__ == "__main__":
    main()
