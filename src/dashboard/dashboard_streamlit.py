import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from pymongo import MongoClient
import plotly.express as px

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin@mongo:27017/lol?authSource=admin")
DB_NAME = os.getenv("MONGO_DB", "lol")
PROCESSED_COLL = os.getenv("MONGO_PROCESSED_COLL", "matches_processed")

@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

@st.cache_data(ttl=60)
def load_processed(limit=2000):
    db = get_db()
    cur = db[PROCESSED_COLL].find({}, {
        "_id": 0,
        "match_id": 1,
        "gameMode": 1,
        "gameDuration": 1,
        "participants.summonerName": 1,
        "participants.kills": 1,
        "participants.deaths": 1,
        "participants.assists": 1,
        "participants.kda": 1,
        "participants.championName": 1,
        "participants.win": 1
    }).limit(limit)
    docs = list(cur)
    rows = []
    for d in docs:
        for p in d.get("participants", []):
            rows.append({
                "match_id": d.get("match_id"),
                "gameMode": d.get("gameMode"),
                "gameDuration": d.get("gameDuration"),
                "summonerName": p.get("summonerName"),
                "championName": p.get("championName"),
                "kills": p.get("kills"),
                "deaths": p.get("deaths"),
                "assists": p.get("assists"),
                "kda": p.get("kda"),
                "win": p.get("win"),
            })
    return pd.DataFrame(rows)

st.set_page_config(page_title="LoL Real‑Time Analytics", layout="wide")
st.title("📊 LoL Real‑Time Analytics — Dashboard")

with st.sidebar:
    st.subheader("⚙️ Filtros")
    limit = st.slider("Máx. partidas a cargar", 100, 5000, 1000, step=100)

df = load_processed(limit=limit)

if df.empty:
    st.info("No hay datos en matches_processed todavía.")
    st.stop()

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidas", df["match_id"].nunique())
c2.metric("Invocadores", df["summonerName"].nunique())
c3.metric("KDA medio", round(df["kda"].dropna().mean(), 2))
c4.metric("Duración media (min)", round(df["gameDuration"].dropna().mean()/60, 1) if "gameDuration" in df else 0)

# Top campeones por KDA
champ_kda = df.dropna(subset=["kda"]).groupby("championName", as_index=False)["kda"].mean().sort_values("kda", ascending=False).head(10)
st.plotly_chart(px.bar(champ_kda, x="championName", y="kda", title="Top 10 campeones por KDA medio"), use_container_width=True)

# Top invocadores por winrate (mín 3 partidas)
wins = df.groupby(["summonerName"], as_index=False).agg(
    wins=("win", lambda s: int(s.sum())),
    total=("win", "count")
)
wins = wins[wins["total"] >= 3]
wins["winrate"] = (wins["wins"] / wins["total"] * 100).round(1)
wins = wins.sort_values(["winrate", "total"], ascending=[False, False]).head(10)
st.plotly_chart(px.bar(wins, x="summonerName", y="winrate", hover_data=["total","wins"], title="Top invocadores por winrate (mín 3 partidas)"), use_container_width=True)

# Histograma duración
if "gameDuration" in df:
    dmin = (df["gameDuration"] / 60).dropna()
    st.plotly_chart(px.histogram(dmin, nbins=20, title="Histograma de duración (min)"), use_container_width=True)

# Tabla detalle
st.subheader("Detalle (muestra)")
st.dataframe(df.sample(min(len(df), 50)))
