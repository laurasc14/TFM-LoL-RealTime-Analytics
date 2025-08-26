# src/dashboard/dashboard_streamlit.py
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://appuser:appsecret@mongo:27017/lol?authSource=lol")
client = MongoClient(MONGO_URI)
