FROM python:3.11-slim

WORKDIR /app

# Añadimos /app al PYTHONPATH para que reconozca el paquete src
ENV PYTHONPATH=/app

# Copiar dependencias
COPY src/riot_fetcher/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente
COPY src /app/src

CMD ["python", "src/riot_fetcher/fetcher.py"]
