import os
from dotenv import load_dotenv
from src.config.config import RIOT_API_KEY

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP")
SUMMONER_NAME = os.getenv("SUMMONER_NAME")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

load_dotenv()

def get_env_config():
    return {
        "RIOT_API_KEY": RIOT_API_KEY,  # 🔹 Siempre viene de config.py
        "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9093,kafka3:9094"),
        "SUMMONER_NAME": os.getenv("SUMMONER_NAME", "MEMENTO MØRI#FLASH"),
        "TOPIC": os.getenv("TOPIC", "matches"),
        "GROUP_ID": os.getenv("GROUP_ID", "lol-consumer"),
        "MONGO_URI": os.getenv("MONGO_URI", "mongodb://admin:admin@mongo:27017/lol?authSource=admin"),
        "MONGO_DB": os.getenv("MONGO_DB", "lol"),
        "MONGO_COLLECTION": os.getenv("MONGO_COLLECTION", "matches_raw")
    }

print("✔️ ENV VARS (desde env_config.py):")
print("KAFKA_BOOTSTRAP_SERVERS =", KAFKA_BOOTSTRAP_SERVERS)
print("SUMMONER_NAME =", SUMMONER_NAME)
