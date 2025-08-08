import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP")
SUMMONER_NAME = os.getenv("SUMMONER_NAME")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

import os

def get_env_config():
    return {
        "KAFKA_BOOTSTRAP_SERVERS": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        "SUMMONER_NAME": os.getenv("SUMMONER_NAME"),
        "MONGO_URI": os.getenv("MONGO_URI"),
        "MONGO_DB": os.getenv("MONGO_DB"),
    }

print("✔️ ENV VARS (desde env_config.py):")
print("KAFKA_BOOTSTRAP_SERVERS =", KAFKA_BOOTSTRAP_SERVERS)
print("SUMMONER_NAME =", SUMMONER_NAME)
