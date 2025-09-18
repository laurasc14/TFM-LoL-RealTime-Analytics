# src/bootstrap.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Rutas e imports
# ---------------------------------------------------------------------
# Este archivo vive en .../FINAL/src -> subimos 1 nivel para llegar a la raíz
ROOT = Path(__file__).resolve().parents[1]        # H:\00_TFM\FINAL
SRC  = ROOT / "src"

# Asegurar que ROOT y SRC están en sys.path
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Cargar .env desde la raíz del proyecto
load_dotenv(dotenv_path=ROOT / ".env")

# Variables de entorno disponibles globalmente
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
MONGO_URI    = os.getenv("MONGO_URI")
BACKEND_URL  = os.getenv("BACKEND_URL")

# ---------------------------------------------------------------------
# Normalización de regiones: plataforma (LOL API v4) -> routing (API v5)
# ---------------------------------------------------------------------
# Conjuntos/routings válidos para las APIs v5 de Riot
ROUTINGS = {"europe", "americas", "asia", "sea"}

# Mapa de plataforma (euw1, na1, kr, …) a routing (europe, americas, asia, sea)
PLATFORM_TO_ROUTING = {
    # EUROPE
    "euw1": "europe",
    "eun1": "europe",
    "tr1":  "europe",
    "ru":   "europe",

    # AMERICAS
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "oc1": "americas",

    # ASIA
    "jp1": "asia",
    "kr":  "asia",

    # SEA
    "ph2": "sea",
    "sg2": "sea",
    "tw2": "sea",
    "th2": "sea",
    "vn2": "sea",
}

def to_routing(value: str) -> str:
    """
    Acepta tanto 'platform' (euw1, na1, kr, …) como 'routing' (europe, americas, …)
    y devuelve siempre el routing normalizado en minúsculas.
    Si no se reconoce, devuelve la cadena normalizada tal cual.
    """
    if not value:
        return ""
    v = value.strip().lower()
    if v in ROUTINGS:
        return v
    return PLATFORM_TO_ROUTING.get(v, v)

def is_platform(value: str) -> bool:
    """Devuelve True si 'value' parece ser una plataforma (euw1, na1, kr, …)."""
    if not value:
        return False
    return value.strip().lower() in PLATFORM_TO_ROUTING

# Exponer utilidades
__all__ = [
    "ROOT", "SRC",
    "RIOT_API_KEY", "MONGO_URI", "BACKEND_URL",
    "ROUTINGS", "PLATFORM_TO_ROUTING",
    "to_routing", "is_platform",
]
