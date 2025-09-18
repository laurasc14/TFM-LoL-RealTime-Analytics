# src/dashboard/pages/_03_Champion_Stats.py
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
import pandas as pd
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8081")

QUEUE_OPTIONS = {
    "Todas": None,
    "SoloQ": 420,
    "Flex": 440,
    "Normals": "normals",  # 400/430
}

ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
ROLE_LABEL = {
    "TOP": "Top",
    "JUNGLE": "Jungle",
    "MIDDLE": "Mid",
    "BOTTOM": "ADC",
    "UTILITY": "Support",
    "NONE": "—",
}


# ------------- helpers de sesión ----------------
def _load_player_from_session() -> Dict[str, Any] | None:
    # Preferimos un objeto compacto en st.session_state["player"]
    p = st.session_state.get("player")
    if isinstance(p, dict) and p.get("platform") and p.get("puuid"):
        return p

    # Retro-compat: llaves antiguas
    platform = st.session_state.get("platform")
    puuid = st.session_state.get("puuid")
    riotid = st.session_state.get("riotid")
    if platform and puuid:
        return {
            "platform": platform,
            "puuid": puuid,
            "riot_id": riotid or "",
        }
    return None


def _need_player() -> Dict[str, Any] | None:
    p = _load_player_from_session()
    if not p:
        st.warning("No hay jugador cargado. Ve a **01 Summoner Search**.")
        return None
    return p


# ------------- filtros ----------------
def _filter_by_queue(m: Dict[str, Any], qsel: Any) -> bool:
    if qsel is None:
        return True
    qid = m["info"].get("queueId")
    if qsel == "normals":
        return qid in (400, 430)
    return qid == qsel


def _filter_by_time(m: Dict[str, Any], last30d: bool) -> bool:
    if not last30d:
        return True
    ts = m["info"].get("gameStartTimestamp")
    if not ts:
        return False
    dt = datetime.utcfromtimestamp(ts / 1000.0)
    return dt >= datetime.utcnow() - timedelta(days=30)


# ------------- backend robusto ----------------
def _parse_matches_payload(payload: Any) -> List[Dict[str, Any]]:
    """
    Normaliza la respuesta del backend a lista de matches.
    Puede venir {"matches": [...]} o directamente [...].
    """
    if isinstance(payload, dict):
        return payload.get("matches", payload.get("data", [])) or []
    if isinstance(payload, list):
        return payload
    return []


def _get_full_matches(platform: str, puuid: str, start: int, count: int) -> List[Dict]:
    url = f"{BACKEND}/match/{platform}/matches_full"
    r = requests.get(url, params={"puuid": puuid, "start": start, "count": count}, timeout=60)
    r.raise_for_status()
    return _parse_matches_payload(r.json())


def _progressive_fetch(platform: str, puuid: str, max_games: int) -> List[Dict]:
    out: List[Dict] = []
    batch = 20
    grabbed = 0
    pb = st.progress(0)
    while grabbed < max_games:
        take = min(batch, max_games - grabbed)
        try:
            chunk = _get_full_matches(platform, puuid, start=grabbed, count=take)
        except requests.HTTPError as e:
            st.error(f"Error al bajar partidas: {e}")
            break

        if not chunk:
            break

        out.extend(chunk)
        grabbed += len(chunk)
        pb.progress(int(100 * grabbed / max_games))
        time.sleep(0.03)

        if len(chunk) < take:
            break

    pb.progress(100)
    return out


def _own_participant(match: Dict[str, Any], puuid: str) -> Dict[str, Any] | None:
    for p in match["info"]["participants"]:
        if p.get("puuid") == puuid:
            return p
    return None


