import os, time
import streamlit as st
from datetime import datetime, timezone
from riotwatcher import LolWatcher, ApiError
from pymongo import MongoClient
import pandas as pd

# ---------- Config ----------
st.set_page_config(page_title="LoL – Perfil de Invocador", layout="wide")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
assert RIOT_API_KEY, "Falta RIOT_API_KEY en el entorno"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://final-mongo:27017/lol")
MONGO_DB = os.getenv("MONGO_DB", "lol")

REGION_TO_ROUTING = {
    "euw1": ("europe", "EUW"), "eun1": ("europe", "EUNE"), "na1": ("americas", "NA"),
    "kr": ("asia", "KR"), "br1": ("americas", "BR"), "la1": ("americas", "LAN"),
    "la2": ("americas", "LAS"), "oc1": ("sea", "OCE"), "tr1": ("europe", "TR"),
    "ru": ("europe", "RU"), "jp1": ("asia", "JP")
}
QUEUE_MAP = {420: "SoloQ", 440: "Flex", 450: "ARAM", 400: "Normal Draft", 430: "Normal Blind"}

DD_VER = "15.16.1"  # versión de Data Dragon (opcionalmente puedes autodetectar)
CDN = f"https://ddragon.leagueoflegends.com/cdn/{DD_VER}"

# ---------- Recursos cacheados ----------
@st.cache_resource
def get_clients():
    return LolWatcher(RIOT_API_KEY), MongoClient(MONGO_URI)

watcher, mongo = get_clients()
db = mongo[MONGO_DB]
coll_profiles = db["profiles_cache"]
coll_matches  = db["matches_cache"]

@st.cache_data(show_spinner=False, ttl=300)
def get_summoner_by_name(region, name):
    # cache adicional en Mongo (por si reinicias)
    doc = coll_profiles.find_one({"region": region, "name_lower": name.lower()})
    if doc:
        return doc["data"]
    data = watcher.summoner.by_name(region, name)
    coll_profiles.update_one(
        {"region": region, "name_lower": name.lower()},
        {"$set": {"data": data, "updated_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    return data

@st.cache_data(show_spinner=False, ttl=300)
def get_ranked(region, summoner_id):
    try:
        ranks = watcher.league.by_summoner(region, summoner_id)
    except ApiError:
        return []
    # Sólo SoloQ/Flex
    return [r for r in ranks if r.get("queueType") in ("RANKED_SOLO_5x5","RANKED_FLEX_SR")]

@st.cache_data(show_spinner=False, ttl=300)
def get_recent_match_ids(routing, puuid, count=10):
    return watcher.match.matchlist_by_puuid(routing, puuid, count=count)

@st.cache_data(show_spinner=False, ttl=300)
def get_match(routing, match_id):
    cached = coll_matches.find_one({"_id": match_id})
    if cached:
        return cached["data"]
    data = watcher.match.by_id(routing, match_id)
    coll_matches.update_one({"_id": match_id}, {"$set": {"data": data}}, upsert=True)
    return data

@st.cache_data(show_spinner=False, ttl=15)
def get_live_game(region, summoner_id):
    try:
        return watcher.spectator.by_summoner(region, summoner_id)
    except ApiError:
        return None

def rank_block(ranks):
    solo = next((r for r in ranks if r["queueType"]=="RANKED_SOLO_5x5"), None)
    flex = next((r for r in ranks if r["queueType"]=="RANKED_FLEX_SR"), None)
    def fmt(r):
        if not r: return "Unranked"
        wr = 100 * r["wins"] / (r["wins"] + r["losses"]) if (r["wins"]+r["losses"])>0 else 0
        return f'{r["tier"].title()} {r["rank"]} – {r["leaguePoints"]} LP · {wr:.0f}% WR'
    return fmt(solo), fmt(flex)

def participant_row(match, puuid):
    info = match["info"]
    me = next(p for p in info["participants"] if p["puuid"] == puuid)
    dur = int(info.get("gameDuration", 0))
    mins = dur // 60
    k, d, a = me["kills"], me["deaths"], me["assists"]
    kda = (k + a) / max(1, d)
    champ = me["championName"]
    qid = info.get("queueId", 0)
    result = "W" if me.get("win") else "L"
    start = datetime.fromtimestamp(info["gameStartTimestamp"]/1000, tz=timezone.utc)
    return {
        "match_id": match["metadata"]["matchId"],
        "when": start.astimezone().strftime("%Y-%m-%d %H:%M"),
        "queue": QUEUE_MAP.get(qid, qid),
        "champion": champ,
        "result": result,
        "duration": f"{mins}m",
        "K/D/A": f"{k}/{d}/{a}",
        "KDA": f"{kda:.2f}",
    }

# ---------- UI ----------
st.sidebar.header("Búsqueda")
region = st.sidebar.selectbox("Región", list(REGION_TO_ROUTING.keys()), index=0)
name = st.sidebar.text_input("Invocador", value="MEMENTO MØRI-提莫國王")
auto = st.sidebar.checkbox("Auto-refresh (15s)", value=True)

if st.sidebar.button("Buscar") or name:
    routing, region_label = REGION_TO_ROUTING[region]
    try:
        su = get_summoner_by_name(region, name)
    except ApiError as e:
        st.error(f"No se pudo buscar al invocador: {e}")
        st.stop()

    # Cabecera
    icon_url = f"{CDN}/img/profileicon/{su['profileIconId']}.png"
    col1, col2, col3 = st.columns([2,2,2])
    with col1:
        st.image(icon_url, width=96)
        st.markdown(f"### {su['name']}")
        st.caption(f"Nivel {su['summonerLevel']} · {region_label}")
    ranks = get_ranked(region, su["id"])
    solo_txt, flex_txt = rank_block(ranks)
    with col2:
        st.metric("SoloQ", solo_txt)
        st.metric("Flex",   flex_txt)
    live = get_live_game(region, su["id"])
    with col3:
        if live:
            q = QUEUE_MAP.get(live.get("gameQueueConfigId", 0), "Desconocida")
            st.success(f"**EN PARTIDA** · {q}")
        else:
            st.info("No está en partida")

    st.divider()

    # Últimas partidas
    ids = get_recent_match_ids(routing, su["puuid"], count=10)
    rows = []
    for mid in ids:
        m = get_match(routing, mid)
        rows.append(participant_row(m, su["puuid"]))

    df = pd.DataFrame(rows)
    st.subheader("Últimas partidas")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Campeón + icono en la tabla (opcional: expander rápido)
    with st.expander("Cómo leer la tabla"):
        st.write("Resultado (W/L), duración, K/D/A y KDA. La cola usa el mapeo habitual (420=SoloQ, 440=Flex, etc.).")

    if auto:
        st.caption("Refrescando cada 15s…")
        st.experimental_rerun()
