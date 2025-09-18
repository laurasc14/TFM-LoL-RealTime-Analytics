# src/dashboard/pages/_02_Match_History.py
from __future__ import annotations

from datetime import datetime, timezone
import streamlit as st

from src.dashboard.utils.api_client import (
    BACKEND_URL,
    get_matches_full_by_puuid,
)

# ----------------- Imports robustos (con fallback) -----------------
try:
    from src.dashboard.utils import riot as riot_utils  # type: ignore

    QUEUE_OPTION = getattr(
        riot_utils,
        "QUEUE_OPTION",
        {
            420: "Ranked Solo/Duo",
            440: "Flex 5v5",
            400: "Normal Draft",
            430: "Normal Blind",
            450: "ARAM",
        },
    )

    normalize_patch = getattr(
        riot_utils,
        "normalize_patch",
        lambda v: (v or "14.18.1").split(".")[0] + "." + (v or "14.18.1").split(".")[1],
    )

    champion_icon_url = getattr(
        riot_utils,
        "champion_icon_url",
        lambda champ, patch=None: f"https://ddragon.leagueoflegends.com/cdn/14.18.1/img/champion/{champ}.png",
    )

    build_icons_row_html = getattr(
        riot_utils,
        "build_icons_row_html",
        lambda p, patch=None, size=20: "",
    )

    display_name_for_participant = getattr(
        riot_utils,
        "display_name_for_participant",
        lambda p: f"{p.get('riotIdGameName','')}{('#'+p.get('riotIdTagline','')) if p.get('riotIdTagline') else ''}".strip()
        or p.get("summonerName", "—"),
    )

except Exception:
    QUEUE_OPTION = {
        420: "Ranked Solo/Duo",
        440: "Flex 5v5",
        400: "Normal Draft",
        430: "Normal Blind",
        450: "ARAM",
    }

    def normalize_patch(v: str | None) -> str:
        v = v or "14.18.1"
        parts = v.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return v

    def champion_icon_url(champ: str, patch: str | None = None) -> str:
        return f"https://ddragon.leagueoflegends.com/cdn/14.18.1/img/champion/{champ}.png"

    def build_icons_row_html(p, patch: str | None = None, size: int = 20) -> str:
        return ""

    def display_name_for_participant(p):
        rid = p.get("riotIdGameName")
        tag = p.get("riotIdTagline")
        if rid and tag:
            return f"{rid}#{tag}"
        return p.get("summonerName", "—")


# ---------- UI helpers ----------
def _pill(text: str, bg: str, fg: str = "#fff", px: int = 8, py: int = 2, radius: int = 999) -> str:
    return (
        f'<span style="background:{bg};color:{fg};padding:{py}px {px}px;'
        f'border-radius:{radius}px;font-weight:600;white-space:nowrap;">{text}</span>'
    )

def _result_colors(win: bool | None) -> tuple[str, str]:
    if win is True:
        return ("linear-gradient(90deg,#123b1e,#0f5132)", "#d1f8e1")
    if win is False:
        return ("linear-gradient(90deg,#3b1212,#842029)", "#ffd3d6")
    return ("linear-gradient(90deg,#20232b,#2f3542)", "#d5d8e0")

def _result_symbol(win: bool | None) -> str:
    if win is True:
        return "🟢"
    if win is False:
        return "🔴"
    return "⚪"

def _status_badge(win: bool | None) -> str:
    if win is True:
        return _pill("Win", "#0d6efd33", "#9ad1ff")
    if win is False:
        return _pill("Lose", "#dc354533", "#ffb7c0")
    return _pill("Remake", "#6c757d33", "#d0d5db")

def _queue_badge(queue_id: int | None) -> str:
    name = QUEUE_OPTION.get(int(queue_id), "Custom/Other" if queue_id else "Unknown")
    return _pill(name, "#343a40", "#e6e6e6", px=10, py=3)

def _fmt_pct(x: float | int | None) -> str:
    try:
        if x is None:
            return "-"
        return f"{round(float(x) * 100) if float(x) <= 1 else int(x)}%"
    except Exception:
        return "-"

def _minutes_secs(seconds: int) -> str:
    m, s = divmod(int(seconds or 0), 60)
    return f"{m}m {s:02d}s"

def _safe_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _get_session_identity():
    puuid = st.session_state.get("puuid") or st.session_state.get("summoner_puuid") or (
        st.session_state.get("player") or {}
    ).get("puuid")
    platform = st.session_state.get("platform") or st.session_state.get("summoner_platform") or (
        st.session_state.get("player") or {}
    ).get("platform")
    return platform, puuid


