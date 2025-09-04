# check_key.py
import os
import requests

# Lee la clave del entorno
API_KEY = os.getenv("RIOT_API_KEY")

if not API_KEY:
    print("❌ No se encontró la variable de entorno RIOT_API_KEY")
    print("   Configúrala con:")
    print("   Linux/Mac: export RIOT_API_KEY=tu_clave")
    print("   Windows PowerShell: $env:RIOT_API_KEY=\"tu_clave\"")
    exit(1)

# Endpoint sencillo: status de EUW1
url = "https://euw1.api.riotgames.com/lol/status/v4/platform-data"

try:
    r = requests.get(url, headers={"X-Riot-Token": API_KEY}, timeout=6)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        print("✅ API key válida. Puedes usarla en tu proyecto.")
    elif r.status_code == 403:
        print("❌ Forbidden: la API key está caducada o mal copiada.")
    elif r.status_code == 429:
        print("⚠️ Rate limited: demasiadas peticiones, espera unos minutos.")
    else:
        print("⚠️ Respuesta inesperada:", r.text[:200])
except Exception as e:
    print("❌ Error de red:", e)
