FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements.txt (desde raíz del proyecto o ajusta si está en otro sitio)
COPY ./src/riot_fetcher/requirements.txt ./requirements.txt

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY ./src /app/src

# Copiar el archivo .env si lo necesitas dentro del contenedor
COPY .env .env

# Comando por defecto (opcional, si lo usas como ENTRYPOINT)
CMD ["python", "src/riot_fetcher/fetcher.py"]
