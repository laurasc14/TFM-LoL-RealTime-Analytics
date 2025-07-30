import json
from kafka import KafkaProducer
from kafka.errors import KafkaError

KAFKA_BROKER = "127.0.0.1:9092"
TOPIC = "tfm-events"

def main():
    try:
        # Inicializar productor
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        print(f"✅ Productor conectado a {KAFKA_BROKER}")

        # Evento de ejemplo
        event = {
            "event": "match_summary",
            "data": {
                "match_id": "ABCD1234",
                "winner": "TEAM_100",
                "kills": {"TEAM_100": 25, "TEAM_200": 18}
            }
        }

        # Enviar evento
        future = producer.send(TOPIC, event)
        result = future.get(timeout=10)
        print(f"📤 Evento enviado a {TOPIC}: {result}")

    except KafkaError as ke:
        print(f"❌ Error de Kafka: {ke}")
    except Exception as e:
        print(f"❌ Error general: {e}")
    finally:
        try:
            producer.close()
            print("🔒 Productor cerrado.")
        except:
            pass

if __name__ == "__main__":
    main()
