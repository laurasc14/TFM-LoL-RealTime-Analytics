# TFM - Análisis en Tiempo Real de Partidas de Videojuegos Competitivos

Este proyecto implementa un sistema de **analítica en tiempo real** para League of Legends (LoL) usando:
- **Apache Kafka** para la ingestión de datos
- **MongoDB** para el almacenamiento
- **Docker Compose** para orquestación de servicios
- **Streamlit** para visualización en dashboard
- Scripts de agregación y análisis con `mongosh`

---


## 🧱 Arquitectura

![Arquitectura del proyecto](./docs/arquitectura_lol_analytics.png)


**Flujo:** Riot API → Kafka → Consumers/ETL → MongoDB → Dashboard

**Servicios (Docker Compose):**
- `zookeeper` + `kafka[1..3]` – cluster Kafka
- `final-riot-fetcher` – productor (RiotWatcher 3.3.x + aiokafka)
- `final-mongo` – base de datos
- *(opcional)* `dashboard` – Streamlit

---

## 🚀 Tecnologías utilizadas

| Tecnología    | Uso                               |
|---------------|-----------------------------------|
| **Docker**    | Contenedorización y orquestación  |
| **Kafka**     | Streaming de datos                |
| **Zookeeper** | Coordinación de Kafka             |
| **MongoDB**   | Base de datos NoSQL               |
| **Python**    | Servicios backend y procesadores  |
| **Streamlit** | Dashboard interactivo             |
| **FastAPI**   | Exposición de datos vía API REST  |
| **Makefile**  | Simplificar la gestión del entorno|

--- 

## 📁 Estructura
```plaintext
├── app/
│ ├── api/ # Servicio FastAPI
│ ├── dashboard/ # Dashboard en Streamlit
│ ├── ingestion/ # Procesamiento de datos
│ └── riot_fetcher/ # Conexión con la API de Riot Games
├── data/ # Datos persistentes (MongoDB, Kafka)
├── connect
├── output
├── src/
│ ├── api/ 
│ ├── dashboard/ 
│ └── services/
│     ├── ingestion/ 
      ├── processing/
│     └── riot_fetcher/
├── .env 
├── docs/ # Diagramas y documentación
├── init-topics.sh # Script para inicializar tópicos Kafka
├── docker-compose.yml # Orquestación de contenedores
├── Makefile # Comandos simplificados para levantar el entorno
└── README.md # Este archivo
```

## 🚀 Puesta en marcha

### 1️⃣ Clonar repositorio
```bash
git clone <URL_REPOSITORIO>
cd FINAL
```

### 2️⃣ Levantar infraestructura
```bash
docker compose up -d --build
```

Esto levanta:
- **Zookeeper**
- **Kafka (3 brokers)**
- **MongoDB**
- **Riot Fetcher** (productor de Kafka)
- **Kafka Consumer**
- **Streamlit Dashboard**

---

## 📊 Scripts de consultas MongoDB

Ejemplo para ejecutar consultas de agregación:

```bash
docker cp db_scripts/queries_extended.js final-mongo:/queries_extended.js
docker exec -it final-mongo mongosh "mongodb://admin:admin@mongo:27017/admin" /queries_extended.js
```

Salida esperada:
```
🏆 Top 5 Campeones por KDA medio:
[ { _id: 'Rengar', avgKDA: 19 }, ... ]

🔥 Top 5 Invocadores por Winrate:
[ { _id: 'TerribleLeafar#EUW', winrate: 100 }, ... ]

⏱ Histograma de duración de partidas (min):
[ { _id: 18, count: 1 }, ... ]
```

---

## 📈 Dashboard con Streamlit

### Construcción y despliegue
```bash
docker compose up -d --build final-dashboard
```

Acceder en navegador:
```
http://localhost:8501
```

---

## 🐳 Dockerfile del dashboard

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     ca-certificates curl &&     rm -rf /var/lib/apt/lists/*

COPY src/dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/dashboard/dashboard_streamlit.py /app/dashboard_streamlit.py

CMD ["streamlit", "run", "dashboard_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 🔌 Variables de entorno relevantes

En `docker-compose.yml`:
```yaml
environment:
  MONGO_URI: mongodb://admin:admin@mongo:27017/lol?authSource=admin
  MONGO_DB: lol
  MONGO_PROCESSED_COLL: matches_processed
```

---

## 📌 Notas
- El sistema requiere **Docker Desktop** y **Python 3.11+** para desarrollo local.
- Los contenedores deben estar en la misma red definida en `docker-compose.yml` (`tfm-net`).
- La ingestión de datos de Riot API requiere una clave API válida.
---

## Autor
Proyecto desarrollado por Laura Solé como parte del Trabajo Fin de Máster, UCM.
