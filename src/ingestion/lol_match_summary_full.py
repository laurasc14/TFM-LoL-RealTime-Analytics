import requests
import urllib.parse

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
        return
    data = res.json()
    print(f"\nMatch {match_id} - Mode: {data['info']['gameMode']} - Duration: {data['info']['gameDuration']}s")
    teams = {100: [], 200: []}
    results = {}
    for p in data['info']['participants']:
        tid = p['teamId']
        if tid not in results:
            results[tid] = p['win']
        is_me = "(YOU)" if p['puuid'] == my_puuid else ""
        teams[tid].append({
            "summoner": p['summonerName'],
            "champion": p['championName'],
            "kda": f"{p['kills']}/{p['deaths']}/{p['assists']}",
            "is_me": is_me
        })
    for tid in [100, 200]:
        result = "WIN" if results[tid] else "LOSE"
        print(f"\nTEAM {tid} - {result}")
        for p in teams[tid]:
            print(f" - {p['summoner']:<20} {p['champion']:<12} KDA: {p['kda']:<10} {p['is_me']}")

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
    for mid in match_ids:
        get_match_summary(mid, puuid)
