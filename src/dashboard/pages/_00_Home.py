import streamlit as st
import requests
import random

# No llames a set_page_config aquí; ya lo hace el entrypoint.

SPLASH = "https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Ahri_0.jpg"

def _init_state():
    if "theme" not in st.session_state:
        st.session_state["theme"] = "dark"
    if "dd_version" not in st.session_state:
        st.session_state["dd_version"] = "14.18.1"

def _styles(theme: str):
    # Paleta según tema
    if theme == "light":
        overlay1 = "rgba(255,255,255,.70)"
        overlay2 = "rgba(255,255,255,.70)"
        card_bg  = "rgba(0,0,0,.04)"
        card_bd  = "rgba(0,0,0,.10)"
        text_op  = "0.85"
    else:  # dark
        overlay1 = "rgba(10,10,14,.80)"
        overlay2 = "rgba(10,10,14,.80)"
        card_bg  = "rgba(255,255,255,.05)"
        card_bd  = "rgba(255,255,255,.10)"
        text_op  = "0.90"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient({overlay1}, {overlay2}),
                        url('{SPLASH}') center/cover fixed no-repeat;
        }}
        .hero {{
            text-align:center; 
            padding: 6rem 1rem 1rem 1rem;
        }}
        .hero h1 {{
            font-size: 3.2rem; 
            margin: 0.2rem 0;
            letter-spacing: .5px;
        }}
        .hero p {{
            font-size: 1.05rem; 
            opacity: {text_op};
            margin-top: .4rem;
        }}
        .card {{
            background: {card_bg};
            border: 1px solid {card_bd};
            border-radius: 16px;
            padding: 1rem;
            backdrop-filter: blur(4px);
        }}
        .footer {{
            text-align:center; 
            opacity:.8; 
            font-size:.9rem; 
            padding:2rem 0 1rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def _hero():
    st.markdown(
        """
        <div class="hero">
            <img src="https://upload.wikimedia.org/wikipedia/commons/7/77/League_of_Legends_logo.png" width="220">
            <h1>LoL Dashboard</h1>
            <p>Explora estadísticas en tiempo real: invocadores, historial de partidas, campeones y partidas en vivo.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def _toolbar():
    # Toggle de tema + selector de versión DDragon
    col1, col2, col3 = st.columns([1.2, 1, 3])
    with col1:
        use_light = st.toggle("🌞 Tema claro", value=(st.session_state["theme"] == "light"), key="home_theme_toggle")
        st.session_state["theme"] = "light" if use_light else "dark"
    with col2:
        versions = ["14.18.1", "14.17.1", "14.16.1", "14.15.1"]
        try:
            default_idx = versions.index(st.session_state["dd_version"])
        except ValueError:
            default_idx = 0
        chosen = st.selectbox("DDragon", options=versions, index=default_idx, key="dd_version_select")
        st.session_state["dd_version"] = chosen
    with col3:
        st.write("")  # espacio

def _quick_links():
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🔎  Summoner Search", use_container_width=True):
            st.session_state["__go_to"] = "Summoner Search"
            st.rerun()
    with c2:
        if st.button("📜  Match History", use_container_width=True):
            st.session_state["__go_to"] = "Match History"
            st.rerun()
    with c3:
        if st.button("📊  Champion Stats", use_container_width=True):
            st.session_state["__go_to"] = "Champion Stats"
            st.rerun()
    with c4:
        if st.button("🟢  Live Game", use_container_width=True):
            st.session_state["__go_to"] = "Live Game"
            st.rerun()

@st.cache_data(ttl=3600)
def get_champion_names(version_hint: str):
    """Descarga la lista de campeones desde DDragon o devuelve un fallback."""
    url = f"https://ddragon.leagueoflegends.com/cdn/{version_hint}/data/en_US/champion.json"
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        return sorted(list(data["data"].keys()))
    except Exception:
        return [
            "Ahri","Yasuo","Lux","LeeSin","Jinx","Darius",
            "Zed","Ezreal","Katarina","Garen","Vayne","Ashe"
        ]

def _champion_grid(version: str):
    champs = get_champion_names(version)
    sample = random.sample(champs, k=min(12, len(champs)))

    st.markdown("#### Campeones destacados")
    grid_cols = 6
    rows = (len(sample) + grid_cols - 1) // grid_cols

    for r in range(rows):
        cols = st.columns(grid_cols)
        for i, col in enumerate(cols):
            idx = r * grid_cols + i
            if idx >= len(sample):
                continue
            name = sample[idx]
            img_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{name}.png"
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.image(img_url, use_container_width=True)
                st.markdown(
                    f"<div style='text-align:center; margin-top:.35rem;'>{name}</div>",
                    unsafe_allow_html=True
                )
                st.markdown('</div>', unsafe_allow_html=True)

def _what_you_can_do():
    st.markdown("### ¿Qué puedes hacer aquí?")
    st.markdown(
        """
        - **Buscar invocadores** y ver rangos y últimos resultados.
        - Consultar **historial de partidas** con filtros por cola, fecha y campeón.
        - Revisar **estadísticas por campeón** (KDA, winrate, builds más usadas).
        - Comprobar si hay **partida en vivo** y extraer composición y runas.
        """
    )

def main():
    _init_state()
    _styles(st.session_state["theme"])
    _hero()
    _toolbar()
    _quick_links()
    st.write("")  # espacio
    _champion_grid(st.session_state["dd_version"])
    _what_you_can_do()
    st.markdown('<div class="footer">Usa el menú de la izquierda o los accesos rápidos para empezar.</div>', unsafe_allow_html=True)
