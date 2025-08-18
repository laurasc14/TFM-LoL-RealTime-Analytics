import os
import asyncio
import time
import json
import argparse
import urllib.parse
import logging
from typing import List, Optional

import requests
from aiokafka import AIOKafkaProducer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fetcher")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9093,kafka3:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "matches")

# ------------- helpers Riot (HTTP simple, sin riotwatcher) ------------------

def riot_headers(api_key: str) -> dict:
    return {"X-Riot-Token": api_key}

def get_puuid_from_riot_id(region: str, game_name: str, tag_line: str, api_key: str) -> str:
    # region ejemplo "europe"
    base = f"https://{region}.api.riotgames.com"
    name = urllib.parse.quote(game_name, safe="")
    tag  = urllib.parse.quote(tag_line, safe="")
    url  = f"{base}/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    r = requests.get(url, headers=riot_headers(api_key), timeout=15)
    r.raise_for_status()
    return r.json()["puuid"]

def list_match_ids_by_puuid(platform: str, puuid: str, count: int, api_key: str) -> List[str]:
    # platform ejemplo "europe" para match-v5 (en EU también es 'europe')
    base = f"https://{platform}.api.riotgames.com"
    url  = f"{base}/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    r = requests.get(url, headers=riot_headers(api_key), timeout=20)
    r.raise_for_status()
    return r.json()

# ------------- productor Kafka ---------------------------------------------

async def produce_match_ids(match_ids: List[str]) -> None:
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP.split(","))
    await producer.start()
    try:
        for mid in match_ids:
            payload = json.dumps({"match_id": mid}).encode("utf-8")
            await producer.send_and_wait(KAFKA_TOPIC, payload)
        log.info("✅ Enviados %s match_id → topic=%s", len(match_ids), KAFKA_TOPIC)
    finally:
        await producer.stop()

# ------------- MODO BACKFILL (one-shot) ------------------------------------

def backfill_once(game_tag: str, region: str, count: int, api_key: str) -> None:
    if "#" not in game_tag:
        raise ValueError("Formato Riot ID inválido. Usa gameName#tagLine")

    game_name, tag_line = game_tag.split("#", 1)
    puuid = get_puuid_from_riot_id(region, game_name, tag_line, api_key)
    log.info("PUUID de %s: %s", game_tag, puuid[:12] + "…")

    mids = list_match_ids_by_puuid(region, puuid, count, api_key)
    if not mids:
        log.warning("No hay matches para ese jugador.")
        return

    asyncio.run(produce_match_ids(mids))

# ------------- MODO DAEMON (loop continuo como antes) ----------------------

async def daemon_loop(api_key: str, game_tag: str, region: str, poll_count: int = 20, sleep_s: float = 60.0):
    """
    Cada 'sleep_s' consulta los últimos 'poll_count' matches del jugador por env var
    y los publica si aparecen nuevos.
    """
    seen = set()
    while True:
        try:
            game_name, tag_line = game_tag.split("#", 1)
            puuid = get_puuid_from_riot_id(region, game_name, tag_line, api_key)
            mids = list_match_ids_by_puuid(region, puuid, poll_count, api_key)
            new_mids = [m for m in mids if m not in seen]
            if new_mids:
                await produce_match_ids(new_mids)
                seen.update(new_mids)
            else:
                log.info("No hay nuevos matches (vigilando a %s).", game_tag)
        except Exception as e:
            log.exception("Error en daemon: %s", e)
        await asyncio.sleep(sleep_s)

def daemon_main():
    api_key = os.getenv("RIOT_API_KEY", "").strip()
    game_tag = os.getenv("SUMMONER_NAME", "").strip()        # p.ej. "MEMENTO MØRI#FLASH"
    region   = os.getenv("RIOT_REGION", "europe").strip()

    if not api_key:
        raise ValueError("RIOT_API_KEY no definido (env) para modo daemon")
    if "#" not in game_tag:
        raise ValueError("SUMMONER_NAME debe ser gameName#tagLine")

    log.info("=== Riot Fetcher (daemon) ===  region=%s player=%s kafka=%s",
             region, game_tag, KAFKA_BOOTSTRAP)
    asyncio.run(daemon_loop(api_key, game_tag, region))

# ------------- entrypoint unificado ----------------------------------------

def main():
    p = argparse.ArgumentParser(description="Riot fetcher: daemon o backfill one-shot")
    p.add_argument("--player", help="Riot ID (gameName#tagLine) para backfill único")
    p.add_argument("--region", default="europe", help="Región para Account y Match (ej. europe)")
    p.add_argument("--count", type=int, default=50, help="Nº de partidas a traer (backfill)")
    p.add_argument("--api-key", dest="api_key", help="API key de Riot para backfill (si no, usa env)")
    args = p.parse_args()

    if args.player:
        # MODO BACKFILL (no necesita tener el servicio corriendo en loop)
        api_key = (args.api_key or os.getenv("RIOT_API_KEY", "")).strip()
        if not api_key:
            raise ValueError("Falta API key (usa --api-key o RIOT_API_KEY)")
        backfill_once(args.player, args.region, args.count, api_key)
    else:
        # MODO DAEMON (igual que antes)
        daemon_main()
