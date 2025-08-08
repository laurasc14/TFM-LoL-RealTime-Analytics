import os
import sys
import asyncio
import json
import time
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from riotwatcher import RiotWatcher, LolWatcher

# Config paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Cargar RIOT_API_KEY (solo desde config.py)
from src.config.config import RIOT_API_KEY
# Cargar variables del .env
from src.config.env_config import get_env_config

print("=== Riot Fetcher Starting ===")

# Cargar variables de entorno del contenedor
load_dotenv(dotenv_path="/app/.env")

env = get_env_config()
print("✔️ ENV VARS (desde env_config.py):")
print(f"KAFKA_BOOTSTRAP_SERVERS = {env['KAFKA_BOOTSTRAP_SERVERS']}")
print(f"SUMMONER_NAME = {env['SUMMONER_NAME']}")

# Configuración
API_KEY = RIOT_API_KEY
SUMMONER_NAME = env["SUMMONER_NAME"]
KAFKA_SERVERS = env["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = "matches"
REGION = "euw1"
PLATFORM_ROUTING = "europe"

rw = RiotWatcher(API_KEY)      # <-- para Account
lw = LolWatcher(API_KEY)      # <-- para LoL: match, summoner, etc

if not SUMMONER_NAME or not KAFKA_SERVERS:
    print("❌ SUMMONER_NAME o KAFKA_BOOTSTRAP_SERVERS no están definidos")
    exit(1)

print(f"Loaded config: Summoner={SUMMONER_NAME}, Kafka={KAFKA_SERVERS}")

# Obtener PUUID desde el Riot ID
def get_puuid():
    try:
        game_name, tag_line = SUMMONER_NAME.split("#", 1)
        account_info = rw.account.by_riot_id(PLATFORM_ROUTING, game_name, tag_line)
        puuid = account_info['puuid']
        print(f"✔️ PUUID obtenido: {puuid}")
        return puuid
    except Exception as e:
        print(f"❌ Error obteniendo PUUID: {e}")
        raise

# Obtener partidas recientes
def get_recent_matches(puuid):
    try:
        matches = lw.match.matchlist_by_puuid(PLATFORM_ROUTING, puuid, count=5)
        print(f"✔️ Matches recientes: {matches}")
        return matches
    except Exception as e:
        print(f"❌ Error obteniendo partidas: {e}")
        return []

# Main async loop
async def main():
    await asyncio.sleep(10)
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_SERVERS)
    await producer.start()
    try:
        print("✔️ Conectado a Kafka")

        puuid = get_puuid()

        while True:
            matches = get_recent_matches(puuid)
            for match_id in matches:
                data = {"match_id": match_id, "timestamp": time.time()}
                await producer.send_and_wait(TOPIC, json.dumps(data).encode("utf-8"))
                print(f"📤 Enviado a Kafka: {data}")
            await asyncio.sleep(60)
    finally:
        await producer.stop()

if __name__ == "__main__":
    print("⏳ Iniciando loop principal...")
    asyncio.run(main())
