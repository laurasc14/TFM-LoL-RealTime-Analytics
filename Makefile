PROJECT_NAME = tfm
DOCKER_COMPOSE = docker compose -p $(PROJECT_NAME) -f docker-compose.yml

.PHONY: up down reset logs ps create-topic list-topics produce consume

# === DOCKER ===
up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down -v --remove-orphans

reset:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker network prune -f
	docker volume prune -f
	docker system prune -f
	$(DOCKER_COMPOSE) up -d --build

logs:
	$(DOCKER_COMPOSE) logs -f

ps:
	$(DOCKER_COMPOSE) ps

# === KAFKA ===
create-topic:
	docker exec -it kafka kafka-topics.sh --create --if-not-exists \
		--topic $(name) \
		--partitions $(or $(partitions),1) \
		--replication-factor $(or $(replication),1) \
		--bootstrap-server kafka:9092

list-topics:
	docker exec -it kafka kafka-topics.sh --list --bootstrap-server kafka:9092

produce:
	docker exec -it kafka kafka-console-producer.sh --broker-list kafka:9092 --topic $(topic)

consume:
	docker exec -it kafka kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic $(topic) --from-beginning

producer:
	./producer.sh

consumer:
	./consumer.sh

seed:
	./seed.sh

init-topics:
	./init-topics.sh

producer-matches:
	./producer-matches.sh

init-topics:
	docker compose run --rm kafka-init

recreate-topics:
	$(DOCKER_COMPOSE) run --rm init-topics

# Ejecutar el productor mock
producer:
	docker exec -it final-ingestion python src/ingestion/producer_mock.py

# Ejecutar el consumidor mock (si quieres probar)
consumer:
	docker exec -it final-ingestion python src/ingestion/consumer_mock.py

# Entrar a la shell de MongoDB
mongo:
	docker exec -it final-mongo mongosh

check-mongo:
	docker exec -it final-mongo mongosh lol_realtime --eval "db.matches.find().pretty()"

smoke:
	docker compose ps
	docker exec -it kafka1 /usr/bin/kafka-topics --bootstrap-server kafka1:9092 --describe --topic matches
	docker logs --tail 50 final-riot-fetcher
	docker logs --tail 50 final-kafka-consumer
	docker exec -it final-mongo mongosh "mongodb://admin:admin@mongo:27017/admin" --eval "use('lol'); db.matches_raw.countDocuments()"
	docker exec -it final-mongo mongosh "mongodb://admin:admin@mongo:27017/admin" --eval "use('lol'); db.matches_raw.find({}, {_id:0, match_id:1}).limit(5).toArray()"
