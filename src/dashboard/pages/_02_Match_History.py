# src/dashboard/pages/_02_Match_History.py
from __future__ import annotations

from typing import Optional, Dict, Any, List
import streamlit as st

from src.dashboard.utils.riot import (
    # API
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    resolve_summoner_name,

    # UI helpers
    queue_name,
    secs_to_str,
    status_label_from_match,
    status_badge_color,

    # DDragon helpers
    ddragon_version_from_match,
    build_runes_spells_items_html,   # (runes + spells + items)
    kda_text,
    cs_text,
    gold_text,
    kp_text,
    dmg_text,
    vision_text,

    # Champ helpers
    load_champions,
    get_champion_image,

    # Filtros y constantes
    QUEUES,
)

# =========================================================
# Helpers de UI
# =========================================================
def _pill(value: str, label: str) -> str:
    return (
        f"<div style='display:flex;flex-direction:column;gap:4px'>"
        f"<div style='font-size:12px;opacity:.7'>{label}</div>"
        f"<div style='padding:8px 12px;border-radius:8px;background:#123018;"
        f"border:1px solid rgba(255,255,255,.08);font-weight:600'>{value}</div>"
        f"</div>"
    )

def _status_badge(text: str) -> str:
    col = status_badge_color(text)
    return (
        f"<div style='padding:8px 18px;border-radius:8px;border:1px solid {col};"
        f"text-align:center'>{text}</div>"
    )

# Fondo suavemente tintado según Win/Lose/Remake
def _status_soft_bg(status: str, base: str = "#141414") -> str:
    s = (status or "").lower()
    if "win" in s:
        tint = "rgba(34,197,94,.08)"
    elif "lose" in s:
        tint = "rgba(239,68,68,.08)"
    elif "remake" in s or "ff" in s:
        tint = "rgba(250,204,21,.10)"
    else:
        tint = "rgba(148,163,184,.06)"
    return f"linear-gradient(0deg,{tint},{tint}), {base}"

def _champion_name_from_map(champion_id: int, champs: dict) -> str:
    """`champs` es { int(key) -> 'LeeSin' }. Devuelve 'LeeSin' o ''."""
    return champs.get(champion_id, "") or ""

def _header_row(match: dict, me: dict, version: str, champs: dict, platform: str) -> None:
    info = match.get("info", {}) or {}
    md = match.get("metadata", {}) or {}
    match_id = md.get("matchId", "—")
    qname = queue_name(int(info.get("queueId", 0)))
    duration = secs_to_str(info.get("gameDuration", 0))
    status = status_label_from_match(match, me)

    # Name (solo nombre del invocador)
    name = resolve_summoner_name(platform, me)

    # Champion (icono + nombre del champ)
    champ_id = me.get("championId")
    champ_icon = get_champion_image(champ_id, champs)
    champ_name = _champion_name_from_map(champ_id, champs)
    champ_cell = (
        f"<div style='display:flex;align-items:center;gap:8px'>"
        f"<img src='{champ_icon}' style='width:20px;height:20px;border-radius:4px'>"
        f"<div style='font-weight:600'>{champ_name}</div></div>"
    )

    # Runes + Spells + Items
    rsi = build_runes_spells_items_html(me, version)

    # Columnas: MatchID | Queue | Name | Champion | Runes/Spells/Items | KDA | CS | Gold | KP | Duration | Status | Patch
    cols = st.columns([1.2, 1.2, 1.7, 1.9, 4.3, 0.9, 0.9, 1.0, 0.9, 1.1, 0.9, 1.0])

    with cols[0]:
        st.caption("Match ID")
        st.markdown(f"<div style='font-weight:600'>{match_id}</div>", unsafe_allow_html=True)
    with cols[1]:
        st.caption("Queue")
        st.markdown(qname)
    with cols[2]:
        st.caption("Name")
        st.markdown(f"<div style='font-weight:600'>{name}</div>", unsafe_allow_html=True)
    with cols[3]:
        st.caption("Champion")
        st.markdown(champ_cell, unsafe_allow_html=True)
    with cols[4]:
        st.caption("Runes • Spells • Items")
        st.markdown(rsi, unsafe_allow_html=True)
    with cols[5]:
        st.caption("KDA")
        st.markdown(f"<div style='font-weight:600'>{kda_text(me)}</div>", unsafe_allow_html=True)
    with cols[6]:
        st.caption("CS")
        st.markdown(f"<div style='font-weight:600'>{cs_text(me)}</div>", unsafe_allow_html=True)
    with cols[7]:
        t100 = [p for p in info.get("participants", []) if p.get("teamId") == 100]
        t200 = [p for p in info.get("participants", []) if p.get("teamId") == 200]
        team_kills = sum(pp.get("kills", 0) for pp in (t100 if me.get("teamId") == 100 else t200))
        st.caption("KP")
        st.markdown(f"<div style='font-weight:600'>{kp_text(me, team_kills)}</div>", unsafe_allow_html=True)
    with cols[8]:
        st.caption("Duration")
        st.markdown(f"<div style='font-weight:600'>{duration}</div>", unsafe_allow_html=True)
    with cols[9]:
        st.caption("Status")
        st.markdown(_status_badge(status), unsafe_allow_html=True)
    with cols[10]:
        st.caption("Patch")
        st.markdown(
            f"<div style='padding:8px 12px;border-radius:8px;background:#0e1f34;"
            f"border:1px solid rgba(255,255,255,.08);font-weight:600'>{version}</div>",
            unsafe_allow_html=True,
        )