# ------------- KPIs por campeón ----------------
def _build_champ_rows(matches: List[Dict[str, Any]], puuid: str) -> pd.DataFrame:
    agg: Dict[str, Dict[str, Any]] = {}

    for m in matches:
        me = _own_participant(m, puuid)
        if not me:
            continue

        champ = me.get("championName", "Unknown")
        dur_s = m["info"].get("gameDuration", 0)
        if m["info"].get("gameEndTimestamp") and dur_s < 24 * 60 * 60:
            dur_s = int(dur_s)

        row = agg.setdefault(
            champ,
            dict(
                Champ=champ,
                Games=0,
                Wins=0,
                Kills=0,
                Deaths=0,
                Assists=0,
                CS=0,
                DMG=0,
                Vision=0,
                TimeS=0,
            ),
        )
        row["Games"] += 1
        if me.get("win"):
            row["Wins"] += 1
        row["Kills"] += me.get("kills", 0)
        row["Deaths"] += me.get("deaths", 0)
        row["Assists"] += me.get("assists", 0)
        cs = me.get("totalMinionsKilled", 0) + me.get("neutralMinionsKilled", 0)
        row["CS"] += cs
        row["DMG"] += me.get("totalDamageDealtToChampions", 0)
        row["Vision"] += me.get("visionScore", 0)
        row["TimeS"] += dur_s

    rows = []
    for _, k in agg.items():
        g = k["Games"]
        wr = (100.0 * k["Wins"] / g) if g else 0.0
        kda = (k["Kills"] + k["Assists"]) / (k["Deaths"] if k["Deaths"] else 1)
        min_played = (k["TimeS"] / g) / 60.0 if g else 0.0
        cs_min = (k["CS"] / (k["TimeS"] / 60.0)) if k["TimeS"] else 0.0
        dmg_avg = int(k["DMG"] / g) if g else 0
        vision_avg = int(k["Vision"] / g) if g else 0

        rows.append(
            dict(
                Champ=k["Champ"],
                Games=g,
                WR=wr,
                KDA=kda,
                CSmin=cs_min,
                DMG=dmg_avg,
                Vision=vision_avg,
            )
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Games", "WR"], ascending=[False, False], ignore_index=True)
    return df


# ------------- Resumen por roles ----------------
def _role_summary(matches: List[Dict[str, Any]], puuid: str) -> pd.DataFrame:
    # teamPosition del participante: TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY/NONE
    agg: Dict[str, Dict[str, int]] = {}
    for m in matches:
        me = _own_participant(m, puuid)
        if not me:
            continue
        role = me.get("teamPosition", "NONE")
        r = agg.setdefault(role, dict(Games=0, Wins=0))
        r["Games"] += 1
        if me.get("win"):
            r["Wins"] += 1

    rows = []
    for r in ROLE_ORDER + ["NONE"]:
        if r not in agg:
            continue
        g = agg[r]["Games"]
        wr = 100.0 * agg[r]["Wins"] / g if g else 0.0
        rows.append(dict(Role=ROLE_LABEL.get(r, r), Games=g, WR=wr))

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Games", ascending=False, ignore_index=True)
    return df


# ------------- UI: barras estilo Porofessor ----------------
def _bar(value: float, maxv: float, color: str, fmt: str) -> str:
    pct = 0 if maxv <= 0 else int(100 * value / maxv)
    pct = max(0, min(100, pct))
    return f"""
    <div style="width:100%;background:#20262e;border-radius:6px;overflow:hidden;height:14px;position:relative;">
        <div style="width:{pct}%;background:{color};height:100%"></div>
        <div style="position:absolute;top:0;left:6px;font-size:0.72rem;color:#cbd5e1;line-height:14px">{fmt}</div>
    </div>
    """


def _porofessor_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No hay datos para mostrar.")
        return

    max_games = int(df["Games"].max()) if "Games" in df else 0
    st.write(
        """
        <style>
        .tbl-row {display:grid;grid-template-columns: 180px 140px 140px 120px 120px 120px; gap:14px; align-items:center;}
        .tbl-head {font-weight:600; color:#e2e8f0; margin:6px 0 4px;}
        .tbl-cell {font-size:0.95rem; color:#cbd5e1;}
        .tbl-wrap {background:#0f141a;border-radius:10px;padding:14px 16px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # cabecera
    st.markdown(
        """
        <div class="tbl-row tbl-head">
            <div>Campeón</div>
            <div>Jugadas</div>
            <div>WR%</div>
            <div>KDA</div>
            <div>CS / min</div>
            <div>DMG</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write('<div class="tbl-wrap">', unsafe_allow_html=True)
    for _, r in df.iterrows():
        champ = r["Champ"]
        games = int(r["Games"])
        wr = float(r["WR"])
        kda = float(r["KDA"])
        csmin = float(r["CSmin"])
        dmg = int(r["DMG"])

        wrbar = _bar(wr, 100.0, "#22c55e", f"{wr:.1f}%")
        gbar = _bar(games, float(max_games), "#38bdf8", f"{games}")

        st.markdown(
            f"""
            <div class="tbl-row">
                <div class="tbl-cell">{champ}</div>
                <div>{gbar}</div>
                <div>{wrbar}</div>
                <div class="tbl-cell">{kda:.2f}</div>
                <div class="tbl-cell">{csmin:.2f}</div>
                <div class="tbl-cell">{dmg:,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.write("</div>", unsafe_allow_html=True)


# ------------- page ----------------
def main():
    st.markdown("<h1>📊 Champion Stats</h1>", unsafe_allow_html=True)
    p = _need_player()
    if not p:
        return

    st.caption(f"Jugador en sesión: **{p.get('riot_id', '')}** · Plataforma **{p['platform']}**")

    c_top = st.columns([1, 2, 3])
    with c_top[0]:
        max_games = st.number_input("Partidas a analizar", 10, 200, 60, step=10)
    with c_top[1]:
        cola = st.selectbox("Cola a filtrar", list(QUEUE_OPTIONS.keys()), index=0)
    with c_top[2]:
        period = st.radio("Tiempo", ["Toda la season", "Últimos 30 días"], horizontal=True, index=0)

    # Descarga progresiva
    matches = _progressive_fetch(p["platform"], p["puuid"], max_games=max_games)

    # Filtros iguales a Match History
    last30 = period == "Últimos 30 días"
    qsel = QUEUE_OPTIONS[cola]
    matches = [m for m in matches if _filter_by_queue(m, qsel) and _filter_by_time(m, last30)]

    if not matches:
        st.info("Sin partidas para esos filtros.")
        return

    # KPIs por campeón
    df_champs = _build_champ_rows(matches, p["puuid"])

    # Resumen por roles
    with st.expander("Resumen por rol"):
        df_roles = _role_summary(matches, p["puuid"])
        if df_roles.empty:
            st.write("No hay datos de roles.")
        else:
            # Render tipo tarjeta
            cols = st.columns(len(df_roles))
            for col, (_, row) in zip(cols, df_roles.iterrows()):
                wr = row["WR"]
                col.metric(f"{row['Role']}", f"{int(row['Games'])}", help="Partidas",
                           delta=f"{wr:.0f}% WR", delta_color="normal")

    # Encabezado global (coincide con match history porque se filtra igual)
    total = len(matches)
    wins = sum(1 for m in matches if (_own_participant(m, p["puuid"]) or {}).get("win"))
    wr_total = 100.0 * wins / total if total else 0.0
    st.write("")
    s1, s2 = st.columns(2)
    s1.metric("Games", total)
    s2.metric("WR", f"{wr_total:.0f}%")

    st.write("")
    _porofessor_table(df_champs)


if __name__ == "__main__":
    main()
