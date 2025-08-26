FROM python:3.11-slim

WORKDIR /app

# deps nativos básicos (compila rápido y sin bloat)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# requirements (usa el tuyo; si no, añade estos mínimos)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir riotwatcher kafka-python pymongo requests

# copia SOLO lo que necesitamos
COPY src ./src

# por defecto no ejecuta nada; cada servicio pondrá su CMD
