# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from typing import Iterable, Mapping, Tuple, Optional
from collections import defaultdict

import streamlit as st


# ==========
# Session helpers
# ==========
def get_active_player() -> Optional[dict]:
    """Devuelve el jugador activo desde la sesión (o None si no hay)."""
    # Puede venir como "summoner" (resumen) o "invoker_ctx" (contexto rico)
    return st.session_state.get("invoker_ctx") or st.session_state.get("summoner")


def require_active_player() -> dict:
    """Igual que arriba, pero error si no hay jugador."""
    ctx = get_active_player()
    if not ctx:
        raise RuntimeError("No hay jugador cargado en sesión (usa 01 Summoner Search).")
    return ctx


# ==========
# Math / format helpers (reemplazo ligero de lo que solías tener en riot.py)
# ==========
def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0:
            return default
        return float(a) / float(b)
    except Exception:
        return default


def kda_str(k: int, d: int, a: int) -> str:
    """Devuelve 'KDA' clásico y ratio (p.e. '7/3/9 (5.33)')"""
    ratio = _safe_div(k + a, max(1, d))
    return f"{k}/{d}/{a} ({ratio:.2f})"


def cs_per_min(cs_total: float, duration_seconds: float) -> float:
    return _safe_div(cs_total, duration_seconds / 60.0)


def gold_per_min(gold: float, duration_seconds: float) -> float:
    return _safe_div(gold, duration_seconds / 60.0)


def dmg_share(team_damage: float, player_damage: float) -> float:
    return _safe_div(player_damage, team_damage)


def fmt_pct(x: float, ndigits: int = 1) -> str:
    return f"{x * 100:.{ndigits}f}%"


def fmt_ratio(x: float, ndigits: int = 2) -> str:
    return f"{x:.{ndigits}f}"


def winrate(wins: int, losses: int) -> float:
    total = wins + losses
    return _safe_div(wins, total)


# ==========
# Aggregations (ejemplos de KPIs a partir de partidas)
#   Los datos de partida/participante los trae tu backend;
#   estas funciones solo agregan y formatean.
# ==========
def aggregate_basic_kpis(rows: Iterable[Mapping]) -> dict:
    """
    rows: iterable de diccionarios de partidas del jugador (uno por match), con campos como:
      kills, deaths, assists, cs, goldEarned, timePlayed, damageDealt, teamDamage, win (bool)
    """
    total = 0
    k = d = a = 0
    cs = gold = tsec = dmg = team_dmg = 0
    wins = losses = 0

    for r in rows:
        total += 1
        k += int(r.get("kills", 0))
        d += int(r.get("deaths", 0))
        a += int(r.get("assists", 0))
        cs += float(r.get("cs", 0.0))
        gold += float(r.get("goldEarned", 0.0))
        tsec += float(r.get("timePlayed", 0.0))
        dmg += float(r.get("damageDealt", 0.0))
        team_dmg += float(r.get("teamDamage", 0.0))
        if r.get("win") is True:
            wins += 1
        else:
            losses += 1

    kpis = {
        "games": total,
        "kda_str": kda_str(k, d, a),
        "cs_min": cs_per_min(cs, tsec) if total else 0.0,
        "gpm": gold_per_min(gold, tsec) if total else 0.0,
        "dmg_share": dmg_share(team_dmg, dmg) if team_dmg > 0 else 0.0,
        "winrate": winrate(wins, losses),
        "kills": k,
        "deaths": d,
        "assists": a,
        "wins": wins,
        "losses": losses,
        "timePlayed": tsec,
    }
    return kpis


def kpis_to_strings(kpis: Mapping) -> Mapping[str, str]:
    """Formatea KPIs para pintar rápido en tarjetas."""
    return {
        "Partidas": str(kpis.get("games", 0)),
        "KDA": kpis.get("kda_str", "0/0/0 (0.00)"),
        "CS/min": fmt_ratio(kpis.get("cs_min", 0.0), 2),
        "Oro/min": fmt_ratio(kpis.get("gpm", 0.0), 0),
        "Daño%": fmt_pct(kpis.get("dmg_share", 0.0), 1),
        "Winrate": fmt_pct(kpis.get("winrate", 0.0), 1),
    }

# ==========
# Compat: champion KPIs agrupando por campeón a partir de partidas
# ==========

def _minutes_from_duration_s_or_ms(x: int | None) -> float:
    if not x:
        return 0.0
    secs = int(x if x < 100_000 else x // 1000)
    return secs / 60.0

def champ_kpis_from_matches(matches: list[dict], puuid: str) -> list[dict]:
    """
    Agrega KPIs por campeón para el jugador `puuid` a partir de partidas RSO (match-v5).
    Cada fila devuelta:
      {
        "champion": str,
        "games": int,
        "wins": int,
        "winrate": float (0..1),
        "k": float, "d": float, "a": float, "kda": float,
        "cs_per_min": float,
        "gold_per_min": float,
        "vision_per_game": float,
      }
    """
    agg = defaultdict(lambda: {
        "games": 0, "wins": 0,
        "k": 0, "d": 0, "a": 0,
        "cs": 0, "gold": 0, "vision": 0,
        "minutes": 0.0,
    })

    for m in matches or []:
        info = (m or {}).get("info", {}) or {}
        parts = info.get("participants", []) or []
        dur_min = _minutes_from_duration_s_or_ms(info.get("gameDuration"))

        target = None
        for p in parts:
            if p.get("puuid") == puuid:
                target = p
                break
        if not target:
            continue

        champ = target.get("championName") or "Unknown"
        a = agg[champ]
        a["games"] += 1
        # ganamos: usa participant["win"] si existe; si no, deriva de team
        win_flag = target.get("win")
        if isinstance(win_flag, bool):
            win = win_flag
        else:
            # fallback: si no viene win booleano, intenta con teams o kills
            win = False
            for t in info.get("teams", []) or []:
                if t.get("teamId") == target.get("teamId"):
                    w = t.get("win")
                    if isinstance(w, bool):
                        win = w
                    elif isinstance(w, str):
                        win = w.lower() in ("win", "true")
                    break
        if win:
            a["wins"] += 1

        k, d, v = target.get("kills", 0), target.get("deaths", 0), target.get("assists", 0)
        cs = target.get("totalMinionsKilled", 0) + target.get("neutralMinionsKilled", 0)
        gold = target.get("goldEarned", 0)
        vis = target.get("visionScore", 0)

        a["k"] += k
        a["d"] += d
        a["a"] += v
        a["cs"] += cs
        a["gold"] += gold
        a["vision"] += vis
        a["minutes"] += max(dur_min, 0.0001)

    rows = []
    for champ, a in agg.items():
        games = a["games"]
        wins = a["wins"]
        minutes = max(a["minutes"], 0.0001)

        kda = _safe_div(a["k"] + a["a"], a["d"], default=a["k"] + a["a"])
        rows.append({
            "champion": champ,
            "games": games,
            "wins": wins,
            "winrate": _safe_div(wins, games),
            "k": a["k"] / games,
            "d": a["d"] / games,
            "a": a["a"] / games,
            "kda": kda,
            "cs_per_min": a["cs"] / minutes,
            "gold_per_min": a["gold"] / minutes,
            "vision_per_game": a["vision"] / games,
        })

    # ordena por winrate y juegos
    rows.sort(key=lambda r: (r["winrate"], r["games"]), reverse=True)
    return rows