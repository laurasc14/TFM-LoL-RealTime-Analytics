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

- Lenguaje: Python
- Ingestión: Apache Kafka
- Procesamiento: Apache Spark Streaming
- Almacenamiento: MongoDB / PostgreSQL
- Visualización: Streamlit
- Infraestructura: Docker
- Control de versiones: GitHub

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
