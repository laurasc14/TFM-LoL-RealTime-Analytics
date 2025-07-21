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
Riot API → Kafka → Spark Streaming →
├── MongoDB (almacenamiento)
├── Streamlit (visualización)
└── Módulo ML (análisis contextual)


## 🚀 Tecnologías utilizadas

- Apache Kafka
- Apache Spark Streaming
- Python (requests, kafka-python, pandas)
- MongoDB / PostgreSQL
- Streamlit
- Docker
- GitHub

## 📁 Estructura
src/
├── ingestion/ # Productores Kafka
├── processing/ # Spark Streaming
├── storage/ # Guardado en Mongo
├── insights/ # Reglas y modelos ML
├── dashboard/ # Streamlit app
tests/
docs/
configs/


## 🛠 Requisitos

```bash
pip install -r requirements.txt

### 🔐 Configuración de clave API

Este proyecto requiere una clave válida de Riot Games.  
Por seguridad, esta clave no está incluida en el repositorio.

Antes de ejecutar los scripts, crea un archivo:

```plaintext
src/config.py
```

con el siguiente contenido:

```python
RIOT_API_KEY = "tu_clave_aquí"
```

Este archivo está ignorado en `.gitignore` y debe crearse manualmente en cada entorno.
💡 Puedes usar como plantilla el archivo de ejemplo:

```plaintext
src/config_example.py
```
