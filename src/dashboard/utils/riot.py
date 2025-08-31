from __future__ import annotations
from pymongo import MongoClient

import os
import time
import random
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import requests
import json

# ──────────────────────────────────────────────────────────────────────────────
# Excepciones
# ──────────────────────────────────────────────────────────────────────────────

class RiotError(Exception):
    pass

class NotFound(RiotError):
    pass

class Forbidden(RiotError):
    """403 – normalmente API key expirada/incorrecta o header faltante."""
    pass

# ──────────────────────────────────────────────────────────────────────────────
# Routing
# ──────────────────────────────────────────────────────────────────────────────

PLATFORM_HOSTS: Dict[str, str] = {
    # EU
    "euw1": "https://euw1.api.riotgames.com",
    "eune1": "https://eune1.api.riotgames.com",
    "tr1": "https://tr1.api.riotgames.com",
    "ru": "https://ru.api.riotgames.com",
    # AMERICAS
    "na1": "https://na1.api.riotgames.com",
    "br1": "https://br1.api.riotgames.com",
    "la1": "https://la1.api.riotgames.com",
    "la2": "https://la2.api.riotgames.com",
    "oc1": "https://oc1.api.riotgames.com",
    # ASIA
    "kr": "https://kr.api.riotgames.com",
    "jp1": "https://jp1.api.riotgames.com",
    # SEA
    "ph2": "https://ph2.api.riotgames.com",
    "sg2": "https://sg2.api.riotgames.com",
    "th2": "https://th2.api.riotgames.com",
    "tw2": "https://tw2.api.riotgames.com",
    "vn2": "https://vn2.api.riotgames.com",
}

# platform -> cluster (para /riot/account y /match-v5)
PLATFORM_TO_CLUSTER: Dict[str, str] = {
    # EU
    "euw1": "europe",
    "eune1": "europe",
    "tr1": "europe",
    "ru": "europe",
    # AMERICAS
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "oc1": "americas",
    # ASIA
    "kr": "asia",
    "jp1": "asia",
    # SEA
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}

REGIONAL_HOST = "https://{cluster}.api.riotgames.com"

# Colas más comunes
QUEUES: Dict[str, Optional[int]] = {
    "Todas": None,
    "Clasificatoria Solo/Dúo": 420,
    "Clasificatoria Flexible": 440,
    "Normal Draft": 400,
    "ARAM": 450,
    "URF": 1900,
}

def queue_label_to_id(label: str) -> Optional[int]:
    return QUEUES.get(label)

# ──────────────────────────────────────────────────────────────────────────────
# Conexión a MongoDB
# ──────────────────────────────────────────────────────────────────────────────

client = MongoClient("mongodb://localhost:27017/")
db = client["your_database"]
collection = db["summoner_profiles"]

# ──────────────────────────────────────────────────────────────────────────────
# Conexión e interacción con la base de datos MongoDB
# ──────────────────────────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Obtiene el perfil del invocador desde la base de datos"""
    user_profile = collection.find_one({"user_id": user_id})
    return user_profile

def update_user_profile(user_id: str, user_profile: Dict[str, Any]) -> None:
    """Actualiza el perfil del invocador en la base de datos"""
    collection.update_one({"user_id": user_id}, {"$set": user_profile}, upsert=True)

# ──────────────────────────────────────────────────────────────────────────────
# Cargar campeones
# ──────────────────────────────────────────────────────────────────────────────

