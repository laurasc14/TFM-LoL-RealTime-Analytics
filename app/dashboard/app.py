# app/dashboard/app.py
import os, subprocess, sys

# Ruta ABS del dashboard real (multipágina) dentro del contenedor
TARGET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "dashboard", "dashboard_streamlit.py"))

if not os.path.exists(TARGET):
    sys.stderr.write(f"[ERR] No encuentro el dashboard multipágina: {TARGET}\n")
    sys.exit(1)

# Opcional: forzar puerto/dirección si quieres sobreescribir
PORT = os.environ.get("PORT", "8501")
ADDR = os.environ.get("BIND_ADDR", "0.0.0.0")

# Ejecuta Streamlit apuntando al archivo real (esto preserva multipágina)
os.execvp("streamlit", ["streamlit", "run", TARGET, "--server.port", PORT, "--server.address", ADDR])
