# TFM-LoL-RealTime-Analytics

Este proyecto tiene como objetivo realizar análisis en tiempo real de partidas de *League of Legends* utilizando la API de Riot Games. Permite consultar el estado en vivo de las partidas, el historial de partidas, y las estadísticas de los campeones, todo integrado en un *dashboard* interactivo con **Streamlit**.

---

## Funcionalidades

- Consulta el estado de las partidas activas en tiempo real.
- Accede al historial de partidas de un invocador.
- Estadísticas de campeones por partida.
- Visualización interactiva de los datos a través de **Streamlit**.
- Utiliza la API de Riot Games para obtener los datos de las partidas y los invocadores.

---

## Tecnologías

- **Python 3.11**
- **Streamlit** para la interfaz de usuario.
- **API de Riot Games** para obtener información sobre las partidas y los invocadores.
- **Docker** para la contenedorización del proyecto.

---

## Requisitos

Antes de ejecutar el proyecto, asegúrate de tener instalado lo siguiente:

- **Python 3.11** o superior
- **Docker** (si deseas usar contenedores)
- **API Key de Riot Games** (se obtiene desde [Riot Developer Portal](https://developer.riotgames.com/))

---

## Instalación

1. Clona este repositorio:

    ```bash
    git clone https://github.com/laurasc14/TFM-LoL-RealTime-Analytics.git
    ```

2. Navega al directorio del proyecto:

    ```bash
    cd TFM-LoL-RealTime-Analytics
    ```

3. Crea y activa un entorno virtual:

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows, usa .venv\Scripts\activate
    ```

4. Instala las dependencias:

    ```bash
    pip install -r requirements.txt
    ```

5. Establece la clave de la API de Riot Games:

    - Regístrate en el [Riot Developer Portal](https://developer.riotgames.com/).
    - Obtén tu API Key.
    - Configura la clave en tu entorno:

      ```bash
      export RIOT_API_KEY="tu_api_key"  # En Windows usa set en vez de export
      ```
---

## Uso

---
### Sin Docker

1. Para ejecutar la aplicación de *Streamlit* de forma local:

    ```bash
    streamlit run src/dashboard/dashboard_streamlit.py
    ```

2. Accede al dashboard desde tu navegador en `http://localhost:8501`.

### Con Docker

Si prefieres usar **Docker** para ejecutar el proyecto:

1. Construye la imagen del contenedor:

    ```bash
    docker compose build final-dashboard
    ```

2. Ejecuta el contenedor:

    ```bash
    docker compose up -d final-dashboard
    ```

3. Accede al dashboard desde tu navegador en `http://localhost:8501`.

## Actualización de la API Key

Si estás utilizando **Streamlit Cloud**, puedes agregar tu API Key en la sección de *secrets* para configurarla automáticamente sin necesidad de pasarla por variables de entorno.

---
## Contribuciones

Las contribuciones son bienvenidas. Si encuentras errores o tienes sugerencias, por favor abre un *issue* o envía un *pull request*. Asegúrate de seguir las siguientes pautas para las contribuciones:

1. Realiza un fork del repositorio.
2. Crea una nueva rama (`git checkout -b nueva-funcionalidad`).
3. Realiza tus cambios y haz commit (`git commit -m 'Añadir nueva funcionalidad'`).
4. Empuja tus cambios (`git push origin nueva-funcionalidad`).
5. Crea un *pull request*.

---
## Autor
Proyecto desarrollado por Laura Solé como parte del Trabajo Fin de Máster, UCM.
