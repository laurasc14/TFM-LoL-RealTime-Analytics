# app.py
import json
import os
import signal
import sys
import time
from typing import Any, Dict

from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

# -------------------------------
# Config
# -------------------------------
load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "final-kafka:9092")
IN_TOPIC = os.getenv("IN_TOPIC", "lol.raw")
OUT_TOPIC = os.getenv("OUT_TOPIC", "lol.expanded")
GROUP_ID = os.getenv("GROUP_ID", "match-expander")

MONGO_HOST = os.getenv("MONGO_HOST", "final-mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "lol_realtime")
MONGO_COLL = os.getenv("MONGO_COLL", "matches_full")
# En Docker oficial de Mongo, el root está en admin:
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
MONGO_AUTH_DB = os.getenv("MONGO_AUTH_DB", "admin")

# -------------------------------
# Utils
# -------------------------------

def log(*args: Any) -> None:
    print(*args, flush=True)

def connect_mongo() -> MongoClient:
    if MONGO_USER and MONGO_PASS:
        uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/?authSource={MONGO_AUTH_DB}"
    else:
        uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
    return MongoClient(uri)

def ensure_indexes(col) -> None:
    # Índice único por match_id (ya lo tienes creado, pero aseguramos por si acaso)
    try:
        col.create_index([("match_id", ASCENDING)], unique=True, name="match_id_1")
    except PyMongoError as e:
        log("[match-expander] Aviso creando índice:", repr(e))

# Si ya tienes una función real de expansión, reemplaza esta.
def expand_event(evt: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotente: devuelve el payload enriquecido. Debe incluir match_id."""
    out = dict(evt)
    # ejemplo de pequeño enriquecimiento
    out.setdefault("expanded_at", int(time.time()))
    return out

# -------------------------------
# Main
# -------------------------------

_running = True
def _graceful_exit(signum, frame):
    global _running
    _running = False

signal.signal(signal.SIGINT, _graceful_exit)
signal.signal(signal.SIGTERM, _graceful_exit)

def main():
    log("[match-expander] Conectando a Mongo y Kafka...")

    client = connect_mongo()
    db = client[MONGO_DB]
    col = db[MONGO_COLL]
    ensure_indexes(col)

    consumer = KafkaConsumer(
        IN_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        enable_auto_commit=True,
        auto_offset_reset=os.getenv("AUTO_OFFSET_RESET", "latest"),  # 'latest' por defecto
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        linger_ms=10,
        acks="all",
    )

    log(f"[match-expander] Escuchando {IN_TOPIC} -> {OUT_TOPIC}")

    try:
        for msg in consumer:
            if not _running:
                break

            try:
                event_in = msg.value or {}
                expanded = expand_event(event_in)

                if "match_id" not in expanded:
                    # Si no hay match_id, no podemos upsertear de forma estable.
                    log("[match-expander] Evento sin match_id; se ignora:", expanded)
                    continue

                # ✅ Upsert: evita E11000 duplicados
                col.update_one(
                    {"match_id": expanded["match_id"]},
                    {"$set": expanded},
                    upsert=True,
                )

                # Publica al topic de salida
                producer.send(OUT_TOPIC, expanded)
                producer.flush()

            except DuplicateKeyError:
                # Por si existía el índice único y justo colisiona:
                try:
                    col.update_one(
                        {"match_id": expanded["match_id"]},
                        {"$set": expanded},
                        upsert=True,
                    )
                except PyMongoError as e:
                    log("[match-expander] Error procesando mensaje (dup):", repr(e))

            except PyMongoError as e:
                log("[match-expander] Error Mongo:", repr(e))

            except Exception as e:
                log("[match-expander] Error procesando mensaje:", repr(e))
    finally:
        try:
            consumer.close()
        except Exception:
            pass
        try:
            producer.flush(5)
            producer.close()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
        log("[match-expander] Apagado limpio.")

if __name__ == "__main__":
    main()