def _team_header(title: str, bg: str) -> None:
    st.markdown(
        f"<div style='margin-top:10px;margin-bottom:6px;font-weight:700;color:#cbd5e1'>{title}</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns([2.5, 3.9, 1.1, 0.9, 1.1, 0.9, 0.9, 1.2, 1.0])
    headers = ["Summoner", "Runes • Spells • Items", "KDA", "CS", "Gold", "KP", "DMG", "Vision", "Status"]
    for c, h in zip(cols, headers):
        with c:
            st.markdown(
                f"<div style='background:{bg};padding:8px 10px;border-radius:6px;font-weight:600'>{h}</div>",
                unsafe_allow_html=True,
            )

def _row_for_player(
    p: dict,
    me_puuid: str,
    version: str,
    platform: str,
    champs: dict,
    team_kills: int,
    status_source_match: dict,
) -> None:
    status = status_label_from_match(status_source_match, p)
    row_bg = _status_soft_bg(status, base="#141414")
    left_border = "rgba(56,189,248,.55)" if p.get("puuid") == me_puuid else "transparent"

    name = resolve_summoner_name(platform, p)
    champ_icon = get_champion_image(p.get("championId"), champs)
    name_cell = (
        f"<div style='display:flex;align-items:center;gap:8px'>"
        f"<img src='{champ_icon}' style='width:18px;height:18px;border-radius:4px'>"
        f"<div>{name}</div></div>"
    )

    rsi = build_runes_spells_items_html(p, version)

    cols = st.columns([2.5, 3.9, 1.1, 0.9, 1.1, 0.9, 0.9, 1.2, 1.0])
    with cols[0]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg};"
            f"border-left:4px solid {left_border}'>{name_cell}</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{rsi}</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{kda_text(p)}</div>",
            unsafe_allow_html=True,
        )
    with cols[3]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{cs_text(p)}</div>",
            unsafe_allow_html=True,
        )
    with cols[4]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{gold_text(p)}</div>",
            unsafe_allow_html=True,
        )
    with cols[5]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{kp_text(p, team_kills)}</div>",
            unsafe_allow_html=True,
        )
    with cols[6]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{dmg_text(p)}</div>",
            unsafe_allow_html=True,
        )
    with cols[7]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg}'>{vision_text(p)}</div>",
            unsafe_allow_html=True,
        )
    with cols[8]:
        st.markdown(
            f"<div style='padding:8px 10px;border-radius:6px;background:{row_bg};"
            f"border:1px solid {status_badge_color(status)};text-align:center'>{status}</div>",
            unsafe_allow_html=True,
        )

def _participants_table(match: dict, platform: str, me_puuid: str, version: str, champs: dict) -> None:
    info = match.get("info", {}) or {}
    parts = info.get("participants", []) or []

    t1 = [p for p in parts if p.get("teamId") == 100]
    t2 = [p for p in parts if p.get("teamId") == 200]
    t1_kills = sum(p.get("kills", 0) for p in t1)
    t2_kills = sum(p.get("kills", 0) for p in t2)

    _team_header("Blue Side", "#0b1f3a")
    for p in t1:
        _row_for_player(p, me_puuid, version, platform, champs, t1_kills, match)

    _team_header("Red Side", "#3a0b0b")
    for p in t2:
        _row_for_player(p, me_puuid, version, platform, champs, t2_kills, match)

# =========================================================
# Página
# =========================================================
def main() -> None:
    st.title("Match History")

    summoner = st.session_state.get("summoner")
    if not summoner:
        st.info("Introduce el invocador en la página de búsqueda para cargar su historial.")
        st.stop()

    platform: str = summoner.get("region", "") or summoner.get("platform", "")
    puuid: str = summoner.get("puuid", "")
    if not platform or not puuid:
        st.error("No se encontró región/puuid en sesión. Vuelve a buscar el invocador.")
        st.stop()

    queue_label = st.selectbox("Cola a filtrar", list(QUEUES.keys()), index=0)
    queue_id = QUEUES.get(queue_label, None)
    count = st.slider("Número de partidas", 1, 20, 5)

    # Cargar mapeo de campeones una vez
    try:
        champs = load_champions()
    except Exception:
        champs = {}

    try:
        match_ids = matches_by_puuid(puuid, platform, count=count, queue=queue_id)
    except Exception as e:
        st.error(f"No se pudieron recuperar partidas: {e}")
        st.stop()

    for mid in match_ids:
        try:
            match = match_by_id(platform, mid)
        except Exception as e:
            st.warning(f"No se pudo cargar el match {mid}: {e}")
            continue

        me = find_participant_by_puuid(match, puuid)
        if not me:
            continue

        version = ddragon_version_from_match(match)

        # Cabecera
        _header_row(match, me, version, champs, platform)

        with st.expander(f"  Detalles del Match {mid}", expanded=False):
            _participants_table(match, platform, puuid, version, champs)

        # separador
        st.markdown("<hr style='opacity:.15'>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
