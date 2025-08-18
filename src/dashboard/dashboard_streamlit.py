# src/dashboard/dashboard_streamlit.py
import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from pymongo import MongoClient
import plotly.express as px

# ==============================
# Config
# ==============================
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin@mongo:27017/lol?authSource=admin")
DB_NAME = os.getenv("MONGO_DB", "lol")
PROCESSED_COLL = os.getenv("MONGO_PROCESSED_COLL", "matches_processed")

# ==============================
# Helpers
# ==============================
@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

@st.cache_data(ttl=60)
def load_processed(limit=2000):
    """
    Carga partidas procesadas y las aplanamos a nivel de participante (una fila por invocador por partida).
    """
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

def escape_powershell_player(player: str) -> str:
    """
    PowerShell necesita escapar el # dentro de comillas con la tilde invertida: `#
    """
    return player.replace("#", "`#")

# ==============================
# UI
# ==============================
st.set_page_config(page_title="LoL Real‑Time Analytics", layout="wide")
st.title("📊 LoL Real‑Time Analytics — Dashboard")

with st.sidebar:
    st.subheader("⚙️ Filtros")
    limit = st.slider("Máx. partidas a cargar", 100, 5000, 1000, step=100)

    st.markdown("---")
    st.subheader("🧰 Backfill de jugador (offline)")
    st.caption("Escribe un Riot ID (gameName#tagLine) y te generamos el comando para ejecutar en **tu terminal**. "
               "Tras ejecutarlo, vuelve y pulsa **Recargar datos**.")

    txt_player = st.text_input("Riot ID (gameName#tagLine)", value="", placeholder="p.ej. MEMENTO MØRI#FLASH")
    region = st.selectbox("Región de enrutado", options=["europe", "americas", "asia"], index=0,
                          help="Para EUW/EUNE/TR/RU usa europe. NA/BR/LAN/LAS usa americas. KR/JP usa asia.")
    count = st.number_input("Nº de partidas a traer", min_value=1, max_value=200, value=50, step=1)

    if txt_player.strip():
        ps_player = escape_powershell_player(txt_player.strip())
        st.markdown("**PowerShell (Windows)**")
        st.code(
f"""docker compose run --rm `
  -e PYTHONPATH=/app/src `
  final-riot-fetcher `
  python -m services.tools.backfill_player `
  --player "{ps_player}" `
  --region {region} `
  --count {count} `
  --api-key "RGAPI-.TU_KEY." """,
            language="powershell"
        )

        st.markdown("**Bash (Linux/Mac/WSL)**")
        st.code(
f"""docker compose run --rm \\
  -e PYTHONPATH=/app/src \\
  final-riot-fetcher \\
  python -m services.tools.backfill_player \\
  --player "{txt_player.strip()}" \\
  --region {region} \\
  --count {count} \\
  --api-key "RGAPI-.TU_KEY." """,
            language="bash"
        )

    if st.button("🔄 Recargar datos"):
        load_processed.clear()
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()

# ==============================
# Datos
# ==============================
df = load_processed(limit=limit)

if df.empty:
    st.info("No hay datos en matches_processed todavía. Usa el generador de comandos en la barra lateral para ingerir partidas de un jugador y luego pulsa **Recargar datos**.")
    st.stop()

# ==============================
# Cabecera / KPIs
# ==============================
players = sorted(df["summonerName"].dropna().unique().tolist())
default_player = players[0] if players else None

with st.sidebar:
    st.markdown("---")
    st.subheader("👤 Filtrar por jugador (en BD)")
    selected_player = st.selectbox("Jugador", options=players, index=players.index(default_player) if default_player else 0)

st.markdown(f"### {selected_player}")

df_player = df[df["summonerName"] == selected_player]
if df_player.empty:
    st.warning("No hay partidas para el jugador seleccionado con los datos actuales.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidas", df_player["match_id"].nunique())
winrate = (df_player["win"].mean() * 100).round(1) if "win" in df_player and not df_player["win"].isna().all() else 0.0
c2.metric("Winrate", f"{winrate}%")
kda_mean = round(df_player["kda"].dropna().mean(), 2) if "kda" in df_player else 0.0
c3.metric("KDA medio", kda_mean)
dur_mean = round(df_player["gameDuration"].dropna().mean()/60, 1) if "gameDuration" in df_player else 0.0
c4.metric("Duración media (min)", dur_mean)

# ==============================
# Campeones más jugados (tabla)
# ==============================
st.subheader("Campeones más jugados")
tbl = (
    df_player.groupby("championName", as_index=False)
    .agg(partidas=("match_id", "nunique"),
         kda=("kda", "mean"),
         winrate=("win", lambda s: float(s.mean()*100)))
    .sort_values(["partidas", "winrate"], ascending=[False, False])
)
st.dataframe(tbl, use_container_width=True)

# ==============================
# Top KDA por campeón (bar)
# ==============================
top_kda = (
    df_player.dropna(subset=["kda"])
    .groupby("championName", as_index=False)["kda"].mean()
    .sort_values("kda", ascending=False)
    .head(10)
)
if not top_kda.empty:
    st.plotly_chart(px.bar(top_kda, x="championName", y="kda", title="Mejor KDA por campeón"), use_container_width=True)

# ==============================
# Duración de partidas (hist)
# ==============================
if "gameDuration" in df_player and not df_player["gameDuration"].dropna().empty:
    dmin = (df_player["gameDuration"] / 60).dropna()
    st.plotly_chart(px.histogram(dmin, nbins=12, title="Duración de partidas (min)"), use_container_width=True)

# ==============================
# Muestra rápida (últimas del jugador)
# ==============================
st.subheader("Muestra rápida de partidas (del jugador)")
quick = (
    df_player.groupby("match_id", as_index=False)
    .agg(
        kda_medio=("kda", "mean"),
        campeones=("championName", lambda s: ", ".join(s.dropna().unique()[:3])),
        win=("win", lambda s: int(s.any())),
    )
    .sort_values("match_id", ascending=False)
    .head(10)
)
st.dataframe(quick, use_container_width=True)

# ==============================
# Detalle (muestra)
# ==============================
st.subheader("Detalle (muestra)")
st.dataframe(df_player.sort_values("match_id", ascending=False).head(25), use_container_width=True)