def load_champions() -> dict:
    # Ruta robusta: relativa a riot.py, funciona local y en Docker
    file_path = os.path.join(os.path.dirname(__file__), "../data/champions.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encuentra champions.json en {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        champions = {int(champ['key']): champ['id'] for champ in data['data'].values()}
    return champions

# Función para obtener la URL de la imagen del campeón
def get_champion_image(champion_id: int, champions: dict) -> str:
    """Devuelve la URL de la imagen del campeón."""
    champion_name = champions.get(champion_id)
    if champion_name:
        return f"http://ddragon.leagueoflegends.com/cdn/12.15.1/img/champion/{champion_name}.png"
    return ""

# ──────────────────────────────────────────────────────────────────────────────
# Internos HTTP
# ──────────────────────────────────────────────────────────────────────────────

def _api_key() -> str:
    key = os.getenv("RIOT_API_KEY")
    if not key:
        # soporte para Streamlit Cloud
        try:
            import streamlit as st  # type: ignore
            key = st.secrets.get("RIOT_API_KEY")  # type: ignore
        except Exception:
            key = None
    if not key:
        raise RiotError("RIOT_API_KEY no está configurada.")
    return key

SESSION = requests.Session()
_last_call_ts = 0.0

def _headers() -> Dict[str, str]:
    return {"X-Riot-Token": _api_key()}

def _polite_delay(min_interval: float = 0.12) -> None:
    """
    Garantiza un intervalo mínimo entre llamadas HTTP. 0.12s ≈ 8 req/s.
    Evita picos que disparen 429 con claves dev.
    """
    global _last_call_ts
    now = time.monotonic()
    wait = min_interval - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()

def _platform_host(platform: str) -> str:
    p = platform.lower()
    if p in PLATFORM_HOSTS:
        return PLATFORM_HOSTS[p]
    raise ValueError(f"Plataforma inválida: {platform}")

def _regional_host(platform_or_cluster: str) -> str:
    x = platform_or_cluster.lower()
    if x in {"europe", "americas", "asia", "sea"}:
        return REGIONAL_HOST.format(cluster=x)
    cluster = PLATFORM_TO_CLUSTER.get(x)
    if not cluster:
        raise ValueError(f"Región para routing inválida: {platform_or_cluster}")
    return REGIONAL_HOST.format(cluster=cluster)

def _get(url: str, params: Optional[Dict[str, Any]] = None, tries: int = 8) -> Any:
    last_status = None
    for i in range(tries):
        _polite_delay()
        r = SESSION.get(url, params=params, headers=_headers(), timeout=20)
        last_status = r.status_code

        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            raise NotFound(f"404 en {url}")
        if r.status_code == 403:
            raise Forbidden("403 Forbidden – revisa la RIOT_API_KEY")
        if r.status_code in (429, 503):
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                sleep_s = float(retry_after)
            else:
                sleep_s = min(1.5 * (2 ** i), 15) + random.uniform(0.05, 0.3)
            time.sleep(sleep_s)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(0.5 * (2 ** i) + random.uniform(0.05, 0.25))
            continue

        text = r.text[:200].replace("\n", " ")
        raise RiotError(f"{r.status_code} en {url}: {text}")

    raise RiotError(f"Too many retries ({last_status}) en {url}")

# ──────────────────────────────────────────────────────────────────────────────
# Cuentas / Invocador
# ──────────────────────────────────────────────────────────────────────────────

def account_by_riot_id(platform: str, game_name: str, tag_line: str) -> Dict[str, Any]:
    host = _regional_host(platform)
    url = f"{host}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    return _get(url)

def account_by_puuid(platform: str, puuid: str) -> Dict[str, Any]:
    host = _regional_host(platform)
    url = f"{host}/riot/account/v1/accounts/by-puuid/{puuid}"
    return _get(url)

def summoner_by_name(platform: str, lol_name: str) -> Dict[str, Any]:
    name_enc = quote(lol_name, safe="")
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name_enc}"
    return _get(url)

def summoner_by_puuid(platform: str, puuid: str) -> Dict[str, Any]:
    puuid_enc = quote(puuid, safe="")
    url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid_enc}"
    return _get(url)

# ──────────────────────────────────────────────────────────────────────────────
# Actualización del Nombre y Partidas
# ──────────────────────────────────────────────────────────────────────────────

def update_summoner_profile(user_id: str, new_name: str):
    """Actualizar el nombre y asociar las partidas del nuevo nombre."""
    # Obtén los datos del invocador desde Riot
    summoner_data = summoner_by_name("na1", new_name)

    # Obtener el perfil del usuario desde tu base de datos
    user_profile = get_user_profile(user_id)

    # Si el nombre ha cambiado, guardamos el nombre anterior en el historial
    if user_profile['current_name'] != new_name:
        if 'previous_names' not in user_profile:
            user_profile['previous_names'] = []  # Si no existe, creamos la lista
        user_profile['previous_names'].append(user_profile['current_name'])

        # Actualizamos el nombre
        user_profile['current_name'] = new_name

        # Obtener las partidas del invocador
        match_history = matches_by_puuid(summoner_data['puuid'], "na1")
        user_profile['games'] = match_history

        # Actualizar los datos en la base de datos MongoDB
        update_user_profile(user_id, user_profile)  # Usamos la función correcta para actualizar
        print(f"Nombre actualizado a {new_name} y partidas asociadas.")
    else:
        print("El nombre no ha cambiado.")

# ──────────────────────────────────────────────────────────────────────────────
# Match-V5
# ──────────────────────────────────────────────────────────────────────────────

def matches_by_puuid(
    puuid: str,
    platform: str,
    *,
    count: int = 10,
    queue: Optional[int] = None,
    start_time: Optional[int] = None,
) -> List[str]:
    host = _regional_host(platform)
    url = f"{host}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params: Dict[str, Any] = {"start": 0, "count": int(count)}
    if queue is not None:
        params["queue"] = int(queue)
    if start_time is not None:
        params["startTime"] = int(start_time)
    return _get(url, params=params)

