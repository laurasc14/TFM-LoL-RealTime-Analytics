# TFM - Análisis en Tiempo Real de Partidas de Videojuegos Competitivos

Este proyecto busca desarrollar un sistema de analítica en tiempo real para partidas de League of Legends, utilizando un stack de procesamiento basado en Kafka, MongoDB y servicios en contenedores para adquisición, ingestión y visualización de datos.

---

## 🎯 Objetivo

Plataforma para:
- Ingerir datos en tiempo real desde la **Riot API (LoL)**.
- Publicar eventos en **Kafka** y consumirlos con **Python (aiokafka)**.
- Persistirlos en **MongoDB**.
- Mostrar métricas en un **dashboard (Streamlit)**.
- Sentar bases para detección de eventos tácticos (reglas/ML ligero).

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
│     └── riot_fetcher/
├── .env 
├── docs/ # Diagramas y documentación
├── init-topics.sh # Script para inicializar tópicos Kafka
├── docker-compose.yml # Orquestación de contenedores
├── Makefile # Comandos simplificados para levantar el entorno
└── README.md # Este archivo
```
---

## 🚀 Puesta en marcha

### 1) Prerrequisitos
- Docker + Docker Compose
- Clave válida de Riot Games

### 2) Configuración
Crea `src/config/config.py` (no versionado) con:
```python
RIOT_API_KEY = "TU_CLAVE_AQUI"
```

Este archivo está ignorado en `.gitignore` y debe crearse manualmente en cada entorno.
💡 Puedes usar como plantilla el archivo de ejemplo:

```plaintext
src/config/config_example.py
```

Edita .env (o variables) para:

````python
SUMMONER_NAME="NOMBRE#TAG"
KAFKA_BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9093,kafka3:9094"
````
### 3) Levantar infraestructura

```python
docker compose up -d
```

### 4) Ver logs del fetcher

```python
docker logs -f final-riot-fetcher
```

Deberías ver:

- PUUID resuelto
- Últimas partidas (EUW1_xxxxx)
- Mensajes producidos al tópico matches

Nota: el tópico matches se autocrea. El primer envío puede mostrar “Topic … is not available during auto-create initialization”; es normal y se resuelve solo en segundos.
---
## 📊 Datos y tópicos
- Topic: matches 
- Payload ejemplo:

```python
{"match_id": "EUW1_7485826231", "timestamp": 1754648870.0463}
```
- Colección Mongo (sugerida): lol.matches_raw
---
## 🧰 Scripts útiles

````python
docker compose down -v           # parar y borrar volúmenes
docker compose build --no-cache  # reconstruir imágenes
docker logs -f final-riot-fetcher

````
---
## ⚡ Comandos Rápidos

Antes de empezar, asegúrate de tener Docker y Make instalados.  
En Windows puedes instalar `make` con:
```bash
winget install GnuWin32.Make
```

Levantar todos los servicios
```bash
make up
```

Ver logs
```bash
make logs
```

Apagar servicios
```bash
make down
```

Reiniciar todo y reconstruir imágenes
```bash
make reset
```

Verificar contenedores en ejectución
```bash
make ps
```

Re-crear tópicos Kafka
```bash
make recreate-topics
```

Probar productor de datos simulados
```bash
make producer-mock
```

---

## 🚀 Cómo ejecutar el proyecto

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/laurasc14/TFM-LoL-RealTime-Analytics.git
   cd TFM-LoL-RealTime-Analytics
   ```
2. **Levantar la infraestructura**
    ```bash
   make up
   ```
3. (Opcional) Incializar tópicos Kafka
    ```bash
   make init-topics
   ```
   
4. (Opcional) Ejecutar productor mock
    ```bash
   make producer-mockhttps://github.com/laurasc14/TFM-LoL-RealTime-Analytics
   ```

5. Detener entorno
    ```bash
   make down
   ```

---

