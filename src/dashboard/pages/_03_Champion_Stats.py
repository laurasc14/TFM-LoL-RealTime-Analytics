# _03_Champion_Stats.py — Champion Stats con roles, emojis y gráficos (fix Arena por-partida)
from __future__ import annotations
from typing import Dict, Any, List
import streamlit as st
import pandas as pd

import src.dashboard.utils.riot as riot

# Referencias seguras al módulo riot
matches_by_puuid = getattr(riot, "matches_by_puuid", None)
match_by_id      = getattr(riot, "match_by_id", None)
find_me          = getattr(riot, "find_participant_by_puuid", None)
load_champions   = getattr(riot, "load_champions", lambda: {})
queue_name       = getattr(riot, "queue_name", lambda q: f"Queue {q}")
season_ts        = getattr(riot, "season_to_date_start_timestamp", lambda: None)
get_champ_img    = getattr(riot, "get_champion_image", None)

st.set_page_config(page_title="Champion Stats", layout="wide")

# Colas que NO tienen rol clásico (mostrar '—')
NO_ROLE_QUEUES = {
    450,   # ARAM
    1700,  # Arena (antiguo/beta)
    1710,  # Arena (actual)
    1300,  # Nexus Blitz
    1400,  # Ultimate Spellbook
    2000, 2010, 2020,  # eventos rotativos
    910, 920           # modos rotativos antiguos
}

def _safe_div(a: float, b: float) -> float:
    b = float(b or 0.0)
    return float(a) / b if b > 0 else 0.0

def _role_of(p: dict, queue_id: int | None) -> str:
    """
    Normaliza el rol del participante:
    - UTILITY  -> SUPPORT
    - BOTTOM/BOT -> ADC
    - Colas sin rol (ARAM, Arena, Nexus Blitz, etc.) -> '—'
    """
    if queue_id in NO_ROLE_QUEUES:
        return "—"

    r = (p.get("teamPosition") or "").upper().strip()
    if r == "UTILITY":
        return "SUPPORT"
    if r == "BOTTOM":
        return "ADC"
    if r in {"TOP", "JUNGLE", "MIDDLE", "SUPPORT", "ADC"}:
        return r

    # Fallbacks si viene vacío
    lane = (p.get("lane") or "").upper().strip()
    if lane in {"MID", "MIDDLE"}:
        return "MIDDLE"
    if lane in {"BOT", "BOTTOM"}:
        return "ADC"
    if lane in {"TOP", "JUNGLE"}:
        return lane
    return "UNKNOWN"

def _role_emoji(role: str) -> str:
    mapping = {
        "TOP": "🛡️",
        "JUNGLE": "🌲",
        "MIDDLE": "🎩",
        "ADC": "🎯",
        "SUPPORT": "💉",
        "—": "🎲",        # ARAM/Arena/rotaciones sin rol
        "UNKNOWN": "❓",
    }
    return mapping.get(role, "❓")

def _team_kills(match: dict, team_id: int) -> int:
    info = match.get("info", {}) or {}
    parts = info.get("participants", []) or []
    return sum(pp.get("kills", 0) for pp in parts if int(pp.get("teamId", 0)) == int(team_id))

