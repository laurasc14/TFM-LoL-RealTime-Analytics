# src/processing/match_expander.py
import os
import time
import json
import logging
from kafka import KafkaConsumer, errors as kafka_errors
from pymongo import MongoClient, errors as mongo_errors
from riotwatcher import LolWatcher, ApiError

# --- logging ---
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("expander")

# --- entorno ---
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "final-kafka:9092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "matches")
GROUP_ID = os.getenv("GROUP_ID", "match-expander")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://final-mongo:27017/lol")
MONGO_DB = os.getenv("MONGO_DB", "lol")
OUT_COLL = os.getenv("OUT_COLL", "matches_full")

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
RIOT_ROUTE = os.getenv("RIOT_REGIONAL_ROUTE", "europe")
if not RIOT_API_KEY:
    raise SystemExit("[expander] Falta RIOT_API_KEY en variables de entorno.")

watcher = LolWatcher(RIOT_API_KEY)


# --- conexión Mongo con retry ---
def _mongo_connect(max_retries: int = 10, delay: float = 1.0):
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
            client.admin.command("ping")
            db = client[MONGO_DB]
            coll = db[OUT_COLL]
            try:
                coll.create_index("match_id", unique=True)
            except mongo_errors.PyMongoError as ie:
                log.warning(f"[expander] no se pudo crear índice único match_id: {ie}")
            return client, db, coll
        except Exception as e:
            last_err = e
            log.warning(f"[expander] Mongo no disponible (intento {attempt}/{max_retries}): {e}")
            time.sleep(delay)
            delay = min(delay * 1.5, 5.0)
    raise SystemExit(f"[expander] Mongo inaccesible tras {max_retries} intentos: {last_err}")


# --- conexión Kafka con retry ---
def _kafka_consumer_with_retry(max_retries: int = 12, delay: float = 2.0) -> KafkaConsumer:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            consumer = KafkaConsumer(
                INPUT_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                enable_auto_commit=True,
                auto_offset_reset="latest",
                consumer_timeout_ms=0,
                max_poll_interval_ms=900_000,  # 15 minutos
                request_timeout_ms=60_000,
                api_version=(2, 5, 0),  # evita el probe inicial
            )
            return consumer
        except Exception as e:
            last_err = e
            log.warning(f"[expander] Kafka no disponible (intento {attempt}/{max_retries}): {e}")
            time.sleep(delay)
            delay = min(delay * 1.5, 8.0)
    raise SystemExit(f"[expander] Kafka inaccesible tras {max_retries} intentos: {last_err}")


# --- lógica de expansión ---
def expand_and_upsert(coll, match_id: str):
    try:
        match = watcher.match.by_id(RIOT_ROUTE, match_id)
        coll.update_one(
            {"match_id": match_id},
            {"$set": {"match_id": match_id, "match": match}},
            upsert=True,
        )
        log.info(f"[expander] upsert OK {match_id} -> {OUT_COLL}")
    except ApiError as e:
        log.error(f"[expander] Riot API error {e}")
    except Exception as e:
        log.error(f"[expander] Error general al expandir {match_id}: {e}")


# --- main ---
def main():
    log.info(f"[expander] topic={INPUT_TOPIC} group_id={GROUP_ID} route={RIOT_ROUTE}")
    client, db, coll = _mongo_connect()
    consumer = _kafka_consumer_with_retry()

    while True:
        try:
            batch = consumer.poll(timeout_ms=1000, max_records=20)
            if not batch:
                continue
            for tp, msgs in batch.items():
                for msg in msgs:
                    payload = msg.value
                    match_id = payload.get("match_id")
                    if not match_id:
                        continue
                    log.info(f"[expander] recibido match_id={match_id}")
                    expand_and_upsert(coll, match_id)
            consumer.commit_async()
        except Exception as e:
            log.error(f"[expander] bucle error: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    main()
