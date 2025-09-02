from __future__ import annotations

import os
import time
import random
import json
import pathlib
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from datetime import datetime, timezone
from functools import lru_cache

import requests
from pymongo import MongoClient

# ───────────────────────────────
# Excepciones
# ───────────────────────────────
class RiotError(Exception):
    pass


class NotFound(RiotError):
    pass


class Forbidden(RiotError):
    """403 – normalmente API key expirada/incorrecta o header faltante."""
    pass


# ───────────────────────────────
# Routing / Hosts
# ───────────────────────────────
PLATFORM_HOSTS: Dict[str, str] = {
    "euw1": "https://euw1.api.riotgames.com",
    "eune1": "https://eune1.api.riotgames.com",
    "tr1": "https://tr1.api.riotgames.com",
    "ru": "https://ru.api.riotgames.com",
    "na1": "https://na1.api.riotgames.com",
    "br1": "https://br1.api.riotgames.com",
    "la1": "https://la1.api.riotgames.com",
    "la2": "https://la2.api.riotgames.com",
    "oc1": "https://oc1.api.riotgames.com",
    "kr": "https://kr.api.riotgames.com",
    "jp1": "https://jp1.api.riotgames.com",
    "ph2": "https://ph2.api.riotgames.com",
    "sg2": "https://sg2.api.riotgames.com",
    "th2": "https://th2.api.riotgames.com",
    "tw2": "https://tw2.api.riotgames.com",
    "vn2": "https://vn2.api.riotgames.com",
}

PLATFORM_TO_CLUSTER: Dict[str, str] = {
    "euw1": "europe", "eune1": "europe", "tr1": "europe", "ru": "europe",
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas", "oc1": "americas",
    "kr": "asia", "jp1": "asia",
    "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
}

def _regional_host(platform: str) -> str:
    p = (platform or "").lower().strip()
    cluster = PLATFORM_TO_CLUSTER.get(p)
    if not cluster:
        raise ValueError(f"Plataforma inválida: {platform}")
    return f"https://{cluster}.api.riotgames.com"


# ───────────────────────────────
# Colas
# ───────────────────────────────
QUEUES: Dict[str, Optional[int]] = {
    "Todas": None,
    "Clasificatoria Solo/Dúo": 420,
    "Clasificatoria Flexible": 440,
    "Normal Draft": 400,
    "ARAM": 450,
    "URF": 1900,
}

def queue_label_to_id(label: str) -> Optional[int]:
    return QUEUES.get(label, None)


