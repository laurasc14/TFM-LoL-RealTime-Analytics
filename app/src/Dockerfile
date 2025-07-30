FROM python:3.11-slim
WORKDIR /app
COPY consumer.py /app/
RUN pip install aiokafka motor
CMD ["python", "consumer.py"]
