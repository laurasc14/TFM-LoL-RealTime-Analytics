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
        "MONGO_DB": os.getenv("MONGO_DB", "lol"),
        "MONGO_COLL": os.getenv("MONGO_COLL", "matches"),

        # Log level opcional
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    }
