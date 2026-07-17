import os, logging
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

logging.getLogger("streamlit.watcher.local_sources_watcher").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from utils.auth import check_password
from config.database import get_conn
from config.styles import (
    configure_page,
    apply_custom_styles,
    loading_overlay,
    render_welcome_banner,
)
from services.data_loader import cargar_datos_base
from data import build_nbc_condition

from components import render_sidebar

from views import (
    mostrar_metodologia, render_etdh_dashboard,
    render_tab_academico, render_tab_laboral,
    render_tab_territorial, render_tab_decision,
)

try:
    from services.rag.retrieval import EducacionRAG
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

configure_page()
apply_custom_styles()

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

TEMPLATE_COLORS = ["#9B1B30", "#C7A951", "#6B9080", "#52423C", "#C5304A", "#D97706", "#0D9488", "#7C3AED"]
TEMPLATE = go.layout.Template()
TEMPLATE.layout.colorway = TEMPLATE_COLORS
TEMPLATE.layout.paper_bgcolor = "#FFFFFF"
TEMPLATE.layout.plot_bgcolor = "#F9F7F4"
TEMPLATE.layout.font = dict(family="Inter, sans-serif", size=12, color="#0B0F19")

TEMPLATE.layout.hoverlabel = dict(bgcolor="#FFFFFF", font_size=12, font_family="Inter, sans-serif")
TEMPLATE.layout.margin = dict(l=40, r=30, t=50, b=30)
TEMPLATE.layout.xaxis = dict(gridcolor="#E5DDD6", zerolinecolor="#E5DDD6", tickfont_size=11, tickfont_color="#A09088", automargin=True)
TEMPLATE.layout.yaxis = dict(gridcolor="#E5DDD6", zerolinecolor="#E5DDD6", tickfont_size=11, tickfont_color="#A09088", automargin=True)

go.layout.Template._TEMPLATE = TEMPLATE
px.defaults.template = TEMPLATE

import plotly.io as pio
pio.templates.default = TEMPLATE

# ==============================================================================
# LLM ANALYSIS FUNCTION
# ==============================================================================

