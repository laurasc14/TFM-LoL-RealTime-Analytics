import json
import os
import sys
import signal
from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import PyMongoError

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP") or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "final-kafka:9092")
TOPIC = os.getenv("TOPIC", "matches")
GROUP_ID = os.getenv("GROUP_ID", "final-consumer")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://appuser:appsecret@final-mongo:27017/lol?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB_NAME", "lol")
MONGO_COL = os.getenv("MONGO_COLLECTION", "matches")

stop = False
def _handle_sigterm(*_):
    global stop
    stop = True
signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

def mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return client, db[MONGO_COL]

def main():
    print(f"[consumer] bootstrap={BOOTSTRAP} topic={TOPIC} group_id={GROUP_ID}")
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        api_version_auto_timeout_ms=5000,
    )

    client, col = mongo_collection()
    print(f"[consumer] conectado a Mongo y suscrito a {TOPIC}")

    try:
        for msg in consumer:
            if stop:
                break
            doc = msg.value
            print(f"[consumer] recibido: {doc}")
            try:
                col.update_one({"match_id": doc.get("match_id")}, {"$set": doc}, upsert=True)
            except PyMongoError as e:
                print(f"[consumer] error Mongo: {e}", file=sys.stderr)
    finally:
        consumer.close()
        client.close()
        print("[consumer] cerrado ✓")

if __name__ == "__main__":
    main()