## 🔧 Comandos útiles
**Crear un nuevo tópico:**
   ```bash
   docker exec -it kafka1 kafka-topics.sh --create --topic <nombre> --partitions 3 --replication-factor 3 --bootstrap-server kafka1:9092
   ```
**Probar productor/consumidor:**
   ```bash
   docker exec -it kafka1 kafka-console-producer.sh --broker-list kafka1:9092 --topic test
   docker exec -it kafka1 kafka-console-consumer.sh --bootstrap-server kafka1:9092 --topic test --from-beginning
   ```

---

## 📊 Tópicos Kafka

| Tópico        | Particiones | Replicación | Retención |
| ------------- | ----------- | ----------- | --------- |
| `lol-matches` | 6           | 3           | 7 días    |
| `lol-players` | 6           | 3           | 7 días    |
| `lol-events`  | 6           | 3           | 3 días    |

---
## ✅ Estado actual (MVP)

- ✔️ Productor Riot → Kafka operativo 
- ✔️ Autocreación de tópico matches
- ⏳ Consumer a Mongo (en progreso)
- ⏳ Dashboard Streamlit (en progreso)
- ⏳ Reglas/ML (siguientes iteraciones)

---

## 🗺️ Roadmap corto

- Consumer asíncrono → MongoDB 
- Esquema y validaciones (pydantic)
- Dashboard inicial (últimas partidas, filtros)
- Enriquecimientos: duración, modo, equipos, KDA por jugador 
- Reglas básicas (snowball/comeback)

---

## 📚 Notas

- Librería: riotwatcher >= 3.3.1 (no existe 3.2.6 en PyPI). 
- Endpoints: Account (puuid) y Match (list/details) con routing europeo.

---

## 📌 Validaciones recientes
Tras la última ejecución del final-kafka-consumer, se realizaron pruebas y validaciones para confirmar la correcta ingestión y persistencia de datos en MongoDB desde Kafka.

1. **Estado de la colección matches_raw**
   ```bash
   # Total de documentos
   db.matches_raw.countDocuments()
   ```
Resultado:
   ```bash
  5
   ```
2. **Ejemplo de documentos almacenados**
   ```bash
   db.matches_raw.find(
   {},
   { _id: 0, match_id: 1, 'metadata.dataVersion': 1, 'info.gameDuration': 1 }
   ).sort({ _id: -1 }).limit(3).toArray()
   ```
Resultado:
   ```bash
   [
  {
    "match_id": "EUW1_7488804638",
    "info": { "gameDuration": 1709 },
    "metadata": { "dataVersion": "2" }
  },
  {
    "match_id": "EUW1_7488826864",
    "info": { "gameDuration": 1138 },
    "metadata": { "dataVersion": "2" }
  },
  {
    "match_id": "EUW1_7488855596",
    "info": { "gameDuration": 1712 },
    "metadata": { "dataVersion": "2" }
  }
]
  ````

3. **Verificación de índices**
  ```bash
  db.matches_raw.getIndexes()
  ```
Resultado:
   ````python
   [
  { "v": 2, "key": { "_id": 1 }, "name": "_id_" },
  { "v": 2, "key": { "match_id": 1 }, "name": "ux_match_id", "unique": true }
]
   ````

4. **Observaciones del consumer**
- Conexión exitosa a Kafka y MongoDB. 
- Se están realizando upserts correctamente:
  - matched=1, modified=1 → documento encontrado y actualizado. 
  - matched=1, modified=0 → documento encontrado, sin cambios.

- No se han producido errores de pydantic ni de env_config tras ajustes de rutas y variables.

- Algunos documentos iniciales podrían carecer de ciertos campos por:
  - Partidas antiguas sin datos completos. 
  - Fallos de red o límites de la API en el fetch inicial.

El commit quedaría:
````makefile
docs: actualizar README con validaciones de MongoDB/Kafka y estado del consumer
````
---

## Autor
Proyecto desarrollado por Laura Solé como parte del Trabajo Fin de Máster, UCM.
