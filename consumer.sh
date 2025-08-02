#!/bin/bash
docker exec -it kafka1 kafka-console-consumer.sh \
  --bootstrap-server kafka1:9092 \
  --topic test \
  --from-beginning
