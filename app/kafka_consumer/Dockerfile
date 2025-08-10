FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY app/kafka_consumer/app.py ./app.py
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:${PYTHONPATH}
CMD ["python", "app.py"]
