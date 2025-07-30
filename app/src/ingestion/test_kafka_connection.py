
import time
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = "localhost:9092"  # O usa "host.docker.internal:9092" si estás en contenedor

print(f"🔌 Conectando a Kafka en {KAFKA_BROKER}...")
print("⏳ Esperando que Kafka termine de iniciar...")
time.sleep(10)  # Espera de seguridad

try:
    producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER)
    print("✅ Conexión exitosa a Kafka.")
except NoBrokersAvailable:
    print("❌ No se pudo conectar a Kafka: NoBrokersAvailable")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
