"""Authentication module — user login and session management."""

import hashlib
import json
import urllib.request
from datetime import datetime
from string import Template

import streamlit as st
from config.styles import T


@st.cache_data(ttl=86400)
def _get_frase():
    try:
        req = urllib.request.Request(
            "https://frasedeldia.azurewebsites.net/api/phrase",
            headers={"User-Agent": "EstudioContexto/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            frase = data.get("phrase", "").strip()
            autor = data.get("author", "").strip()
            if frase:
                return f"{frase} — {autor}" if autor else frase
    except Exception:
        pass
    return ""


@st.cache_data(ttl=3600)
def _get_location_info():
    try:
        req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "EstudioContexto/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            city = data.get("city", "")
            country = data.get("country_name", "")
            if city and country:
                return f"{city}, {country}"
            return country or city or "Colombia"
    except Exception:
        return "Colombia"


def _greeting():
    h = datetime.now().hour
    if h < 12:
        return "Buenos dias"
    elif h < 18:
        return "Buenas tardes"
    return "Buenas noches"


def check_password():
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def credentials_entered():
        try:
            correct_username = st.secrets["AUTH_USERNAME"]
            correct_password_hash = st.secrets["AUTH_PASSWORD_HASH"]
        except Exception:
            correct_username = "admin"
            correct_password_hash = hash_password("EstudioContexto2026!")

        entered_hash = hash_password(st.session_state.get("password", ""))
        if (st.session_state.get("username", "") == correct_username and
            entered_hash == correct_password_hash):
            st.session_state["authenticated"] = True
            del st.session_state["password"]
            del st.session_state["username"]
            return True
        else:
            st.session_state["authenticated"] = False
            return False

    if st.session_state.get("authenticated", False):
        return True

    _render_login(credentials_entered, _greeting(), _get_location_info(), _get_frase())
    return False


def _render_login(credentials_entered, saludo, ubicacion, frase):
    D = T["deep"]
    C = T["crimson"]
    CD = T["crimson_dark"]
    CL = T["crimson_light"]
    CG = T["crimson_glow"]
    G = T["gold"]
    GL = T["gold_light"]
    SG = T["sage"]
    W = T["surface"]
    ST = T["stone"]

    CSS_TPL = Template("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Lora:ital,wght@0,400;0,600;0,700;1,400&display=swap');
header[data-testid="stHeader"]{display:none}
footer{display:none}
.main .block-container{padding:0!important;max-width:100%!important}
.stApp{background:linear-gradient(160deg,$deep 0%,#1a1520 40%,$cdark 100%);background-attachment:fixed}
.stApp::before{content:'';position:fixed;inset:0;opacity:.045;pointer-events:none;z-index:0;background:repeating-linear-gradient(43deg,transparent,transparent 2px,$gold 2px,$gold 3px),repeating-linear-gradient(-43deg,transparent,transparent 7px,$gold 7px,$gold 8px),repeating-linear-gradient(0deg,transparent,transparent 34px,$sage 34px,$sage 35px);animation:pf 24s ease-in-out infinite}
.stApp::after{content:'';position:fixed;bottom:-15%;right:-10%;width:50%;height:50%;background:radial-gradient(ellipse at center,$cglow 0%,transparent 70%);pointer-events:none;z-index:0}
@keyframes pf{0%{transform:translate(0,0) rotate(0)}50%{transform:translate(5px,-2px) rotate(.4deg)}100%{transform:translate(0,0) rotate(0)}}
@keyframes fs{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
div[data-testid="column"]:first-child{position:relative;z-index:1;display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important;min-height:100vh;padding:3rem 2rem!important}
div[data-testid="column"]:last-child{position:relative;z-index:1;background:rgba(10,8,14,.50)!important;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:center!important;min-height:100vh;padding:2.5rem 2rem!important}
[data-testid="stTextInput"]{width:360px!important;max-width:360px!important;display:block;margin-left:auto!important;margin-right:auto!important}
.stTextInput label{color:rgba(255,255,255,.65)!important;font-weight:500!important;font-size:1.15rem!important;margin-bottom:.2rem!important;font-family:Inter,sans-serif}
.stTextInput input{width:100%!important;background:rgba(255,255,255,.06)!important;border:1px solid rgba(255,255,255,.10)!important;border-radius:10px!important;color:$white!important;font-size:1.2rem!important;padding:14px 16px!important;transition:all .25s ease!important;box-shadow:none!important;font-family:Inter,sans-serif}
.stTextInput input::placeholder{color:rgba(255,255,255,.20)!important;font-size:1.1rem!important}
.stTextInput input:focus{border-color:$gold!important;box-shadow:0 0 0 3px rgba(199,169,81,.15)!important;background:rgba(255,255,255,.09)!important;outline:none!important}
.stFormSubmitButton{width:360px!important;margin-left:auto!important;margin-right:auto!important}
.stFormSubmitButton button{background:linear-gradient(135deg,$crim,$cdark)!important;color:$white!important;border:none!important;border-radius:10px!important;padding:16px 24px!important;font-size:1.15rem!important;font-weight:600!important;transition:all .25s ease!important;width:100%!important;margin-top:.3rem;box-shadow:0 4px 16px rgba(155,27,48,.22)}
[data-testid="stForm"] [data-testid="stVerticalBlock"]>*{align-self:center!important}
.stFormSubmitButton button:hover{background:linear-gradient(135deg,$clight,$crim)!important;transform:translateY(-2px);box-shadow:0 8px 24px rgba(155,27,48,.32)!important}
[data-testid="InputInstructions"]{display:none !important}
[data-testid="stForm"]>div{gap:8px !important}
[data-testid="stForm"]{padding:0 !important}
.stTextInput{margin-bottom:0 !important}
.stFormSubmitButton button{margin-top:.3rem !important}
@media(max-width:768px){div[data-testid="column"]:first-child{min-height:30vh;padding:2rem 1.5rem!important}div[data-testid="column"]:last-child{min-height:auto;padding:1.5rem 1rem 3rem 1rem!important}}
</style>""")

    css = CSS_TPL.substitute(
        deep=D, cdark=CD, gold=G, sage=SG, cglow=CG,
        white=W, crim=C, clight=CL, stone=ST
    )
    st.markdown(css, unsafe_allow_html=True)

    col_brand, col_form = st.columns([45, 55], gap="small")

    with col_brand:
        st.markdown(
            f'<div style="width:64px;height:64px;border-radius:18px;background:linear-gradient(135deg,{C},{CD});display:block;margin:0 auto 1.2rem auto;box-shadow:0 6px 24px rgba(155,27,48,.40);animation:fs .8s ease-out"><div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%"><i class="fas fa-chart-line" style="font-size:1.5rem;color:{W}"></i></div></div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div style="font-family:Lora,Georgia,serif;font-size:2.2rem;font-weight:700;color:{W};letter-spacing:-.4px;text-align:center;animation:fs .8s ease-out .05s both">Estudio Contexto</div>'
            f'<div style="font-size:1.2rem;color:{ST};line-height:1.6;max-width:380px;margin:.5rem auto 0 auto;font-family:Inter,sans-serif;text-align:center;animation:fs .8s ease-out .1s both">Analisis de pertinencia educativa para educacion superior en Colombia</div>',
            unsafe_allow_html=True
        )
        if frase:
            st.markdown(
                f'<div style="font-family:Lora,Georgia,serif;font-style:italic;font-size:1rem;color:{GL};text-align:center;margin:1.5rem auto 0 auto;max-width:300px;line-height:1.65;opacity:.75;animation:fs .8s ease-out .18s both">{frase}</div>',
                unsafe_allow_html=True
            )
        st.caption("2026")

    with col_form:
        _, fc, _ = st.columns([1, 2, 1])
        with fc:
            st.markdown(
                f'<div style="display:inline-flex;align-items:center;gap:6px;background:rgba(199,169,81,.10);border:1px solid rgba(199,169,81,.14);border-radius:14px;padding:5px 14px;margin-bottom:1rem;font-size:.85rem;color:{GL};font-weight:500;font-family:Inter,sans-serif">'
                f'<i class="fas fa-map-marker-alt" style="font-size:.75rem;opacity:.7"></i> {ubicacion} | '
                f'<i class="far fa-clock" style="font-size:.75rem;opacity:.7"></i> {saludo}</div>'
                f'<div style="font-family:Lora,Georgia,serif;font-size:2.2rem;font-weight:700;color:{W};letter-spacing:-.2px;margin-bottom:.15rem">Bienvenido de nuevo</div>'
                f'<div style="font-size:1.2rem;color:{ST};margin-bottom:1.8rem;font-family:Inter,sans-serif">Ingresa tus credenciales para continuar</div>',
                unsafe_allow_html=True
            )

            with st.form("login_form", clear_on_submit=False):
                st.text_input("Usuario", key="username", placeholder="usuario@ejemplo.edu.co")
                st.text_input("Contrasena", type="password", key="password", placeholder="Tu contrasena")
                submitted = st.form_submit_button("Iniciar Sesion", use_container_width=False)
                if submitted:
                    if credentials_entered():
                        st.success("Acceso concedido")
                        st.rerun()
                    else:
                        st.error("Usuario o contrasena incorrectos")


def logout():
    st.session_state["authenticated"] = False
    st.rerun()
