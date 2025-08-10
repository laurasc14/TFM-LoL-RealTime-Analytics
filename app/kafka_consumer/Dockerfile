FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY src ./src
COPY app/kafka_consumer/app.py ./app.py

# Módulo env_config en su ruta real ➜ /app/env_config.py
COPY src/config/env_config.py ./env_config.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/src
CMD ["python", "app.py"]
