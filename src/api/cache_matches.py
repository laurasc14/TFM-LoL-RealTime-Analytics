from __future__ import annotations
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne

router = APIRouter()

# -----------------------------
# ENV & Mongo
# -----------------------------
MONGO_URI  = os.getenv("MONGO_URI",  "mongodb://localhost:27017")
DB_NAME    = os.getenv("CACHE_DB",   "lol_realtime")   # usa SIEMPRE esta DB
COLL_NAME  = os.getenv("CACHE_COLL", "matches_full")

_client = MongoClient(MONGO_URI)
_db     = _client[DB_NAME]
_coll   = _db[COLL_NAME]

def _ensure_indexes() -> None:
    """
    Crea índices sin reventar si ya existen y evita el problema del null duplicado
    con un índice parcial (solo documentos que sí tengan matchId).
    """
    try:
        _coll.create_index(
            [("metadata.matchId", ASCENDING)],
            name="metadata.matchId_1",
            unique=True,
            partialFilterExpression={"metadata.matchId": {"$type": "string"}},
        )
        _coll.create_index([("info.gameStartTimestamp", DESCENDING)], name="info.gst_desc")
        _coll.create_index([("info.queueId", ASCENDING)], name="info.queueId_1")
        _coll.create_index([("metadata.participants", ASCENDING)], name="metadata.participants_1")
        print("[cache] índices OK")
    except Exception as e:
        print(f"[cache] warn: no se pudieron crear índices -> {e}")

_ensure_indexes()

# -----------------------------
# Riot helpers
# -----------------------------
def _get_api_key() -> str:
    key = os.getenv("RIOT_API_KEY", "")
    if not key:
        raise HTTPException(status_code=401, detail={"status": {
            "status_code": 401, "message": "RIOT_API_KEY ausente en el backend"
        }})
    return key

def _headers() -> Dict[str, str]:
    return {"X-Riot-Token": _get_api_key()}

def _platform_to_region(platform: str) -> str:
    eu = {"EUW1", "EUN1", "TR1", "RU"}
    na = {"NA1", "BR1", "LA1", "LA2", "OC1"}
    kr = {"KR", "JP1"}
    p = platform.upper()
    if p in eu: return "europe"
    if p in na: return "americas"
    if p in kr: return "asia"
    return "europe"

# -----------------------------
# Cache CRUD
# -----------------------------
def _proj() -> Dict[str, int]:
    return {"_id": 0, "metadata.matchId": 1, "metadata.participants": 1, "info": 1}

def upsert_match(doc: Dict[str, Any]) -> None:
    mid = (doc or {}).get("metadata", {}).get("matchId")
    if not mid:
        return
    _coll.update_one({"metadata.matchId": mid}, {"$set": doc}, upsert=True)

def bulk_upsert(docs: List[Dict[str, Any]]) -> None:
    ops = []
    for d in docs:
        mid = (d or {}).get("metadata", {}).get("matchId")
        if mid:
            ops.append(UpdateOne({"metadata.matchId": mid}, {"$set": d}, upsert=True))
    if ops:
        _coll.bulk_write(ops, ordered=False)

def _flt(puuid: str, queue: Optional[int], since_ms: Optional[int]) -> Dict[str, Any]:
    q: Dict[str, Any] = {"metadata.participants": puuid}
    if queue is not None:
        q["info.queueId"] = queue
    if since_ms is not None:
        q["info.gameStartTimestamp"] = {"$gte": since_ms}
    return q

# -----------------------------
# Endpoints de lectura directa a cache
# -----------------------------
@router.get("/cache/matches_full/{puuid}")
def cache_read_matches(
    puuid: str,
    start: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    queue: Optional[int] = None,
    since_ms: Optional[int] = None,
):
    cur = (
        _coll.find(_flt(puuid, queue, since_ms), _proj())
        .sort("info.gameStartTimestamp", DESCENDING)
        .skip(start)
        .limit(limit)
    )
    return list(cur)

# -----------------------------
# Progresivo: cache -> Riot (guardando lo que falte)
# -----------------------------
async def _riot_match_ids(platform: str, puuid: str, start: int, count: int,
                          queue: Optional[int], since_days: Optional[int]) -> List[str]:
    region = _platform_to_region(platform)
    params: Dict[str, Any] = {"start": start, "count": count}
    if queue is not None:
        params["queue"] = queue
    if since_days is not None:
        params["startTime"] = int(time.time()) - since_days * 86400

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids",
            params=params, headers=_headers()
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
            )
        return r.json() or []

async def _riot_match_full(platform: str, match_id: str) -> Dict[str, Any]:
    region = _platform_to_region(platform)
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}",
            headers=_headers()
        )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
            )
        return r.json()

@router.get("/match/{platform}/matches_full")
async def matches_full_progressive(
    platform: str,
    puuid: str,
    start: int = Query(0, ge=0),
    count: int = Query(10, ge=1, le=100),
    queue: Optional[int] = None,
    since_days: Optional[int] = None,
):
    # 1) lee cache
    since_ms = None
    if since_days is not None:
        since_ms = int((datetime.utcnow() - timedelta(days=since_days)).timestamp() * 1000)

    cached = list(
        _coll.find(_flt(puuid, queue, since_ms), _proj())
        .sort("info.gameStartTimestamp", DESCENDING)
        .skip(start)
        .limit(count)
    )
    if len(cached) >= count:
        return cached

    # 2) pide ids de esa página y rellena faltantes
    try:
        ids = await _riot_match_ids(platform, puuid, start, count, queue, since_days)
    except HTTPException:
        raise
    except Exception as e:
        # 502 para distinguir fallo de proxy/Riot de otros errores
        raise HTTPException(status_code=502, detail=f"match_ids proxy error: {e}")

    docs: List[Dict[str, Any]] = []
    for mid in ids:
        doc = _coll.find_one({"metadata.matchId": mid}, _proj())
        if not doc:
            try:
                full = await _riot_match_full(platform, mid)
                upsert_match(full)
                doc = _coll.find_one({"metadata.matchId": mid}, _proj())
            except Exception:
                # si una partida falla, seguimos con el resto
                continue
        if doc:
            docs.append(doc)

    docs.sort(key=lambda d: d.get("info", {}).get("gameStartTimestamp", 0), reverse=True)
    return docs

# -----------------------------
# Debug
# -----------------------------
@router.get("/debug/env")
def debug_env():
    return {
        "has_RIOT_API_KEY": bool(os.getenv("RIOT_API_KEY")),
        "BACKEND_URL": os.getenv("BACKEND_URL"),
        "RIOT_PROXY_BASE": os.getenv("RIOT_PROXY_BASE"),
        "mongo": {"uri": MONGO_URI, "db": DB_NAME, "coll": COLL_NAME},
    }
