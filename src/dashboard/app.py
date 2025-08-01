import streamlit as st
import requests

st.title("LoL Analytics Dashboard")

try:
    r = requests.get("http://api:8000")
    st.write("API status:", r.json())
except:
    st.write("API not reachable")
