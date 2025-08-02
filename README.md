# TFM - Análisis en Tiempo Real de Partidas de Videojuegos Competitivos

Este repositorio contiene el desarrollo del Trabajo de Fin de Máster en Ingeniería de Datos (UCM), titulado:

**"Análisis inteligente en tiempo real de partidas de videojuegos competitivos"**

## 🎯 Objetivo

Desarrollar una plataforma capaz de:
- Ingerir datos en tiempo real desde la API de Riot Games (League of Legends).
- Procesar los eventos con Spark Streaming.
- Detectar eventos tácticos relevantes (snowballs, comebacks...).
- Visualizar estadísticas y análisis contextual en un dashboard interactivo.
- Integrar lógica basada en reglas y modelos ligeros de ML.

## 🧱 Arquitectura General
```plaintext
Riot API 
   ↓
Apache Kafka 
   ↓
Spark Streaming 
   ├── MongoDB / PostgreSQL (almacenamiento)
   ├── Streamlit (visualización)
   └── Módulo ML (análisis contextual)
```


## 🚀 Tecnologías utilizadas

- **Docker & Docker Compose** – Orquestación de todos los servicios.
- **Kafka (3 brokers)** – Ingestión y distribución de eventos en tiempo real.
- **Zookeeper** – Coordinación de los brokers Kafka.
- **MongoDB** – Base de datos NoSQL para almacenar partidas y estadísticas.
- **FastAPI** – Backend para exponer datos y endpoints.
- **Streamlit** – Dashboard para visualización de métricas.
- **Python** – Lógica de procesamiento e ingestión.
- **Makefile** – Automatización de comandos Docker.
- **Bash Scripts** – Inicialización automática de tópicos Kafka.

## 📁 Estructura
```plaintext
src/
├── ingestion/       # Productores Kafka
├── riot_fetcher/    # Obtención de datos desde la API de Riot
├── processing/      # Procesamiento con Spark Streaming
├── storage/         # Guardado en Mongo/PostgreSQL
├── dashboard/       # Aplicación Streamlit
├── shared/          # Configuración compartida
tests/               # Pruebas
docs/                # Documentación
```


## 🛠 Requisitos

```bash
pip install -r requirements.txt

### 🔐 Configuración de clave API

Este proyecto requiere una clave válida de Riot Games.  
Por seguridad, esta clave no está incluida en el repositorio.

Antes de ejecutar los scripts, crea un archivo:

```plaintext
shared/onfig.py
```

con el siguiente contenido:

```python
RIOT_API_KEY = "tu_clave_aquí"
```

Este archivo está ignorado en `.gitignore` y debe crearse manualmente en cada entorno.
💡 Puedes usar como plantilla el archivo de ejemplo:

```plaintext
shared/config_example.py
```

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

## 📊 Tópicos Kafka

| Tópico        | Particiones | Replicación | Retención |
| ------------- | ----------- | ----------- | --------- |
| `lol-matches` | 6           | 3           | 7 días    |
| `lol-players` | 6           | 3           | 7 días    |
| `lol-events`  | 6           | 3           | 3 días    |

## 🔮 Próximos pasos

- Integración con sistema de métricas (Prometheus + Grafana).
- Autenticación en la API.
- Mejora del Dashboard con visualizaciones avanzadas.

## Autor
Proyecto desarrollado por Laura Solé como parte del Trabajo Fin de Máster.
