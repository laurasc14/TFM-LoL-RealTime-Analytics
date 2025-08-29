# syntax=docker/dockerfile:1.6
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src

# Requisitos del match-expander
COPY src/match-expander/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código común
COPY src ./src

# Si tu servicio tiene ficheros propios adicionales, cópialos también:
# COPY app/match-expander/*.py ./service/

# HEALTHCHECK opcional en Dockerfile (sin heredoc). Si prefieres, déjalo en compose.
# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
#   CMD python -c "import os,socket,sys; b=os.getenv('KAFKA_BROKERS','final-kafka:9092').split(',')[0]; h,p=b.split(':'); s=socket.create_connection((h,int(p)),3); s.close()"

CMD ["python","-u","-m","src.processing.match_expander"]
