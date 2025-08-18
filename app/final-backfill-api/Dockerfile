FROM python:3.11-slim

WORKDIR /app

# deps
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# código
COPY src ./src

# que Python encuentre /app/src como raíz de paquetes
ENV PYTHONPATH=/app/src

EXPOSE 8000

# OJO: ahora apuntamos a tools.backfill_api y le indicamos el app-dir
CMD ["uvicorn", "tools.backfill_api:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/src"]
