# -*- coding: utf-8 -*-
# src/dashboard/utils/riot.py
"""
Utilidades Riot para el dashboard:
- Filtros y helpers comunes
- Iconos de campeones, spells, runas, items
- Funciones usadas por Match History y Champion Stats
"""

from __future__ import annotations
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

from src.dashboard.utils import api_client as api

# -------------------------------------------------
# Colas conocidas (para filtros/etiquetas)
# -------------------------------------------------
QUEUE_OPTION: Dict[int, str] = {
    420: "Ranked Solo/Duo",
    440: "Flex 5v5",
    400: "Normal Draft",
    430: "Normal Blind",
    450: "ARAM",
}
# (versión “string->id” para Champion Stats)
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

# -------------------------------------------------
# Normalización de versión y nombres
# -------------------------------------------------
def normalize_patch(v: Optional[str]) -> str:
    v = v or "14.18.1"
    parts = v.split(".")
    return f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else v

# Algunos nombres “raros” de DDragon
_CHAMP_API_NAME_FIX = {
    "Wukong": "MonkeyKing",
    "LeBlanc": "Leblanc",
    "Nunu & Willump": "Nunu",
    "Renata Glasc": "Renata",
    "Kha'Zix": "Khazix",
    "Vel'Koz": "Velkoz",
    "Cho'Gath": "Chogath",
    "Kai'Sa": "Kaisa",
    "Bel'Veth": "Belveth",
}
def _champ_key(name: str) -> str:
    if not name:
        return "Unknown"
    return _CHAMP_API_NAME_FIX.get(name, name).replace(" ", "")

def champion_icon_url(champ_name: str, patch: Optional[str] = None) -> str:
    """URL del icono de campeón (usa patch si viene, si no 14.18.1)."""
    v = f"{normalize_patch(patch)}.1" if patch and "." in patch else (patch or "14.18.1")
    key = _champ_key(champ_name)
    return f"https://ddragon.leagueoflegends.com/cdn/{v}/img/champion/{key}.png"

def display_name_for_participant(p: Dict[str, Any]) -> str:
    """Prioriza Riot ID (gameName#tagline); si no, summonerName."""
    rid = (p.get("riotIdGameName") or "").strip()
    tag = (p.get("riotIdTagline") or "").strip()
    if rid and tag:
        return f"{rid}#{tag}"
    return p.get("summonerName") or "—"

# -------------------------------------------------
# Spells, Items, Runes
# -------------------------------------------------
# DDragon NO usa IDs numéricos en el nombre del PNG de los spells.
# Mapeamos ID -> filename.
SPELL_ID_TO_FILE: Dict[int, str] = {
    1:  "SummonerBoost",           # Cleanse
    3:  "SummonerExhaust",
    4:  "SummonerFlash",
    6:  "SummonerHaste",           # Ghost
    7:  "SummonerHeal",
    11: "SummonerSmite",
    12: "SummonerTeleport",
    13: "SummonerMana",            # (legacy/ARAM)
    14: "SummonerDot",             # Ignite
    21: "SummonerBarrier",
    30: "SummonerPoroRecall",
    31: "SummonerPoroThrow",
    32: "SummonerSnowball",        # Mark/Dash
    39: "SummonerSnowURFSnowball_Mark",
    54: "Summoner_UltBookPlaceholder",
    55: "Summoner_UltBookSmite",
}

def _spell_img(sid: Optional[int], version: str, size: int) -> str:
    if not sid:
        return ""
    name = SPELL_ID_TO_FILE.get(int(sid))
    if not name:
        return ""
    return (
        f'<img src="https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{name}.png" '
        f'width="{size}" height="{size}" title="{name}"/>'
    )

def _item_img(iid: Optional[int], version: str, size: int) -> str:
    if not iid or int(iid) <= 0:
        return ""
    return (
        f'<img src="https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{int(iid)}.png" '
        f'width="{size}" height="{size}" title="Item {int(iid)}"/>'
    )

