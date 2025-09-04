import streamlit as st
from typing import Dict, Any, List, Optional
from src.dashboard.utils.riot import (
    lookup_summoner,
    league_entries_by_summoner,
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    queue_label_to_id,
    explain_rank_fallback,
    save_last_known_ranks,
    load_last_known_ranks,
)

REGIONS = [
    "euw1", "eune1", "na1", "br1", "la1", "la2", "oc1",
    "kr", "jp1", "tr1", "ru", "ph2", "sg2", "th2", "tw2", "vn2",
]

def _rank_line(entry: Optional[Dict[str, Any]]) -> str:
    if not entry:
        return "Unranked — 0 LP"
    tier = entry.get("tier")
    rank = entry.get("rank")
    lp = entry.get("leaguePoints", 0)
    if tier and rank:
        return f"{tier.title()} {rank} — {lp} LP"
    return "Unranked — 0 LP"

def _find_entry(entries: List[Dict[str, Any]], queue: str) -> Optional[Dict[str, Any]]:
    for e in entries or []:
        if e.get("queueType") == queue:
            return e
    return None

def _recent_wr_summary(platform: str, puuid: str, queue_id: Optional[int], count: int = 20) -> str:
    try:
        if queue_id is None:
            ids = matches_by_puuid(puuid, platform, count=count)
        else:
            ids = matches_by_puuid(puuid, platform, count=count, queue=queue_id)
    except Exception:
        return "—"
    total = len(ids)
    if total == 0:
        return "—"
    wins = 0
    for mid in ids:
        try:
            m = match_by_id(mid, platform)
            p = find_participant_by_puuid(m, puuid)
            if p and p.get("win"):
                wins += 1
        except Exception:
            pass
    wr = (wins / total) * 100 if total > 0 else 0.0
    return f"{total} partidas • {wr:.1f}% WR"

def _safe_lookup(region: str, query: str) -> Optional[Dict[str, Any]]:
    """Intenta ambos órdenes de argumentos para lookup_summoner."""
    try:
        s = lookup_summoner(region, query)
        if s:
            return s
    except Exception:
        pass
    try:
        s = lookup_summoner(query, region)
        if s:
            return s
    except Exception:
        pass
    return None

def main():
    st.title("Summoner Search")

    if "region" not in st.session_state:
        st.session_state["region"] = "euw1"
    if "summoner_query" not in st.session_state:
        st.session_state["summoner_query"] = ""
    if "summoner" not in st.session_state:
        st.session_state["summoner"] = None

    c1, c2 = st.columns([1, 3])
    with c1:
        region = st.selectbox("Región", REGIONS, index=REGIONS.index(st.session_state["region"]))
    with c2:
        query = st.text_input(
            "Invocador (ej: Nombre#TAG)",
            value=st.session_state["summoner_query"],
            max_chars=40,
        )

    do_search = st.button("Buscar", use_container_width=True)

    if do_search or region != st.session_state["region"] or query != st.session_state["summoner_query"]:
        st.session_state["region"] = region.strip().lower()
        st.session_state["summoner_query"] = query.strip()

        summ = None
        if st.session_state["summoner_query"]:
            summ = _safe_lookup(st.session_state["region"], st.session_state["summoner_query"])

        if not summ or (not summ.get("id") and not summ.get("puuid")):
            st.session_state["summoner"] = None
            st.warning("No se pudo resolver el invocador. Verifica el nombre/región.")
        else:
            summ["region"] = st.session_state["region"]
            st.session_state["summoner"] = summ

    summ = st.session_state["summoner"]

    if not summ:
        st.subheader("—")
        st.caption("Introduce un invocador y pulsa **Buscar**.")
        return

    display_name = summ.get("name") or st.session_state["summoner_query"]
    st.subheader(display_name)
    st.caption(f"Nivel {summ.get('level', '—')}")

    # Mostrar el ícono del perfil
    profile_icon_url = f"http://ddragon.leagueoflegends.com/cdn/12.22.1/img/profileicon/{summ.get('profileIconId')}.png"
    st.image(profile_icon_url, width=50)

    entries: List[Dict[str, Any]] = []
    if summ.get("id"):
        try:
            entries = league_entries_by_summoner(st.session_state["region"], summ["id"])
        except Exception:
            entries = []

    if summ.get("puuid") and entries:
        try:
            save_last_known_ranks(summ["puuid"], entries)
        except Exception:
            pass

    cL, cR = st.columns(2)
    with cL:
        st.markdown("**Solo/Dúo:**")
        solo_entry = _find_entry(entries, "RANKED_SOLO_5x5")
        if not solo_entry and summ.get("puuid"):
            try:
                cached = load_last_known_ranks(summ["puuid"])
                solo_entry = _find_entry(cached or [], "RANKED_SOLO_5x5")
            except Exception:
                pass
        st.write(_rank_line(solo_entry))

    with cR:
        st.markdown("**Flexible:**")
        flex_entry = _find_entry(entries, "RANKED_FLEX_SR")
        if not flex_entry and summ.get("puuid"):
            try:
                cached = load_last_known_ranks(summ["puuid"])
                flex_entry = _find_entry(cached or [], "RANKED_FLEX_SR")
            except Exception:
                pass
        st.write(_rank_line(flex_entry))

    if not _find_entry(entries, "RANKED_SOLO_5x5") and not _find_entry(entries, "RANKED_FLEX_SR"):
        st.info(explain_rank_fallback(summ.get("puuid")), icon="ℹ️")

    st.divider()
    st.markdown("### Actividad reciente (últimos 20)")
    if not summ.get("puuid"):
        st.caption("— No hay PUUID disponible para consultar partidas.")
        return

    qs = [
        ("SoloQ", queue_label_to_id("Clasificatoria Solo/Dúo")),
        ("Flex", queue_label_to_id("Clasificatoria Flexible")),
    ]
    for label, qid in qs:
        summary = _recent_wr_summary(st.session_state["region"], summ["puuid"], qid, count=20)
        st.markdown(f"**{label}** — {summary}")

if __name__ == "__main__":
    main()
