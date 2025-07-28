Write-Host ">>> Enviando históricos a Kafka..."
docker compose exec ingestion python /app/ingestion/replay_topic.py
Write-Host ">>> Listo. Comprueba con 'docker compose logs ingestion' o en el dashboard."
