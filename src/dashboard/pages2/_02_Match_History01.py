# src/dashboard/pages/_02_Match_History01.py
from __future__ import annotations

import os
import math
import requests
from datetime import datetime, timezone, timedelta

import streamlit as st
from src.dashboard.utils import riot

# ================================================================
# Config
# ================================================================
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8081")

QUEUES = {
    "Todas": None,
    "Solo/Dúo": 420,
    "Flex": 440,
    "Normal Draft": 400,
    "ARAM": 450,
}
RANGE_OPTS = {"Toda la season": "season", "Últimos 30 días": "30d"}

QUEUE_NAMES = {
    420: "Solo/Dúo",
    440: "Flex",
    400: "Normal Draft",
    450: "ARAM",
}

# ================================================================
# Helpers
# ================================================================
def queue_name(qid: int | None) -> str:
    if qid is None:
        return "Desconocida"
    return QUEUE_NAMES.get(qid, str(qid))


def utc_str(ms: int) -> str:
    """gameStartTimestamp suele venir en milisegundos."""
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def duration_str(x: int | None) -> str:
    """Acepta duración en segundos o milisegundos (robusto)."""
    if not x:
        return "-"
    secs = int(x if x < 100_000 else x // 1000)
    m, s = divmod(secs, 60)
    return f"{m}m {s:02d}s"


def since_from_range(label: str) -> int:
    """Devuelve timestamp (segundos) de inicio del rango elegido."""
    if RANGE_OPTS.get(label) == "30d":
        return int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    # Inicio de la temporada/dataset (ajústalo si te conviene)
    return 1735689600  # 2025-01-01 00:00:00 UTC


def fmt_kda(k: int, d: int, a: int) -> str:
    ratio = (k + a) / max(1, d)
    return f"{k}/{d}/{a} ({ratio:.2f})" if d > 0 else f"{k}/{d}/{a} (∞)"


def participants_by_team(info: dict):
    parts = info.get("participants", []) or []
    blue = [p for p in parts if p.get("teamId") == 100]
    red = [p for p in parts if p.get("teamId") == 200]
    return blue, red


def team_kills(info: dict, team_id: int) -> int:
    ps = [p for p in info.get("participants", []) if p.get("teamId") == team_id]
    return sum(p.get("kills", 0) for p in ps)


def team_result(info: dict, team_id: int) -> bool:
    """True si ganó ese equipo, False si perdió (maneja boolean/string)."""
    for t in info.get("teams", []) or []:
        if t.get("teamId") == team_id:
            w = t.get("win")
            if isinstance(w, bool):
                return w
            if isinstance(w, str):
                return w.lower() in ("win", "true")
    # fallback: por si no viene la sección teams
    blue_k = team_kills(info, 100)
    red_k = team_kills(info, 200)
    if team_id == 100:
        return blue_k >= red_k
    return red_k >= blue_k


def kp_str(p: dict, team_k: int) -> str:
    return f"{round(100 * (p.get('kills', 0) + p.get('assists', 0)) / max(1, team_k))}%"


# ================================================================
# Data
# ================================================================
@st.cache_data(show_spinner=False, ttl=60)
def fetch_matches(since_s: int, limit: int = 1000):
    r = requests.get(
        f"{BACKEND_URL}/matches_full",
        params={"since": since_s, "limit": limit},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items", data)
    # Orden descendente por inicio
    items.sort(key=lambda x: x.get("info", {}).get("gameStartTimestamp", 0), reverse=True)
    return items


# ================================================================
# UI
# ================================================================
def main():
    st.title("📜 Match History")
    st.caption(f"Backend: [{BACKEND_URL}]({BACKEND_URL})")

    c1, c2 = st.columns(2)
    queue_label = c1.selectbox("Cola a filtrar", list(QUEUES.keys()), index=0)
    range_label = c2.selectbox("Rango de partidas", list(RANGE_OPTS.keys()), index=0)

    c3, c4 = st.columns(2)
    per_page = c3.selectbox("Por página", [10, 25, 50, 100], index=1)
    page = c4.number_input("Página", min_value=1, step=1, value=1)

    # CSS — grid + badges + cabecera
    st.markdown(
        """
<style>
  .mh-headerbar{
    display:flex; gap:12px; align-items:center; flex-wrap:wrap;
    padding:10px 12px; border:1px solid #2b2f36; border-radius:10px;
    background: linear-gradient(90deg, #101419, #11161c);
    margin: 6px 0 12px 0;
  }
  .mh-h-title{ font-weight:800; font-size:1.05rem; color:#f5f7fb; }
  .tag{
    display:inline-flex; align-items:center; gap:6px;
    padding:4px 10px; border-radius:999px; font-weight:700; font-size:.80rem;
    border:1px solid #2b2f36; background:#141a21; color:#cdd3dd;
  }
  .tag.queue{ background:#0f1520; color:#d1e8ff; border-color:#223145; }
  .tag.time{ background:#141a1a; color:#ffd8a8; border-color:#3d2f1f; }
  .tag.dur{ background:#141a18; color:#c7f9cc; border-color:#2d4a3b; }
  .tag.patch{ background:#17141a; color:#eebefa; border-color:#3c2a48; }

  .mh-sidehead{ display:flex; align-items:center; gap:10px; margin: 10px 0 6px 0; }
  .pill{
    padding: 2px 10px; border-radius: 999px; font-size: .85rem; font-weight: 800;
  }
  .pill.win  { background:#1f3328; border:1px solid #2f4f3e; color:#dff2e1; }
  .pill.lose { background:#3a1f22; border:1px solid #51262b; color:#ffd6d9; }

  .mh-header {
    display: grid;
    grid-template-columns: 220px 1fr 140px 70px 80px 70px 70px;
    gap: 12px; align-items: center; margin: 4px 0 6px 0; color: #aeb3bc;
    font-weight: 700;
  }
  .mh-row {
    display: grid;
    grid-template-columns: 220px 1fr 140px 70px 80px 70px 70px;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid #2b2f36;
    border-radius: 10px;
    background: #11151a;
    margin-bottom: 8px;
  }
  .mh-name {
    display:flex; align-items:center; gap:8px; font-weight:700;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
  }
  .mh-name img{ border-radius:6px; }
  .mh-icons{ display:flex; align-items:center; gap:6px; }
  .mh-stat{ text-align:right; font-variant-numeric:tabular-nums; }
</style>
        """,
        unsafe_allow_html=True,
    )

    # Rango temporal
    since_s = since_from_range(range_label)

    # Datos
    try:
        all_matches = fetch_matches(since_s, 1000)
    except Exception as e:
        st.error(f"El backend no responde: {e}")
        st.stop()

    # Filtro por cola
    qid = QUEUES[queue_label]
    matches = [m for m in all_matches if qid is None or m.get("info", {}).get("queueId") == qid]

    # Paginación
    total = len(matches)
    pages = max(1, math.ceil(total / per_page))
    page = min(max(1, page), pages)
    st.write(f"Encontradas (aprox): **{total}** · Página **{page}/{pages}**")

    start = (page - 1) * per_page
    end = start + per_page
    page_matches = matches[start:end]

    # Render
    for m in page_matches:
        info = m.get("info", {}) or {}
        match_id = m.get("match_id", "unknown")

        qname = queue_name(info.get("queueId"))
        start_utc = utc_str(info.get("gameStartTimestamp", 0))
        duration = duration_str(info.get("gameDuration", 0))
        patch_norm = riot.normalize_patch(info.get("gameVersion", ""))

        blue, red = participants_by_team(info)
        blue_tk = team_kills(info, 100)
        red_tk = team_kills(info, 200)
        blue_win = team_result(info, 100)
        red_win = team_result(info, 200)

        with st.expander(f"Detalles del Match {match_id}", expanded=False):
            # Cabecera con badges
            st.markdown(
                f"""
<div class="mh-headerbar">
  <div class="mh-h-title">Match: <code>{match_id}</code></div>
  <div class="tag queue">Cola: {qname}</div>
  <div class="tag time">Inicio (UTC): {start_utc}</div>
  <div class="tag dur">Duración: {duration}</div>
  <div class="tag patch">Patch: {patch_norm}</div>
</div>
                """,
                unsafe_allow_html=True,
            )

            left, right = st.columns(2)

            def draw_side(col, parts, tk, label, won):
                with col:
                    st.markdown(
                        f"""
<div class="mh-sidehead">
  <div class="mh-h-title">{label}</div>
  <span class="pill {'win' if won else 'lose'}">{'Victoria' if won else 'Derrota'}</span>
</div>
<div class='mh-header'>
  <div>Summoner</div><div>Runes · Spells · Items</div><div>KDA</div><div>CS</div><div>Gold</div><div>KP</div><div>Vision</div>
</div>
                        """,
                        unsafe_allow_html=True,
                    )

                    for p in parts:
                        champ = p.get("championName", "Unknown")
                        icon_url = riot.champion_icon_url(champ, patch_norm)
                        summ = riot.display_name_for_participant(p, champ)
                        icons_html = riot.build_icons_row_html(p, patch_norm, size=22)

                        k, d, a = p.get("kills", 0), p.get("deaths", 0), p.get("assists", 0)
                        cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
                        gold = p.get("goldEarned", 0)
                        kda_txt = fmt_kda(k, d, a)
                        kp_txt = kp_str(p, tk)
                        vision = p.get("visionScore", 0)

                        st.markdown(
                            f"""
<div class="mh-row">
  <div class="mh-name"><img src="{icon_url}" width="26" height="26"/> {summ}</div>
  <div class="mh-icons">{icons_html}</div>
  <div class="mh-stat">{kda_txt}</div>
  <div class="mh-stat">{cs}</div>
  <div class="mh-stat">{gold}</div>
  <div class="mh-stat">{kp_txt}</div>
  <div class="mh-stat">{vision}</div>
</div>
                            """,
                            unsafe_allow_html=True,
                        )

            draw_side(left, blue, blue_tk, "Blue Side", blue_win)
            draw_side(right, red, red_tk, "Red Side", red_win)


if __name__ == "__main__":
    main()
