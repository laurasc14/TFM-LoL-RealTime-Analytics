from __future__ import annotations
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# Carga .env de la raíz del repo si existe
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from src.api.riot_proxy import router as riot_router
from src.api.cache_matches import router as cache_router

app = FastAPI(title="LoL Realtime API", version="1.0")

# CORS abierto para Streamlit local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# --------- Mongo (solo ping para log) ----------
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
    print(f"[Mongo] Conectado -> {mongo_uri}")
except Exception as e:
    print("[Mongo] ERROR:", e)

# --------- Rutas ----------
app.include_router(riot_router)
app.include_router(cache_router)

@app.get("/ping")
def ping():
    return {"ok": True}
