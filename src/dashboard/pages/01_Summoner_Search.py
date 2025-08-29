import json
import streamlit as st
from src.dashboard.utils.riot import lookup_summoner

st.set_page_config(page_title="Summoner Search", layout="wide")
st.title("Summoner Search  ↪")

name_input = st.text_input("Enter Summoner Name or Riot ID (Name#TAG)", value="", placeholder="p. ej. MEMENTO MØRI#提莫国王")
region = st.text_input("Región (platform tag)", value="euw1", help="euw1, na1, kr, etc.")

if st.button("Search"):
    if not name_input.strip():
        st.warning("Escribe un nombre o Riot ID.")
        st.stop()

    summ = lookup_summoner(name_input.strip(), region.strip().lower())
    st.session_state["summoner"] = summ
    st.success("¡Encontrado y guardado en la sesión!")

summ = st.session_state.get("summoner")
if not summ:
    st.info("Primero busca un invocador; quedará guardado para las demás pestañas.")
    st.stop()

c1, c2, c3 = st.columns([2,1,2])
with c1:
    st.subheader("Name")
    st.write(summ.get("name") or "—")
with c2:
    st.subheader("Level")
    st.metric(label="Level", value=summ.get("level") or "—")
with c3:
    st.subheader("P UUID / ID (encryptedSummonerId)")
    st.text_input("PUUID", value=summ.get("puuid") or "—", disabled=True)
    st.text_input("ID (encryptedSummonerId)", value=summ.get("id") or "—", disabled=True)

with st.expander("Ver JSON completo", expanded=False):
    st.code(json.dumps(summ, ensure_ascii=False, indent=2))
