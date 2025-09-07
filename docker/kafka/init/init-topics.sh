#!/bin/bash
set -e

echo "⏳ Esperando a que Kafka esté listo..."
while ! nc -z localhost 9092; do
  sleep 1
done

echo "✅ Kafka está arriba, creando topics..."

for topic in matches players events; do
  kafka-topics --create \
    --if-not-exists \
    --topic $topic \
    --bootstrap-server localhost:9092 \
    --partitions 1 \
    --replication-factor 1
done

echo "🎉 Topics inicializados correctamente."
