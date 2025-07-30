FROM python:3.11-slim
WORKDIR /app

# Copiar dependencias compartidas
COPY shared/ /app/shared
COPY wait-for-kafka.sh /wait-for-kafka.sh

# Copiar el código del riot_fetcher
COPY riot_fetcher/ /app/riot_fetcher

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y netcat-openbsd && chmod +x /wait-for-kafka.sh
RUN pip install requests aiokafka

# Añadir /app al PYTHONPATH para que funcionen los imports
ENV PYTHONPATH=/app

# Ejecutar el fetcher
CMD ["/wait-for-kafka.sh", "python", "-u", "riot_fetcher/fetcher.py"]
