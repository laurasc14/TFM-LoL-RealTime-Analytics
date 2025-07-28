FROM python:3.11-slim
WORKDIR /app

# Copiar dependencias compartidas
COPY shared/ /app/shared

# Copiar el código de la API
COPY api/ /app/api

# Instalar dependencias
RUN pip install fastapi uvicorn

# Añadir /app al PYTHONPATH para que funcionen los imports
ENV PYTHONPATH=/app

# Ejecutar la API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
