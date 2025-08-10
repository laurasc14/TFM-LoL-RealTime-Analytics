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

# ---------- DB helpers ----------
@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

@st.cache_data(ttl=60)
def load_processed(limit=5000):
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
        # si en el futuro guardas "teamId": 1, inclúyelo aquí y lo usamos
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
                # "teamId": p.get("teamId")  # opcional si lo añades después
            })
    return pd.DataFrame(rows)

def normalize_name(s: str) -> str:
    return (s or "").strip()

# ---------- UI ----------
st.set_page_config(page_title="LoL Real‑Time Analytics", layout="wide")
st.title("📊 LoL Real‑Time Analytics — Perfil de Jugador")

with st.sidebar:
    st.subheader("⚙️ Filtros")
    limit = st.slider("Máx. partidas a cargar", 200, 10000, 2000, step=200)
    df = load_processed(limit=limit)

    if df.empty:
        st.info("No hay datos todavía en matches_processed.")
        st.stop()

    # selector rápido + entrada manual
    nombres = sorted([n for n in df["summonerName"].dropna().unique() if n])
    prefill = os.getenv("SUMMONER_NAME", "")
    sel = st.selectbox("Elegir jugador (detectado en BD):", ["(escribe manualmente)"] + nombres, index=0)
    manual = st.text_input("…o escribe SummonerName#Tag", value=prefill)

    player = manual if sel == "(escribe manualmente)" else sel
    player = normalize_name(player)

    if not player:
        st.warning("Introduce un SummonerName#Tag o elige uno del selector.")
        st.stop()

# ---------- Filtrado por jugador ----------
df_player = df[df["summonerName"].str.casefold() == player.casefold()].copy()
if df_player.empty:
    st.error(f"No se encontraron partidas para **{player}**.")
    st.stop()

# KPIs
games = df_player["match_id"].nunique()
wins = int(df_player["win"].sum())  # cada fila es un participante (el propio), win=True/False
winrate = round(wins / games * 100, 1) if games else 0.0
kda_mean = round(df_player["kda"].dropna().mean(), 2) if "kda" in df_player else 0.0
avg_dur = round((df_player["gameDuration"].dropna().mean() or 0) / 60, 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidas", games)
c2.metric("Winrate", f"{winrate} %")
c3.metric("KDA medio", kda_mean)
c4.metric("Duración media (min)", avg_dur)

st.markdown(f"### 👤 {player}")

# Campeones más jugados (y su KDA)
champ_usage = (df_player.groupby("championName", as_index=False)
               .agg(partidas=("match_id", "nunique"),
                    kda_medio=("kda", "mean"),
                    wins=("win", "sum"))
               .sort_values(["partidas", "kda_medio"], ascending=[False, False]))
champ_usage["kda_medio"] = champ_usage["kda_medio"].round(2)
st.plotly_chart(px.bar(champ_usage.head(10), x="championName", y="partidas",
                       hover_data=["kda_medio", "wins"],
                       title="Top campeones más jugados (hover → KDA/Wins)"),
                use_container_width=True)

# KDA medio por campeón
champ_kda = (df_player.dropna(subset=["kda"])
             .groupby("championName", as_index=False)["kda"].mean()
             .sort_values("kda", ascending=False)
             .head(10))
st.plotly_chart(px.bar(champ_kda, x="championName", y="kda",
                       title="Mejor KDA por campeón"),
                use_container_width=True)

# ---------- Últimas partidas (con compañeros) ----------
st.subheader("🧑‍🤝‍🧑 Compañeros por partida (últimas 10)")

# Para cada partida del jugador, extraemos a sus compañeros.
# Heurística: compañeros = participantes del mismo match con el mismo resultado 'win' que el jugador y distinto nombre.
# (Cuando dispongamos de teamId, sustituimos esta heurística por teamId igual.)
rows = []
last_matches = (df_player.sort_values("match_id", ascending=False)["match_id"].unique())[:10]

for mid in last_matches:
    p_slice = df_player[df_player["match_id"] == mid]
    if p_slice.empty:
        continue
    p_win = bool(p_slice.iloc[0]["win"])

    same_match = df[df["match_id"] == mid]
    teammates = same_match[
        (same_match["summonerName"].str.casefold() != player.casefold()) &
        (same_match["win"] == p_win)
    ]

    mate_list = [
        f"{r['summonerName']} ({r.get('championName', '-')}, KDA {r.get('kda', '-')})"
        for _, r in teammates.iterrows()
    ]

    # datos del propio jugador en esa partida (campeón, kda)
    me = p_slice.iloc[0]
    rows.append({
        "match_id": mid,
        "resultado": "Win" if p_win else "Loss",
        "tu_campeon": me.get("championName", "-"),
        "tu_KDA": me.get("kda", "-"),
        "duración_min": round((float(me.get("gameDuration", 0)) or 0) / 60, 1),
        "compañeros": ",  ".join(mate_list) if mate_list else "(no disponible)"
    })

df_matches = pd.DataFrame(rows)
st.dataframe(df_matches, use_container_width=True)

# ---------- Histograma duración (solo del jugador) ----------
if "gameDuration" in df_player:
    dmin = (df_player["gameDuration"] / 60).dropna()
    st.plotly_chart(px.histogram(dmin, nbins=20,
                                 title="Histograma de duración de partidas (del jugador)"),
                    use_container_width=True)
