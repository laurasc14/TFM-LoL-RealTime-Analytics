#!/bin/sh
host="kafka"
port="9092"

echo "Esperando a que Kafka esté disponible en $host:$port..."
while ! nc -z $host $port; do
  sleep 1
done

echo "Kafka está disponible, iniciando servicio..."
exec "$@"
