# dashboard_streamlit.py
from __future__ import annotations
import sys
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

import streamlit as st
from src.dashboard import Home

st.set_page_config(page_title="Dashboard LoL", page_icon="📊", layout="wide")

# llama a la home real
Home.render()
