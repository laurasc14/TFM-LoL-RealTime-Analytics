import os
import sys
import subprocess

if __name__ == "__main__":
    # Ruteo del fichero Streamlit dentro del repo
    target = "src/dashboard/dashboard_streamlit.py"

    # Opcional: permitir puerto por env
    port = os.getenv("STREAMLIT_PORT", "8501")
    addr = os.getenv("STREAMLIT_ADDR", "0.0.0.0")

    cmd = [
        sys.executable, "-m", "streamlit", "run", target,
        "--server.port", port,
        "--server.address", addr,
    ]
    subprocess.run(cmd, check=True)
