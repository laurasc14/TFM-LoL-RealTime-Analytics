Write-Host ">>> Levantando todo el stack (Kafka, Connect, API, Dashboard)..."
docker compose up -d
Write-Host ">>> Espera unos segundos y verifica con 'docker compose ps'"
