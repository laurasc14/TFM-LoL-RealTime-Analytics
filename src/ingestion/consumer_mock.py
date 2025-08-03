# src/ingestion/consumer_mock.py
import json
import logging
from kafka import KafkaConsumer
from pymongo import MongoClient, errors

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

KAFKA_BROKER = "kafka1:9092"
TOPIC = "matches"
MONGO_URI = "mongodb://final-mongo:27017/"
DB_NAME = "lol_realtime"
COLLECTION_NAME = "matches"

# Conexión a MongoDB
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[DB_NAME]
    collection = db[COLLECTION_NAME]
    logging.info("Conectado a MongoDB en %s", MONGO_URI)
except errors.ConnectionFailure:
    logging.error("No se pudo conectar a MongoDB.")
    exit(1)

# Conexión a Kafka
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)
logging.info("Escuchando mensajes en el topic '%s'...", TOPIC)

# Consumo e inserción
for message in consumer:
    data = message.value
    try:
        collection.insert_one(data)
        logging.info("Insertado en MongoDB: %s", data)
    except Exception as e:
        logging.error("Error insertando el mensaje %s: %s", data, e)
