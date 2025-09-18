from __future__ import annotations
import os, time, logging, asyncio
from datetime import datetime, timezone
from typing import Any, Optional, Dict

import requests
from fastapi import APIRouter
from pydantic import BaseModel, Field

log = logging.getLogger("backfill_api")

# Router (no sub-app)
router = APIRouter(prefix="/backfill", tags=["Backfill"])

# -----------------------------
# Inyección de DB desde main.py
# -----------------------------
_db: Optional[Any] = None
def set_db(db):  # llamado desde main
    global _db
    _db = db

def _out_collection_name() -> str:
    return os.getenv("MONGO_OUT_COL", "matches_full")

def _get_out_coll():
    if _db is None:
        return None, "no-db"
    try:
        return _db[_out_collection_name()], None
    except Exception as e:
        log.exception("No pude abrir la colección destino")
        return None, f"coll-error:{e}"

# ---------- Debug ----------
@router.get("/health")
def health():
    return {
        "status": "ok",
        "mongo": "ok" if _db is not None else "missing",
        "out_col": _out_collection_name(),
        "time": datetime.utcnow().isoformat(),
    }

@router.get("/debug/env")
def debug_env():
    return {
        "MONGO_URL": os.getenv("MONGO_URL"),
        "MONGO_DB": os.getenv("MONGO_DB"),
        "MONGO_OUT_COL": _out_collection_name(),
        "RIOT_API_KEY_set": bool(os.getenv("RIOT_API_KEY")),
    }

# ---------- Lectura ----------
@router.get("/matches_full")
def matches_full(since: int, limit: int = 100):
    if _db is None:
        return {"items": []}
    coll, err = _get_out_coll()
    if err:
        return {"items": []}
    since_ms = since * 1000
    cur = (
        coll.find({"gameStartTimestamp": {"$gte": since_ms}})
            .sort("gameStartTimestamp", -1)
            .limit(limit)
    )
    items = list(cur)
    for it in items:
        it["_id"] = str(it["_id"])
    return {"items": items}

# ---------- Riot helpers ----------
PLATFORM_TO_REGION = {
    "euw1": "europe","eune1":"europe","tr1":"europe","ru":"europe",
    "na1":"americas","la1":"americas","la2":"americas","br1":"americas",
    "oc1":"sea","jp1":"asia","kr":"asia",
}
def _region(p: str) -> str:
    return PLATFORM_TO_REGION.get(p.lower(), "europe")

def _session() -> requests.Session:
    k = os.getenv("RIOT_API_KEY")
    if not k:
        raise RuntimeError("RIOT_API_KEY no definido")
    s = requests.Session()
    s.headers.update({"X-Riot-Token": k, "Accept-Encoding": "gzip, deflate"})
    return s

class BackfillRequest(BaseModel):
    puuid: str
    platform: str
    since: int | None = None
    count: int = Field(default=100, ge=1, le=100)
    start: int = 0
    max_total: int | None = None

def _upsert(doc: Dict[str, Any]) -> bool:
    if _db is None:
        return False
    coll, err = _get_out_coll()
    if err:
        return False
    try:
        meta = (doc or {}).get("metadata", {}) or {}
        info = (doc or {}).get("info", {}) or {}
        mid = meta.get("matchId")
        gst = info.get("gameStartTimestamp") or info.get("gameStartTime") or 0
        # normaliza segundos -> milisegundos
        if isinstance(gst, (int, float)) and gst < 10_000_000_000:
            gst = int(gst) * 1000
        coll.update_one(
            {"match_id": mid},
            {"$set": {"match_id": mid, "gameStartTimestamp": int(gst), **doc}},
            upsert=True,
        )
        return True
    except Exception:
        log.exception("upsert falló")
        return False

def _get_ids(s: requests.Session, region: str, puuid: str, start: int, count: int, since: int | None):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": start, "count": min(max(count, 1), 100)}
    if since:
        params["startTime"] = int(since)
    r = s.get(url, params=params)
    return r.status_code, r.text, (r.json() if r.status_code == 200 else [])

def _get_match(s: requests.Session, region: str, mid: str):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{mid}"
    r = s.get(url)
    return r.status_code, r.text, (r.json() if r.status_code == 200 else None)

@router.post("/backfill")
def backfill(req: BackfillRequest):
    if _db is None:
        return {"ok": False, "reason": "no-db"}
    s = _session()
    region = _region(req.platform)
    start = max(0, int(req.start))
    per = min(max(int(req.count), 1), 100)
    saved = fetched = pages = 0

    while True:
        st, raw, ids = _get_ids(s, region, req.puuid, start, per, req.since)
        if st != 200:
            return {"ok": False, "reason": f"riot-{st}", "detail": raw, "fetched": fetched, "saved": saved}
        if not ids:
            break

        fetched += len(ids)
        pages += 1

        for mid in ids:
            st2, raw2, payload = _get_match(s, region, mid)
            if st2 != 200 or not payload:
                continue
            if _upsert(payload):
                saved += 1
            time.sleep(0.12)  # throttle

        start += len(ids)
        if len(ids) < per:
            break
        if req.max_total and saved >= req.max_total:
            break

    return {"ok": True, "pages": pages, "fetched": fetched, "saved": saved, "skipped": fetched - saved}

# --------- Colector continuo ---------
_COLLECTOR_TASK: Optional[asyncio.Task] = None
_RUNNING = False

def _last_ts_sec() -> int | None:
    coll, err = _get_out_coll()
    # >>> FIX IMPORTANTE: NO usar 'not coll' con Collection
    if err or coll is None:
        return None
    last = coll.find_one({}, sort=[("gameStartTimestamp", -1)])
    if not last:
        return None
    return int(last.get("gameStartTimestamp", 0)) // 1000

class CollectorStart(BaseModel):
    puuid: str
    platform: str
    interval_sec: int = Field(default=60, ge=10, le=3600)
    page_size: int = Field(default=100, ge=1, le=100)

@router.post("/collector/start")
async def collector_start(req: CollectorStart):
    global _COLLECTOR_TASK, _RUNNING
    if _db is None:
        return {"ok": False, "reason": "no-db"}
    if _RUNNING:
        return {"ok": False, "reason": "already-running"}

    _RUNNING = True

    async def loop():
        while _RUNNING:
            try:
                since = _last_ts_sec()
                await asyncio.to_thread(
                    backfill,
                    BackfillRequest(
                        puuid=req.puuid,
                        platform=req.platform,
                        since=since,
                        count=req.page_size,
                        start=0,
                        max_total=None,
                    ),
                )
            except Exception:
                log.exception("collector error")
            await asyncio.sleep(max(10, int(req.interval_sec)))

    _COLLECTOR_TASK = asyncio.create_task(loop())
    return {"ok": True, "status": "running"}

@router.post("/collector/stop")
async def collector_stop():
    global _COLLECTOR_TASK, _RUNNING
    if not _RUNNING:
        return {"ok": False, "reason": "not-running"}
    _RUNNING = False
    if _COLLECTOR_TASK:
        _COLLECTOR_TASK.cancel()
        _COLLECTOR_TASK = None
    return {"ok": True, "status": "stopped"}

@router.get("/collector/status")
def collector_status():
    return {"running": _RUNNING, "out_col": _out_collection_name()}
