from src.dashboard.utils.riot import matches_by_puuid, find_participant_by_puuid, match_by_id
import streamlit as st

# ──────────────────────────────────────────────
# Estadísticas generales
# ──────────────────────────────────────────────

def calculate_general_stats(user_id: str, platform: str, max_games: int = 1000) -> dict:
    """Calcula las estadísticas generales del invocador (winrate, total de partidas, KDA)."""
    total_kills = 0
    total_deaths = 0
    total_assists = 0
    total_games = 0
    total_wins = 0
    matches = []

    while len(matches) < max_games:
        match_ids = matches_by_puuid(user_id, platform, count=100)
        for match_id in match_ids:
            match_details = match_by_id(platform, match_id)
            match_info = match_details.get("info", {})

            total_games += 1
            participant = find_participant_by_puuid(match_info, user_id)

            if participant:
                kills = participant.get("kills", 0)
                deaths = participant.get("deaths", 0)
                assists = participant.get("assists", 0)
                win = participant.get("win", False)

                total_kills += kills
                total_deaths += deaths
                total_assists += assists

                if win:
                    total_wins += 1

    winrate = (total_wins / total_games) * 100 if total_games > 0 else 0
    kda = (total_kills + total_assists) / total_deaths if total_deaths > 0 else total_kills + total_assists

    return {
        "total_games": total_games,
        "winrate": winrate,
        "kda": kda,
    }

def display_general_stats(user_id: str, platform: str):
    """Mostrar estadísticas generales del invocador en Streamlit."""
    stats = calculate_general_stats(user_id, platform)

    st.title("Resumen General del Invocador")
    st.write(f"**Total de partidas**: {stats['total_games']}")
    st.write(f"**Winrate**: {stats['winrate']}%")
    st.write(f"**KDA**: {stats['kda']}")
    st.write("---")


# ──────────────────────────────────────────────
# Estadísticas por campeón
# ──────────────────────────────────────────────

def calculate_champion_stats(user_id: str, platform: str, max_games: int = 1000) -> dict:
    """Calcula estadísticas por campeón (winrate, partidas jugadas)."""
    champion_stats = {}
    matches = []

    while len(matches) < max_games:
        match_ids = matches_by_puuid(user_id, platform, count=100)
        for match_id in match_ids:
            match_details = match_by_id(platform, match_id)
            match_info = match_details.get("info", {})

            participant = find_participant_by_puuid(match_info, user_id)

            if participant:
                champion_id = participant.get("championId")
                win = participant.get("win", False)

                if champion_id not in champion_stats:
                    champion_stats[champion_id] = {"games": 0, "wins": 0}

                champion_stats[champion_id]["games"] += 1
                if win:
                    champion_stats[champion_id]["wins"] += 1

    for champ_id, stats in champion_stats.items():
        stats["winrate"] = (stats["wins"] / stats["games"]) * 100 if stats["games"] > 0 else 0

    return champion_stats

def display_champion_stats(user_id: str, platform: str):
    """Mostrar estadísticas por campeón en Streamlit."""
    champion_stats = calculate_champion_stats(user_id, platform)

    st.title("Estadísticas por Campeón")
    for champ_id, stats in champion_stats.items():
        st.write(f"**Campeón {champ_id}:**")
        st.write(f"  - **Partidas jugadas**: {stats['games']}")
        st.write(f"  - **Winrate**: {stats['winrate']}%")
        st.write("---")
