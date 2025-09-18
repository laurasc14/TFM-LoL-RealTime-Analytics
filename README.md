# 🎮 LoL RealTime Analytics – Trabajo Fin de Máster (UCM)

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Streamlit](https://img.shields.io/badge/streamlit-dashboard-red.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

Proyecto desarrollado como **Trabajo de Fin de Máster en Big Data & Data Engineering (UCM, 2025)**.  
El objetivo es implementar una **plataforma de análisis en tiempo real de partidas de League of Legends**, integrando tecnologías de ingesta, procesamiento distribuido, almacenamiento NoSQL y visualización interactiva.

---

## ✨ Funcionalidades principales

- 🔍 **Summoner Search** → búsqueda de invocadores por nombre y estadísticas básicas.  
- 🛡️ **Champion Stats** → métricas agregadas de campeones por partida.  
- 📜 **Match History** → cronología de partidas anteriores con resultados y eventos.  
- 📡 **Live (placeholder)** → base para análisis de partidas en curso en tiempo real.  
- 📊 **Dashboard en Streamlit** → interfaz simple e interactiva para visualizar los datos.  

---

## 🛠️ Tecnologías empleadas

- **Python 3.11**  
- **Kafka + Spark Streaming** → ingesta y procesamiento en tiempo real  
- **MongoDB** → almacenamiento flexible de datos semiestructurados  
- **Streamlit** → dashboard interactivo  
- **Docker / Docker Compose** → contenedorización y despliegue reproducible  
- **Riot Games API** → fuente oficial de datos de juego  

---

## 📋 Requisitos previos

- [Python 3.11](https://www.python.org/downloads/)  
- [Docker](https://www.docker.com/) + Docker Compose (opcional, para despliegue en contenedores)  
- **API Key de Riot Games** (desde el [Riot Developer Portal](https://developer.riotgames.com/))  

---

## ⚙️ Instalación y uso

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/laurasc14/TFM-LoL-RealTime-Analytics.git
   cd TFM-LoL-RealTime-Analytics
   ```

2. Crear entorno virtual e instalar dependencias:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Crear un archivo `.env` en la raíz del proyecto y añadir tu API Key de Riot Games:

   ```env
   RIOT_API_KEY=tu_api_key
   ```

4. Ejecutar el dashboard localmente:

   ```bash
   streamlit run src/dashboard/dashboard_streamlit.py
   ```

   Accede en 👉 [http://localhost:8501](http://localhost:8501)

---

### ▶️ Ejecución con Docker

```bash
docker compose build final-dashboard
docker compose up -d final-dashboard
```

Dashboard disponible en 👉 [http://localhost:8501](http://localhost:8501)

---

## 📊 Resultados obtenidos

- Pipeline **funcional y validado** desde Riot API → Kafka → Spark → MongoDB → Dashboard.  
- **Latencia media**: ~1,8 segundos.  
- **Throughput**: >200 eventos/segundo en pruebas locales.  
- Dashboard con **Summoner Search, Champion Stats, Match History** y placeholder de **Live**.  

---

## 🚀 Futuras mejoras

- Completar el módulo **Live** con estadísticas en tiempo real de partidas en curso.  
- Desplegar en la nube (GCP/AWS/Azure) para validar la escalabilidad.  
- Incorporar un **módulo ML avanzado** para detección de jugadas y predicciones.  
- Extender el dashboard con comparativas entre equipos, regiones o torneos.  

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas:  
1. Haz un fork del repo  
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)  
3. Haz tus cambios y commit (`git commit -m 'feat: nueva funcionalidad'`)  
4. Push (`git push origin feature/nueva-funcionalidad`)  
5. Abre un Pull Request  

---

## 👩‍💻 Autor

**Laura Solé Català**  
Máster en Big Data & Data Engineering – Universidad Complutense de Madrid (UCM)  
Trabajo Fin de Máster · 2025  
