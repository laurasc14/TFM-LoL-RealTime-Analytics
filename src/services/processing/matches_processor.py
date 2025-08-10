import logging
from pymongo import MongoClient, UpdateOne
from src.config.env_config import get_env_config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("processor")


def display_name(p):
    """
    Devuelve un nombre visible para el jugador.
    Si summonerName está vacío, construye a partir de riotIdGameName + riotIdTagline.
    """
    name = (p.get("summonerName") or "").strip()
    if name:
        return name
    g = (p.get("riotIdGameName") or "").strip()
    t = (p.get("riotIdTagline") or "").strip()
    if g and t:
        return f"{g}#{t}"
    if g:
        return g
    return p.get("puuid", "") or ""


def process_match(doc):
    """
    Procesa un documento raw y devuelve uno listo para matches_processed.
    """
    info = doc.get("info", {})
    participants = [
        {
            "summonerName": display_name(p),
            "championName": p.get("championName", ""),
            "kills": p.get("kills", 0) or 0,
            "deaths": p.get("deaths", 0) or 0,
            "assists": p.get("assists", 0) or 0,
            "win": bool(p.get("win", False)),
            "teamId": p.get("teamId", None),
            "kda": round(
                (p.get("kills", 0) + p.get("assists", 0)) / (p.get("deaths", 0) or 1), 3
            ),
        }
        for p in info.get("participants", [])
    ]

    return {
        "match_id": doc.get("match_id", ""),
        "gameMode": info.get("gameMode", ""),
        "gameDuration": info.get("gameDuration", 0),
        "participants": participants,
    }


def main():
    cfg = get_env_config()
    mongo_uri = cfg["MONGO_URI"]

    log.info(f"Conectando a Mongo: {mongo_uri}")
    cli = MongoClient(mongo_uri)

    raw_coll = cli.lol.matches_raw
    proc_coll = cli.lol.matches_processed

    bulk_ops = []
    total_raw = 0
    total_proc = 0
    total_disc = 0

    for doc in raw_coll.find({}):
        total_raw += 1
        if not doc.get("info") or not doc.get("metadata"):
            total_disc += 1
            continue

        processed = process_match(doc)
        bulk_ops.append(
            UpdateOne(
                {"match_id": processed["match_id"]},
                {"$set": processed},
                upsert=True,
            )
        )
        total_proc += 1

    if bulk_ops:
        result = proc_coll.bulk_write(bulk_ops)
        log.info(
            f"bulk_write fin: upserted={len(result.upserted_ids)} "
            f"modified={result.modified_count} matched={result.matched_count}"
        )

    log.info(
        f"Total raw={total_raw} | procesadas={total_proc} | descartadas={total_disc}"
    )


if __name__ == "__main__":
    main()