# ---------- KPI (Games y WR) ----------
def _kpi_wr(matches: list[dict], my_puuid: str) -> tuple[int, float]:
    games = 0
    wins = 0
    for m in matches or []:
        info = m.get("info", {})
        meta = m.get("metadata", {})
        if (info.get("gameDuration") or 0) < 300:
            continue
        parts = info.get("participants", [])
        try:
            idx_me = meta.get("participants", []).index(my_puuid)
        except Exception:
            idx_me = 0
        if idx_me < len(parts):
            me = parts[idx_me]
            games += 1
            if me.get("win"):
                wins += 1
    wr = (wins / games) if games else 0.0
    return games, wr


# ---------- Result helpers ----------
def _my_result(m: dict, my_puuid: str) -> bool | None:
    info = m.get("info", {})
    meta = m.get("metadata", {})
    duration = info.get("gameDuration") or 0
    if duration < 300:
        return None
    parts = info.get("participants", [])
    try:
        idx_me = meta.get("participants", []).index(my_puuid)
    except Exception:
        idx_me = 0
    me = parts[idx_me] if idx_me < len(parts) else {}
    return True if me.get("win") else False


# ---------- Render de filas / equipos ----------
def _row_html(p: dict, patch: str) -> str:
    name = display_name_for_participant(p)
    champ = p.get("championName") or "Unknown"
    champ_url = champion_icon_url(champ, patch)
    kda = f"{_safe_int(p.get('kills'))}/{_safe_int(p.get('deaths'))}/{_safe_int(p.get('assists'))}"
    cs = _safe_int(p.get("totalMinionsKilled")) + _safe_int(p.get("neutralMinionsKilled"))
    team_dmg = _safe_int(p.get("totalDamageDealtToChampions"))
    gold = _safe_int(p.get("goldEarned"))
    vis = _safe_int(p.get("visionScore"))
    kp = p.get("challenges", {}).get("killParticipation", None)
    kp_txt = _fmt_pct(kp)

    icons = build_icons_row_html(p, patch=patch, size=20)
    icons_html = (
        '<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;max-width:300px">'
        f"{icons}</div>"
    )

    return f"""
    <div style="display:grid;
                grid-template-columns:240px 300px repeat(6,72px);
                gap:8px;align-items:center;
                padding:6px 8px;border-radius:8px;background:#0f141a;">
        <div style="display:flex;align-items:center;gap:8px;">
            <img src="{champ_url}" width="24" height="24" style="border-radius:7px;opacity:.95"/>
            <div style="display:flex;flex-direction:column;line-height:1.1">
                <span style="font-weight:700;color:#e9eef5">{name}</span>
                <span style="opacity:.65;font-size:12px">{champ}</span>
            </div>
        </div>
        {icons_html}
        <div style="text-align:center">{kda}</div>
        <div style="text-align:center">{cs}</div>
        <div style="text-align:center">{kp_txt}</div>
        <div style="text-align:center">{gold:,}</div>
        <div style="text-align:center">{team_dmg:,}</div>
        <div style="text-align:center">{vis}</div>
    </div>
    """

def _team_block_html(title: str, team_players: list[dict], patch: str, win: bool) -> str:
    head_badge = _pill("Win" if win else "Lose", "#0d6efd33" if win else "#dc354533", "#bfe5ff" if win else "#ffb7c0")
    rows = "\n".join(_row_html(p, patch) for p in team_players)
    return f"""
        <div style="display:flex;flex-direction:column;gap:6px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">
                <span style="font-size:20px;font-weight:800;color:#eaeef3">{title}</span>
                {head_badge}
            </div>
            <div style="display:grid;
                        grid-template-columns:240px 300px repeat(6,72px);
                        gap:8px;opacity:.78;font-size:12px">
                <div>Summoner</div><div>Runes · Spells · Items</div>
                <div style="text-align:center">KDA</div>
                <div style="text-align:center">CS</div>
                <div style="text-align:center">KP</div>
                <div style="text-align:center">Gold</div>
                <div style="text-align:center">DMG</div>
                <div style="text-align:center">Vision</div>
            </div>
            {rows}
        </div>
    """

