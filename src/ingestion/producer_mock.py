import json
import os
import time
from kafka import KafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "final-kafka:9092")
TOPIC = os.getenv("TOPIC", "matches")

def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        api_version_auto_timeout_ms=5000,
    )
    print(f"[producer] conectado a {BOOTSTRAP}")

    msgs = [
        {"match_id": "001", "team1": "Azul", "team2": "Rojo", "winner": "Azul"},
        {"match_id": "002", "team1": "Verde", "team2": "Amarillo", "winner": "Amarillo"},
    ]

    for m in msgs:
        producer.send(TOPIC, m)
        print(f"[producer] enviado a {TOPIC}: {m}")
        time.sleep(2)

    producer.flush()
    producer.close()
    print("[producer] listo ✓")

if __name__ == "__main__":
    main()
