import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer
from motor.motor_asyncio import AsyncIOMotorClient
from riotwatcher import LolWatcher, ApiError

from src.config.env_config import get_env_config

LOG = logging.getLogger("consumer")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

cfg = get_env_config()

# 🔑 API key
RIOT_API_KEY = os.getenv("RIOT_API_KEY") or cfg.get("RIOT_API_KEY")

RIOT_ROUTING = cfg.get("RIOT_ROUTING", "europe")  # por defecto europe (EUW/EUNE)

KAFKA_BOOTSTRAP = cfg.get("KAFKA_BOOTSTRAP_SERVERS", "final-kafka:9092")
KAFKA_TOPIC = cfg.get("KAFKA_TOPIC", "matches")
KAFKA_GROUP = cfg.get("KAFKA_GROUP_ID", "lol-consumer")

MONGO_URI = cfg.get("MONGO_URI", "mongodb://admin:admin@mongo:27017/lol?authSource=admin")
MONGO_DB = cfg.get("MONGO_DB", "lol")
MONGO_COLL = cfg.get("MONGO_COLLECTION", "matches_raw")

watcher = LolWatcher(RIOT_API_KEY) if RIOT_API_KEY else None


@asynccontextmanager
async def mongo_client(uri: str):
    client = AsyncIOMotorClient(uri)
    try:
        await client.admin.command("ping")
        yield client
    finally:
        client.close()


async def fetch_match_detail(match_id: str) -> dict:
    """
    Pide el match completo a Riot. Si no hay API key, devuelve stub con solo match_id.
    Ejecuta la llamada bloqueante de riotwatcher en un executor para no bloquear el loop.
    """
    if not watcher:
        LOG.warning("RIOT_API_KEY no definida; guardo solo match_id")
        return {"match_id": match_id}

    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(None, lambda: watcher.match.by_id(RIOT_ROUTING, match_id))
        if isinstance(data, dict):
            data.setdefault("match_id", match_id)
        else:
            data = {"match_id": match_id}
        return data
    except ApiError as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code == 429:
            LOG.warning("Rate limited (429) al pedir %s; reintento breve", match_id)
            await asyncio.sleep(2)
            return await fetch_match_detail(match_id)
        if code == 404:
            LOG.warning("Match %s no encontrado (404); guardo stub", match_id)
            return {"match_id": match_id}
        LOG.error("ApiError %s al pedir %s: %s", code, match_id, e)
        return {"match_id": match_id}
    except Exception as e:
        LOG.exception("Error inesperado al pedir %s: %s", match_id, e)
        return {"match_id": match_id}


async def run():
    LOG.info("BOOTSTRAP=%s TOPIC=%s GROUP=%s", KAFKA_BOOTSTRAP, KAFKA_TOPIC, KAFKA_GROUP)
    LOG.info("MONGO_URI=%s DB=%s COLL=%s", MONGO_URI, MONGO_DB, MONGO_COLL)

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        group_id=KAFKA_GROUP,
        enable_auto_commit=True,
        auto_offset_reset=os.getenv("AUTO_OFFSET_RESET", "latest"),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    try:
        async with mongo_client(MONGO_URI) as mcli:
            coll = mcli[MONGO_DB][MONGO_COLL]

            # ✅ Solo crear índice si no existe
            existing_indexes = await coll.index_information()
            if not any("match_id" in idx["key"][0] for idx in existing_indexes.values()):
                await coll.create_index("match_id", unique=True)

            async for msg in consumer:
                match_id = msg.value.get("match_id")
                if not match_id:
                    continue

                # 🔎 1) pedir detalle
                doc = await fetch_match_detail(match_id)

                # 💾 2) upsert completo
                res = await coll.update_one(
                    {"match_id": match_id},
                    {"$set": doc},
                    upsert=True,
                )
                LOG.info("[mongo] upsert match_id=%s matched=%s modified=%s upserted_id=%s",
                         match_id, res.matched_count, res.modified_count, res.upserted_id)
    finally:
        await consumer.stop()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
