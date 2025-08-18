# src/services/tools/backfill_api.py

from .backfill_player import backfill_player_data

def run_backfill(player_name: str) -> dict:
    """
    Ejecuta el proceso de backfill para un jugador concreto.
    Aquí puedes añadir la lógica de tu ETL o llamadas al fetcher.
    """
    try:
        # llamamos a la función que ya tienes en backfill_player.py
        result = backfill_player_data(player_name)
        return {
            "status": "ok",
            "player": player_name,
            "details": result
        }
    except Exception as e:
        return {
            "status": "error",
            "player": player_name,
            "error": str(e)
        }
