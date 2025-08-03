# src/ingestion/producer_mock.py
import json
import time
import logging
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

KAFKA_BROKER = "kafka1:9092"
TOPIC = "matches"

# Intentar conectar con Kafka con reintentos
for attempt in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logging.info("Conectado a Kafka en %s", KAFKA_BROKER)
        break
    except NoBrokersAvailable:
        logging.warning("Kafka no disponible. Reintentando (%d/5)...", attempt + 1)
        time.sleep(5)
else:
    logging.error("No se pudo conectar a Kafka después de varios intentos.")
    exit(1)

# Mensajes mock
mock_data = [
    {"match_id": "001", "team1": "Azul", "team2": "Rojo", "winner": "Azul"},
    {"match_id": "002", "team1": "Verde", "team2": "Amarillo", "winner": "Amarillo"},
]

for msg in mock_data:
    producer.send(TOPIC, msg)
    logging.info("Mensaje enviado a %s: %s", TOPIC, msg)
    time.sleep(2)

producer.flush()
logging.info("Producción finalizada.")
