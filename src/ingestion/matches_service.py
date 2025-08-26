# src/ingestion/matches_service.py
import json
import logging
import os
import sys
import time
from typing import Any, Dict

from kafka import KafkaConsumer
from pymongo import MongoClient, errors as mongo_errors

# Carga opcional desde env_config, pero SIEMPRE priorizando os.getenv
try:
    from src.config.env_config import get_env_config  # type: ignore
except Exception:
    def get_env_config() -> Dict[str, Any]:
        # Fallback por si no existe el módulo en tu build
        return {
            "KAFKA_BOOTSTRAP": "final-kafka:9092",
            "KAFKA_TOPIC": "matches",
            "GROUP_ID": "final-consumer",
            "MONGO_URI": "mongodb://final-mongo:27017/lol",
            "MONGO_DB": "lol",
            "MONGO_COLL": "matches",
            "LOG_LEVEL": "INFO",
        }

# ---------- Config & logging ----------
_cfg = get_env_config()

def _env(name: str, default: str) -> str:
    """Lee de entorno y si no, del env_config (que ya tiene defaults seguros)."""
    return os.getenv(name, _cfg.get(name, default))

LOG_LEVEL = _env("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")
log = logging.getLogger("consumer")

KAFKA_BOOTSTRAP = _env("KAFKA_BOOTSTRAP", "final-kafka:9092")
KAFKA_TOPIC = _env("KAFKA_TOPIC", "matches")
GROUP_ID = _env("GROUP_ID", "final-consumer")

MONGO_URI = _env("MONGO_URI", "mongodb://final-mongo:27017/lol")
MONGO_DB = _env("MONGO_DB", "lol")
MONGO_COLL = _env("MONGO_COLL", "matches")

# ---------- Mongo ----------
def _mongo_connect():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
    db = client[MONGO_DB]
    coll = db[MONGO_COLL]
    # Validar conexión
    client.admin.command("ping")
    # Asegurar índice único en match_id (idempotente)
    try:
        coll.create_index("match_id", unique=True)
    except mongo_errors.PyMongoError as ie:
        log.warning(f"[consumer] no se pudo crear índice único match_id: {ie}")
    return client, db, coll

# ---------- Kafka ----------
def _kafka_consumer():
    # auto_offset_reset='latest' para no reprocesar histórico al reiniciar
    # enable_auto_commit=True confirma periódicamente
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="latest",
        consumer_timeout_ms=0,
        max_poll_interval_ms=300000,
    )

def _upsert_match(coll, payload: Dict[str, Any]) -> None:
    """Upsert por match_id; tolera duplicados concurrentes."""
    try:
        coll.update_one(
            {"match_id": payload.get("match_id")},
            {"$set": payload},
            upsert=True,
        )
    except mongo_errors.DuplicateKeyError:
        # Otro proceso/hilo pudo insertar antes: normal con unique index
        pass
    except mongo_errors.PyMongoError as me:
        log.error(f"[consumer] error Mongo: {me}, full error: {getattr(me, 'details', {})}")

def main():
    log.info(f"[consumer] bootstrap={KAFKA_BOOTSTRAP} topic={KAFKA_TOPIC} group_id={GROUP_ID}")

    # Conecta a Mongo
    try:
        client, db, coll = _mongo_connect()
        log.info("[consumer] conectado a Mongo y suscrito a matches")
    except Exception as e:
        log.error(f"[consumer] error conectando a Mongo: {e}")
        sys.exit(1)

    # Crea consumer Kafka
    consumer = _kafka_consumer()

    while True:
        try:
            for msg in consumer:
                payload = msg.value  # dict
                log.info(f"[consumer] recibido: {payload}")
                _upsert_match(coll, payload)
        except Exception as e:
            log.error(f"[consumer] bucle error: {e}")
            time.sleep(1.5)

if __name__ == "__main__":
    # Desactiva buffering de stdout
    try:
        os.environ.setdefault("PYTHONUNBUFFERED", "1")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    main()