# Keystone primaria + icono de la sub-ruta secundaria
def _rune_primary_keystone(perks: Dict[str, Any], size: int) -> str:
    try:
        primary = next(s for s in perks.get("styles", []) if s.get("description") == "primaryStyle")
        icon = (primary.get("selections") or [{}])[0].get("icon")
        if icon:
            return f'<img src="https://ddragon.canisback.com/img/{icon}" width="{size}" height="{size}" title="Keystone"/>'
    except StopIteration:
        pass
    return ""

def _rune_secondary_style(perks: Dict[str, Any], size: int) -> str:
    try:
        secondary = next(s for s in perks.get("styles", []) if s.get("description") == "subStyle")
        style_id = secondary.get("style")
        if style_id:
            return (
                f'<img src="https://ddragon.canisback.com/img/perk-images/Styles/{style_id}.png" '
                f'width="{size}" height="{size}" title="Secondary"/>'
            )
    except StopIteration:
        pass
    return ""

def build_icons_row_html(p: Dict[str, Any], patch: Optional[str] = None, size: int = 20) -> str:
    # Antes:
    # version = patch or "14.18.1"

    # Después (robusto: si viene "14.18" lo convertimos a "14.18.1"):
    version = f"{normalize_patch(patch)}.1" if patch else "14.18.1"

    spells_html = [
        _spell_img(p.get("summoner1Id"), version, size),
        _spell_img(p.get("summoner2Id"), version, size),
    ]
    perks = (p.get("perks") or {})
    runes_html = [
        _rune_primary_keystone(perks, size),
        _rune_secondary_style(perks, size),
    ]
    items_html = [_item_img(p.get(f"item{i}"), version, size) for i in range(7)]
    return "".join([h for h in spells_html + runes_html + items_html if h])


# -------------------------------------------------
# Utilidades de sesión y filtros (Champion Stats)
# -------------------------------------------------
def _load_player_from_session() -> Optional[Dict[str, Any]]:
    """Preferimos st.session_state['player']; soportamos claves antiguas."""
    p = st.session_state.get("player")
    if isinstance(p, dict) and p.get("platform") and p.get("puuid"):
        return p
    platform = st.session_state.get("platform")
    puuid = st.session_state.get("puuid")
    riotid = st.session_state.get("riotid")
    if platform and puuid:
        return {"platform": platform, "puuid": puuid, "riot_id": riotid or ""}
    return None

def _need_player() -> Optional[Dict[str, Any]]:
    p = _load_player_from_session()
    if not p:
        st.warning("No hay jugador cargado. Ve a **01 Summoner Search**.")
        return None
    return p

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

# -------------------------------------------------
# Descarga robusta de partidas (Champion Stats)
# -------------------------------------------------
def _parse_matches_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        return payload.get("matches", payload.get("data", [])) or []
    if isinstance(payload, list):
        return payload
    return []

def _get_full_matches(platform: str, puuid: str, start: int, count: int) -> List[Dict[str, Any]]:
    data = api.get_matches_full_by_puuid(platform, puuid, start, count)
    return _parse_matches_payload(data)

def _progressive_fetch(platform: str, puuid: str, max_games: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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

def _own_participant(match: Dict[str, Any], puuid: str) -> Optional[Dict[str, Any]]:
    for p in match["info"]["participants"]:
        if p.get("puuid") == puuid:
            return p
    return None

# -------------------------------------------------
# KPIs por campeón / rol (Champion Stats)
# -------------------------------------------------
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
            dict(Champ=champ, Games=0, Wins=0, Kills=0, Deaths=0, Assists=0, CS=0, DMG=0, Vision=0, TimeS=0),
        )
        row["Games"] += 1
        if me.get("win"):
            row["Wins"] += 1
        row["Kills"] += me.get("kills", 0)
        row["Deaths"] += me.get("deaths", 0)
        row["Assists"] += me.get("assists", 0)
        row["CS"] += me.get("totalMinionsKilled", 0) + me.get("neutralMinionsKilled", 0)
        row["DMG"] += me.get("totalDamageDealtToChampions", 0)
        row["Vision"] += me.get("visionScore", 0)
        row["TimeS"] += dur_s

    rows = []
    for _, k in agg.items():
        g = k["Games"]
        wr = (100.0 * k["Wins"] / g) if g else 0.0
        kda = (k["Kills"] + k["Assists"]) / (k["Deaths"] if k["Deaths"] else 1)
        cs_min = (k["CS"] / (k["TimeS"] / 60.0)) if k["TimeS"] else 0.0
        dmg_avg = int(k["DMG"] / g) if g else 0
        rows.append(dict(Champ=k["Champ"], Games=g, WR=wr, KDA=kda, CSmin=cs_min, DMG=dmg_avg))

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Games", "WR"], ascending=[False, False], ignore_index=True)
    return df

