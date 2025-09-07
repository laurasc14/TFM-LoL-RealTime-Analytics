from pymongo import MongoClient

client = MongoClient("mongodb://app:appsecret@final-mongo:27017/lol_realtime?authSource=lol_realtime")
db = client.lol_realtime

# prueba colección
print(db.list_collection_names())
