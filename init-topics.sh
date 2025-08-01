#!/bin/bash
# Esperar a que Kafka esté listo
sleep 10
echo "Creando topic 'test'..."
kafka-topics.sh --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --replication-factor 1 \
  --partitions 1 \
  --topic test
