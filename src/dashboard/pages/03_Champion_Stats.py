from collections import defaultdict
from typing import Optional, Dict, Any, List

import pandas as pd
import streamlit as st

from src.dashboard.utils.riot import (
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    queue_label_to_id,
    QUEUES,
    RiotError,
    NotFound,
    season_to_date_start_timestamp,
)

st.set_page_config(page_title="Champion Stats", layout="wide")
st.title("Champion Stats")

summ = st.session_state.get("summoner")
if not summ:
    st.info("Primero busca un invocador; se guardará en la sesión.")
    st.stop()

region = summ.get("region")
puuid = summ.get("puuid")

col_a, col_b = st.columns([2,1])
with col_a:
    queue_label = st.selectbox("Cola", list(QUEUES.keys()), index=0)
with col_b:
    use_s2d = st.checkbox("Usar temporada (Season-to-date)", value=False)

n = st.slider("Nº de partidas a analizar", min_value=10, max_value=100, value=100)

queue_id = queue_label_to_id(queue_label)
start_time = season_to_date_start_timestamp() if use_s2d else None

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

agg = defaultdict(lambda: {"games":0, "wins":0, "kills":0, "deaths":0, "assists":0, "cs":0, "gold":0})

prog = st.progress(0.0, text="Calculando estadísticas por campeón…")
for i, mid in enumerate(ids, start=1):
    try:
        m = _cached_match(region, mid)
        p = find_participant_by_puuid(m, puuid)
        if not p:
            continue
        champ = p.get("championName") or str(p.get("championId"))
        a = agg[champ]
        a["games"] += 1
        a["wins"] += 1 if p.get("win") else 0
        a["kills"] += p.get("kills", 0)
        a["deaths"] += p.get("deaths", 0)
        a["assists"] += p.get("assists", 0)
        a["cs"] += p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
        a["gold"] += p.get("goldEarned", 0)
    except NotFound:
        pass
    except RiotError:
        # si hay 429 puntual, lo salvamos porque está cacheado para la siguiente
        pass
    prog.progress(i/len(ids))

rows = []
for champ, a in agg.items():
    if a["games"] == 0:
        continue
    deaths = a["deaths"] if a["deaths"] else 1
    rows.append({
        "Champion": champ,
        "Games": a["games"],
        "Win%": round(100 * a["wins"]/a["games"], 1),
        "KDA": round((a["kills"] + a["assists"]) / deaths, 2),
        "Avg K": round(a["kills"]/a["games"], 2),
        "Avg D": round(a["deaths"]/a["games"], 2),
        "Avg A": round(a["assists"]/a["games"], 2),
        "Avg CS": round(a["cs"]/a["games"], 1),
        "Avg Gold": round(a["gold"]/a["games"]),
    })

df = pd.DataFrame(rows).sort_values(["Games","Win%"], ascending=[False, False])
st.dataframe(df, use_container_width=False, width=1600)
