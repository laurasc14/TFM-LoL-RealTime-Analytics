import json, os, sys, time
from kafka import KafkaConsumer, KafkaProducer
from pymongo import MongoClient

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "final-kafka:9092")
IN_TOPIC      = os.getenv("IN_TOPIC", "lol.raw")
OUT_TOPIC     = os.getenv("OUT_TOPIC", "lol.expanded")
MONGO_URI     = os.getenv("MONGO_URI", "mongodb://final-mongo:27017")
MONGO_DB      = os.getenv("DB", "lol_realtime")
COLLECTION    = os.getenv("COLL", "matches_full")

def log(*a): print(*a, flush=True)

def connect_mongo():
    while True:
        try:
            client = MongoClient(MONGO_URI)
            client.admin.command("ping")
            return client
        except Exception as e:
            log("[match-expander] Mongo no disponible aún:", e)
            time.sleep(2)

def connect_kafka():
    while True:
        try:
            consumer = KafkaConsumer(
                IN_TOPIC,
                bootstrap_servers=KAFKA_BROKERS.split(","),
                group_id="match-expander",
                enable_auto_commit=True,
                auto_offset_reset="earliest",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKERS.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            return consumer, producer
        except Exception as e:
            log("[match-expander] Kafka no disponible aún:", e)
            time.sleep(2)

def expand_event(evt: dict) -> dict:
    # Ejemplo tonto de “expandir” el evento:
    out = dict(evt)
    out["expanded"] = True
    out["processed_at"] = int(time.time())
    return out

def main():
    log(f"[match-expander] Conectando a Mongo y Kafka...")
    mongo = connect_mongo()
    db = mongo[MONGO_DB]
    col = db[COLLECTION]

    consumer, producer = connect_kafka()
    log(f"[match-expander] Escuchando {IN_TOPIC} -> {OUT_TOPIC}")

    for msg in consumer:
        try:
            event_in = msg.value
            expanded = expand_event(event_in)

            # Guardar en Mongo
            col.insert_one(expanded)

            # Re-publicar a Kafka
            producer.send(OUT_TOPIC, expanded)
            producer.flush()

            log("[match-expander] OK:", expanded.get("event_id", "?"))
        except Exception as e:
            log("[match-expander] Error procesando mensaje:", e)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
