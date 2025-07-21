import requests
import urllib.parse
import json
import os

RIOT_API_KEY = "RGAPI-2d148fa7-7edc-44bd-ad3c-900a6d6af06d" 
REGION_ROUTING = "europe"
MATCH_COUNT = 5

def get_puuid_from_riot_id(riot_id):
    if "#" not in riot_id:
        print("❌ Formato incorrecto. Usa 'nombre#tag'")
        return None
    game_name, tag_line = riot_id.split("#")
    encoded_name = urllib.parse.quote(game_name)
    url = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        return data["puuid"], data["gameName"], data["tagLine"]
    else:
        print(f"❌ Error obteniendo puuid: {res.status_code} {res.text}")
        return None, None, None

def get_match_ids(puuid, count):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params = {"start": 0, "count": count}
    res = requests.get(url, headers=headers, params=params)
    return res.json() if res.status_code == 200 else []

def get_match_summary(match_id, my_puuid):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"❌ Error {res.status_code}: {res.text}")
        return None

    data = res.json()
    summary = {
        "match_id": match_id,
        "gameMode": data['info']['gameMode'],
        "duration": data['info']['gameDuration'],
        "teams": {
            100: {"result": None, "players": []},
            200: {"result": None, "players": []}
        }
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

if __name__ == "__main__":
    riot_id = input("🔎 Introduce tu Riot ID (nombre#tag): ").strip()
    puuid, game_name, tag = get_puuid_from_riot_id(riot_id)
    if not puuid:
        exit(1)
    print(f"✅ PUUID encontrado: {puuid}")
    match_ids = get_match_ids(puuid, MATCH_COUNT)
    if not match_ids:
        print("No se encontraron partidas.")
        exit(1)

    all_summaries = []
    for mid in match_ids:
        summary = get_match_summary(mid, puuid)
        if summary:
            all_summaries.append(summary)
            print(f"\nMatch {mid} - Mode: {summary['gameMode']} - Duration: {summary['duration']}s")
            for tid in [100, 200]:
                print(f"\nTEAM {tid} - {summary['teams'][tid]['result']}")
                for p in summary['teams'][tid]["players"]:
                    you = " (YOU)" if p["is_you"] else ""
                    print(f" - {p['summoner']:<20} {p['champion']:<12} KDA: {p['kda']:<10} {you}")

    os.makedirs("output", exist_ok=True)
    with open("output/match_events.json", "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, ensure_ascii=False, indent=2)

    print("\n📁 Archivo guardado en: output/match_events.json")
