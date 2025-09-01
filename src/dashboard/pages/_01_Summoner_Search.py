# src/dashboard/pages/_01_Summoner_Search.py
from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List, Optional

# Utilidades Riot (asegúrate de tener estas funciones en utils/riot.py)
from src.dashboard.utils.riot import (
    lookup_summoner,
    league_entries_by_summoner,
    matches_by_puuid,
    match_by_id,
    find_participant_by_puuid,
    queue_label_to_id,
    explain_rank_fallback,
    save_last_known_ranks,   # opcional (cache persistente del último rango)
    load_last_known_ranks,   # opcional (lectura de ese cache)
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de UI / formateo
# ──────────────────────────────────────────────────────────────────────────────

REGIONS = [
    "euw1", "eune1", "na1", "br1", "la1", "la2", "oc1",
    "kr", "jp1", "tr1", "ru", "ph2", "sg2", "th2", "tw2", "vn2",
]


def _rank_line(entry: Optional[Dict[str, Any]]) -> str:
    """Devuelve una línea legible de rango (o Unranked)."""
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
    """
    Calcula partidas y tasa de victorias para los últimos `count` matches
    de una cola concreta (si `queue_id` es None, todas las colas).
    """
    try:
        ids = matches_by_puuid(puuid, platform, count=count, queue=queue_id)
    except Exception:
        # No rompemos la página si el endpoint falla
        return "—"

    total = len(ids)
    if total == 0:
        return "—"

    wins = 0
    for mid in ids:
        try:
            m = match_by_id(platform, mid)
            p = find_participant_by_puuid(m, puuid)
            if p and p.get("win"):
                wins += 1
        except Exception:
            # Ignoramos partidas individuales que no carguen
            pass

    wr = (wins / total) * 100 if total > 0 else 0.0
    return f"{total} partidas • {wr:.1f}% WR"


# ──────────────────────────────────────────────────────────────────────────────
# Página
# ──────────────────────────────────────────────────────────────────────────────

def main():
    st.title("Summoner Search")

    # Estado compartido
    if "region" not in st.session_state:
        st.session_state["region"] = "euw1"
    if "summoner_query" not in st.session_state:
        st.session_state["summoner_query"] = ""
    if "summoner" not in st.session_state:
        st.session_state["summoner"] = None  # dict con {region, id, puuid, name, level, ...}

    # Controles
    c1, c2 = st.columns([1, 3])
    with c1:
        region = st.selectbox("Región", REGIONS, index=REGIONS.index(st.session_state["region"]))
    with c2:
        query = st.text_input("Invocador (ej: Nombre#TAG)", value=st.session_state["summoner_query"], max_chars=32)

    # Botón
    do_search = st.button("Buscar", use_container_width=True)

    # Resolver invocador
    if do_search or region != st.session_state["region"] or query != st.session_state["summoner_query"]:
        st.session_state["region"] = region
        st.session_state["summoner_query"] = query

        if query.strip():
            try:
                summ = lookup_summoner(query, region)
            except Exception:
                summ = None

            if not summ or (not summ.get("id") and not summ.get("puuid")):
                st.session_state["summoner"] = None
                st.warning("No se pudo resolver el invocador. Verifica el nombre/región.")
            else:
                summ["region"] = region.strip().lower()
                st.session_state["summoner"] = summ

    summ = st.session_state["summoner"]

    if not summ:
        st.subheader("—")
        st.caption("Introduce un invocador y pulsa **Buscar**.")
        return

    # Cabecera segura
    display_name = summ.get("name") or st.session_state["summoner_query"]
    st.subheader(display_name)
    st.caption(f"Nivel {summ.get('level', '—')}")

    # Ligas del invocador (por ID)
    entries: List[Dict[str, Any]] = []
    if summ.get("id"):
        try:
            entries = league_entries_by_summoner(region, summ["id"])
        except Exception:
            entries = []

    # Si tenemos PUUID, guardamos el "último rango conocido" cuando haya datos
    if summ.get("puuid") and entries:
        try:
            save_last_known_ranks(summ["puuid"], entries)
        except Exception:
            pass

    # Dos columnas: Solo/Dúo & Flex
    cL, cR = st.columns(2)
    with cL:
        st.markdown("**Solo/Dúo:**")
        solo_entry = _find_entry(entries, "RANKED_SOLO_5x5")
        if not solo_entry and summ.get("puuid"):
            # Intento de recuperar el último conocido
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
            # Intento de recuperar el último conocido
            try:
                cached = load_last_known_ranks(summ["puuid"])
                flex_entry = _find_entry(cached or [], "RANKED_FLEX_SR")
            except Exception:
                pass
        st.write(_rank_line(flex_entry))

    # Si Riot no expone rango para ninguna cola, mostramos explicación
    if not _find_entry(entries, "RANKED_SOLO_5x5") and not _find_entry(entries, "RANKED_FLEX_SR"):
        st.info(explain_rank_fallback(summ.get("puuid")), icon="ℹ️")

    # Resumen de actividad reciente (últimos 20)
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
        summary = _recent_wr_summary(region, summ["puuid"], qid, count=20)
        st.markdown(f"**{label}** — {summary}")


# Streamlit entry point
if __name__ == "__main__":
    main()
