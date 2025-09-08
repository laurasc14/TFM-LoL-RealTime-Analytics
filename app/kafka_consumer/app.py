import os
import json
import logging
import signal
import sys
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("match-expander")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "final-kafka:9092")
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://app:appsecret@final-mongo:27017/lol_realtime?authSource=lol_realtime"
)
TOPIC_RAW = os.getenv("TOPIC_RAW", "lol.raw")
TOPIC_EXPANDED = os.getenv("TOPIC_EXPANDED", "lol.expanded")
MONGO_DB = os.getenv("MONGO_DB", "lol_realtime")
MONGO_COLL = os.getenv("MONGO_COLL", "matches_full")

running = True

def shutdown(signum, frame):
    global running
    logger.info("[match-expander] Apagado limpio.")
    running = False

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def main():
    logger.info("[match-expander] Conectando a Mongo y Kafka...")

    # Mongo
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    coll = db[MONGO_COLL]

    # Consumer
    consumer = KafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=[KAFKA_BROKER],
        group_id="match-expander",
        value_deserializer=lambda b: b,  # Recibir bytes
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    # Producer
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    logger.info(f"[match-expander] Escuchando {TOPIC_RAW} -> {TOPIC_EXPANDED}")

    for msg in consumer:
        if not running:
            break

        try:
            payload = json.loads(msg.value.decode("utf-8"))
        except Exception as e:
            logger.warning(
                f"[match-expander] Mensaje inválido en offset {msg.offset}: "
                f"{msg.value!r} ({e}) — se ignora."
            )
            continue

        logger.info(f"[match-expander] Procesando {payload}")

        # Añadimos campo extra
        payload["expanded_at"] = int(datetime.utcnow().timestamp())

        # Guardar en Mongo
        try:
            coll.update_one(
                {"match_id": payload["match_id"]},
                {"$set": payload},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"[match-expander] Error guardando en Mongo: {e}")

        # Enviar al topic expanded
        try:
            producer.send(TOPIC_EXPANDED, value=payload)
            producer.flush()
        except Exception as e:
            logger.error(f"[match-expander] Error produciendo a Kafka: {e}")

    consumer.close()
    producer.close()
    client.close()
    logger.info("[match-expander] Finalizado.")

if __name__ == "__main__":
    main()
