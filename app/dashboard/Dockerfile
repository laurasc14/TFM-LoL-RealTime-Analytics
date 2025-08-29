# src/dashboard/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# dependencias del sistema mínimas (añade más si alguna lib lo pide)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# copia e instala requirements del dashboard
COPY src/dashboard/requirements.txt /app/src/dashboard/requirements.txt
RUN pip install --no-cache-dir -r /app/src/dashboard/requirements.txt

# copia el proyecto (ajusta si tu código usa más carpetas)
COPY src /app/src

# streamlit en puerto 8501
EXPOSE 8501

# evita que streamlit se queje de no-interactivo
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# <- tu app de Streamlit
CMD ["streamlit","run","/app/src/dashboard/dashboard_streamlit.py","--server.port","8501","--server.address","0.0.0.0"]
