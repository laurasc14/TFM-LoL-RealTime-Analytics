import time
import json
from kafka import KafkaProducer
from datetime import datetime
import random

TOPIC = "matches"
BOOTSTRAP_SERVERS = ['kafka1:9092', 'kafka2:9093', 'kafka3:9094']

# Función para generar datos simulados
def generar_dato():
    return {
        "match_id": random.randint(1000, 9999),
        "player": random.choice(["Player1", "Player2", "Player3"]),
        "score": random.randint(0, 20),
        "timestamp": datetime.utcnow().isoformat()
    }

# Intentar conexión a Kafka con reintentos
producer = None
while not producer:
    try:
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("✅ Conectado a Kafka.")
    except Exception as e:
        print(f"❌ Kafka no disponible: {e}. Reintentando en 5s...")
        time.sleep(5)

# Enviar datos cada 2 segundos
print(f"📤 Enviando datos simulados al topic '{TOPIC}'...")
while True:
    data = generar_dato()
    producer.send(TOPIC, value=data)
    print(f"Enviado: {data}")
    time.sleep(2)
