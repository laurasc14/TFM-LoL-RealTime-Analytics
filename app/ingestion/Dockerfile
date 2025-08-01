FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app/src

COPY src/ingestion/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src

CMD ["python", "src/ingestion/main.py"]