def match_by_id(platform: str, match_id: str) -> Dict[str, Any]:
    _polite_delay(0.15)  # un pelín más lento para partidas
    host = _regional_host(platform)
    url = f"{host}/lol/match/v5/matches/{match_id}"
    return _get(url)

def find_participant_by_puuid(match_info: dict, user_id: str) -> dict:
    """Busca un participante en una partida utilizando su PUUID."""
    for participant in match_info.get("info", {}).get("participants", []):
        if participant.get("puuid") == user_id:
            return participant
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Spectator
# ──────────────────────────────────────────────────────────────────────────────

def live_game_by_summoner_id(platform: str, encrypted_summoner_id: str) -> Dict[str, Any]:
    host = _platform_host(platform)
    url = f"{host}/lol/spectator/v5/active-games/by-summoner/{encrypted_summoner_id}"
    return _get(url)

def _id_from_recent_match(platform: str, puuid: str) -> Optional[str]:
    """Fallback: leer 1 partida y extraer encryptedSummonerId."""
    try:
        ids = matches_by_puuid(puuid, platform, count=1)
        if not ids:
            return None
        m = match_by_id(platform, ids[0])
        for p in m.get("info", {}).get("participants", []):
            if p.get("puuid") == puuid:
                return p.get("summonerId")
    except RiotError:
        return None
    return None

def live_game_by_puuid(platform: str, puuid: str) -> Dict[str, Any]:
    """Obtiene el estado de la partida en vivo usando el PUUID."""
    host = _platform_host(platform)
    url = f"{host}/lol/spectator/v5/active-games/by-summoner/{puuid}"
    return _get(url)


# ──────────────────────────────────────────────────────────────────────────────
# Búsqueda integral
# ──────────────────────────────────────────────────────────────────────────────

def lookup_summoner(query: str, platform: str) -> Dict[str, Any]:
    """
    Devuelve {region, puuid, id, level, name}. Acepta 'GameName#TAG' o nombre LoL.
    Rellena 'id' con fallbacks: by-puuid -> by-name -> via match-v5.
    """
    query = query.strip()
    platform = platform.lower()
    out = {"region": platform, "puuid": None, "id": None, "level": None, "name": None}

    def _pretty(game, tag, lolname):
        base = (game or lolname or "").strip()
        return f"{base}#{tag}" if base and tag else (base or None)

    # Riot ID (GameName#TAG)
    if "#" in query:
        game, tag = [x.strip() for x in query.split("#", 1)]
        try:
            acc = account_by_riot_id(platform, game, tag)   # regional
            out["puuid"] = acc.get("puuid")
        except RiotError:
            return out

        # etiqueta bonita
        try:
            acc2 = account_by_puuid(platform, out["puuid"])
            out["name"] = _pretty(acc2.get("gameName"), acc2.get("tagLine"), None)
        except RiotError:
            pass

        # 1) summoner-v4 by-puuid
        try:
            if out["puuid"]:
                summ = summoner_by_puuid(platform, out["puuid"])
                out["id"] = summ.get("id")
                out["level"] = summ.get("summonerLevel")
                out["name"] = out["name"] or summ.get("name")
        except RiotError:
            pass

        # 2) by-name si aún falta id
        if not out["id"]:
            preferred = (out["name"] or "").split("#")[0].strip() if out["name"] else None
            if preferred:
                try:
                    s2 = summoner_by_name(platform, preferred)
                    if s2 and s2.get("puuid") == out["puuid"]:
                        out["id"] = s2.get("id") or out["id"]
                        out["level"] = s2.get("summonerLevel") or out["level"]
                        out["name"] = s2.get("name") or out["name"]
                except RiotError:
                    pass

        # 3) fallback por partida
        if not out["id"] and out["puuid"]:
            out["id"] = _id_from_recent_match(platform, out["puuid"])
        return out

    # nombre LoL sin TAG
    try:
        s = summoner_by_name(platform, query)
        out["puuid"] = s.get("puuid")
        out["id"] = s.get("id")
        out["level"] = s.get("summonerLevel")
        out["name"] = s.get("name")
    except RiotError:
        return out

    # completar RiotID bonito
    try:
        if out["puuid"]:
            acc2 = account_by_puuid(platform, out["puuid"])
            out["name"] = _pretty(acc2.get("gameName"), acc2.get("tagLine"), out["name"])
    except RiotError:
        pass

    # último fallback: partida
    if not out["id"] and out["puuid"]:
        out["id"] = _id_from_recent_match(platform, out["puuid"])

    return out

# ──────────────────────────────────────────────────────────────────────────────
# Fechas
# ──────────────────────────────────────────────────────────────────────────────

def season_to_date_start_timestamp() -> int:
    """1 de enero del año actual (UTC)."""
    import datetime as _dt
    now = _dt.datetime.utcnow()
    start = _dt.datetime(year=now.year, month=1, day=1)
    return int(start.timestamp())
