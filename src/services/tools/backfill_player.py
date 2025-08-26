# src/api/backfill_api.py
import os
import urllib.parse
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
from kafka import KafkaProducer
import json

# --- util Kafka (igual que en tu backfill actual) ---
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "final-kafka:9092")
TOPIC = os.getenv("KAFKA_MATCHES_TOPIC", "matches")

def get_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=10,
        retries=3,
        acks="all",
    )

# --- entrada API ---
class BackfillReq(BaseModel):
    player: str = Field(..., description="Riot ID: gameName#tagLine, p.ej. MEMENTO MØRI#EUW")
    region: str = Field("europe", description="routing region para endpoint /riot/account")
    count: int = Field(20, ge=1, le=100)
    api_key: Optional[str] = Field(None, description="Opcional. Si no viene, usa RIOT_API_KEY del contenedor")

# --- FastAPI ---
app = FastAPI(title="Riot Backfill API")

@app.post("/backfill")
def backfill(req: BackfillReq):
    api_key = req.api_key or os.getenv("RIOT_API_KEY")
    if not api_key:
        raise HTTPException(400, "Falta API key (ni en body ni en RIOT_API_KEY)")

    # 1) Resolver PUUID desde Riot ID
    try:
        name, tag = req.player.split("#", 1)
    except ValueError:
        raise HTTPException(400, "player debe ser gameName#tagLine")

    name_q = urllib.parse.quote(name)
    tag_q = urllib.parse.quote(tag)
    url_puuid = f"https://{req.region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_q}/{tag_q}"
    r = requests.get(url_puuid, headers={"X-Riot-Token": api_key}, timeout=15)
    if r.status_code == 404:
        raise HTTPException(404, f"Jugador no encontrado: {req.player}")
    if r.status_code == 401:
        raise HTTPException(401, "API key inválida/caducada")
    r.raise_for_status()
    puuid = r.json()["puuid"]

    # 2) Region de plataforma para LoL (europa → EUW/EUW1 → routing americas/europe/asia)
    #    Para simplificar, usamos 'europe' → 'EUROPE' (routing cluster de Match-V5)
    routing = "europe"  # si luego quieres mapear NA → americas, KR → asia, se amplía aquí.
    url_ids = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={req.count}"
    r2 = requests.get(url_ids, headers={"X-Riot-Token": api_key}, timeout=15)
    if r2.status_code == 401:
        raise HTTPException(401, "API key inválida/caducada (match ids)")
    r2.raise_for_status()
    match_ids = r2.json() or []

    if not match_ids:
        return {"ok": True, "sent": 0, "msg": "Sin partidas para enviar"}

    # 3) Producir match_id → Kafka
    prod = get_producer()
    for mid in match_ids:
        prod.send(TOPIC, {"match_id": mid})
    prod.flush(10)

    return {"ok": True, "sent": len(match_ids), "player": req.player}
