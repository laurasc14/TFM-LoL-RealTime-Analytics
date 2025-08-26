# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import logging

from src.config.env_config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="final-backfill-api", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Mongo ----
MONGO_URL = settings.MONGO_URI   # 🔥 aquí usamos MONGO_URI
client: MongoClient | None = None
db = None

@app.on_event("startup")
def on_startup() -> None:
    global client, db
    logger.info("[mongo] usando URI: %s", MONGO_URL)
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    client.admin.command("ping")
    logger.info("[mongo] ping OK")

    try:
        db_name = client.get_default_database().name
        logger.info("[mongo] base de datos por defecto: %s", db_name)
    except Exception:
        logger.info("[mongo] sin base de datos por defecto en la URI")

@app.on_event("shutdown")
def on_shutdown() -> None:
    global client
    if client is not None:
        client.close()
        logger.info("[mongo] conexión cerrada")

@app.get("/")
def root():
    return {"ok": True, "service": "final-backfill-api"}

@app.get("/health")
def health():
    try:
        client.admin.command("ping")
        mongo = "ok"
    except Exception as e:
        mongo = f"error: {e!s}"
    return {"status": "ok", "mongo": mongo}
