# src/dashboard/pages/_04_Live_Game.py
from __future__ import annotations
import os, time, random, requests
import streamlit as st
from src.dashboard.utils import riot
from src.dashboard.utils import api_client

# Usa mismo backend que en Summoner Search
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8081")

# ---------------- Helpers ----------------
def _safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

def _spectator(platform: str, summoner_id: str, timeout: int = 15):
    url = f"{BACKEND_URL}/spectator/{platform}/{summoner_id}"
    r = requests.get(url, timeout=timeout)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

# ids válidos para demo (CommunityDragon)
CHAMPION_SAMPLE_IDS = [266,103,84,12,32,34,1,22,131,145,157,517,221,13,111,9,876,711,526,777]

def _fake_demo():
    start_ms = int((time.time() - random.randint(120, 1500)) * 1000)
    parts = []
    for i in range(10):
        parts.append({
            "summonerName": f"Player{i+1}",
            "teamId": 100 if i < 5 else 200,
            "championId": random.choice(CHAMPION_SAMPLE_IDS),
            "spell1Id": 4,
            "spell2Id": random.choice([7,11,12,14,3,6]),
        })
    return {
        "gameId": random.randint(1_000_000_000, 9_999_999_999),
        "gameStartTime": start_ms,
        "gameMode": "CLASSIC",
        "gameQueueConfigId": 420,
        "participants": parts,
    }

def _get_platform() -> str | None:
    return st.session_state.get("platform") or (st.session_state.get("player") or {}).get("platform")

def _get_summoner_id() -> str | None:
    summ = st.session_state.get("summoner")
    if isinstance(summ, dict) and summ.get("id"):
        return summ["id"]

    p = st.session_state.get("player") or {}
    ps = p.get("summoner") or {}
    if isinstance(ps, dict) and ps.get("id"):
        st.session_state["summoner"] = ps
        return ps["id"]

    riot_id = st.session_state.get("riotid")
    platform = _get_platform()
    if riot_id and platform:
        try:
            data = api_client.get_summoner_by_riot_id(platform, riot_id)
            summoner = data.get("summoner") if isinstance(data, dict) else data
            if isinstance(summoner, dict) and summoner.get("id"):
                st.session_state["summoner"] = summoner
                st.session_state["summoner_id"] = summoner["id"]
                return summoner["id"]
        except Exception:
            pass
    return None

def _mmss(sec: int) -> str:
    m, s = divmod(max(0, int(sec)), 60)
    return f"{m:02}:{s:02}"

def _elapsed_from_spec(spec: dict) -> int:
    now_ms = int(time.time() * 1000)
    start_ms = spec.get("gameStartTime") or spec.get("gameStartTimeMillis")
    if isinstance(start_ms, (int, float)) and start_ms > 0:
        return max(0, (now_ms - int(start_ms)) // 1000)
    key = "live_local_start_ms"
    if key not in st.session_state:
        st.session_state[key] = now_ms
    return (now_ms - st.session_state[key]) // 1000

def _estimate_team_gold(participants: list[dict], elapsed_sec: int) -> tuple[int, int]:
    minutes = max(1.0, elapsed_sec / 60.0)
    est = []
    for p in participants:
        base = 350 + 250 * minutes
        noise = random.uniform(-120, 120)
        est.append((p["teamId"], int(max(200, base + noise))))
    blue = sum(v for tid, v in est if tid == 100)
    red  = sum(v for tid, v in est if tid == 200)
    return blue, red

# ---------------- Render ----------------
def _header(spec: dict):
    game_id = spec.get("gameId", "—")
    qid = spec.get("gameQueueConfigId")
    queue_name = riot.QUEUE_OPTION.get(qid, str(qid) if qid else "Unknown")

    elapsed = _elapsed_from_spec(spec)
    st.markdown(
        f"""
        <div style="text-align:center;margin:4px 0 12px">
            <h2 style="margin:0">🎮 Live Match</h2>
            <div style="opacity:.75">Game ID: <code>{game_id}</code> · {queue_name} · <b>{_mmss(elapsed)}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    gold_b, gold_r = _estimate_team_gold(spec["participants"], elapsed)
    diff = gold_b - gold_r
    c1, c2, c3 = st.columns(3)
    c1.metric("Blue Gold", f"{gold_b:,}")
    c2.metric("Diff", f"{diff:+,}")
    c3.metric("Red Gold", f"{gold_r:,}")

    total = max(1, gold_b + gold_r)
    pct_b = int(100 * gold_b / total)
    st.markdown(
        f"""
        <div style="margin:14px 0;border-radius:10px;overflow:hidden;height:14px;background:#20262e;display:flex">
            <div style="width:{pct_b}%;background:#3498db"></div>
            <div style="width:{100-pct_b}%;background:#e74c3c"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _teams(spec: dict):
    left, right = st.columns(2)
    for col, tid, color in [(left, 100, "#3498db"), (right, 200, "#e74c3c")]:
        with col:
            st.markdown(
                f"<h3 style='color:{color};margin-top:10px;margin-bottom:8px'>"
                f"{'Blue Side' if tid == 100 else 'Red Side'}</h3>",
                unsafe_allow_html=True,
            )
            for p in [x for x in spec["participants"] if x["teamId"] == tid]:
                champ_icon = riot.champion_icon_by_id_url(p["championId"])
                s1 = riot.spell_icon_url(p["spell1Id"])
                s2 = riot.spell_icon_url(p["spell2Id"])
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;
                                border:1px solid rgba(120,130,150,.18);border-radius:10px;padding:8px;background:rgba(40,48,63,.25)">
                        <img src="{champ_icon}" width="36" height="36" style="border-radius:6px">
                        <div style="flex:1;min-width:0">
                            <div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p['summonerName']}</div>
                            <div style="font-size:12px;opacity:.75">Champion #{p['championId']}</div>
                        </div>
                        <img src="{s1}" width="22" height="22" style="border-radius:4px">
                        <img src="{s2}" width="22" height="22" style="border-radius:4px">
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ---------------- Página ----------------
def main():
    st.set_page_config(page_title="Live Game", page_icon="🎥", layout="wide")
    st.title("🎥 Live Game")

    c1, c2 = st.columns([1, 1])
    with c1:
        demo = st.toggle("Modo demo", value=False)
    with c2:
        if st.button("Refrescar", use_container_width=True):
            _safe_rerun()

    # --- Demo primero ---
    if demo:
        spec = _fake_demo()
        _header(spec)
        _teams(spec)
        return

    # --- Flujo normal ---
    platform = _get_platform()
    summ_id = _get_summoner_id()
    if not platform or not summ_id:
        st.info("Primero busca un invocador en **01 Summoner Search** (necesito su Summoner ID).")
        return

    try:
        spec = _spectator(platform, summ_id)
    except Exception as e:
        st.error(f"No se pudo obtener partida en vivo: {e}")
        return

    if not spec:
        st.warning("No hay partida activa para este invocador.")
        return

    _header(spec)
    _teams(spec)

if __name__ == "__main__":
    main()
