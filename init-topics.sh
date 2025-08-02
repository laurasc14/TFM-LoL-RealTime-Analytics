#!/bin/bash
echo "Esperando a Kafka..."
sleep 10

BROKER="kafka1:9092"

create_topic() {
  local topic=$1
  local partitions=$2
  local replication=$3
  local retention=$4

  kafka-topics.sh --bootstrap-server $BROKER --list | grep -q "^$topic$"
  if [ $? -eq 0 ]; then
    echo "El tópico '$topic' ya existe, omitiendo..."
  else
    echo "Creando tópico '$topic' con $partitions particiones, factor $replication y retención $retention ms..."
    kafka-topics.sh --create \
      --if-not-exists \
      --topic "$topic" \
      --partitions "$partitions" \
      --replication-factor "$replication" \
      --config retention.ms="$retention" \
      --bootstrap-server "$BROKER"
  fi
}

create_topic "lol-matches" 6 3 604800000
create_topic "lol-players" 6 3 604800000
create_topic "lol-events" 6 3 259200000

echo "Tópicos inicializados correctamente."
