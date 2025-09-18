# src/api/riot_proxy.py
import os
import time
from typing import Dict, Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _get_api_key() -> str:
    """Lee la API key de Riot desde la variable de entorno RIOT_API_KEY."""
    return os.getenv("RIOT_API_KEY", "") or ""

def _headers() -> Dict[str, str]:
    """Cabeceras con la API key. Lanza 401 si falta."""
    key = _get_api_key()
    if not key:
        raise HTTPException(
            status_code=401,
            detail={
                "status": {
                    "status_code": 401,
                    "message": (
                        "RIOT_API_KEY ausente en el backend. "
                        "Define la variable de entorno antes de arrancar Uvicorn."
                    ),
                }
            },
        )
    return {"X-Riot-Token": key}

def _platform_to_region(platform: str) -> str:
    """Mapea plataforma (EUW1/…​) a región (europe/americas/asia)."""
    eu = {"EUW1", "EUN1", "TR1", "RU"}
    na = {"NA1", "BR1", "LA1", "LA2", "OC1"}
    kr = {"KR", "JP1"}
    p = platform.upper()
    if p in eu:
        return "europe"
    if p in na:
        return "americas"
    if p in kr:
        return "asia"
    return "europe"

# ---------------------------------------------------------------------
# Endpoints Riot
# ---------------------------------------------------------------------

@router.get("/summoner/by-riot-id/{platform}/{name}/{tag}")
async def api_summoner_by_riot_id(platform: str, name: str, tag: str):
    """Account por Riot ID y Summoner por PUUID."""
    region = _platform_to_region(platform)

    # 1) Account (global, por Riot ID)
    async with httpx.AsyncClient(timeout=20.0) as client:
        r1 = await client.get(
            f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}",
            headers=_headers(),
        )
        if r1.status_code != 200:
            raise HTTPException(
                status_code=r1.status_code,
                detail=r1.json() if r1.headers.get("content-type", "").startswith("application/json") else r1.text,
            )
        account = r1.json()

    # 2) Summoner (regional de plataforma) por PUUID
    async with httpx.AsyncClient(timeout=20.0) as client:
        r2 = await client.get(
            f"https://{platform.lower()}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{account['puuid']}",
            headers=_headers(),
        )
        if r2.status_code != 200:
            raise HTTPException(
                status_code=r2.status_code,
                detail=r2.json() if r2.headers.get("content-type", "").startswith("application/json") else r2.text,
            )
        summoner = r2.json()

    return {"platform": platform, "region": region, "account": account, "summoner": summoner}


@router.get("/match/{platform}/match_ids")
async def api_match_ids(
    platform: str,
    puuid: str,
    start: int = Query(0, ge=0),
    count: int = Query(10, ge=1, le=100),
    queue: Optional[int] = None,
    since_days: Optional[int] = None,
):
    """Devuelve IDs de partida para un PUUID, con filtros básicos."""
    region = _platform_to_region(platform)
    params: Dict[str, Any] = {"start": start, "count": count}
    if queue is not None:
        params["queue"] = queue
    if since_days is not None:
        params["startTime"] = int(time.time()) - since_days * 86400

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids",
            params=params,
            headers=_headers(),
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            )
        return r.json()


@router.get("/match/{platform}/match/{match_id}")
async def api_match_full(platform: str, match_id: str):
    """Devuelve el documento completo de una partida por ID."""
    region = _platform_to_region(platform)
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers=_headers(),
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            )
        return r.json()

# ---------------------------------------------------------------------
# Debug opcional
# ---------------------------------------------------------------------

@router.get("/debug/riot_key")
def debug_riot_key():
    key = os.getenv("RIOT_API_KEY", "")
    return {"has_key": bool(key), "len": len(key)}
