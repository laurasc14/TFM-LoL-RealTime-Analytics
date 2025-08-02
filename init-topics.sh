#!/bin/bash
echo "Esperando a que Kafka esté disponible..."

# Esperar hasta que Kafka responda
until kafka-topics.sh --bootstrap-server kafka1:9092 --list &>/dev/null; do
  echo "Kafka no está listo, reintentando en 2 segundos..."
  sleep 2
done

echo "Kafka disponible. Creando tópicos..."
kafka-topics.sh --create --if-not-exists --topic matches --partitions 3 --replication-factor 1 --bootstrap-server kafka1:9092
kafka-topics.sh --create --if-not-exists --topic players --partitions 3 --replication-factor 1 --bootstrap-server kafka1:9092
kafka-topics.sh --create --if-not-exists --topic events --partitions 3 --replication-factor 1 --bootstrap-server kafka1:9092

echo "Tópicos iniciales creados: matches, players, events"
