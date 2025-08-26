# src/ingestion/riot_fetcher.py
import os
import time
import json
import logging
from typing import List, Set

from kafka import KafkaProducer

try:
    from riotwatcher import RiotWatcher, LolWatcher
except Exception as e:
    raise SystemExit(
        "Necesitas riotwatcher con RiotWatcher y LolWatcher disponibles. "
        "Recomiendo: riotwatcher>=3.2.0\n"
        f"Import error: {e}"
    )

try:
    from riotwatcher import ApiError  # type: ignore
except Exception:
    ApiError = Exception

# -------------------------
# Config & logging
# -------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(message)s",
)
log = logging.getLogger("fetcher")

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
SUMMONER_ID_RAW = os.getenv("SUMMONER_NAME")  # Puede ser GameName#TagLine o solo nombre

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "final-kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "matches")

# Platform (euw1, na1, ...) y Regional (europe, americas, asia, sea)
RIOT_REGION = os.getenv("RIOT_REGION", "euw1")
RIOT_REGIONAL_ROUTE = os.getenv("RIOT_REGIONAL_ROUTE", "europe")

MAX_MATCHES = int(os.getenv("MAX_MATCHES", "20"))
POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "30"))

if not RIOT_API_KEY:
    raise SystemExit("Falta RIOT_API_KEY en variables de entorno.")
if not SUMMONER_ID_RAW:
    raise SystemExit("Falta SUMMONER_NAME en variables de entorno (GameName#TagLine o solo nombre).")

# -------------------------
# Kafka
# -------------------------
def make_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        linger_ms=50,
        retries=3,
        acks=1,
    )

# -------------------------
# Riot helpers
# -------------------------
def _resolve_puuid(rw: RiotWatcher, lw: LolWatcher) -> str:
    """
    Devuelve el PUUID a partir de SUMMONER_ID_RAW.
    - 'GameName#TagLine' -> usa Account-V1 (RiotWatcher.account.by_riot_id) en ruta regional.
    - solo nombre -> usa LoL Summoner-V4 (LolWatcher.summoner.by_name) en región de plataforma.
    """
    raw = SUMMONER_ID_RAW.strip()

    # Caso Riot ID con tag
    if "#" in raw:
        game_name, tag_line = raw.split("#", 1)
        acct = rw.account.by_riot_id(RIOT_REGIONAL_ROUTE, game_name.strip(), tag_line.strip())
        return acct["puuid"]

    # Caso solo nombre de invocador
    summ = lw.summoner.by_name(RIOT_REGION, raw)
    return summ["puuid"]

def fetch_and_send_once(rw: RiotWatcher, lw: LolWatcher, producer: KafkaProducer, seen: Set[str]) -> int:
    """
    Obtiene matches por PUUID y publica IDs en Kafka. Devuelve cuántos nuevos se enviaron.
    """
    puuid = _resolve_puuid(rw, lw)
    match_ids: List[str] = lw.match.matchlist_by_puuid(
        RIOT_REGIONAL_ROUTE, puuid, count=MAX_MATCHES
    )

    sent = 0
    for mid in match_ids:
        if mid in seen:
            continue
        payload = {
            "match_id": mid,
            "puuid": puuid,
            "region": RIOT_REGION,
            "route": RIOT_REGIONAL_ROUTE,
            "fetched_at": int(time.time()),
        }
        producer.send(KAFKA_TOPIC, payload)
        seen.add(mid)
        sent += 1
        log.info(f"[fetcher] enviado {mid} -> {KAFKA_TOPIC}")

    producer.flush(1.0)
    return sent

# -------------------------
# Main loop
# -------------------------
def main() -> None:
    log.info(f"[fetcher] region={RIOT_REGION} route={RIOT_REGIONAL_ROUTE} topic={KAFKA_TOPIC}")

    # Instancias: rw para account; lw para LoL (summoner, match)
    rw = RiotWatcher(RIOT_API_KEY)
    lw = LolWatcher(RIOT_API_KEY)

    producer = make_producer()
    log.info(f"[fetcher] conectado a Kafka {KAFKA_BOOTSTRAP}")

    seen: Set[str] = set()

    while True:
        try:
            sent = fetch_and_send_once(rw, lw, producer, seen)
            log.info(f"[fetcher] ciclo OK, enviados {sent}")
        except ApiError as e:  # type: ignore
            status = getattr(getattr(e, "response", None), "status_code", None)
            log.error(f"[fetcher] ApiError (HTTP {status}): {e}")
        except Exception as e:
            log.error(f"[fetcher] Error raíz: {e}")
        time.sleep(POLL_INTERVAL_SEC)

if __name__ == "__main__":
    # Fuerza logs sin buffer aunque no se invoque con -u
    try:
        import sys, os as _os
        _os.environ.setdefault("PYTHONUNBUFFERED", "1")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    main()
