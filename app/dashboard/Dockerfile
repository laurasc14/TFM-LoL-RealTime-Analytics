FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (certs/ca y curl por si lo necesitas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Requisitos de Python (usa el requirements.txt que tienes en src/dashboard)
COPY src/dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el script del dashboard
COPY src/dashboard/dashboard_streamlit.py /app/dashboard_streamlit.py

EXPOSE 8501
CMD ["streamlit", "run", "dashboard_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