# ───────────────────────────────
# Campeones (opcional, para imágenes)
# ───────────────────────────────
def load_champions() -> dict:
    """Carga champions.json (DDragon) y prepara un map {int(key)->champId}."""
    file_path = os.path.join(os.path.dirname(__file__), "../data/champions.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encuentra champions.json en {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {int(champ['key']): champ['id'] for champ in data['data'].values()}

def get_champion_image(champion_id: int, champions: dict) -> str:
    champion_name = champions.get(champion_id)
    if champion_name:
        # Versión estable de ddragon
        return f"http://ddragon.leagueoflegends.com/cdn/12.15.1/img/champion/{champion_name}.png"
    return ""


# ───────────────────────────────
# Rank / League helpers + cache persistente
# ───────────────────────────────
def get_rank_icon_url(tier: Optional[str], rank: Optional[str]) -> str:
    if not tier or tier.lower() == "unranked":
        return ""
    return f"https://opgg-static.akamaized.net/images/medals/{tier.lower()}_{(rank or '').lower()}.png"

# Cache: Mongo si hay MONGO_URI; si no, fichero JSON
_CACHE_FILE = "/app/data/rank_cache.json"
_mongo_client: Optional[MongoClient] = None

def _rank_cache_coll():
    uri = os.getenv("MONGO_URI")
    if not uri:
        return None
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(uri)
    db = _mongo_client.get_default_database()
    if db is None:
        db = _mongo_client["lol_realtime"]
    return db["rank_cache"]

def load_last_known_ranks(puuid: str) -> list[dict]:
    """Carga de Mongo la última info de rangos guardada para este invocador."""
    coll = _rank_cache_coll()
    if coll is not None:
        doc = coll.find_one({"_id": puuid})
        return (doc or {}).get("entries", [])
    return []


def save_last_known_ranks(puuid: str, entries: list[dict]) -> None:
    """Guarda en Mongo la info de rangos para este invocador."""
    coll = _rank_cache_coll()
    if coll is not None:
        coll.update_one(
            {"_id": puuid},
            {"$set": {"entries": entries, "updatedAt": datetime.utcnow()}},
            upsert=True,
        )

        return
    pathlib.Path(os.path.dirname(_CACHE_FILE)).mkdir(parents=True, exist_ok=True)
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data[puuid] = entries
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ───────────────────────────────
# API KEY
# ───────────────────────────────
def get_riot_api_key() -> str:
    """
    Resuelve la clave en este orden: st.secrets → env → módulo opcional env_config.
    """
    # 1) streamlit secrets
    try:
        import streamlit as st
        k = st.secrets.get("RIOT_API_KEY")
        if k:
            return str(k)
    except Exception:
        pass
    # 2) variable de entorno
    k = os.getenv("RIOT_API_KEY")
    if k:
        return k
    # 3) módulo opcional
    try:
        from src.env_config import RIOT_API_KEY as K2  # type: ignore
        if K2:
            return str(K2)
    except Exception:
        pass
    return ""


def _api_key() -> str:
    key = get_riot_api_key()
    if not key:
        raise RiotError("RIOT_API_KEY no está configurada.")
    return key


# ───────────────────────────────
# HTTP internos (rate-limit + retry)
# ───────────────────────────────
SESSION = requests.Session()
_last_call_ts = 0.0

def _headers() -> Dict[str, str]:
    return {"X-Riot-Token": _api_key()}

def _polite_delay(min_interval: float = 0.12) -> None:
    global _last_call_ts
    now = time.monotonic()
    wait = min_interval - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.monotonic()

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
        if r.status_code == 401:
            raise RiotError("401 Unauthorized – API key desconocida o inválida")
        if r.status_code in (429, 503):
            retry_after = r.headers.get("Retry-After")
            sleep_s = float(retry_after) if retry_after else min(1.5*(2**i), 15) + random.uniform(0.05, 0.3)
            time.sleep(sleep_s)
            continue
        if 500 <= r.status_code < 600:
            time.sleep(0.5*(2**i) + random.uniform(0.05, 0.25))
            continue

        text = r.text[:200].replace("\n", " ")
        raise RiotError(f"{r.status_code} en {url}: {text}")
    raise RiotError(f"Too many retries ({last_status}) en {url}")


# ───────────────────────────────
# Invocador / Cuenta
# ───────────────────────────────
def summoner_by_name(platform: str, lol_name: str) -> Dict[str, Any]:
    platform = platform.lower().strip()
    if platform not in PLATFORM_HOSTS:
        raise ValueError(f"Plataforma inválida: {platform}")
    name_enc = quote(lol_name, safe="")
    url = f"{PLATFORM_HOSTS[platform]}/lol/summoner/v4/summoners/by-name/{name_enc}"
    return _get(url)

def summoner_by_puuid(platform: str, puuid: str) -> Dict[str, Any]:
    puuid_enc = quote(puuid, safe="")
    url = f"{PLATFORM_HOSTS[platform]}/lol/summoner/v4/summoners/by-puuid/{puuid_enc}"
    return _get(url)

def account_by_puuid(platform: str, puuid: str) -> Dict[str, Any]:
    host = _regional_host(platform)
    url = f"{host}/riot/account/v1/accounts/by-puuid/{puuid}"
    return _get(url)

def account_by_riot_id(platform: str, game_name: str, tag_line: str) -> Dict[str, Any]:
    host = _regional_host(platform)
    g = quote(game_name, safe="")
    t = quote(tag_line, safe="")
    url = f"{host}/riot/account/v1/accounts/by-riot-id/{g}/{t}"
    return _get(url)


def summoner_leagues(platform: str, summoner_id: str) -> List[dict]:
    """Devuelve las ligas del invocador (puede venir vacío si Riot no expone aún el split)."""
    url = f"{PLATFORM_HOSTS[platform]}/lol/league/v4/entries/by-summoner/{summoner_id}"
    data = _get(url)
    return data if isinstance(data, list) else []


# ───────────────────────────────
# Match-V5
# ───────────────────────────────
def matches_by_puuid(puuid: str, platform: str, *, count: int = 10,
                     queue: Optional[int] = None, start_time: Optional[int] = None) -> List[str]:
    host = _regional_host(platform)
    url = f"{host}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params: Dict[str, Any] = {"start": 0, "count": int(count)}
    if queue is not None:
        params["queue"] = int(queue)
    if start_time is not None:
        params["startTime"] = int(start_time)
    return _get(url, params=params)

def match_by_id(platform: str, match_id: str) -> Dict[str, Any]:
    _polite_delay(0.15)
    host = _regional_host(platform)
    url = f"{host}/lol/match/v5/matches/{match_id}"
    return _get(url)

def find_participant_by_puuid(match_info: dict, user_id: str) -> Optional[dict]:
    for p in match_info.get("info", {}).get("participants", []):
        if p.get("puuid") == user_id:
            return p
    return None


# ───────────────────────────────
# Spectator
# ───────────────────────────────
def live_game_by_summoner_id(platform: str, encrypted_summoner_id: str) -> Dict[str, Any]:
    host = PLATFORM_HOSTS[platform]
    url = f"{host}/lol/spectator/v5/active-games/by-summoner/{encrypted_summoner_id}"
    return _get(url)

def _id_from_recent_match(platform: str, puuid: str) -> Optional[str]:
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
    """OJO: este endpoint espera summonerId (no puuid); lo resolvemos con fallback si podemos."""
    sid = _id_from_recent_match(platform, puuid)
    if not sid:
        raise RiotError("No se pudo inferir summonerId desde partidas recientes.")
    return live_game_by_summoner_id(platform, sid)


# ───────────────────────────────
# Temporada/Fechas
# ───────────────────────────────
def season_to_date_start_timestamp() -> int:
    dt = datetime(datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc)
    return int(dt.timestamp())


# ───────────────────────────────
# Lookup robusto – Nombre o RiotID
# ───────────────────────────────
def lookup_summoner(query: str, platform: str) -> Dict[str, Any]:
    """
    Permite buscar 'Nombre' o 'Nombre#TAG'.
    Devuelve: { region, puuid, id, level, name, profileIconId }
    """
    out = {
        "region": (platform or "").lower().strip(),
        "puuid": None, "id": None, "level": None,
        "name": None, "profileIconId": None
    }
    q = (query or "").strip()
    if not q:
        return out

    def _fill_from_summ(s: dict):
        if not s:
            return
        out["puuid"] = out["puuid"] or s.get("puuid")
        out["id"] = out["id"] or s.get("id")
        out["level"] = s.get("summonerLevel") or out["level"]
        out["name"] = out["name"] or s.get("name")
        out["profileIconId"] = out["profileIconId"] or s.get("profileIconId")

    try:
        if "#" in q:
            game, tag = [x.strip() for x in q.split("#", 1)]
            # 1) exacto con RiotID
            try:
                acc = account_by_riot_id(platform, game, tag)
                puuid = acc.get("puuid")
                if puuid:
                    s_by_puuid = summoner_by_puuid(platform, puuid)
                    _fill_from_summ(s_by_puuid)
                    return out
            except RiotError:
                pass  # caemos a nombre a pelo

            # 2) Fallback: nombre a pelo
            try:
                s_by_name = summoner_by_name(platform, game)
                _fill_from_summ(s_by_name)
                if out["puuid"]:
                    try:
                        acc2 = account_by_puuid(platform, out["puuid"])
                        if acc2.get("gameName"):
                            out["name"] = f"{acc2.get('gameName')}#{acc2.get('tagLine')}"
                    except RiotError:
                        pass
                return out
            except RiotError:
                return out
        else:
            s_by_name = summoner_by_name(platform, q)
            _fill_from_summ(s_by_name)
            if out["puuid"]:
                try:
                    acc2 = account_by_puuid(platform, out["puuid"])
                    if acc2.get("gameName"):
                        out["name"] = f"{acc2.get('gameName')}#{acc2.get('tagLine')}"
                except RiotError:
                    pass
            return out
    except RiotError:
        return out


# Wrapper por compatibilidad con tu código
def league_entries_by_summoner(platform: str, summoner_id: str) -> List[Dict[str, Any]]:
    return summoner_leagues(platform, summoner_id)


def explain_rank_fallback(puuid: Optional[str]) -> str:
    """Mensaje cuando no hay rango en el split actual."""
    cached = load_last_known_ranks(puuid or "")
    if cached:
        return ("Mostramos el **último rango conocido** porque la API de Riot no "
                "devuelve tier/división en este momento. En cuanto lo exponga, se actualizará.")
    return ("Aún no tenemos histórico para este invocador. Cuando Riot exponga "
            "el rango (p. ej., tras jugar clasificatorias) lo mostraremos aquí.")

# ───────────────────────────────
# Caché de nombres por (region, puuid) para no machacar la API
# ───────────────────────────────

# ---- Nombres: reconstrucción y caché en memoria --------------------------------
_name_cache: dict[str, str] = {}   # puuid -> "Nombre#TAG" (o Summoner Name)

def _save_name_cache(puuid: str, name: str) -> str:
    if puuid and name:
        _name_cache[puuid] = name
    return name

def resolve_summoner_name(platform: str, participant: dict) -> str:
    """
    Devuelve un nombre para mostrar:
    1) Si el match trae riotIdGameName/tagLine, lo usa (RiotID).
    2) Si no, intenta account-v1 by puuid (gameName + tagLine).
    3) Si no, intenta summoner-v4 by puuid (Summoner 'name').
    4) Si todo falla, usa lo que venga en participant ('summonerName') o un pseudo.
    Siempre cachea por puuid.
    """
    try:
        puuid = (participant or {}).get("puuid")
        if not puuid:
            # último recurso sin caché: cualquier cosa que venga
            base = (
                participant.get("riotIdGameName")
                or participant.get("gameName")
                or participant.get("summonerName")
                or participant.get("name")
            )
            return base or "-"

        # 0) caché
        cached = _name_cache.get(puuid)
        if cached:
            return cached

        # 1) ¿Viene en el participant?
        game = participant.get("riotIdGameName") or participant.get("gameName")
        tag  = participant.get("riotIdTagline")  or participant.get("tagLine")
        if game:
            return _save_name_cache(puuid, f"{game}#{tag}" if tag else game)

        # 2) account-v1 (RiotID) -> necesita host regional
        try:
            acc = account_by_puuid(platform, puuid)  # europe/americas/asia...
            g = acc.get("gameName")
            t = acc.get("tagLine")
            if g:
                return _save_name_cache(puuid, f"{g}#{t}" if t else g)
        except Exception:
            pass  # seguimos probando

        # 3) summoner-v4 (Summoner Name clásico, host de plataforma)
        try:
            summ = summoner_by_puuid(platform, puuid)
            n = summ.get("name")
            if n:
                return _save_name_cache(puuid, n)
        except Exception:
            pass

        # 4) Fallbacks del participant
        base = (
            participant.get("summonerName")
            or participant.get("name")
        )
        if base:
            return _save_name_cache(puuid, base)

        # 5) Pseudo si no conseguimos nada
        pseudo = f"{puuid[:8]}…"
        return _save_name_cache(puuid, pseudo)

    except Exception:
        # último ‘paracaídas’ para no romper el render
        pu = participant.get("puuid")
        return _save_name_cache(pu, (participant.get("summonerName") or "-"))
