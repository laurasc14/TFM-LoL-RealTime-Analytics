#!/bin/bash
docker exec -it kafka1 kafka-console-producer.sh \
  --broker-list kafka1:9092 \
  --topic test
