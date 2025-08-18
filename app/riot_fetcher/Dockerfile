FROM python:3.11-slim

WORKDIR /app

# Instala dependencias
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia tu código
COPY src ./src
COPY app/riot_fetcher/app.py ./app.py

# Expón el puerto de la API
EXPOSE 8000

# Arranque robusto: uvicorn como módulo (evita problemas de PATH)
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
