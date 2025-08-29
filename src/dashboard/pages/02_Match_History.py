import json
from typing import Optional, Dict, Any, List

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
)

st.set_page_config(page_title="Match History", layout="wide")
st.title("Match History")

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

n = st.slider("Número de partidas", min_value=1, max_value=100, value=10)

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

rows = []
prog = st.progress(0.0, text="Descargando partidas…")
for i, mid in enumerate(ids, start=1):
    try:
        m = _cached_match(region, mid)
        rows.append({
            "matchId": mid,
            "queueId": m.get("info", {}).get("queueId"),
            "duration (s)": m.get("info", {}).get("gameDuration"),
            "patch": m.get("info", {}).get("gameVersion"),
        })
    except NotFound:
        pass
    except RiotError as e:
        st.warning(f"Error en {mid}: {e}")
    prog.progress(i/len(ids))

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=False, width=1200)

with st.expander("IDs y JSON (primer match)"):
    st.code(json.dumps({"ids": ids[:20]}, indent=2))
    if rows:
        st.code(json.dumps(_cached_match(region, ids[0]), ensure_ascii=False, indent=2)[:4000] + " …")
