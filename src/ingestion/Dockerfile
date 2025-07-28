FROM python:3.11-slim
WORKDIR /app

# Copiar dependencias compartidas
COPY shared/ /app/shared
COPY wait-for-kafka.sh /wait-for-kafka.sh
COPY requirements.txt /requirements.txt

# Copiar el código de ingestion
COPY src/ingestion/ /app/ingestion

# Instalar dependencias
RUN apt-get update && apt-get install -y netcat-openbsd && chmod +x /wait-for-kafka.sh
RUN pip install -r /requirements.txt

# Añadir /app al PYTHONPATH para que funcionen los imports
ENV PYTHONPATH=/app

# Ejecutar el main de ingestion
CMD ["/wait-for-kafka.sh", "python", "-u", "ingestion/main.py"]
