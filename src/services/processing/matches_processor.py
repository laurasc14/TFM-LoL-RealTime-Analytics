import os
import json
import logging
from typing import Any, Dict, List

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

LOG = logging.getLogger("processor")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin@mongo:27017/lol?authSource=admin")
DB_NAME = os.getenv("MONGO_DB", "lol")
RAW_COLL = os.getenv("MONGO_COLL_RAW", "matches_raw")
PROC_COLL = os.getenv("MONGO_COLL_PROCESSED", "matches_processed")

def safe_get(d: Dict, path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def transform(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae un doc compacto para análisis."""
    match_id = raw.get("match_id")
    metadata = raw.get("metadata", {})
    info = raw.get("info", {})

    participants = info.get("participants", []) or []
    proc_participants = []
    for p in participants:
        proc_participants.append({
            "puuid": p.get("puuid"),
            "summonerName": p.get("summonerName"),
            "championName": p.get("championName"),
            "teamId": p.get("teamId"),
            "kills": p.get("kills"),
            "deaths": p.get("deaths"),
            "assists": p.get("assists"),
            "win": p.get("win"),
            "goldEarned": p.get("goldEarned"),
            "totalDamageDealtToChampions": p.get("totalDamageDealtToChampions"),
            "totalMinionsKilled": p.get("totalMinionsKilled"),
            "neutralMinionsKilled": p.get("neutralMinionsKilled"),
            "cs": (p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)),
            "kda": (
                (p.get("kills", 0) + p.get("assists", 0)) / max(1, p.get("deaths", 0))
            ),
            "role": p.get("role") or p.get("teamPosition"),
        })

    doc = {
        "match_id": match_id,
        "dataVersion": metadata.get("dataVersion"),
        "gameId": info.get("gameId"),
        "gameMode": info.get("gameMode"),
        "queueId": info.get("queueId"),
        "gameDuration": info.get("gameDuration"),
        "gameStartTimestamp": info.get("gameStartTimestamp"),
        "participants": proc_participants,
        "teams": info.get("teams"),  # útil para victorias por teamId
    }
    return doc

def is_complete(raw: Dict[str, Any]) -> bool:
    """Filtro rápido para evitar guardar partidas muy incompletas."""
    if "info" not in raw or "metadata" not in raw:
        return False
    info = raw["info"]
    if "participants" not in info or not isinstance(info["participants"], list) or len(info["participants"]) == 0:
        return False
    # gameDuration y dataVersion suelen ser buenos indicadores
    if "gameDuration" not in info or "dataVersion" not in raw.get("metadata", {}):
        return False
    return True

def main():
    LOG.info("Conectando a Mongo: %s", MONGO_URI)
    cli = MongoClient(MONGO_URI)
    db = cli[DB_NAME]
    raw = db[RAW_COLL]
    proc = db[PROC_COLL]

    # índices
    proc.create_index("match_id", unique=True)
    proc.create_index("participants.puuid")
    proc.create_index("gameMode")
    proc.create_index("queueId")

    # lee en lotes
    batch_size = int(os.getenv("PROC_BATCH", "500"))
    cursor = raw.find({}, {"_id": 0}).batch_size(batch_size)

    ops: List[UpdateOne] = []
    total = 0
    kept = 0
    for doc in cursor:
        total += 1
        if not is_complete(doc):
            continue
        kept += 1
        compact = transform(doc)
        ops.append(UpdateOne(
            {"match_id": compact["match_id"]},
            {"$set": compact},
            upsert=True
        ))

        # ejecuta en lotes
        if len(ops) >= batch_size:
            try:
                res = proc.bulk_write(ops, ordered=False)
                LOG.info("bulk_write ok: upserted=%s modified=%s matched=%s",
                         res.upserted_count, res.modified_count, res.matched_count)
            except BulkWriteError as e:
                LOG.warning("bulk_write con conflictos: %s", e.details.get("writeErrors"))
            ops = []

    # cola final
    if ops:
        try:
            res = proc.bulk_write(ops, ordered=False)
            LOG.info("bulk_write fin: upserted=%s modified=%s matched=%s",
                     res.upserted_count, res.modified_count, res.matched_count)
        except BulkWriteError as e:
            LOG.warning("bulk_write fin con conflictos: %s", e.details.get("writeErrors"))

    LOG.info("Total raw=%s | procesadas=%s | descartadas=%s", total, kept, total - kept)
    cli.close()

if __name__ == "__main__":
    main()
