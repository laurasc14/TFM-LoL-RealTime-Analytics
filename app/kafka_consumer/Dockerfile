# syntax=docker/dockerfile:1.6
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src

# Requisitos específicos del consumer
# (ajusta la ruta si tu requirements está en otro sitio)
COPY src/services/kafka_consumer/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código común y de servicio
COPY src ./src
COPY app/kafka_consumer/app.py ./app.py

CMD ["python","-u","app.py"]
