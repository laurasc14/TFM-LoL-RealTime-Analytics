from pymongo import MongoClient
cli = MongoClient("mongodb://app:appsecret@localhost:27018/lol_realtime?authSource=lol_realtime")
db  = cli["lol_realtime"]
db.matches_full.create_index([("gameStartTimestamp", -1)])
db.matches_full.create_index([("info.queueId", 1), ("gameStartTimestamp", -1)])
print("Índices creados.")
