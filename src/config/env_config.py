# src/config/env_config.py
import os

def get_env_config() -> dict:
    """
    Devuelve un diccionario con los valores de configuración.
    PRIORIDAD: variables de entorno > defaults seguros (sin auth para Mongo).
    Usa nombres alineados con los servicios Docker y el resto del código.
    """
    return {
        # Kafka
        "KAFKA_BOOTSTRAP": os.getenv("KAFKA_BOOTSTRAP", "final-kafka:9092"),
        "KAFKA_TOPIC": os.getenv("KAFKA_TOPIC", "matches"),
        "GROUP_ID": os.getenv("GROUP_ID", "final-consumer"),

        # Mongo (por defecto SIN autenticación)
        "MONGO_URI": os.getenv("MONGO_URI", "mongodb://final-mongo:27017/lol"),
        "MONGO_DB": os.getenv("MONGO_DB", "lol_realtime"),
        "MONGO_COLL": os.getenv("MONGO_COLL", "matches"),

        # Log level opcional
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    }

try:
    # Pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

    class Settings(BaseSettings):
        # Valores por defecto sensatos para desarrollo local
        MONGO_URI: str = (
            "mongodb://app:appsecret@localhost:27017/"
            "lol_realtime?authSource=lol_realtime"
        )
        MONGO_DB: str = "lol_realtime"

        # Lee de .env si existe
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
        )

    settings = Settings()

except Exception:
    # Fallback sin pydantic
    class _Settings:
        MONGO_URI: str = os.getenv(
            "MONGO_URI",
            "mongodb://app:appsecret@localhost:27017/"
            "lol_realtime?authSource=lol_realtime",
        )
        MONGO_DB: str = os.getenv("MONGO_DB", "lol_realtime")

    settings = _Settings()

__all__ = ["settings"]