def main() -> None:
    st.title("Champion Stats")

    summ = st.session_state.get("summoner")
    if not summ:
        st.info("Primero busca un invocador en **Summoner Search**.")
        st.stop()

    platform = summ.get("region") or summ.get("platform")
    puuid    = summ.get("puuid")
    if not platform or not puuid:
        st.error("Falta región/puuid en sesión.")
        st.stop()

    # --------- Filtros superiores ---------
    QUEUES = getattr(riot, "QUEUES", {
        "Todas": None, "Clasificatoria Solo/Dúo": 420, "Clasificatoria Flexible": 440,
        "Normal Draft": 400, "ARAM": 450, "URF": 1900, "Arena": 1710
    })
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        queue_label = st.selectbox("Cola a analizar", list(QUEUES.keys()), index=0)
        queue_filter_id = QUEUES.get(queue_label, None)  # filtro (puede ser None si 'Todas')
    with c2:
        count = st.slider("Nº partidas a muestrear", 5, 50, 20)
    with c3:
        since_season = st.toggle("Desde inicio de temporada", value=False)

    start_time = None
    if since_season:
        try:
            start_time = season_ts()
        except Exception:
            start_time = None

    # --------- Obtener matches ---------
    try:
        mids = matches_by_puuid(
            puuid, platform, count=count, queue=queue_filter_id, start_time=start_time
        ) if matches_by_puuid else []
    except Exception as e:
        st.error(f"No se pudieron recuperar partidas: {e}")
        st.stop()

    champs_map = load_champions()  # { intKey -> 'Ahri' }
    if not champs_map:
        st.warning("No se pudo cargar el mapa de campeones. Revisa la red o DDragon.")

    # ------------------------------------------------------------
    # Acumuladores por campeón y distribución de roles global
    # ------------------------------------------------------------
    agg: Dict[int, Dict[str, Any]] = {}          # championKey -> métricas agregadas
    roles_count: Dict[int, Dict[str, int]] = {}  # championKey -> { role -> count }
    roles_global: Dict[str, int] = {}            # distribución total por rol

    for mid in mids:
        try:
            m = match_by_id(platform, mid) if match_by_id else None
            if not m:
                continue
        except Exception:
            continue

        info = m.get("info", {}) or {}
        dur_s = int(info.get("gameDuration", 0) or 0)
        dur_m = max(1.0, dur_s / 60.0)

        # ⚠️ Cola real de ESTA partida (clave para Arena/ARAM aunque el filtro sea "Todas")
        queue_id_this_match = int(info.get("queueId", 0) or 0)

        me = find_me(m, puuid) if find_me else None
        if not me:
            continue

        cid = int(me.get("championId", 0))
        team_id = int(me.get("teamId", 0))
        tk = _team_kills(m, team_id)

        kills   = int(me.get("kills", 0))
        deaths  = int(me.get("deaths", 0))
        assists = int(me.get("assists", 0))
        gold    = int(me.get("goldEarned", 0))
        dmg     = int(me.get("totalDamageDealtToChampions", 0))
        vision  = float(me.get("visionScore", 0) or 0.0)
        win     = bool(me.get("win", False))
        role    = _role_of(me, queue_id_this_match)  # <-- detectar rol por partida

        a = agg.setdefault(cid, dict(
            games=0, wins=0,
            kills=0, deaths=0, assists=0,
            cs=0, gold=0, dmg=0, vision=0.0,
            time_min=0.0,
            kp_sum=0.0, dpm_sum=0.0, gpm_sum=0.0, vpm_sum=0.0,
        ))
        a["games"]  += 1
        a["wins"]   += 1 if win else 0
        a["kills"]  += kills
        a["deaths"] += deaths
        a["assists"]+= assists
        a["cs"]     += int(me.get("totalMinionsKilled",0)) + int(me.get("neutralMinionsKilled",0))
        a["gold"]   += gold
        a["dmg"]    += dmg
        a["vision"] += vision
        a["time_min"] += dur_m

        kp = 100.0 * _safe_div(kills + assists, tk)
        a["kp_sum"]  += kp
        a["dpm_sum"] += _safe_div(dmg, dur_m)
        a["gpm_sum"] += _safe_div(gold, dur_m)
        a["vpm_sum"] += _safe_div(vision, dur_m)

        # Roles
        rmap = roles_count.setdefault(cid, {})
        rmap[role] = rmap.get(role, 0) + 1
        roles_global[role] = roles_global.get(role, 0) + 1

    if not agg:
        st.info("Sin datos suficientes para estos filtros.")
        st.stop()

    # Rol principal por campeón
    def _main_role(cid: int) -> str:
        rmap = roles_count.get(cid, {})
        if not rmap:
            return "UNKNOWN"
        role = max(rmap.items(), key=lambda kv: kv[1])[0]
        if role == "UTILITY":
            return "SUPPORT"
        if role in {"BOTTOM", "BOT"}:
            return "ADC"
        return role

    def _champ_name(cid: int) -> str:
        return champs_map.get(int(cid), "") or ""

    def _champ_icon(cid: int) -> str:
        return get_champ_img(int(cid), champs_map) if get_champ_img else ""

    # --------------------- Tabla principal ---------------------
    rows: List[Dict[str, Any]] = []
    for cid, a in agg.items():
        g = max(1, int(a["games"]))
        name = _champ_name(cid)
        icon = _champ_icon(cid)
        combo = (
            f"<div style='display:flex;align-items:center;gap:8px'>"
            f"<img src='{icon}' width='24' height='24' style='border-radius:6px'>"
            f"<span style='font-weight:600'>{name or cid}</span>"
            f"</div>"
        )
        kda = _safe_div(a["kills"] + a["assists"], max(1, a["deaths"]))
        main_role = _main_role(cid)
        rows.append({
            "Champion": combo,
            "Games": g,
            "Winrate": round(100.0 * a["wins"] / g, 1),
            "KDA": round(kda, 2),
            "KP%": round(a["kp_sum"] / g, 1),
            "DPM": round(a["dpm_sum"] / g, 1),
            "GPM": round(a["gpm_sum"] / g, 1),
            "Vision/min": round(a["vpm_sum"] / g, 2),
            "Avg CS": round(a["cs"] / g, 1),
            "Avg Gold": round(a["gold"] / g),
            "Avg DMG": round(a["dmg"] / g),
            "Main Role": f"{_role_emoji(main_role)} {main_role}",
        })

    df = pd.DataFrame(rows)
    df_sorted = df.sort_values(["Games", "Winrate"], ascending=[False, False])

    st.markdown(
        f"### Rendimiento por campeón — {queue_label}"
        + (" — desde inicio de temporada" if since_season else "")
    )
    st.write(df_sorted.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.caption("KP%: participación en asesinatos. DPM/GPM/Vision/min calculados por partida y promediados por campeón.")

    # --------------------- Visuales rápidas ---------------------
    st.markdown("### Vistas rápidas")
    cA, cB = st.columns(2)

    with cA:
        top_games = df.sort_values("Games", ascending=False).head(8)[["Champion", "Games"]].copy()
        top_games["Name"] = top_games["Champion"].str.replace(r"<.*?>", "", regex=True)
        tg = top_games.set_index("Name")["Games"]
        st.bar_chart(tg, height=260, use_container_width=True)
        st.caption("Top campeones por nº de partidas.")

    with cB:
        eligible = df[df["Games"] >= 3].copy()
        if not eligible.empty:
            top_wr = eligible.sort_values("Winrate", ascending=False).head(8)[["Champion", "Winrate"]]
            top_wr["Name"] = top_wr["Champion"].str.replace(r"<.*?>", "", regex=True)
            tw = top_wr.set_index("Name")["Winrate"]
            st.bar_chart(tw, height=260, use_container_width=True)
            st.caption("Mejor Winrate (≥ 3 partidas).")
        else:
            st.info("No hay suficientes partidas (≥ 3) para mostrar top por winrate.")

    # --------------------- Distribución de roles ---------------------
    st.markdown("### Distribución de roles")
    roles_plot = {r: c for r, c in roles_global.items()}
    if roles_plot:
        ordered = ["TOP", "JUNGLE", "MIDDLE", "ADC", "SUPPORT", "—", "UNKNOWN"]
        data = [(r, roles_plot.get(r, 0)) for r in ordered if roles_plot.get(r, 0) > 0]
        labels = [f"{_role_emoji(r)} {r}" for r, _ in data]
        values = [v for _, v in data]
        try:
            import plotly.express as px
            fig = px.pie(names=labels, values=values, hole=0.35)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            ddf = pd.DataFrame({"Role": labels, "Games": values}).set_index("Role")
            st.bar_chart(ddf, use_container_width=True, height=280)
    else:
        st.info("No hay datos de roles para esta selección.")

    st.caption("Roles por partida detectados con su cola real. Modos sin rol (ARAM/Arena/NB/US, etc.) → 🎲 —.")

if __name__ == "__main__":
    main()
