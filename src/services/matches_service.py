# src/services/matches_service.py
import os
from pymongo import MongoClient
from src.config.env_config import get_env_config

cfg = get_env_config()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/lol?authSource=lol")
MONGO_DB  = os.getenv("MONGO_DB", "lol")
MONGO_COLL = os.getenv("MONGO_COLL", "matches")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
