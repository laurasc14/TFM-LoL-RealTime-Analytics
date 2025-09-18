# src/api/cache.py
from __future__ import annotations
import os
import datetime as dt
from typing import Any, Optional, Dict, List

try:
    from pymongo import MongoClient, ASCENDING, errors
except Exception:  # pymongo no instalado o no hay mongo
    MongoClient = None  # type: ignore

DEFAULT_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "3"))

def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=None)

class MongoCache:
    def __init__(self) -> None:
        self.url = os.getenv("MONGO_URL")
        self.db_name = os.getenv("MONGO_DB")
        self.enabled = bool(self.url and self.db_name and MongoClient is not None)
        self.client = None
        self.db = None
        if self.enabled:
            try:
                self.client = MongoClient(self.url, serverSelectionTimeoutMS=1500)
                # fuerza ping
                self.client.admin.command("ping")
                self.db = self.client[self.db_name]
                self._ensure_indexes()
            except Exception:
                # Si falla el conexionado, se desactiva el cache
                self.enabled = False
                self.client = None
                self.db = None

    # ---------- índices TTL ----------
    def _ensure_indexes(self) -> None:
        # colecciones
        coll_summ = self.db["summoners"]
        coll_ids  = self.db["match_ids"]
        coll_full = self.db["matches_full"]

        # TTL por fecha de expiración
        for coll in (coll_summ, coll_ids, coll_full):
            try:
                coll.create_index([("key", ASCENDING)], unique=True)
                coll.create_index("expiresAt", expireAfterSeconds=0)
            except Exception:
                pass

    # ---------- helpers ----------
    def _ttl(self, days: Optional[int] = None) -> dt.datetime:
        return _utcnow() + dt.timedelta(days=days or DEFAULT_TTL_DAYS)

    # ---------- summoner ----------
    def get_summoner_by_riot_id(
        self, platform: str, gameName: str, tagLine: str
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        key = f"summ:{platform}:{gameName}:{tagLine}"
        doc = self.db["summoners"].find_one({"key": key}, {"_id": 0})
        return doc["value"] if doc else None

    def set_summoner_by_riot_id(
        self, platform: str, gameName: str, tagLine: str, value: Dict[str, Any], ttl_days: Optional[int] = None
    ) -> None:
        if not self.enabled:
            return
        key = f"summ:{platform}:{gameName}:{tagLine}"
        self.db["summoners"].update_one(
            {"key": key},
            {"$set": {"key": key, "value": value, "expiresAt": self._ttl(ttl_days)}},
            upsert=True,
        )

    # ---------- match ids ----------
    def get_match_ids(
        self, puuid: str, start: int, count: int
    ) -> Optional[List[str]]:
        if not self.enabled:
            return None
        key = f"ids:{puuid}:{start}:{count}"
        doc = self.db["match_ids"].find_one({"key": key}, {"_id": 0})
        return doc["value"] if doc else None

    def set_match_ids(
        self, puuid: str, start: int, count: int, ids: List[str], ttl_days: Optional[int] = None
    ) -> None:
        if not self.enabled:
            return
        key = f"ids:{puuid}:{start}:{count}"
        self.db["match_ids"].update_one(
            {"key": key},
            {"$set": {"key": key, "value": ids, "expiresAt": self._ttl(ttl_days)}},
            upsert=True,
        )

    # ---------- match full ----------
    def get_match_full(self, match_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        key = f"full:{match_id}"
        doc = self.db["matches_full"].find_one({"key": key}, {"_id": 0})
        return doc["value"] if doc else None

    def set_match_full(self, match_id: str, payload: Dict[str, Any], ttl_days: Optional[int] = None) -> None:
        if not self.enabled:
            return
        key = f"full:{match_id}"
        self.db["matches_full"].update_one(
            {"key": key},
            {"$set": {"key": key, "value": payload, "expiresAt": self._ttl(ttl_days)}},
            upsert=True,
        )

# singleton
CACHE = MongoCache()
