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