def analizar_con_llm(contexto: str, nbc_codigo: str = None, departamento: str = None,
                    filtros_activos: dict = None, instrucciones_adicionales: str = ""):
    """
    Envia el contexto al LLM de Gemini para analisis academico riguroso.
    Integra sistema RAG para enriquecer con datos de desercion, SABER, transito.
    """
    try:
        try:
            import google.generativeai as genai
        except Exception:
            genai = None

        if RAG_AVAILABLE and nbc_codigo and departamento:
            try:
                rag_system = EducacionRAG('data/repositorio.duckdb')
                contexto = rag_system.augment_context(
                    nbc_codigo, departamento, contexto, filtros_activos
                )
                rag_system.close()
            except Exception as e:
                print(f"[Warning] Error en RAG, usando contexto base: {e}")

        api_key = os.environ.get('GEMINIAPIKEY') or os.environ.get('GOOGLEAPIKEY')
        if not api_key:
            return "**API Key no configurada.** Configure GEMINIAPIKEY en los Secrets del Space para usar el asistente IA."

        if genai is None:
            return "**Paquete 'google.generativeai' no disponible.** Instale la libreria 'google-generative-ai' o anadala a los requirements del entorno."

        genai.configure(api_key=api_key)

        system_prompt = r"""Eres un INVESTIGADOR SENIOR y EXPERTO ACADEMICO en pertinencia educativa con las siguientes credenciales:

PERFIL ACADEMICO:
- Doctor en Politicas Educativas con enfasis en educacion superior latinoamericana
- 25 años de experiencia en diseño curricular basado en competencias
- Consultor del Ministerio de Educacion Nacional de Colombia
- Experto en el Marco Nacional de Cualificaciones (MNC) y sistema SNIES/SIET
- Investigador en prospectiva laboral y brechas de capital humano
- Especialista en analisis de desercion, calidad educativa (SABER/ICFES) y transito

TU METODOLOGIA DE ANALISIS:
1. ANALIZAR los datos cuantitativos proporcionados con rigor estadistico
2. ENRIQUECER con tu conocimiento del contexto colombiano y tendencias globales
3. INTEGRAR datos de desercion, calidad (SABER), y transito en el analisis de riesgos
4. ARGUMENTAR cada conclusion con evidencia y razonamiento academico
5. VERIFICAR internamente que tus afirmaciones sean coherentes y correctas
6. CITAR SIEMPRE la fuente de cada dato mencionado usando el formato indicado

REGLA CRITICA DE CITACION DE FUENTES:
CADA VEZ que menciones un dato numerico o estadistico, DEBES incluir la fuente entre parentesis.
FORMATO DE CITACION: (FUENTE - Periodo)

CATALOGO DE FUENTES OFICIALES:
| Programas, IES, Matricula   | SNIES - MEN 2024                        |
| Graduados                   | SNIES Graduados - MEN 2014-2024         |
| Educacion ETDH              | SIET - MEN 2023                         |
| Vacantes laborales          | APE - MinTrabajo 2024                   |
| Competencias/Conocimientos  | CUOC - MinTrabajo/DANE 2024             |
| Salarios                    | GEIH - DANE 2023-2024                   |
| Desercion academica         | ES Desercion - MEN Colombia             |
| Pruebas SABER 11/PRO        | ICFES - MEN Colombia                    |
| Score Sistema               | Sistema de Análisis de Contexto para la Toma de Decisiones Educativas 2024 |

NUNCA escribas datos sin fuente.

FORMATO DEL INFORME - ESTILO PAPER ACADEMICO CON LaTeX:
Genera un informe con formato de PAPER ACADEMICO profesional.
NO uses emojis. Usa notacion LaTeX para formulas, metricas y expresiones matematicas.

REGLAS CRITICAS DE LaTeX:
- USA siempre la barra invertida completa: \frac, \sum, \left, \right
- Para porcentajes usa: 47.43\% (con barra antes del %)

ESTRUCTURA DEL INFORME (7 secciones obligatorias):
1. Resumen Ejecutivo
2. Analisis del Mercado Educativo (HHI, CAGR)
3. Pertinencia Laboral y Ocupacional (APE, CUOC, GEIH)
4. Diseno Curricular Recomendado
5. Ecosistema de Microcredenciales
6. Analisis de Riesgos
7. Recomendacion Final y Hoja de Ruta

REGLAS DE REDACCION:
- Tono: Academico formal, estilo paper cientifico
- Formato: Markdown con LaTeX para formulas ($...$ y $$...$$)
- NO usar emojis
- Cada dato numerico DEBE tener fuente citada
- Parrafos sustantivos, no solo listas de bullets"""

        seccion_usuario = ""
        if instrucciones_adicionales and instrucciones_adicionales.strip():
            seccion_usuario = f"""

================================================================================
                    INSTRUCCIONES ADICIONALES DEL USUARIO
================================================================================
SOLICITUD DEL USUARIO:
{instrucciones_adicionales.strip()}

Integra estas solicitudes de forma natural en las secciones correspondientes.
================================================================================
"""

        task_prompt = f"""
Basandote en los DATOS OFICIALES proporcionados a continuacion, genera un INFORME DE PERTINENCIA EDUCATIVA completo y riguroso.

IMPORTANTE:
- Usa TODOS los datos proporcionados en tu analisis
- Enriquece con tu conocimiento del sistema educativo colombiano
- Argumenta cada conclusion con evidencia
- Sigue la estructura de 7 secciones indicada

{contexto}
{seccion_usuario}
Genera el informe completo ahora:
"""

        modelos = [
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-flash-latest',
            'gemini-2.0-flash-lite'
        ]

        ultimo_error = None
        for modelo in modelos:
            try:
                model = genai.GenerativeModel(modelo)
                response = model.generate_content(
                    f"{system_prompt}\n\n{task_prompt}",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=16384,
                        top_p=0.9,
                        top_k=40
                    )
                )
                return response.text
            except Exception as e:
                ultimo_error = str(e)
                continue

        return f"No se pudo conectar con ningun modelo de Gemini. Ultimo error: {ultimo_error}"

    except ImportError:
        return "Modulo google.generativeai no instalado. Ejecute: pip install google-generativeai"
    except Exception as e:
        return f"Error al analizar: {str(e)}"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    if not check_password():
        return

    filtros_seleccionados, filtros_siet_seleccionados = render_sidebar(mostrar_metodologia)

    sel_campos_amplios = filtros_seleccionados['campos_amplios']
    sel_areas = filtros_seleccionados['areas']
    sel_nbcs = filtros_seleccionados['nbcs']
    sel_deptos = filtros_seleccionados['deptos']
    sel_munis = filtros_seleccionados['municipios']
    sel_modalidades = filtros_seleccionados['modalidades']
    sel_sectores = filtros_seleccionados['sectores']
    sel_niveles = filtros_seleccionados['niveles']
    sel_caracteres = filtros_seleccionados['caracteres']
    sel_estados = filtros_seleccionados['estados']
    busqueda_programa = filtros_seleccionados['busqueda_nombre']
    sel_cod_snies_programas = filtros_seleccionados['cod_snies_programas']

    sel_areas_siet = filtros_siet_seleccionados['areas_desempeno']
    sel_deptos_siet = filtros_siet_seleccionados['deptos_siet']
    sel_estados_siet = filtros_siet_seleccionados['estados_siet']
    sel_modalidades_siet = filtros_siet_seleccionados.get('modalidades_siet', [])
    mostrar_siet = filtros_siet_seleccionados['mostrar']

    st.title("Sistema de Análisis de Contexto para la Toma de Decisiones Educativas")
    st.markdown("Evidencia integrada para decisiones de pertinencia y permanencia estudiantil")

    if not st.session_state.get("welcome_banner_shown", False):
        st.session_state["welcome_banner_shown"] = True
        st.toast("Bienvenido al panel de pertinencia", icon=":material/celebration:")

    if not st.session_state.get("banner_dismissed", False):
        c1, c2 = st.columns([20, 1])
        with c1:
            render_welcome_banner(
                title="Bienvenido, tu panel ya esta listo",
                subtitle='"La desercion no debe leerse como un dato aislado de abandono, sino como una señal de pertinencia y sostenibilidad." — Equipo 195',
                mascot="<i class='fas fa-brain'></i>"
            )
        with c2:
            if st.button("X", key="dismiss_banner", help="Cerrar bienvenida"):
                st.session_state["banner_dismissed"] = True
                st.rerun()

    tiene_filtros_snies = (
        busqueda_programa or
        sel_nbcs or sel_campos_amplios or sel_areas or sel_deptos or
        sel_munis or sel_modalidades or sel_sectores or
        sel_niveles or sel_caracteres or sel_estados or
        sel_cod_snies_programas
    )
    tiene_filtros_siet = mostrar_siet or sel_areas_siet or sel_deptos_siet or sel_estados_siet or sel_modalidades_siet or busqueda_programa
    tiene_filtros_academicos_snies = bool(sel_nbcs or sel_areas or sel_campos_amplios)
    if tiene_filtros_academicos_snies:
        tiene_filtros_siet = True

    if not tiene_filtros_snies and not tiene_filtros_siet:
        st.info("Seleccione al menos un **filtro** en el panel lateral para comenzar el analisis.")
        with st.expander("Sobre este Dashboard"):
            st.markdown("""
            Este sistema produce **estudios de contexto** que integran oferta academica, matricula, desercion, desempeno, ocupaciones, competencias y conectividad para orientar **decisiones curriculares**.

            **Filtros en Cascada:**
            - Campo Amplio CINE-F -> filtra Areas de Conocimiento -> filtra NBCs
            - Departamento -> filtra Municipios
            - Todos los filtros son multiselect para analisis comparativos
            """)
        return

    if tiene_filtros_siet and not tiene_filtros_snies:
        st.divider()
        st.markdown('<h4 class="icon-header"><i class="fas fa-tools"></i> Analisis SIET / ETDH (Educacion para el Trabajo)</h4>', unsafe_allow_html=True)
        render_etdh_dashboard(
            areas_desempeno=sel_areas_siet if sel_areas_siet else None,
            deptos=sel_deptos_siet if sel_deptos_siet else None,
            estados_siet=sel_estados_siet if sel_estados_siet else None,
            busqueda_nombre=busqueda_programa if busqueda_programa else None,
            modalidades_siet=sel_modalidades_siet if sel_modalidades_siet else None,
            key_prefix="etdh_standalone"
        )
        return

    with loading_overlay():
        ctx = cargar_datos_base(filtros_seleccionados, filtros_siet_seleccionados)

    ctx.tiene_filtros_snies = tiene_filtros_snies
    ctx.tiene_filtros_siet = tiene_filtros_siet
    ctx.tiene_filtros_academicos_snies = tiene_filtros_academicos_snies

    if ctx.stats['total_programas'] == 0:
        st.warning(f"""
        **No se encontraron programas de "{ctx.nbc_display or 'los filtros seleccionados'}" con los filtros aplicados.**

        Esto puede significar:
        - No existe oferta de este NBC en el departamento seleccionado
        - La combinacion de filtros es muy restrictiva

        **Sugerencia:** Pruebe relajando los filtros o seleccionando otro departamento.
        """)
        with st.expander("Ver donde hay oferta de este NBC"):
            conn = get_conn()
            if ctx.sel_nbcs:
                nbc_cond = build_nbc_condition(ctx.sel_nbcs)
                df_oferta = conn.execute(f"""
                    SELECT "DEPARTAMENTO_OFERTA_PROGRAMA" as Departamento, COUNT(*) as Programas
                    FROM snies.snies_programas WHERE {nbc_cond}
                    GROUP BY 1 ORDER BY 2 DESC
                """).fetchdf()
            else:
                df_oferta = pd.DataFrame()
            conn.close()
            if not df_oferta.empty:
                st.dataframe(df_oferta, hide_index=True, width='stretch')
            else:
                st.info("No hay programas registrados para este NBC en ningun departamento.")
        return

    titulo_analisis = f"Analisis: {ctx.nbc_display}" if ctx.nbc_display else "Analisis con Filtros Seleccionados"
    st.subheader(titulo_analisis)

    filtros_activos = []
    if ctx.depto_display:
        filtros_activos.append(f"{ctx.depto_display}")
    if ctx.sel_modalidades:
        filtros_activos.append(f"{', '.join(ctx.sel_modalidades)}")
    if ctx.sel_sectores:
        filtros_activos.append(f"{', '.join(ctx.sel_sectores)}")
    if ctx.sel_niveles:
        filtros_activos.append(f"{', '.join(ctx.sel_niveles)}")
    if filtros_activos:
        st.caption(f"Filtrado por: {' | '.join(filtros_activos)}")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Programas Activos", f"{ctx.stats['total_programas']:,}")
    k2.metric("IES Ofertantes", f"{ctx.stats['total_ies']:,}")
    k3.metric("Matricula Promedio", f"${ctx.stats['costo_promedio']:,.0f}", help="Valor promedio de matricula para estudiantes nuevos (SNIES)")
    k4.metric("Modalidades", f"{ctx.stats['modalidades']}")

    tab_acad, tab_lab, tab_terr, tab_decision = st.tabs([
        ":material/school: Sintesis Academica",
        ":material/work: Sintesis Laboral",
        ":material/map: Sintesis Territorial",
        ":material/balance: Decision Final"
    ])

    with tab_acad:
        tab1_output = render_tab_academico(ctx)

    with tab_lab:
        tab2_output = render_tab_laboral(ctx)

    with tab_terr:
        tab3_output = render_tab_territorial(ctx)

    with tab_decision:
        render_tab_decision(ctx, tab1_output, tab2_output, tab3_output, analizar_con_llm_fn=analizar_con_llm)


if __name__ == "__main__":
    main()