# ---------- Render de una partida ----------
def render_match_block(m: dict, my_puuid: str):
    info = m.get("info", {})
    meta = m.get("metadata", {})

    patch = normalize_patch(info.get("gameVersion"))
    gid = meta.get("matchId") or info.get("gameId")
    game_start_ms = info.get("gameStartTimestamp") or 0
    game_start = datetime.fromtimestamp(game_start_ms / 1000, tz=timezone.utc)
    duration_s = info.get("gameDuration") or 0
    queue_id = info.get("queueId")
    q_badge = _queue_badge(queue_id)

    participants = info.get("participants", [])
    try:
        idx_me = meta.get("participants", []).index(my_puuid)
    except Exception:
        idx_me = 0
    me = participants[idx_me] if idx_me < len(participants) else {}
    my_win = me.get("win", None)
    if duration_s and duration_s < 300:
        my_win = None

    blue = [p for p in participants if p.get("teamId") == 100]
    red = [p for p in participants if p.get("teamId") == 200]
    blue_win = any(p.get("win") for p in blue)
    red_win = any(p.get("win") for p in red)

    grad, fg = _result_colors(my_win)
    result = _status_badge(my_win)
    header_html = f"""
    <div style="padding:10px 12px;border-radius:10px;background:{grad};color:{fg};
                display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
            <span style="font-weight:800;letter-spacing:.3px">{gid}</span>
            <span>·</span>
            {q_badge}
            <span>·</span>
            <span>{game_start.strftime('%Y-%m-%d %H:%M:%S')} UTC</span>
            <span>·</span>
            <span>{_minutes_secs(duration_s)}</span>
        </div>
        <div>{result}</div>
    </div>
    """

    blue_html = _team_block_html("Blue Side", blue, patch, blue_win)
    red_html = _team_block_html("Red Side", red, patch, red_win)

    st.markdown(header_html, unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.markdown(blue_html, unsafe_allow_html=True)
    with c2:
        st.markdown(red_html, unsafe_allow_html=True)

# ---------- Página ----------
def main():
    st.set_page_config(page_title="Match History", page_icon="⏱", layout="wide")
    st.title("Match History")

    st.caption(f"Backend: [{BACKEND_URL}]({BACKEND_URL})")

    platform, puuid = _get_session_identity()
    if not puuid:
        st.info("Primero busca un jugador en **Summoner Search**.")
        st.stop()

    cols = st.columns([1, 3, 3])
    with cols[0]:
        start = st.number_input("Start", min_value=0, step=1, value=0)
    with cols[1]:
        q_keys = ["Todas"] + [f"{qid} · {name}" for qid, name in QUEUE_OPTION.items()]
        queue_sel = st.selectbox("Cola a filtrar", q_keys, index=0)
    with cols[2]:
        whole_season = st.radio("Tiempo", ["Toda la season", "Últimos 30 días"], index=0, horizontal=True)

    queue_param = None if queue_sel == "Todas" else int(queue_sel.split(" · ")[0])
    since_days = 30 if whole_season == "Últimos 30 días" else None
    tag = "30d" if since_days else "Season"

    try:
        matches_kpi = get_matches_full_by_puuid(
            platform, puuid, start=0, count=50, queue=queue_param, since_days=since_days
        )
    except Exception:
        matches_kpi = []

    games, wr = _kpi_wr(matches_kpi, puuid)
    kc1, kc2 = st.columns(2)
    kc1.metric(f"Games ({tag})", games)
    kc2.metric(f"WR ({tag})", f"{round(wr*100) if games else 0}%")

    st.divider()

    try:
        count = 10
        matches = get_matches_full_by_puuid(
            platform=platform,
            puuid=puuid,
            start=start,
            count=count,
            queue=queue_param,
            since_days=since_days,
        )
    except Exception as e:
        st.error(f"No se pudieron leer partidas: {e}")
        st.stop()

    if not matches:
        st.info("Sin partidas para esos filtros.")
        st.stop()

    for m in matches:
        info = m.get("info", {})
        meta = m.get("metadata", {})
        gid = (meta or {}).get("matchId", "")
        qname = QUEUE_OPTION.get(info.get("queueId"), "Unknown")
        stamp = datetime.fromtimestamp((info.get("gameStartTimestamp", 0))/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        dur = _minutes_secs(info.get("gameDuration", 0))
        my_win = _my_result(m, puuid)
        sym = _result_symbol(my_win)

        with st.expander(f"{sym} {gid} · {qname} · {stamp} UTC · {dur}", expanded=False):
            render_match_block(m, puuid)

if __name__ == "__main__":
    main()
