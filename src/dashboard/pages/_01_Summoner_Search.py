# src/dashboard/pages/_01_Summoner_Search.py
import os
import requests
import streamlit as st

st.set_page_config(page_title="Summoner Search", page_icon="🔎", layout="wide")

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8081")
PLATFORMS = ["EUW1", "EUN1", "NA1", "BR1", "LA1", "LA2", "OC1", "KR", "JP1", "TR1", "RU"]

def split_riot_id(riot_id: str):
    s = (riot_id or "").strip()
    if "#" in s:
        name, tag = s.split("#", 1)
    elif "/" in s:
        name, tag = [x.strip() for x in s.split("/", 1)]
    else:
        name, tag = s, ""
    return name.strip(), tag.strip()

@st.cache_data(ttl=60 * 60)
def ddragon_version() -> str:
    try:
        r = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=8)
        if r.ok:
            vs = r.json()
            if isinstance(vs, list) and vs:
                return vs[0]
    except Exception:
        pass
    return "14.16.1"

def profile_icon_url(icon_id: int) -> str:
    ver = ddragon_version()
    return f"https://ddragon.leagueoflegends.com/cdn/{ver}/img/profileicon/{icon_id}.png"

def small_label(text, fg="#cbd5e1"):
    st.markdown(f'<div style="font-size:13px;color:{fg};margin-top:8px">{text}</div>', unsafe_allow_html=True)

# ---------------- UI ----------------
st.title("Summoner Search")
st.caption("Busca tu Riot ID y deja guardada la sesión para las otras páginas.")
st.write("**Backend:** ", f"[{BACKEND}]({BACKEND})")

colA, colB = st.columns([1, 3])
with colA:
    platform = st.selectbox("Plataforma", PLATFORMS, index=PLATFORMS.index(st.session_state.get("platform", "EUW1")))
with colB:
    riot_id_in = st.text_input("Riot ID (Nombre#TAG)", value=st.session_state.get("riotid", ""))

search = st.button("Buscar", type="primary")

# ---------------- Logic ----------------
if search:
    name, tag = split_riot_id(riot_id_in)
    if not name or not tag:
        st.error("Introduce tu Riot ID en formato **Nombre#TAG** (por ejemplo: `Buiza#EUW`).")
        st.stop()

    url = f"{BACKEND}/summoner/by-riot-id/{platform}/{requests.utils.quote(name)}/{requests.utils.quote(tag)}"
    try:
        r = requests.get(url, timeout=15)
    except Exception as e:
        st.error(f"No se pudo conectar al backend: {e}")
        st.stop()

    if r.status_code != 200:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        st.error(f"Error {r.status_code}: {detail}")
        st.stop()

    data = r.json()
    puuid = data.get("account", {}).get("puuid")
    if not puuid:
        st.error("Respuesta inesperada: no llegó el PUUID.")
        st.stop()

    # Guardamos claves "planas" (retro-compat)...
    st.session_state["platform"] = platform
    st.session_state["riotid"] = f"{name}#{tag}"
    st.session_state["puuid"] = puuid
    st.session_state["account"] = data.get("account", {})
    st.session_state["summoner"] = data.get("summoner", {})
    if "region" in data:
        st.session_state["region"] = data["region"]

    # ...y una clave compacta y estable para el resto de páginas
    st.session_state["player"] = {
        "platform": platform,
        "puuid": puuid,
        "riot_id": f"{name}#{tag}",
        "account": data.get("account", {}),
        "summoner": data.get("summoner", {}),
        "region": data.get("region", None),
    }
    # Alias opcional si en otro lado mirabas "summoner"/"session_player"/"riot_player"
    st.session_state["session_player"] = st.session_state["player"]
    st.session_state["riot_player"] = st.session_state["player"]

    st.success("✓ Encontrado y guardado en sesión.")

# ---------------- Result card ----------------
if "puuid" in st.session_state:
    acc = st.session_state.get("account", {})
    summ = st.session_state.get("summoner", {})

    st.divider()
    c1, c2 = st.columns([1, 5], vertical_alignment="center")

    with c1:
        icon_id = summ.get("profileIconId")
        icon_src = profile_icon_url(icon_id) if icon_id is not None else \
            "https://raw.githubusercontent.com/LoL-API-stuff/cdn/main/icons/controller.png"
        st.image(icon_src, width=96)
        if "summonerLevel" in summ:
            lvl = summ["summonerLevel"]
            st.markdown(
                f"""
                <div style="display:inline-block;margin-top:6px;padding:3px 8px;border-radius:10px;
                            background:#0e7490;color:#e0f2fe;font-size:12px;">
                    Nivel {lvl}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c2:
        name = acc.get("gameName", "—")
        tag = acc.get("tagLine", "—")
        st.subheader(f"{name}#{tag}")

        small_label("Platform")
        st.markdown(
            f"<span style='background:#1f2937;color:#cbd5e1;padding:3px 8px;border-radius:8px;"
            f"display:inline-block'>{st.session_state.get('platform','—')}</span>",
            unsafe_allow_html=True,
        )

        small_label("PUUID")
        st.markdown(f"<span style='color:#34d399'>{st.session_state['puuid']}</span>", unsafe_allow_html=True)

        with st.expander("Ver JSON"):
            st.json({"account": acc, "summoner": summ, "player": st.session_state.get("player")})

    st.info("Ahora abre **02 Match History** o **03 Champion Stats** para ver tus datos.")
else:
    st.info("Busca un jugador y se guardará en sesión para las demás páginas.")
