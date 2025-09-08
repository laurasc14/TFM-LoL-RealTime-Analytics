import os, json, requests
from kafka import KafkaProducer

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
SUMMONER_NAME = os.getenv("SUMMONER_NAME")
REGION = os.getenv("RIOT_REGION")
ROUTE = os.getenv("RIOT_REGIONAL_ROUTE")
BROKERS = os.getenv("KAFKA_BROKERS", "final-kafka:9092")
TOPIC = os.getenv("IN_TOPIC", "matches")

def main():
    producer = KafkaProducer(bootstrap_servers=BROKERS.split(","), value_serializer=lambda v: json.dumps(v).encode())
    # Fetch PUUID, last matches, then details... (como te mostré antes)
    # Enviar cada detalle como mensaje
    producer.flush()

if __name__ == "__main__":
    main()
