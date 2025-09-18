# src/dashboard/utils/api_client.py
import os
import requests
from typing import Any, Dict, Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8888")


class ApiError(Exception):
    pass


def _handle_resp(resp: requests.Response) -> Dict[str, Any]:
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # detalle amigable en el dashboard
        raise ApiError(f"Error al llamar {resp.url}: {resp.status_code} {resp.text}") from e
    return resp.json()


# ---------- helpers genéricos ----------
def get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _handle_resp(requests.get(url, params=params, timeout=20))


# ---------- endpoints de Riot-proxy que ya usas ----------
def get_summoner_by_riot_id(platform: str, riot_id: str) -> Dict[str, Any]:
    """
    Busca puuid y datos de summoner en servidor backend (usa cache + Riot si hace falta).
    """
    name, tag = riot_id.split("#", 1)
    url = f"{BACKEND_URL}/summoner/by-riot-id/{platform}/{name}/{tag}"
    return get(url)


# ---------- lector cacheado desde Mongo ----------
def get_matches_full_paginated(
    puuid: str,
    start: int = 0,
    limit: int = 50,
    queue: Optional[int] = None,
    since_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Lee de /cache/matches_full/{puuid} con filtros y paginación. NO toca Riot.
    """
    url = f"{BACKEND_URL}/cache/matches_full/{puuid}"
    params: Dict[str, Any] = {
        "start": start,
        "limit": limit,
    }
    if queue is not None:
        params["queue"] = queue
    if since_ms is not None:
        params["since_ms"] = since_ms

    return get(url, params=params)

def get_matches_full_by_puuid(platform: str, puuid: str, start: int, count: int, queue=None, since_days=None, timeout: int = 20):
    url = f"{BACKEND_URL}/match/{platform}/matches_full"
    params = {"puuid": puuid, "start": start, "count": count}
    if queue is not None:
        params["queue"] = queue
    if since_days is not None:
        params["since_days"] = since_days
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()