def _role_summary(matches: List[Dict[str, Any]], puuid: str) -> pd.DataFrame:
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

# -------------------------------------------------
# Mini render (Champion Stats) para tu página 03
# -------------------------------------------------
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
        .tbl-row {display:grid;grid-template-columns: 230px 140px 140px 120px 120px 120px; gap:14px; align-items:center;}
        .tbl-head {font-weight:600; color:#e2e8f0; margin:6px 0 4px;}
        .tbl-cell {font-size:0.95rem; color:#cbd5e1;}
        .tbl-wrap {background:#0f141a;border-radius:10px;padding:14px 16px;}
        .champ {display:flex;gap:10px;align-items:center;}
        .champ img{width:28px;height:28px;border-radius:6px}
        .champ span{color:#e5e7eb}
        </style>
        """,
        unsafe_allow_html=True,
    )

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

        icon = champion_icon_url(champ)
        st.markdown(
            f"""
            <div class="tbl-row">
                <div class="champ"><img src="{icon}" alt="{champ}"/><span>{champ}</span></div>
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

# -------------------------------------------------
# Live
# -------------------------------------------------
def spell_icon_url(sid: int, patch: str | None = None, size: int = 22) -> str:
    """URL del icono de hechizo a partir de su ID numérico."""
    version = f"{normalize_patch(patch)}.1" if patch else "14.18.1"
    name = SPELL_ID_TO_FILE.get(int(sid))
    if not name:
        return ""
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{name}.png"

def champion_icon_by_id_url(cid: int | str, variant: str = "square", size: int = 36) -> str:
    """
    Usa CommunityDragon para icono de campeón a partir del ID:
    variant: 'square' (36x36 aprox) o 'tiles' si quieres otra imagen.
    """
    return f"https://cdn.communitydragon.org/latest/champion/{int(cid)}/{variant}"

# (Opcional) función main para probar esta utilidad como página suelta.
def main():
    st.markdown("<h1>📊 Champion Stats</h1>", unsafe_allow_html=True)
    p = _need_player()
    if not p:
        return

    st.caption(f"Jugador en sesión: **{p.get('riot_id', '')}** · Plataforma **{p['platform']}**")

    c_top = st.columns([2, 3])
    with c_top[0]:
        cola = st.selectbox("Cola a filtrar", list(QUEUE_OPTIONS.keys()), index=0)
    with c_top[1]:
        period = st.radio("Tiempo", ["Toda la season", "Últimos 30 días"], horizontal=True, index=0)

    matches = _progressive_fetch(p["platform"], p["puuid"], max_games=60)

    last30 = period == "Últimos 30 días"
    qsel = QUEUE_OPTIONS[cola]
    matches = [m for m in matches if _filter_by_queue(m, qsel) and _filter_by_time(m, last30)]

    if not matches:
        st.info("Sin partidas para esos filtros.")
        return

    df_champs = _build_champ_rows(matches, p["puuid"])

    with st.expander("Resumen por rol"):
        df_roles = _role_summary(matches, p["puuid"])
        if df_roles.empty:
            st.write("No hay datos de roles.")
        else:
            cols = st.columns(len(df_roles))
            for col, (_, row) in zip(cols, df_roles.iterrows()):
                wr = row["WR"]
                col.metric(f"{row['Role']}", f"{int(row['Games'])}", help="Partidas",
                           delta=f"{wr:.0f}% WR", delta_color="normal")

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
