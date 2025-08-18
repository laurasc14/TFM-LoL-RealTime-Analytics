import os, requests, urllib.parse, json
k = os.getenv("RIOT_API_KEY")
name = urllib.parse.quote("MEMENTO MØRI")
tag  = urllib.parse.quote("提莫國王")
url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
r = requests.get(url, headers={"X-Riot-Token": k})
print("HTTP", r.status_code)
print("Body", r.text[:200])
