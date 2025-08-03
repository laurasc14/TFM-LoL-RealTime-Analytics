import time
import json
from kafka import KafkaConsumer
from pymongo import MongoClient

TOPIC = "matches"
BOOTSTRAP_SERVERS = ['kafka1:9092', 'kafka2:9093', 'kafka3:9094']
MONGO_URI = "mongodb://final-mongo:27017/"
DB_NAME = "tfm"
COLLECTION_NAME = "matches"

# Conectar a MongoDB
print("Conectando a MongoDB...")
mongo_client = None
while not mongo_client:
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print(f"✅ Conectado a MongoDB. Guardando en {DB_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}. Reintentando en 5s...")
        time.sleep(5)

# Conectar a Kafka con reintentos
print("Conectando a Kafka...")
consumer = None
while not consumer:
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='consumer-group-1'
        )
        print(f"✅ Conectado a Kafka. Escuchando el topic '{TOPIC}'...")
    except Exception as e:
        print(f"❌ Kafka no disponible: {e}. Reintentando en 5s...")
        time.sleep(5)

# Procesar mensajes
for message in consumer:
    try:
        match_data = message.value
        if isinstance(match_data, dict):
            collection.insert_one(match_data)
            print(f"📥 Insertado en MongoDB: {match_data}")
        else:
            print(f"⚠️ Mensaje descartado (no es un dict): {match_data}")
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
