FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app/src

# Copiamos e instalamos dependencias
COPY src/dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Aseguramos que streamlit está disponible
RUN pip install streamlit

# Copiamos el código completo
COPY src /app/src

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
