import asyncio
from datetime import datetime
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING

class MongoStore:
    def __init__(self, uri: str, db_name: str):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[db_name]

    async def ensure_indexes(self) -> None:
        await self._db.summoners.create_index([("puuid", ASCENDING), ("region", ASCENDING)], unique=True)
        await self._db.matches.create_index([("matchId", ASCENDING), ("region", ASCENDING)], unique=True)
        await self._db.timelines.create_index([("matchId", ASCENDING), ("region", ASCENDING)], unique=True)
        await self._db.leagues.create_index([("summonerId", ASCENDING), ("queueType", ASCENDING), ("region", ASCENDING)])

    async def upsert_match(self, doc: Dict[str, Any]) -> None:
        match_id = doc["metadata"]["matchId"]
        region = doc.get("region")
        await self._db.matches.update_one(
            {"matchId": match_id, "region": region},
            {"$set": doc, "$currentDate": {"updatedAt": True}, "$setOnInsert": {"createdAt": datetime.utcnow()}},
            upsert=True,
        )

    async def upsert_timeline(self, doc: Dict[str, Any]) -> None:
        match_id = doc["metadata"]["matchId"]
        region = doc.get("region")
        await self._db.timelines.update_one(
            {"matchId": match_id, "region": region},
            {"$set": doc, "$currentDate": {"updatedAt": True}, "$setOnInsert": {"createdAt": datetime.utcnow()}},
            upsert=True,
        )

    async def upsert_summoner(self, doc: Dict[str, Any]) -> None:
        await self._db.summoners.update_one(
            {"puuid": doc["puuid"], "region": doc["region"]},
            {"$set": doc, "$currentDate": {"updatedAt": True}, "$setOnInsert": {"createdAt": datetime.utcnow()}},
            upsert=True,
        )
