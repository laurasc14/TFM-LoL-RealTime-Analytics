import os, sys, asyncio, json
import requests
import urllib.parse
from aiokafka import AIOKafkaProducer

# Aseguramos acceso al config/config.py del proyecto
from src.config.config import RIOT_API_KEY

REGION_ROUTING = "europe"
MATCH_COUNT = 5
SUMMONER_NAME = os.getenv("SUMMONER_NAME", "PlayerName#EUW")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "events_raw"

def get_puuid_from_riot_id(riot_id):
    game_name, tag_line = riot_id.split("#")
    encoded_name = urllib.parse.quote(game_name)
    url = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    return data["puuid"], data["gameName"], data["tagLine"]

def get_match_ids(puuid, count):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params = {"start": 0, "count": count}
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

def get_match_summary(match_id, my_puuid):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return None
    data = res.json()
    summary = {
        "match_id": match_id,
        "gameMode": data['info']['gameMode'],
        "duration": data['info']['gameDuration'],
        "teams": {100: {"result": None, "players": []}, 200: {"result": None, "players": []}}
    }
    for p in data['info']['participants']:
        tid = p['teamId']
        if summary['teams'][tid]["result"] is None:
            summary['teams'][tid]["result"] = "WIN" if p['win'] else "LOSE"
        summary['teams'][tid]["players"].append({
            "summoner": p['summonerName'],
            "champion": p['championName'],
            "kda": f"{p['kills']}/{p['deaths']}/{p['assists']}",
            "is_you": p['puuid'] == my_puuid
        })
    return summary

async def send_to_kafka(producer, data):
    await producer.send_and_wait(TOPIC, json.dumps(data).encode())

async def create_kafka_producer(bootstrap_servers, retries=5, delay=5):
    for attempt in range(retries):
        try:
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
            await producer.start()
            print("Kafka connection established.")
            return producer
        except Exception as e:
            print(f"Kafka connection failed ({e}). Retrying in {delay}s...")
            await asyncio.sleep(delay)
    raise RuntimeError("Failed to connect to Kafka after several retries.")

async def main():
    puuid, game_name, tag = get_puuid_from_riot_id(SUMMONER_NAME)
    producer = await create_kafka_producer(KAFKA_BOOTSTRAP)
    try:
        match_ids = get_match_ids(puuid, MATCH_COUNT)
        for mid in match_ids:
            summary = get_match_summary(mid, puuid)
            if summary:
                await send_to_kafka(producer, summary)
                print(f"Sent match {mid} to Kafka")
        print("All matches sent.")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())
