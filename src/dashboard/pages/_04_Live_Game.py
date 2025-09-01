# src/dashboard/pages/_04_Live_Game.py
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from src.dashboard.utils.riot import (
    live_game_by_summoner_id,
    summoner_by_name,          # para el pequeño formulario de fallback
    load_champions,
    get_champion_image,
    RiotError,
    Forbidden,
    NotFound,
    lookup_summoner,
)

PAGE_TITLE = "Live Game ↪"


# ----------------------------- helpers ---------------------------------
def _champ_name_from_id(champions_dict: dict, champion_id: int) -> str:
    try:
        return champions_dict.get(int(champion_id), "Unknown")
    except Exception:
        return "Unknown"


def _elapsed_minutes(game_start_time_ms: int) -> int:
    if not game_start_time_ms:
        return 0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return max(0, (now_ms - int(game_start_time_ms)) // 60000)


def _team_table(participants: list, champions_dict: dict):
    rows = []
    for p in participants:
        cid = p.get("championId")
        champ_name = _champ_name_from_id(champions_dict, cid)
        champ_img = get_champion_image(cid, champions_dict)
        rows.append({
            "Summoner": p.get("summonerName", "—"),
            "Champion": champ_name,
            "Image": f'<img src="{champ_img}" width="36" style="border-radius:6px;">',
            "Spells": f"{p.get('spell1Id', '—')} / {p.get('spell2Id', '—')}",
        })
    df = pd.DataFrame(rows, columns=["Summoner", "Champion", "Image", "Spells"])
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)


def _bans_block(game: dict, champions_dict: dict):
    bans = game.get("bannedChampions") or []
    if not bans:
        return
    blue_bans = [b for b in bans if b.get("teamId") == 100]
    red_bans = [b for b in bans if b.get("teamId") == 200]

    def _ban_row(items):
        bits = []
        for b in items:
            cid = b.get("championId")
            name = _champ_name_from_id(champions_dict, cid)
            img = get_champion_image(cid, champions_dict)
            bits.append(f'<img src="{img}" width="28" style="border-radius:4px;margin-right:6px;"> {name}')
        return " · ".join(bits) if bits else "—"

    st.markdown("**Bans**")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Blue**: {_ban_row(blue_bans)}", unsafe_allow_html=True)
    with c2:
        st.markdown(f"**Red**: {_ban_row(red_bans)}", unsafe_allow_html=True)


# ----------------------------- page ------------------------------------
def main():
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)

    # 1) Obtenemos el invocador desde la sesión o permitimos cargarlo aquí mismo
    summ = st.session_state.get("summoner")

    region = ((summ or {}).get("region") or st.session_state.get("region") or "").strip().lower()
    encrypted_id = (summ or {}).get("id") or (summ or {}).get("summonerId")  # Spectator usa encryptedSummonerId

    if not (region and encrypted_id):
        st.info("🔎 No hay invocador con `region` y `summonerId` en sesión. Cárgalo aquí o ve a **Summoner Search**.")
        with st.form("load_summoner"):
            region_in = st.selectbox("Región (platform routing)",
                                     ["euw1", "eun1", "na1", "br1", "la1", "la2", "oc1", "kr", "tr1", "ru", "jp1"],
                                     index=0)
            name_in = st.text_input("Nombre de invocador (exacto, formato Nombre#TAG)")
            submitted = st.form_submit_button("Cargar")

        if submitted and name_in.strip():
            try:
                s = lookup_summoner(name_in.strip(), region_in)
                st.session_state["summoner"] = {
                    "region": region_in,
                    "id": s["id"],          # encryptedSummonerId
                    "puuid": s.get("puuid"),
                    "name": s.get("name"),
                }
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo cargar el invocador: {e}")
        st.stop()

    # 2) Datos maestros de campeones para nombres e iconos
    champions_dict = load_champions()

    # 3) Llamada a Spectator
    try:
        game = live_game_by_summoner_id(region, encrypted_id)
    except NotFound:
        st.info("📴 El invocador no está en partida ahora mismo.")
        st.stop()
    except Forbidden:
        st.error("🚫 403 Forbidden – revisa tu RIOT_API_KEY (expirada/incorrecta) o los permisos del proyecto.")
        st.stop()
    except RiotError as e:
        msg = str(e)
        if "401" in msg or "400" in msg:
            st.info("⏳ La partida puede haber arrancado hace segundos. Refresca en unos instantes.")
            st.stop()
        st.error(f"Error al obtener la partida en vivo: {e}")
        st.stop()

    # 4) Cabecera/información básica
    queue = game.get("gameQueueConfigId", "—")
    mode = game.get("gameMode", "—")
    map_id = game.get("mapId", "—")
    started_min = _elapsed_minutes(game.get("gameStartTime", 0))
    st.success(f"✅ Partida en vivo · **{mode}** · Queue **{queue}** · Mapa **{map_id}** · ⏱️ {started_min} min")

    # 5) Bans (si existen)
    _bans_block(game, champions_dict)

    # 6) Equipos
    parts = game.get("participants", [])
    blue = [p for p in parts if p.get("teamId") == 100]
    red = [p for p in parts if p.get("teamId") == 200]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Blue (100)")
        _team_table(blue, champions_dict)
    with c2:
        st.subheader("Red (200)")
        _team_table(red, champions_dict)

    st.caption("Fuente: /lol/spectator/v5/active-games/by-summoner. Refresca la página para actualizar.")

if __name__ == "__main__":
    main()
