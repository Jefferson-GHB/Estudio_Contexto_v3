import os, logging
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import streamlit as st
import pandas as pd
import html
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

# Suprimir ruido en consola
logging.getLogger("streamlit.watcher.local_sources_watcher").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

# ==============================================================================
# IMPORTS DE MÓDULOS PROPIOS
# ==============================================================================
from utils.auth import check_password
from utils.helpers import descargar_datos_grafico
from config.database import get_conn
# Constants used internally by data/filters.py - not needed here
from config.styles import (
    configure_page,
    apply_custom_styles,
    loading_overlay,
    render_welcome_banner,
    insight_card,
)
from services import (
    determinar_tipo_oferta, generar_contexto_analisis,
    calcular_hhi, calcular_cagr, calcular_ratio_absorcion, calcular_score_final
)
from visualizations.charts import crear_gauge, crear_gauge_hhi, crear_gauge_saber, crear_distribucion_saber

# DOCX report generator
from utils.reporte_docx import generar_reporte_docx

# Components
from components import render_sidebar
from components.display import section_header

# Data layer - filters and queries
from data import (
    # Filters
    build_nbc_condition,
    resolver_nbcs_desde_filtros, mapear_niveles_snies_a_mnc,
    # SIET/ETDH
    get_estadisticas_siet, get_desglose_siet, get_programas_detalle_siet,
    get_siet_tendencia_matricula, get_siet_tendencia_certificados,
    get_siet_tendencia_por_area, get_siet_top_instituciones,
    get_siet_top_programas, get_siet_desglose_oferta,
    get_siet_tasa_certificacion_historica,
    get_siet_matricula_por_depto,
    get_comparativa_snies_siet_por_depto, get_comparativa_tipo_formacion,
    # Explorador
    get_datos_explorador_interactivo,
    # SNIES Académico
    get_benchmarking_data, get_market_share, get_programas_detalle,
    get_tendencia_matricula, get_tendencia_inscritos, get_tendencia_admitidos,
    get_tendencia_primer_curso, get_graduados_historico, get_graduados_nacionales,
    get_estadisticas_basicas, get_desglose_academico,
    # Territorial
    get_conectividad_territorial, get_municipios_pdet,
    get_indicadores_educativos_depto, get_graduados_depto_nbc,
    get_matriculados_depto_nbc, get_oferta_programas_depto,
    get_salarios_depto, get_ranking_departamental_nbc,
    # Laboral
    get_vacantes_reales, get_competencias_cuoc, get_salarios_reales,
    get_tendencia_laboral_nbc, get_graduados_nbc_historico,
    get_actividades_tareas_nbc, get_destrezas_cuoc_nbc, get_conocimientos_cuoc_nbc,
    # Global
    get_indicadores_globales, get_habilidades_futuro_filtradas,
    get_habilidades_esco,
    # MEN
    get_estadisticas_cualificaciones_men, get_cualificaciones_por_nbc
)

# Importar módulo de fuentes de datos para citaciones
from services.sources import get_citacion

# Views
from views import mostrar_metodologia, render_etdh_dashboard

# ML matching - importado y usado internamente por data/queries.py
# No se importa aquí directamente

# Importar modulo de ML matching SNIES <-> ETDH (pipeline v2 unificado)
try:
    from services.ml.snies_etdh import (
        match_nbc_to_siet_v2,
        get_skills_bridge_analysis_v2,
        validate_bridge,
    )
    ML_ETDH_AVAILABLE = True
except ImportError:
    ML_ETDH_AVAILABLE = False

# Importar funciones territoriales robustas (con normalización + ML)
try:
    from services.territorial.functions import (
        get_desempeno_dnp, get_cluster_empresarial,
    )
    from services.territorial.normalization import get_region
    TERRITORIAL_ROBUST = True
except ImportError:
    TERRITORIAL_ROBUST = False

# Importar sistema RAG para enriquecimiento de contexto
try:
    from services.rag.retrieval import EducacionRAG
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Configuración de página y estilos
configure_page()
apply_custom_styles()

# Add root path
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

# Old xaxis/yaxis replaced above — merged into template margin block
go.layout.Template._TEMPLATE = TEMPLATE
px.defaults.template = TEMPLATE

# Registrar como template default para TODO (go.Figure y px)
import plotly.io as pio
pio.templates.default = TEMPLATE

# ==============================================================================
# CACHE & DATA LOADING
# ==============================================================================

def analizar_con_llm(contexto: str, nbc_codigo: str = None, departamento: str = None,
                    filtros_activos: dict = None, instrucciones_adicionales: str = ""):
    """
    Envia el contexto al LLM de Gemini para analisis academico riguroso.
    Integra sistema RAG para enriquecer con datos de deserción, SABER, tránsito.
    
    Args:
        contexto: Contexto base del sistema
        nbc_codigo: Código NBC para retrieval contextual
        departamento: Departamento para filtrado territorial
        filtros_activos: Dict con TODOS los filtros aplicados por el usuario
        instrucciones_adicionales: Instrucciones del usuario
    """
    try:
        try:
            import google.generativeai as genai
        except Exception:
            genai = None
        
        # ENRIQUECIMIENTO RAG: Agregar datos adicionales si está disponible
        if RAG_AVAILABLE and nbc_codigo and departamento:
            try:
                rag_system = EducacionRAG('data/repositorio.duckdb')
                contexto = rag_system.augment_context(
                    nbc_codigo, departamento, contexto, filtros_activos
                )
                rag_system.close()
            except Exception as e:
                print(f"[Warning] Error en RAG, usando contexto base: {e}")
        
        # API Key desde variables de entorno (configurar en HF Spaces Secrets)
        api_key = os.environ.get('GEMINIAPIKEY') or os.environ.get('GOOGLEAPIKEY')
        if not api_key:
            return "**API Key no configurada.** Configure GEMINIAPIKEY en los Secrets del Space para usar el asistente IA."
        
        if genai is None:
            return "**Paquete 'google.generativeai' no disponible.** Instale la librería 'google-generative-ai' o añádala a los requirements del entorno."

        genai.configure(api_key=api_key)
        
        # Prompt del sistema - Experto Academico Investigador
        system_prompt = r"""Eres un INVESTIGADOR SENIOR y EXPERTO ACADEMICO en pertinencia educativa con las siguientes credenciales:

PERFIL ACADEMICO:
- Doctor en Politicas Educativas con enfasis en educacion superior latinoamericana
- 25 anos de experiencia en diseno curricular basado en competencias
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
=========================================
CADA VEZ que menciones un dato numerico o estadistico, DEBES incluir la fuente entre parentesis.

FORMATO DE CITACION: (FUENTE - Periodo)

EJEMPLOS CORRECTOS:
- "La matricula alcanzo 15,234 estudiantes (SNIES - MEN 2024)"
- "Se registraron 1,250 vacantes (APE - MinTrabajo 2024)"
- "El salario promedio es $3,200,000 COP (GEIH - DANE 2023-2024)"
- "Existen 45 programas activos (SNIES - MEN 2024)"
- "La tasa de crecimiento fue 5.2% (Calculo Sistema sobre SNIES 2014-2024)"
- "Se identificaron 12 competencias clave (CUOC - MinTrabajo/DANE 2024)"
- "Hay 890 certificados ETDH emitidos (SIET - MEN 2023)"
- "La desercion promedio es 45% (ES Desercion - MEN Colombia)"
- "Puntaje SABER 11 promedio: 265/500 (ICFES - MEN Colombia)"
- "Tasa de transito inmediato: 32% (ES TTI - MEN Colombia)"

CATÁLOGO DE FUENTES OFICIALES:
| Tipo de Dato                | Fuente a Citar                          |
|-----------------------------|-----------------------------------------|
| Programas, IES, Matricula   | SNIES - MEN 2024                        |
| Graduados                   | SNIES Graduados - MEN 2014-2024         |
| Tendencia historica         | SNIES Matriculados - MEN 2014-2024      |
| HHI (concentracion)         | Calculo Sistema sobre SNIES 2024        |
| CAGR (crecimiento)          | Calculo Sistema sobre SNIES 2014-2024   |
| Educacion ETDH              | SIET - MEN 2023                         |
| Vacantes laborales          | APE - MinTrabajo 2024                   |
| Competencias/Conocimientos  | CUOC - MinTrabajo/DANE 2024             |
| Destrezas                   | CUOC - MinTrabajo/DANE 2024             |
| Salarios                    | GEIH - DANE 2023-2024                   |
| Perfiles ocupacionales      | CUOC Perfiles - MinTrabajo 2025         |
| Desercion academica         | ES Desercion - MEN Colombia             |
| Pruebas SABER 11/PRO        | ICFES - MEN Colombia                    |
| Transito inmediato (TTI)    | ES TTI - MEN Colombia                   |
| Cobertura bruta (TCB)       | ES TCB - MEN Colombia                   |
| Score Sistema               | Sistema de análisis para estudio de contexto 2024 |

NUNCA escribas datos sin fuente. Si no tienes la fuente exacta, usa tu conocimiento y cita como: (Estimacion basada en literatura academica)
=========================================

FORMATO DEL INFORME - ESTILO PAPER ACADEMICO CON LaTeX:
========================================================
Genera un informe con formato de PAPER ACADEMICO profesional.
NO uses emojis. Usa notacion LaTeX para formulas, metricas y expresiones matematicas.

REGLAS CRITICAS DE LaTeX (MUY IMPORTANTE):
==========================================
- USA siempre la barra invertida completa en comandos: \frac, \sum, \left, \right, \bar, \text
- NUNCA escribas "frac" sin la barra: SIEMPRE escribe \frac{a}{b}
- NUNCA escribas "left" o "right" sin barra: SIEMPRE \left( y \right)
- Para porcentajes usa: 47.43\% (con barra antes del %)
- Para subindices: x_{sub} (con llaves)
- Para fracciones: \frac{numerador}{denominador}

EJEMPLOS CORRECTOS DE LaTeX:
- Correcto: $HHI = 3125$ 
- Correcto: $CAGR = 47.43\%$
- Correcto: $\frac{9}{776} = 1.16\%$
- Correcto: $$HHI = \sum_{i=1}^{n} s_i^2$$
- Correcto: $$CAGR = \left(\frac{V_f}{V_i}\right)^{1/n} - 1$$

EJEMPLOS INCORRECTOS (NUNCA hagas esto):
- Incorrecto: frac{a}{b} (falta la barra \)
- Incorrecto: left( y right) (falta la barra \)
- Incorrecto: 47.43% (falta la barra antes de %)

REGLAS DE FORMATO:

1. ENCABEZADO INSTITUCIONAL (usa este formato exacto):
---
# INFORME DE PERTINENCIA EDUCATIVA

Sistema de análisis para estudio de contexto

| Campo | Valor |
|:------|:------|
| NBC Analizado | [nombre completo del NBC] |
| Cobertura Geografica | [departamento/region] |
| Fecha de Generacion | [fecha actual] |
| Version | 1.0 |

---

2. METRICAS CON LaTeX (usa este formato para indicadores):
   - Indices: $HHI = 3125$ (mercado concentrado)
   - Tasas: $CAGR = 47.43\%$ (crecimiento fuerte)
   - Scores: $S = 90.7/100$
   - Ratios: $r = \frac{9}{776} = 1.16\%$
   - Promedios: $\bar{x} = 4128150$ COP/mes

3. FORMULAS (usa formato simple y verifica las barras invertidas):
   $$HHI = \sum_{i=1}^{n} s_i^2$$
   
   $$CAGR = \left(\frac{V_f}{V_i}\right)^{1/n} - 1$$

4. TABLAS PROFESIONALES (sin emojis, alineacion correcta):
   | Indicador | Valor | Interpretacion |
   |:----------|------:|:---------------|
   | Score Pertinencia | 90.7 | Excelente oportunidad |
   | Indice HHI | 3125 | Mercado concentrado |
   | Tasa CAGR | 47.43% | Crecimiento sostenido |

5. DESTACADOS CON FORMATO ACADEMICO (no callouts con emojis):
   
   > **Hallazgo Principal:** El mercado presenta alta concentracion con 
   > oportunidades significativas de diferenciacion en modalidad virtual.

   **Nota metodologica:** Los calculos de HHI siguen la metodologia del 
   Departamento de Justicia de EE.UU. para analisis de concentracion.

ESTRUCTURA DEL INFORME (7 secciones obligatorias):

## 1. Resumen Ejecutivo

Parrafo de sintesis con los hallazgos principales. Incluye tabla de metricas clave:

| Indicador | Valor | Clasificacion |
|:----------|------:|:--------------|
| Score de Pertinencia | $S = XX/100$ | [clasificacion] |
| Demanda Laboral | $n = X,XXX$ vacantes | [interpretacion] |
| Concentracion | $HHI = X,XXX$ | [tipo mercado] |
| Crecimiento | $CAGR = X.X\%$ | [tendencia] |

**Veredicto:** OFERTAR / NO OFERTAR / OFERTAR CON CONDICIONES

---

## 2. Analisis del Mercado Educativo

### 2.1 Estructura de Mercado
Analiza la concentracion usando el indice Herfindahl-Hirschman:
$$HHI = \sum_{i=1}^{n} s_i^2$$

Donde $s_i$ representa la participacion de mercado de la institucion $i$.

Interpretacion:
- HHI menor a 1500: Mercado competitivo
- HHI entre 1500 y 2500: Moderadamente concentrado  
- HHI mayor a 2500: Altamente concentrado

### 2.2 Dinamica de Crecimiento
Presenta la tasa de crecimiento anual compuesta:
$$CAGR = \left(\frac{V_f}{V_i}\right)^{1/n} - 1$$

### 2.3 Evolucion Historica
Tabla con serie temporal de matricula y graduados.

### 2.4 Indicadores de Calidad y Retencion
Si hay datos de desercion y SABER, integralos aqui.

---

## 3. Pertinencia Laboral y Ocupacional

### 3.1 Demanda del Mercado Laboral
Vacantes registradas en el Servicio Publico de Empleo (APE).

### 3.2 Ocupaciones Relacionadas (CUOC)
Tabla con codigos CUOC y numero de vacantes.

### 3.3 Competencias Requeridas
Conocimientos y destrezas demandados por el mercado.

### 3.4 Indicadores Salariales
Salario promedio en COP/mes (fuente GEIH-DANE).

---

## 4. Diseno Curricular Recomendado

### 4.1 Nivel de Formacion
Justificacion del nivel recomendado (Tecnico/Tecnologo/Profesional/Posgrado).

### 4.2 Modalidad
Analisis de modalidades (Presencial/Virtual/Hibrido) con justificacion.

### 4.3 Competencias del Marco Nacional de Cualificaciones
Alineacion con niveles MNC.

### 4.4 Estrategias de Retencion
Basadas en datos de desercion del campo.

---

## 5. Ecosistema de Microcredenciales

### 5.1 Microcredenciales de Entrada (40-80 horas)
Propuesta de cursos cortos introductorios.

### 5.2 Microcredenciales de Profundizacion (80-160 horas)
Cursos de especializacion tematica.

### 5.3 Modelo de Apilamiento (Stackable Credentials)
Diagrama conceptual de progresion:

```
[Microcredencial 1] + [Microcredencial 2] + [Microcredencial 3]
                           |
                           v
                  [Certificado Tecnico]
                           |
                           v
                  [Titulo Profesional]
```

---

## 6. Analisis de Riesgos

### 6.1 Matriz de Riesgos

| Categoria | Riesgo | $P$ | $I$ | $P \times I$ | Mitigacion |
|:----------|:-------|:---:|:---:|:------------:|:-----------|
| Mercado | [descripcion] | A/M/B | A/M/B | [valor] | [estrategia] |
| Regulatorio | [descripcion] | A/M/B | A/M/B | [valor] | [estrategia] |
| Operativo | [descripcion] | A/M/B | A/M/B | [valor] | [estrategia] |
| Academico | Desercion elevada | A/M/B | A/M/B | [valor] | [estrategia] |

Donde $P$ = Probabilidad, $I$ = Impacto

### 6.2 Indicadores de Alerta Temprana
Metricas para monitoreo continuo.

---

## 7. Recomendacion Final y Hoja de Ruta

### 7.1 Veredicto

**DECISION: [OFERTAR / NO OFERTAR / OFERTAR CON CONDICIONES]**

### 7.2 Justificacion
Argumentacion basada en evidencia.

### 7.3 Factores Criticos de Exito
1. Factor 1
2. Factor 2
3. Factor 3

### 7.4 Cronograma de Implementacion (6-12 meses)

| Fase | Actividad | Plazo | Responsable |
|:-----|:----------|:------|:------------|
| I | [actividad] | Mes 1-2 | [area] |
| II | [actividad] | Mes 3-4 | [area] |
| III | [actividad] | Mes 5-6 | [area] |

---

**Referencias de Datos**
- SNIES - Ministerio de Educacion Nacional, 2024
- APE - Ministerio del Trabajo, 2024  
- CUOC - MinTrabajo/DANE, 2024
- GEIH - DANE, 2023-2024
- SIET - MEN, 2023

---
*Documento generado automáticamente por el Sistema de análisis para estudio de contexto*
*Oficina de Desarrollo Institucional*

REGLAS DE REDACCION:
- Tono: Academico formal, estilo paper cientifico
- Formato: Markdown con LaTeX para formulas y metricas ($...$ y $$...$$)
- NO usar emojis bajo ninguna circunstancia
- Tablas con alineacion profesional (usar :---|---:|:---)
- Cada dato numerico DEBE tener fuente citada
- Parrafos sustantivos, no solo listas de bullets
- Usar notacion matematica donde sea apropiado"""
        
        # Construir seccion de instrucciones adicionales del usuario
        seccion_usuario = ""
        if instrucciones_adicionales and instrucciones_adicionales.strip():
            seccion_usuario = f"""

================================================================================
                    INSTRUCCIONES ADICIONALES DEL USUARIO
================================================================================
El usuario ha solicitado enfasis o ampliacion en los siguientes aspectos.
IMPORTANTE: Integra estas solicitudes de forma natural en las secciones 
correspondientes del informe, sin alterar la estructura base ni el rigor academico.

SOLICITUD DEL USUARIO:
{instrucciones_adicionales.strip()}

Asegurate de:
- Expandir el analisis en los temas solicitados
- Mantener la estructura de 7 secciones del informe
- Preservar el tono academico y riguroso
- Integrar la informacion adicional donde sea mas pertinente
================================================================================
"""
        
        # Prompt de tarea
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
        
        # Modelos a probar (nombres correctos de la API)
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
                continue  # Probar siguiente modelo
        
        return f"No se pudo conectar con ningun modelo de Gemini. Ultimo error: {ultimo_error}"
        
    except ImportError:
        return "Modulo google.generativeai no instalado. Ejecute: pip install google-generativeai"
    except Exception as e:
        return f"Error al analizar: {str(e)}"

# cargar_filtros_cascada - migrated to components/sidebar.py

# cargar_dependientes - migrated to components/sidebar.py (cascading filters)

# ==============================================================================


def main():
    # === VERIFICACIÓN DE AUTENTICACIÓN ===
    if not check_password():
        return  # No mostrar nada si no está autenticado
    
    # --- Sidebar Filters (rendered by component) ---
    filtros_seleccionados, filtros_siet_seleccionados = render_sidebar(mostrar_metodologia)

    # Extraer variables para uso local (compatibilidad con código existente)
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

    # --- Main Content ---
    st.title("Sistema de análisis para estudio de contexto")
    st.markdown("Evidencia integrada para decisiones de pertinencia y permanencia estudiantil")

    if not st.session_state.get("welcome_banner_shown", False):
        st.session_state["welcome_banner_shown"] = True
        st.toast("Bienvenido al panel de pertinencia", icon=":material/celebration:")

    if not st.session_state.get("banner_dismissed", False):
        c1, c2 = st.columns([20, 1])
        with c1:
            render_welcome_banner(
                title="Bienvenido, tu panel ya está listo",
                subtitle='"La desercion no debe leerse como un dato aislado de abandono, sino como una senal de pertinencia y sostenibilidad." — Equipo 195',
                mascot="<i class='fas fa-brain'></i>"
            )
        with c2:
            if st.button("X", key="dismiss_banner", help="Cerrar bienvenida"):
                st.session_state["banner_dismissed"] = True
                st.rerun()

    # Verificar si hay ALGÚN filtro seleccionado (no solo NBC)
    tiene_filtros_snies = (
        busqueda_programa or  # Búsqueda por nombre
        sel_nbcs or sel_campos_amplios or sel_areas or sel_deptos or 
        sel_munis or sel_modalidades or sel_sectores or 
        sel_niveles or sel_caracteres or sel_estados or
        sel_cod_snies_programas  # Programas específicos
    )
    tiene_filtros_siet = mostrar_siet or sel_areas_siet or sel_deptos_siet or sel_estados_siet or sel_modalidades_siet or busqueda_programa
    # SIET también se muestra cuando hay filtros académicos SNIES que implican áreas SIET
    tiene_filtros_academicos_snies = bool(sel_nbcs or sel_areas or sel_campos_amplios)
    if tiene_filtros_academicos_snies:
        tiene_filtros_siet = True

    if not tiene_filtros_snies and not tiene_filtros_siet:
        st.info("Seleccione al menos un **filtro** en el panel lateral para comenzar el análisis.")
        
        with st.expander("Sobre este Dashboard"):
            st.markdown("""
            Este sistema produce **estudios de contexto** que integran oferta académica, matrícula, deserción, desempeño, ocupaciones, competencias y conectividad para orientar **decisiones curriculares** que fortalezcan condiciones de permanencia estudiantil. Se organiza en 4 síntesis evaluativas:
            

            | **Académico**
            | **Laboral**
            | **Territorial**
            | **Decisión**

            
            **Filtros en Cascada:**
            - Campo Amplio CINE-F → filtra Áreas de Conocimiento → filtra NBCs
            - Departamento → filtra Municipios
            - Todos los filtros son multiselect para análisis comparativos
            
            **Puede filtrar por:** NBC, Departamento, Modalidad, Sector, Nivel o cualquier combinación.
            """)
        return

    # =====================================================================
    # SECCIÓN SIET DISYUNTIVA (Solo si no hay filtros SNIES)
    # =====================================================================
    if tiene_filtros_siet and not tiene_filtros_snies:
        st.divider()
        st.markdown('<h4 class="icon-header"><i class="fas fa-tools"></i> Análisis SIET / ETDH (Educación para el Trabajo)</h4>', unsafe_allow_html=True)
        
        render_etdh_dashboard(
            areas_desempeno=sel_areas_siet if sel_areas_siet else None,
            deptos=sel_deptos_siet if sel_deptos_siet else None,
            estados_siet=sel_estados_siet if sel_estados_siet else None,
            busqueda_nombre=busqueda_programa if busqueda_programa else None,
            modalidades_siet=sel_modalidades_siet if sel_modalidades_siet else None,
            key_prefix="etdh_standalone"
        )
        return

    # =========================================================================
    # ANÁLISIS PRINCIPAL (Con filtros SNIES)
    # =========================================================================
    
    # =========================================================================
    # RESOLUCIÓN DE NBCs: Si no hay NBC explícito pero sí Area o Campo Amplio,
    # resolver automáticamente los NBCs correspondientes vía snies_programas.
    # Relación MANY-TO-MANY: Area ←→ NBC ←→ Campo Amplio (ver RELACION.MD)
    # =========================================================================
    nbcs_explicitos = bool(sel_nbcs)  # True si el usuario seleccionó NBC directamente
    if not sel_nbcs and (sel_areas or sel_campos_amplios or busqueda_programa):
        sel_nbcs = resolver_nbcs_desde_filtros(filtros_seleccionados)
        # Actualizar filtros_seleccionados para que las queries downstream los usen
        # (NO modificar: las queries de programas/matriculados usan area/campo directamente)
        # Si hay busqueda por nombre, tambien inyectar NBCs resueltos en los filtros
        if busqueda_programa and sel_nbcs:
            filtros_seleccionados['nbcs'] = sel_nbcs
    
    sel_nbc = sel_nbcs[0] if sel_nbcs else None
    
    # Label para display: si los NBCs fueron resueltos (no explícitos), mostrar el filtro original
    if nbcs_explicitos:
        filtro_label = ', '.join(sel_nbcs[:3]) + ('...' if len(sel_nbcs) > 3 else '')
    elif sel_nbcs:  # Resueltos desde busqueda o cascada
        filtro_label = ', '.join(sel_nbcs[:3]) + ('...' if len(sel_nbcs) > 3 else '')
    elif sel_areas:
        filtro_label = ', '.join(sel_areas[:2])
    elif sel_campos_amplios:
        filtro_label = ', '.join(sel_campos_amplios[:2])
    else:
        filtro_label = 'Filtros aplicados'
    
    # Mostrar filtros activos
    filtros_activos_header = []
    if nbcs_explicitos:
        filtros_activos_header.append(f"NBC: {', '.join(sel_nbcs[:2])}")
    if sel_areas:
        filtros_activos_header.append(f"Area: {', '.join(sel_areas[:2])}")
    if sel_campos_amplios:
        filtros_activos_header.append(f"Campo: {', '.join(sel_campos_amplios[:2])}")
    if sel_deptos:
        filtros_activos_header.append(f"Depto: {', '.join(sel_deptos[:2])}")
    if sel_modalidades:
        filtros_activos_header.append(f"Modalidad: {', '.join(sel_modalidades)}")
    if sel_sectores:
        filtros_activos_header.append(f"Sector: {', '.join(sel_sectores)}")
    if sel_estados:
        filtros_activos_header.append(f"Estado: {', '.join(sel_estados)}")
    if filtros_activos_header:
        n_nbcs_resueltos = len(sel_nbcs) if not nbcs_explicitos and sel_nbcs else 0
        header_text = f"**Filtros:** {' | '.join(filtros_activos_header)}"
        if n_nbcs_resueltos > 0:
            header_text += f" *({n_nbcs_resueltos} NBCs resueltos)*"
        st.info(header_text)
    
    arg_depto = sel_deptos[0] if sel_deptos else None
    
    # Display label for multiple NBCs/deptos
    nbc_display = filtro_label
    depto_display = ', '.join(sel_deptos[:3]) + ('...' if len(sel_deptos) > 3 else '') if sel_deptos else None
    
    with loading_overlay():
        # NOTA: No pasar sel_nbc/arg_depto como escalares — filtros_seleccionados ya contiene
        # las listas completas de nbcs y deptos. Pasar escalares causa doble-filtrado
        # (= 'X' AND IN ('X','Y','Z') → solo 'X'), ignorando multiselect.
        stats = get_estadisticas_basicas(filtros=filtros_seleccionados)
        df_benchmark = get_benchmarking_data(filtros=filtros_seleccionados)
        df_market = get_market_share(filtros=filtros_seleccionados)
        df_tendencia = get_tendencia_matricula(filtros=filtros_seleccionados)
        df_graduados = get_graduados_historico(filtros=filtros_seleccionados)
        df_inscritos = get_tendencia_inscritos(filtros=filtros_seleccionados)
        df_admitidos = get_tendencia_admitidos(filtros=filtros_seleccionados)
        df_primer_curso = get_tendencia_primer_curso(filtros=filtros_seleccionados)
        # Conectividad territorial: siempre se carga (nacional o departamental)
        # Se usa en Tab 4 como fallback si Tab 3 no se ejecutó
        df_conectividad = get_conectividad_territorial(arg_depto)
        
        # ML matching SNIES ↔ ETDH (programas ETDH relacionados al NBC)
        # Si hay múltiples NBCs, combinar resultados de todos
        etdh_ml_stats = None
        skills_bridge = None
        if sel_nbcs:
            conn_etdh = get_conn()
            try:
                if len(sel_nbcs) == 1:
                    etdh_ml_stats = match_nbc_to_siet_v2(sel_nbcs[0], conn_etdh, top_k=30)
                    try:
                        skills_bridge = get_skills_bridge_analysis_v2(sel_nbcs[0], conn_etdh, depto=arg_depto)
                    except Exception as e_bridge:
                        print(f"[Bridge-v2] Error: {e_bridge}")
                else:
                        # Multi-NBC: combinar resultados
                        combined = {
                            'programas_siet_relacionados': 0,
                            'matricula_siet': 0, 'certificados_siet': 0,
                            'areas_desempeno': [], 'top_programas': [],
                            'tiene_datos': False
                        }
                        seen_progs = set()
                        for nbc_i in sel_nbcs[:5]:
                            df_i = match_nbc_to_siet_v2(nbc_i, conn_etdh, top_k=30)
                            if not df_i.empty:
                                combined['tiene_datos'] = True
                                combined['matricula_siet'] += int(df_i['matricula_2023'].sum())
                                combined['certificados_siet'] += int(df_i['certificados_2023'].sum())
                                for area in df_i['area_desempeno'].dropna().unique():
                                    if area not in combined['areas_desempeno']:
                                        combined['areas_desempeno'].append(area)
                                for _, row in df_i.iterrows():
                                    key = row['nombre_programa']
                                    if key not in seen_progs:
                                        seen_progs.add(key)
                                        combined['top_programas'].append({
                                            'nombre': key,
                                            'area': row.get('area_desempeno', ''),
                                            'score': float(row.get('score_final', 0)),
                                            'matricula': int(row.get('matricula_2023', 0)),
                                            'certificados': int(row.get('certificados_2023', 0)),
                                        })
                        combined['programas_siet_relacionados'] = len(combined['top_programas'])
                        combined['top_programas'] = sorted(
                            combined['top_programas'], key=lambda x: x['score'], reverse=True
                        )[:20]
                        if combined['tiene_datos']:
                            etdh_ml_stats = combined
                        try:
                            skills_bridge = get_skills_bridge_analysis_v2(sel_nbcs[0], conn_etdh, depto=arg_depto)
                        except Exception as e_bridge:
                            print(f"[Bridge-v2] Error multi-NBC: {e_bridge}")
            except Exception as e:
                print(f"[Bridge] Error: {e}")
            finally:
                try:
                    conn_etdh.close()
                except Exception:
                    pass
        
        # =================================================================
        # GLOBAL: Areas SIET efectivas derivadas de filtros SNIES
        # Prioridad simplificada (v2): ML > sidebar manual > None
        # =================================================================
        _ml_areas_siet = None
        if etdh_ml_stats and etdh_ml_stats.get('tiene_datos') and etdh_ml_stats.get('areas_desempeno'):
            _ml_areas_siet = etdh_ml_stats['areas_desempeno']
        
        effective_areas_siet = _ml_areas_siet if _ml_areas_siet else (sel_areas_siet if sel_areas_siet else None)
        # Propagar departamento SNIES a SIET si no hay depto SIET especifico
        effective_deptos_siet = sel_deptos_siet if sel_deptos_siet else (sel_deptos if sel_deptos else None)
        
        hhi, hhi_interp = calcular_hhi(df_market)
        cagr, cagr_interp = calcular_cagr(df_tendencia)
        
        graduados_anual = df_graduados['graduados'].iloc[-1] if not df_graduados.empty else 0
        vacantes_est = int(graduados_anual * 1.1)
        ratio_abs, ratio_interp = calcular_ratio_absorcion(graduados_anual, vacantes_est)
    
    # --- KPIs Header ---
    titulo_analisis = f"Análisis: {nbc_display}" if nbc_display else "Análisis con Filtros Seleccionados"
    st.subheader(titulo_analisis)
    
    # Mostrar filtros activos
    filtros_activos = []
    if depto_display:
        filtros_activos.append(f"{depto_display}")
    if sel_modalidades:
        filtros_activos.append(f"{', '.join(sel_modalidades)}")
    if sel_sectores:
        filtros_activos.append(f"{', '.join(sel_sectores)}")
    if sel_niveles:
        filtros_activos.append(f"{', '.join(sel_niveles)}")
    if filtros_activos:
        st.caption(f"Filtrado por: {' | '.join(filtros_activos)}")
    
    # Verificar si hay datos con los filtros aplicados
    if stats['total_programas'] == 0:
        st.warning(f"""
        **No se encontraron programas de "{nbc_display or 'los filtros seleccionados'}" con los filtros aplicados.**
        
        Esto puede significar:
        - No existe oferta de este NBC en el departamento seleccionado
        - La combinación de filtros es muy restrictiva
        
        **Sugerencia:** Pruebe relajando los filtros o seleccionando otro departamento.
        """)
        # Mostrar dónde SÍ hay oferta (usando todos los NBCs seleccionados)
        with st.expander("Ver dónde hay oferta de este NBC"):
            conn = get_conn()
            if sel_nbcs:
                nbc_cond = build_nbc_condition(sel_nbcs)
                df_oferta = conn.execute(f"""
                    SELECT 
                        "DEPARTAMENTO_OFERTA_PROGRAMA" as Departamento,
                        COUNT(*) as Programas
                    FROM snies.snies_programas 
                    WHERE {nbc_cond}
                    GROUP BY 1
                    ORDER BY 2 DESC
                """).fetchdf()
            else:
                df_oferta = pd.DataFrame()
            conn.close()
            if not df_oferta.empty:
                st.dataframe(df_oferta, hide_index=True, use_container_width=True)
            else:
                st.info("No hay programas registrados para este NBC en ningún departamento.")
        return
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Programas Activos", f"{stats['total_programas']:,}")
    k2.metric("IES Ofertantes", f"{stats['total_ies']:,}")
    k3.metric("Matrícula Promedio", f"${stats['costo_promedio']:,.0f}", help="Valor promedio de matrícula para estudiantes nuevos (SNIES)")
    k4.metric("Modalidades", f"{stats['modalidades']}")
    
    # Guardar stats originales para uso posterior
    stats_originales = stats.copy()
    
    # Crear etiqueta de contexto de filtros para mostrar en gráficos
    tiene_filtros_activos = sel_deptos or sel_modalidades or sel_sectores or sel_niveles or sel_estados or busqueda_programa or sel_cod_snies_programas
    if tiene_filtros_activos:
        partes_contexto = []
        if sel_deptos:
            partes_contexto.append("/".join(d[:8] for d in sel_deptos[:2]))
        if sel_modalidades:
            partes_contexto.append("/".join(m[:4] for m in sel_modalidades[:2]))
        if sel_sectores:
            partes_contexto.append("/".join(s[:4] for s in sel_sectores[:2]))
        if sel_niveles:
            partes_contexto.append("/".join(n[:4] for n in sel_niveles[:2]))
        if sel_estados:
            partes_contexto.append("/".join(e[:6] for e in sel_estados[:2]))
        if busqueda_programa:
            partes_contexto.append(f"Búsq: {busqueda_programa[:15]}")
        if sel_cod_snies_programas:
            partes_contexto.append(f"CódSNIES: {len(sel_cod_snies_programas)}")
        contexto_filtros = " | ".join(partes_contexto)
        label_ambito = f"Filtrado: {contexto_filtros}"
    else:
        label_ambito = "Análisis Nacional"

    # --- Safe defaults para variables compartidas entre tabs ---
    df_vacantes = pd.DataFrame()
    df_conocimientos = pd.DataFrame()
    df_destrezas = pd.DataFrame()
    df_actividades = pd.DataFrame()
    stats_originales = {}
    datos_salarios = {"tiene_datos": False}
    skills_bridge = None

    # --- TABS DE 4 SÍNTESIS EVALUATIVAS ---
    tab_acad, tab_lab, tab_terr, tab_decision = st.tabs([
        ":material/school: Síntesis Académica",
        ":material/work: Síntesis Laboral", 
        ":material/map: Síntesis Territorial", 
        ":material/balance: Decisión Final"
    ])

    # =========================================================================
    # TAB 1: SÍNTESIS ACADÉMICA
    # =========================================================================
    with tab_acad:
        section_header("01", "Pertinencia Academica", "La oferta actual responde a las necesidades de la poblacion o genera condiciones de riesgo para la permanencia?")
        
        # Obtener desglose académico completo (con filtros — sin escalares para respetar multiselect)
        desglose = get_desglose_academico(filtros=filtros_seleccionados)
        
        col_hhi, col_cagr = st.columns(2)
        
        with col_hhi:
            st.markdown("#### Concentracion de Mercado (HHI)")
            st.caption("Distribucion de matricula entre las IES. Concentracion alta = pocos dominan, baja diferenciacion y riesgo de saturacion. Concentracion baja = mercado abierto con oportunidades de insercion sostenible.")
            fig_hhi = crear_gauge_hhi(hhi)
            st.plotly_chart(fig_hhi, use_container_width=True)
            # Exportar datos de market share si disponibles
            if not df_market.empty:
                descargar_datos_grafico(df_market, "market_share_instituciones", "Descargar market share")
            st.caption(get_citacion("snies_matriculados"))
            st.info(hhi_interp)
            
            if not df_market.empty:
                st.markdown("**Top 5 Instituciones:**")
                st.dataframe(
                    df_market.head(5)[['institucion', 'matriculados', 'share']].rename(
                        columns={'institucion': 'Institución', 'matriculados': 'Matrículas', 'share': 'Cuota %'}
                    ),
                    hide_index=True,
                    use_container_width=True
                )
                
                # Botón para ver detalle de programas
                with st.expander("Ver Detalle Completo de Programas", icon=":material/list_alt:"):
                    df_detalle = get_programas_detalle(filtros=filtros_seleccionados)
                    if not df_detalle.empty:
                        st.markdown(f"**{len(df_detalle)} programas encontrados** para *{filtro_label}*")
                        st.dataframe(
                            df_detalle,
                            hide_index=True,
                            use_container_width=True,
                            height=450,
                            column_config={
                                "Institucion": st.column_config.TextColumn("Institución", width="large"),
                                "Programa": st.column_config.TextColumn("Programa", width="large"),
                                "Nivel": st.column_config.TextColumn("Nivel", width="small"),
                                "Modalidad": st.column_config.TextColumn("Modalidad", width="small"),
                                "Sector": st.column_config.TextColumn("Sector", width="small"),
                                "Caracter": st.column_config.TextColumn("Carácter", width="medium"),
                                "Depto": st.column_config.TextColumn("Departamento", width="medium"),
                                "Municipio": st.column_config.TextColumn("Municipio", width="medium"),
                                "Estado": st.column_config.TextColumn("Estado", width="small"),
                                "Creditos": st.column_config.NumberColumn("Créditos", width="small")
                            }
                        )
                        # Botón de descarga XLSX
                        import io
                        buffer = io.BytesIO()
                        df_detalle.to_excel(buffer, index=False, engine='openpyxl')
                        buffer.seek(0)
                        file_suffix = sel_nbc.replace(' ', '_') if sel_nbc else "filtros_aplicados"
                        st.download_button(
                            label="Descargar Excel",
                            data=buffer,
                            file_name=f"programas_{file_suffix}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            icon=":material/download:"
                        )
                    else:
                        st.warning("No se encontraron programas con los filtros aplicados")
        
        with col_cagr:
            st.markdown("#### Tasa de Crecimiento (CAGR)")
            st.caption("Tendencia anual de matricula. Un campo en crecimiento sugiere demanda sostenida y menor riesgo de abandono por perdida de valor del programa.")
            st.metric("CAGR Matricula", f"{cagr}%", help="Compound Annual Growth Rate - Tasa de crecimiento anual compuesto de matriculados")
            st.info(cagr_interp)
            st.caption(get_citacion("snies_matriculados"))
        
        # CAGR: solo mostrar el valor calculado
        cagr_num = float(str(cagr).replace('%','').replace('+',''))
        cagr_str = f"{cagr_num:+.1f}%"
        etiqueta_cagr = "Crecimiento" if cagr_num >= 5 else "Estable" if cagr_num >= 0 else "Declive"
        
        # Saber PRO: calidad academica via matching semantico
        try:
            from data.queries import get_saber_pro_stats
            saber_stats = get_saber_pro_stats(filtros=filtros_seleccionados)
            if saber_stats.get('n_evaluados', 0) > 0:
                st.markdown("---")
                st.markdown("### Calidad Academica (Saber PRO)")
                st.caption(f"Resultados de las pruebas Saber PRO de egresados en programas relacionados. Periodo: {saber_stats.get('periodo', '2020-2022')} | {saber_stats['n_evaluados']:,} evaluados.")
                
                puntaje = saber_stats['puntaje_promedio']
                nacional = saber_stats.get('nacional_promedio', 150)
                
                col_gauge, col_dist = st.columns([1, 2])
                with col_gauge:
                    st.plotly_chart(crear_gauge_saber(puntaje or 0, nacional), use_container_width=True)
                    diff = (puntaje or 0) - (nacional or 0)
                    if diff > 0:
                        st.success(f"**{diff:+.0f} pts** sobre promedio nacional ({nacional:.0f})")
                    elif diff < 0:
                        st.warning(f"**{diff:+.0f} pts** bajo promedio nacional ({nacional:.0f})")
                    else:
                        st.info(f"Igual al promedio nacional ({nacional:.0f})")
                
                with col_dist:
                    st.plotly_chart(crear_distribucion_saber(
                        saber_stats.get('puntaje_min', 0),
                        saber_stats.get('q1', 0),
                        saber_stats.get('mediana', 0),
                        saber_stats.get('q3', 0),
                        saber_stats.get('puntaje_max', 0)
                    ), use_container_width=True)
                    st.caption("Distribucion de puntajes: Min, Cuartiles y Maximo")
                
                st.caption(f"Fuente: ICFES — Saber PRO | Periodo: {saber_stats.get('periodo', '2020-2022')} | Promedio nacional: **{nacional:.0f}/300** | Matching semantico con MiniLM")
        except Exception:
            pass
        
        # =====================================================================
        # NUEVA SECCIÓN: EVOLUCIÓN ESTUDIANTIL (Inscritos, Admitidos, Primer Curso, Graduados)
        # =====================================================================
        st.markdown("---")
        st.markdown("### Evolucion del Ciclo Estudiantil")
        st.caption("Seguimiento del flujo estudiantil: inscritos, admitidos, primer curso y graduados. Identificar donde se concentran las perdidas permite anticipar riesgos de desercion y disenar estrategias de retencion por etapa.")
        st.caption(f"Tendencia historica | {label_ambito}")
        
        col_insc, col_admi = st.columns(2)
        
        with col_insc:
            st.markdown("#### Inscritos")
            if not df_inscritos.empty:
                fig_insc = px.line(
                    df_inscritos, x='anio', y='inscritos',
                    title=f"Histórico de Inscritos (2019-2024)",
                    markers=True, color_discrete_sequence=['#9b1b30']
                )
                st.plotly_chart(fig_insc, use_container_width=True)
                descargar_datos_grafico(df_inscritos, "historico_inscritos", "Descargar datos")
                st.caption(get_citacion("snies_inscritos"))
            else:
                st.warning("Sin datos de inscritos")
        
        with col_admi:
            st.markdown("#### Admitidos")
            if not df_admitidos.empty:
                fig_admi = px.line(
                    df_admitidos, x='anio', y='admitidos',
                    title=f"Histórico de Admitidos (2019-2024)",
                    markers=True, color_discrete_sequence=['#6B9080']
                )
                st.plotly_chart(fig_admi, use_container_width=True)
                descargar_datos_grafico(df_admitidos, "historico_admitidos", "Descargar datos")
                st.caption(get_citacion("snies_admitidos"))
            else:
                st.warning("Sin datos de admitidos")
        
        col_primer, col_matr = st.columns(2)
        
        with col_primer:
            st.markdown("#### Matriculados Primer Curso")
            if not df_primer_curso.empty:
                fig_primer = px.line(
                    df_primer_curso, x='anio', y='primer_curso',
                    title=f"Histórico Primer Curso (2019-2024)",
                    markers=True, color_discrete_sequence=['#cc8800']
                )
                st.plotly_chart(fig_primer, use_container_width=True)
                descargar_datos_grafico(df_primer_curso, "historico_primer_curso", "Descargar datos")
                st.caption(get_citacion("snies_matriculados_primer_curso"))
            else:
                st.warning("Sin datos de primer curso")
        
        with col_matr:
            st.markdown("#### Matriculados Total")
            if not df_tendencia.empty:
                fig_matr = px.line(
                    df_tendencia, x='anio', y='matriculados',
                    title=f"Histórico de Matriculados (2019-2024)",
                    markers=True, color_discrete_sequence=['#a0522d']
                )
                st.plotly_chart(fig_matr, use_container_width=True)
                descargar_datos_grafico(df_tendencia, "historico_matriculados", "Descargar datos")
                st.caption(get_citacion("snies_matriculados"))
            else:
                st.warning("Sin datos de matriculados")
        
        col_grad_solo, _ = st.columns(2)
        
        with col_grad_solo:
            st.markdown("#### Graduados")
            if not df_graduados.empty:
                fig_grad = px.line(
                    df_graduados, x='anio', y='graduados',
                    title=f"Histórico de Graduados (2019-2024)",
                    markers=True, color_discrete_sequence=['#a0522d']
                )
                st.plotly_chart(fig_grad, use_container_width=True)
                descargar_datos_grafico(df_graduados, "historico_graduados", "Descargar datos")
                st.caption(get_citacion("snies_graduados"))
            else:
                st.warning("Sin datos de graduados")
        
        # Gráfico combinado de embudo/conversión
        with st.expander("Ver Gráfico Combinado de Evolución Estudiantil", expanded=False):
            # Crear DataFrame combinado para gráfico
            datos_combinados = []
            if not df_inscritos.empty:
                for _, row in df_inscritos.iterrows():
                    datos_combinados.append({'Año': row['anio'], 'Etapa': 'Inscritos', 'Cantidad': row['inscritos']})
            if not df_admitidos.empty:
                for _, row in df_admitidos.iterrows():
                    datos_combinados.append({'Año': row['anio'], 'Etapa': 'Admitidos', 'Cantidad': row['admitidos']})
            if not df_primer_curso.empty:
                for _, row in df_primer_curso.iterrows():
                    datos_combinados.append({'Año': row['anio'], 'Etapa': 'Primer Curso', 'Cantidad': row['primer_curso']})
            if not df_tendencia.empty:
                for _, row in df_tendencia.iterrows():
                    datos_combinados.append({'Año': row['anio'], 'Etapa': 'Matriculados', 'Cantidad': row['matriculados']})
            if not df_graduados.empty:
                for _, row in df_graduados.iterrows():
                    datos_combinados.append({'Año': row['anio'], 'Etapa': 'Graduados', 'Cantidad': row['graduados']})
            
            if datos_combinados:
                df_comb = pd.DataFrame(datos_combinados)
                fig_comb = px.line(
                    df_comb, x='Año', y='Cantidad', color='Etapa',
                    title=f"Evolución Completa del Ciclo Estudiantil | {label_ambito}",
                    markers=True,
                    color_discrete_map={
                        'Inscritos': '#9B1B30',
                        'Admitidos': '#6B9080',
                        'Primer Curso': '#D97706',
                        'Matriculados': '#52423C',
                        'Graduados': '#C7A951'
                    }
                )
                fig_comb.update_layout(
                    height=420,
                    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                    margin=dict(t=60),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_comb, use_container_width=True)
                descargar_datos_grafico(df_comb, "evolucion_estudiantil_combinado", "Descargar datos")
                st.caption("Fuente: SNIES - MEN Colombia")
        
        # =====================================================================
        # NUEVA SECCIÓN: DESGLOSE ACADÉMICO CON GRÁFICOS DE TORTA Y BARRAS
        # =====================================================================
        st.markdown("---")
        st.markdown("### Desglose de la Oferta Academica")
        st.caption("Como se distribuyen los programas segun modalidad, nivel, duracion, creditos y otros atributos academicos.")
        st.caption(f"Analisis detallado | {label_ambito}")
        
        # Fila 1: Modalidad y Sector (Tortas)
        col_mod, col_sec = st.columns([3, 2])
        
        with col_mod:
            st.markdown("#### Por Modalidad")
            df_mod = desglose.get('modalidad', pd.DataFrame())
            if not df_mod.empty:
                fig_mod = px.pie(
                    df_mod, 
                    values='cantidad', 
                    names='categoria',
                    title="Distribución por Modalidad",
                    color_discrete_sequence=TEMPLATE_COLORS,
                    hole=0.4
                )
                fig_mod.update_traces(textposition='inside', textinfo='percent+label')
                fig_mod.update_layout( showlegend=True)
                st.plotly_chart(fig_mod, use_container_width=True)
                descargar_datos_grafico(df_mod, "desglose_modalidad", "Descargar datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.warning("Sin datos de modalidad")
        
        with col_sec:
            st.markdown("#### Interpretación")
            presencial_pct = "mayoritariamente presencial" if not df_mod.empty and df_mod[df_mod['categoria'].str.upper().str.contains('PRESENCIAL',na=False)].empty else ""
            st.markdown(f"""<div style="font-size:0.85rem;color:#52423C;line-height:1.6;
                padding:0.6rem 0;">
                <p style="margin-bottom:0.5rem;">La modalidad <strong>dominante</strong> revela el formato preferido 
                por los estudiantes en este NBC. Una alta concentración en una sola modalidad sugiere 
                que el mercado ya está definido.</p>
                <p style="margin-bottom:0.5rem;">Si la modalidad virtual tiene baja participación pero el 
                departamento objetivo tiene buena conectividad, existe una <strong>oportunidad de diferenciación</strong>.</p>
                <p>Combine este dato con el análisis territorial para decidir entre oferta presencial, virtual o híbrida.</p>
            </div>""", unsafe_allow_html=True)
        
        with col_sec:
            st.markdown("#### Por Sector")
            df_sec = desglose.get('sector', pd.DataFrame())
            if not df_sec.empty:
                fig_sec = px.pie(
                    df_sec, 
                    values='cantidad', 
                    names='categoria',
                    title="Distribución Oficial vs Privado",
                    color_discrete_map={'Oficial': '#9b1b30', 'Privada': '#a0522d'},
                    hole=0.4
                )
                fig_sec.update_traces(textposition='inside', textinfo='percent+label')
                fig_sec.update_layout( showlegend=True)
                st.plotly_chart(fig_sec, use_container_width=True)
                descargar_datos_grafico(df_sec, "desglose_sector", "Descargar datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.warning("Sin datos de sector")
        
        # Fila 2: Nivel de Formación y Carácter Académico (Barras)
        col_niv, col_car = st.columns(2)
        
        with col_niv:
            st.markdown("#### Por Nivel de Formación")
            df_niv = desglose.get('nivel_formacion', pd.DataFrame())
            if not df_niv.empty:
                fig_niv = px.bar(
                    df_niv.head(8),
                    x='cantidad',
                    y='categoria',
                    orientation='h',
                    title="Programas por Nivel de Formación",
                    color='cantidad',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                )
                fig_niv.update_layout(
                    height=320, 
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_niv, use_container_width=True)
                descargar_datos_grafico(df_niv, "desglose_nivel_formacion", "Descargar datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.warning("Sin datos de nivel de formación")
        
        with col_car:
            st.markdown("#### Por Carácter Académico IES")
            df_car = desglose.get('caracter_academico', pd.DataFrame())
            if not df_car.empty:
                fig_car = px.bar(
                    df_car,
                    x='cantidad',
                    y='categoria',
                    orientation='h',
                    title="Tipo de Institución",
                    color='cantidad',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                )
                fig_car.update_layout(
                    height=320, 
                    yaxis={'categoryorder': 'total ascending'},
                    showlegend=False,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_car, use_container_width=True)
                descargar_datos_grafico(df_car, "desglose_caracter_academico", "Descargar datos")
                st.caption(get_citacion("snies_instituciones"))
            else:
                st.warning("Sin datos de carácter académico")
        
        # Fila 3: Créditos y Duración (Barras)
        col_cred, col_dur = st.columns(2)
        
        with col_cred:
            st.markdown("#### Distribución de Créditos")
            df_cred = desglose.get('creditos', pd.DataFrame())
            if not df_cred.empty:
                fig_cred = px.bar(
                    df_cred,
                    x='categoria',
                    y='cantidad',
                    title="Programas por Rango de Créditos",
                    color='cantidad',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                )
                fig_cred.update_layout(
                    height=300,
                    xaxis_title="Rango de Créditos",
                    yaxis_title="N° Programas",
                    showlegend=False,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_cred, use_container_width=True)
                descargar_datos_grafico(df_cred, "desglose_creditos", "Descargar datos")
                st.caption(get_citacion("snies_programas"))
                
                # Métricas de créditos
                stats = desglose.get('estadisticas', {})
                if stats:
                    st.metric("Créditos Promedio", f"{stats.get('creditos_promedio', 0):.0f}")
            else:
                st.warning("Sin datos de créditos")
        
        with col_dur:
            st.markdown("#### Distribución de Duración")
            df_dur = desglose.get('duracion', pd.DataFrame())
            if not df_dur.empty:
                fig_dur = px.bar(
                    df_dur,
                    x='categoria',
                    y='cantidad',
                    title="Programas por Duración",
                    color='cantidad',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                )
                fig_dur.update_layout(
                    height=300,
                    xaxis_title="Duración (semestres)",
                    yaxis_title="N° Programas",
                    showlegend=False,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_dur, use_container_width=True)
                descargar_datos_grafico(df_dur, "desglose_duracion", "Descargar datos")
                st.caption(get_citacion("snies_programas"))
                
                # Métricas de duración
                stats = desglose.get('estadisticas', {})
                if stats:
                    st.metric("Duración Promedio", f"{stats.get('duracion_promedio', 0):.1f} semestres")
            else:
                st.warning("Sin datos de duración")
        
        # Fila 4: Periodicidad, Estado y Ciclos Propedéuticos (Tortas pequeñas)
        col_per, col_est, col_cic = st.columns(3)
        
        with col_per:
            st.markdown("#### Periodicidad")
            df_per = desglose.get('periodicidad', pd.DataFrame())
            if not df_per.empty:
                fig_per = px.pie(
                    df_per.head(5), 
                    values='cantidad', 
                    names='categoria',
                    hole=0.5,
                    color_discrete_sequence=TEMPLATE_COLORS
                )
                fig_per.update_traces(textposition='inside', textinfo='percent')
                fig_per.update_layout( showlegend=True, legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_per, use_container_width=True)
                descargar_datos_grafico(df_per, "desglose_periodicidad", "Datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.info("Sin datos")
        
        with col_est:
            st.markdown("#### Estado Programa")
            df_est = desglose.get('estado', pd.DataFrame())
            if not df_est.empty:
                fig_est = px.pie(
                    df_est, 
                    values='cantidad', 
                    names='categoria',
                    hole=0.5,
                    color_discrete_map={'Activo': '#6B9080', 'Inactivo': '#a0522d'}
                )
                fig_est.update_traces(textposition='inside', textinfo='percent')
                fig_est.update_layout( showlegend=True, legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_est, use_container_width=True)
                descargar_datos_grafico(df_est, "desglose_estado", "Datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.info("Sin datos")
        
        with col_cic:
            st.markdown("#### Ciclos Propedéuticos")
            df_cic = desglose.get('ciclos_propedeuticos', pd.DataFrame())
            if not df_cic.empty:
                fig_cic = px.pie(
                    df_cic, 
                    values='cantidad', 
                    names='categoria',
                    hole=0.5,
                    color_discrete_sequence=['#9b1b30', '#A09088', '#E5DDD6']
                )
                fig_cic.update_traces(textposition='inside', textinfo='percent')
                fig_cic.update_layout( showlegend=True, legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig_cic, use_container_width=True)
                descargar_datos_grafico(df_cic, "desglose_ciclos_propedeuticos", "Datos")
                st.caption(get_citacion("snies_programas"))
            else:
                st.info("Sin datos")
        
        # Fila 5: Distribución Geográfica (Barra horizontal - Top Departamentos)
        st.markdown("---")
        st.markdown("#### Distribución Geográfica del NBC (Nacional)")
        df_deptos = desglose.get('departamentos', pd.DataFrame())
        if not df_deptos.empty:
            fig_geo = px.bar(
                df_deptos,
                x='cantidad',
                y='categoria',
                orientation='h',
                title=f"Top 10 Departamentos con programas de {filtro_label}",
                color='cantidad',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_geo.update_layout(
                height=400,
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title="N° de Programas",
                yaxis_title="Departamento",
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_geo, use_container_width=True)
            descargar_datos_grafico(df_deptos, "desglose_departamentos", "Descargar datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.warning("Sin datos de distribución geográfica")
        
        # Fila 6: Resumen de estadísticas clave
        st.markdown("---")
        st.markdown("#### Resumen Estadístico del NBC")
        stats = desglose.get('estadisticas', {})
        if stats:
            stat1, stat2, stat3, stat4 = st.columns(4)
            stat1.metric("Matrícula Promedio", f"${stats.get('costo_promedio', 0):,.0f}", help="Valor promedio matrícula estudiantes nuevos")
            stat2.metric("Matrícula Mínima", f"${stats.get('costo_min', 0):,.0f}")
            stat3.metric("Matrícula Máxima", f"${stats.get('costo_max', 0):,.0f}")
            stat4.metric("Vigencia Promedio", f"{stats.get('vigencia_promedio', 0):.1f} años")
        
        # Benchmarking original
        st.markdown("---")
        st.markdown("#### Benchmarking: Matrícula vs Duración")
        if not df_benchmark.empty:
            fig_scatter = px.scatter(
                df_benchmark,
                x='duracion',
                y='costo',
                color='acreditada',
                hover_data=['institucion', 'programa'],
                title="Posicionamiento de Programas (Duración vs Valor Matrícula)",
                labels={'duracion': 'Duración (semestres)', 'costo': 'Valor Matrícula ($)', 'acreditada': 'Acreditada'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            descargar_datos_grafico(df_benchmark, "benchmarking_matricula_duracion", "Descargar datos")
            st.caption(get_citacion("snies_programas"))
            st.caption("**Interpretación:** Buscar cuadrantes con baja densidad = oportunidad de diferenciación")
        else:
            st.warning("No hay datos suficientes para el benchmarking")

        # =====================================================================
        # EXPLORADOR INTERACTIVO DE DATOS (Tipo PowerBI Drill-Down)
        # =====================================================================
        st.markdown("---")
        st.markdown("### :material/query_stats: Explorador Interactivo de Datos")
        st.caption("Construye tu propio grafico seleccionando metricas, dimensiones y tipo de visualizacion. "
                   "Agrega mas dimensiones para hacer **drill-down** (desagregar por escalones).")
        
        # Configuracion del explorador
        col_exp_config1, col_exp_config2 = st.columns(2)
        
        with col_exp_config1:
            exp_metrica = st.selectbox(
                ":material/analytics: Metrica a analizar",
                options=['Matriculados', 'Graduados', 'Inscritos', 'Admitidos', 'Primer Curso'],
                index=0,
                help="Variable numerica que se sumara/agregara",
                key="exp_metrica"
            )
            
            dimensiones_disponibles = [
                'Ano', 'Semestre', 'Sexo', 'Nivel Academico', 'Nivel Formacion',
                'Metodologia', 'Area Conocimiento', 'NBC', 'Sector IES',
                'Caracter IES', 'Departamento', 'Municipio', 'Institucion',
                'IES Acreditada', 'Programa Acreditado'
            ]
            
            exp_dimensiones = st.multiselect(
                ":material/layers: Dimensiones (orden = jerarquia drill-down)",
                options=dimensiones_disponibles,
                default=['Ano'],
                help="Selecciona en orden: la primera es el eje principal, cada dimension adicional agrega un nivel de desagregacion",
                key="exp_dimensiones"
            )
        
        with col_exp_config2:
            tipos_grafico_disponibles = ['Barras Agrupadas', 'Linea Temporal', 'Barras Apiladas',
                                         'Sunburst (Drill-Down)', 'Treemap (Mapa de arbol)',
                                         'Tabla Pivot', 'Heatmap']
            
            # Sugerir tipo segun dimensiones
            default_tipo = 0
            if exp_dimensiones:
                if 'Ano' in exp_dimensiones and len(exp_dimensiones) <= 2:
                    default_tipo = 1  # Linea temporal
                elif len(exp_dimensiones) >= 3:
                    default_tipo = 3  # Sunburst
                elif len(exp_dimensiones) == 2:
                    default_tipo = 0  # Barras agrupadas
            
            exp_tipo_grafico = st.selectbox(
                ":material/bar_chart: Tipo de grafico",
                options=tipos_grafico_disponibles,
                index=default_tipo,
                help="Sunburst y Treemap son ideales para drill-down con 3+ dimensiones",
                key="exp_tipo_grafico"
            )
            
            exp_anio_rango = st.slider(
                ":material/date_range: Rango de anos",
                min_value=2010, max_value=2025,
                value=(2018, 2024),
                key="exp_anio_rango"
            )
            
            exp_top_n = st.slider(
                ":material/filter_list: Top N resultados",
                min_value=5, max_value=100, value=20,
                help="Limitar a los N valores mas grandes (evita graficos saturados)",
                key="exp_top_n"
            )
        
        # Ejecutar consulta y generar grafico
        if exp_dimensiones:
            with loading_overlay("Consultando datos..."):
                df_exp = get_datos_explorador_interactivo(
                    metrica=exp_metrica,
                    dimensiones=exp_dimensiones,
                    anio_inicio=exp_anio_rango[0],
                    anio_fin=exp_anio_rango[1],
                    filtros_base=filtros_seleccionados
                )
            
            if not df_exp.empty:
                # Informacion del resultado
                total_valor = df_exp['valor'].sum()
                st.info(f"**{len(df_exp):,} combinaciones** | Total {exp_metrica}: **{total_valor:,.0f}** | "
                        f"Periodo: {exp_anio_rango[0]}-{exp_anio_rango[1]}")
                
                # Limitar a top N por valor
                dim1 = exp_dimensiones[0]
                dim2 = exp_dimensiones[1] if len(exp_dimensiones) >= 2 else None
                dim3 = exp_dimensiones[2] if len(exp_dimensiones) >= 3 else None
                
                es_temporal = exp_tipo_grafico == 'Linea Temporal'
                
                if es_temporal and dim1 == 'Ano':
                    # Linea temporal: ordenar cronologicamente, pero limitar a top-N grupos por valor total
                    df_exp_sorted = df_exp.sort_values('valor', ascending=False)
                    if dim2:
                        group_totals = df_exp.groupby(dim2)['valor'].sum().nlargest(exp_top_n).index
                        df_plot = df_exp[df_exp[dim2].isin(group_totals)].sort_values(dim1).copy()
                    else:
                        df_plot = df_exp.sort_values(dim1).copy()
                    df_plot[dim1] = df_plot[dim1].astype(int)
                else:
                    df_exp_sorted = df_exp.sort_values('valor', ascending=False)
                    if len(df_exp_sorted) > exp_top_n and exp_tipo_grafico not in ['Sunburst (Drill-Down)', 'Treemap (Mapa de arbol)', 'Tabla Pivot']:
                        df_plot = df_exp_sorted.head(exp_top_n)
                        st.caption(f"Mostrando top {exp_top_n} de {len(df_exp_sorted)} combinaciones")
                    else:
                        df_plot = df_exp_sorted
                
                color_palette = TEMPLATE_COLORS * 4
                
                try:
                    # ==================== BARRAS AGRUPADAS ====================
                    if exp_tipo_grafico == 'Barras Agrupadas':
                        if dim2:
                            # Convertir dim1 a string para eje X
                            df_plot[dim1] = df_plot[dim1].astype(str)
                            fig_exp = px.bar(
                                df_plot, x=dim1, y='valor', color=dim2,
                                barmode='group',
                                title=f"{exp_metrica} por {dim1} y {dim2}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=color_palette,
                                text_auto=True
                            )
                            if dim3:
                                fig_exp = px.bar(
                                    df_plot, x=dim1, y='valor', color=dim2,
                                    facet_col=dim3, facet_col_wrap=3,
                                    barmode='group',
                                    title=f"{exp_metrica} por {dim1}, {dim2} y {dim3}",
                                    labels={'valor': exp_metrica},
                                    color_discrete_sequence=color_palette
                                )
                        else:
                            df_plot[dim1] = df_plot[dim1].astype(str)
                            fig_exp = px.bar(
                                df_plot, x=dim1, y='valor',
                                title=f"{exp_metrica} por {dim1}",
                                labels={'valor': exp_metrica},
                                color='valor', color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                                text_auto=True
                            )
                        st.plotly_chart(fig_exp, use_container_width=True)
                    
                    # ==================== LINEA TEMPORAL ====================
                    elif exp_tipo_grafico == 'Linea Temporal':
                        if dim2:
                            fig_exp = px.line(
                                df_plot, x=dim1, y='valor', color=dim2,
                                markers=True,
                                title=f"Tendencia {exp_metrica} por {dim1} y {dim2}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=color_palette
                            )
                            if dim3:
                                fig_exp = px.line(
                                    df_plot, x=dim1, y='valor', color=dim2,
                                    facet_col=dim3, facet_col_wrap=3,
                                    markers=True,
                                    title=f"Tendencia {exp_metrica} por {dim1}, {dim2} y {dim3}",
                                    labels={'valor': exp_metrica},
                                    color_discrete_sequence=color_palette
                                )
                        else:
                            fig_exp = px.line(
                                df_plot, x=dim1, y='valor',
                                markers=True,
                                title=f"Tendencia {exp_metrica} por {dim1}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=['#9b1b30']
                            )
                        st.plotly_chart(fig_exp, use_container_width=True)
                    
                    # ==================== BARRAS APILADAS ====================
                    elif exp_tipo_grafico == 'Barras Apiladas':
                        if dim2:
                            df_plot[dim1] = df_plot[dim1].astype(str)
                            fig_exp = px.bar(
                                df_plot, x=dim1, y='valor', color=dim2,
                                barmode='stack',
                                title=f"{exp_metrica} apilado por {dim1} y {dim2}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=color_palette,
                                text_auto=True
                            )
                        else:
                            df_plot[dim1] = df_plot[dim1].astype(str)
                            fig_exp = px.bar(
                                df_plot, x=dim1, y='valor',
                                title=f"{exp_metrica} por {dim1}",
                                labels={'valor': exp_metrica},
                                color='valor', color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                                text_auto=True
                            )
                        st.plotly_chart(fig_exp, use_container_width=True)
                    
                    # ==================== SUNBURST (DRILL-DOWN) ====================
                    elif exp_tipo_grafico == 'Sunburst (Drill-Down)':
                        path_dims = exp_dimensiones[:min(len(exp_dimensiones), 5)]
                        # Asegurar que no hay NaN
                        for d in path_dims:
                            df_exp_sorted[d] = df_exp_sorted[d].fillna('Sin dato').astype(str)
                        
                        fig_exp = px.sunburst(
                            df_exp_sorted,
                            path=path_dims,
                            values='valor',
                            title=f"Drill-Down: {exp_metrica} por {' > '.join(path_dims)}",
                            color='valor',
                            color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                            maxdepth=3
                        )
                        fig_exp.update_layout(height=450, uniformtext=dict(minsize=9, mode='hide'))
                        fig_exp.update_traces(
                            textinfo='label+percent parent',
                            insidetextorientation='radial',
                            textfont_size=11
                        )
                        st.plotly_chart(fig_exp, use_container_width=True)
                        st.caption("Haz clic en un segmento para hacer drill-down. Clic en el centro para volver atras.")
                    
                    # ==================== TREEMAP ====================
                    elif exp_tipo_grafico == 'Treemap (Mapa de arbol)':
                        path_dims = exp_dimensiones[:min(len(exp_dimensiones), 5)]
                        for d in path_dims:
                            df_exp_sorted[d] = df_exp_sorted[d].fillna('Sin dato').astype(str)
                        
                        fig_exp = px.treemap(
                            df_exp_sorted,
                            path=[px.Constant("Total")] + path_dims,
                            values='valor',
                            title=f"Treemap: {exp_metrica} por {' > '.join(path_dims)}",
                            color='valor',
                            color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                        )
                        fig_exp.update_layout(height=450, uniformtext=dict(minsize=9, mode='hide'))
                        fig_exp.update_traces(textinfo='label+percent parent', textfont_size=10)
                        st.plotly_chart(fig_exp, use_container_width=True)
                        st.caption("Haz clic en un bloque para hacer drill-down. Clic en el encabezado superior para volver.")
                    
                    # ==================== TABLA PIVOT ====================
                    elif exp_tipo_grafico == 'Tabla Pivot':
                        if dim2:
                            try:
                                pivot_df = df_exp.pivot_table(
                                    index=dim1, columns=dim2, values='valor',
                                    aggfunc='sum', fill_value=0
                                )
                                pivot_df['TOTAL'] = pivot_df.sum(axis=1)
                                pivot_df = pivot_df.sort_values('TOTAL', ascending=False)
                                
                                st.markdown(f"**Tabla cruzada: {dim1} vs {dim2}** (valores = {exp_metrica})")
                                st.dataframe(
                                    pivot_df.style.format("{:,.0f}").background_gradient(cmap='Blues', axis=None),
                                    use_container_width=True, height=max(300, min(600, len(pivot_df)*35))
                                )
                            except Exception:
                                st.dataframe(df_exp_sorted, hide_index=True, use_container_width=True, height=max(300, min(600, len(df_exp_sorted)*35)))
                        else:
                            st.dataframe(
                                df_exp_sorted.style.format({'valor': '{:,.0f}', 'registros': '{:,.0f}'}),
                                hide_index=True, use_container_width=True, height=max(300, min(600, len(df_exp_sorted)*35))
                            )
                    
                    # ==================== HEATMAP ====================
                    elif exp_tipo_grafico == 'Heatmap':
                        if dim2:
                            try:
                                pivot_heat = df_exp.pivot_table(
                                    index=dim2, columns=dim1, values='valor',
                                    aggfunc='sum', fill_value=0
                                )
                                # go ya importado globalmente (linea 14)
                                fig_exp = go.Figure(data=go.Heatmap(
                                    z=pivot_heat.values,
                                    x=[str(c) for c in pivot_heat.columns],
                                    y=[str(i) for i in pivot_heat.index],
                                    colorscale='YlOrRd',
                                    text=[[f"{v:,.0f}" for v in row] for row in pivot_heat.values],
                                    texttemplate="%{text}",
                                    textfont={"size": 9},
                                ))
                                fig_exp.update_layout(
                                    title=f"Heatmap: {exp_metrica} ({dim1} vs {dim2})",
                                    height=max(400, len(pivot_heat) * 30 + 100),
                                    xaxis_title=dim1, yaxis_title=dim2
                                )
                                st.plotly_chart(fig_exp, use_container_width=True)
                            except Exception as e_heat:
                                st.warning(f"No se pudo generar heatmap: {e_heat}")
                        else:
                            st.warning("El heatmap requiere al menos 2 dimensiones")
                
                except Exception as e_chart:
                    st.error(f"Error generando grafico: {e_chart}")
                    st.dataframe(df_exp_sorted.head(50), hide_index=True, use_container_width=True)
                
                # Boton de descarga
                descargar_datos_grafico(df_exp_sorted, f"explorador_{exp_metrica.lower()}", "Descargar datos del explorador")
                
                # Tips de uso
                with st.expander(":material/help: Tips de uso del Explorador", expanded=False):
                    st.markdown("""
                    **Como usar el Explorador Interactivo:**
                    
                    1. **Selecciona una metrica** (Matriculados, Graduados, etc.)
                    2. **Agrega dimensiones en orden de jerarquia:**
                       - 1 dimension = grafico simple (barras o linea)
                       - 2 dimensiones = grafico agrupado/coloreado
                       - 3+ dimensiones = drill-down con Sunburst o Treemap
                    3. **Orden importa:** La primera dimension es el nivel mas alto, cada una agrega un escalon de detalle
                    4. **Drill-down interactivo:** En Sunburst y Treemap, haz clic para profundizar
                    
                    **Ejemplos utiles:**
                    - `Ano + Metodologia` = Tendencia por modalidad
                    - `Ano + Nivel Formacion + Sexo` = Tendencia por nivel y genero
                    - `Departamento + NBC + Institucion` = Drill-down geografico
                    - `Sector IES + Nivel Formacion + Metodologia` = Composicion institucional
                    
                    **Tipos de grafico recomendados:**
                    - **Linea Temporal**: Cuando la primera dimension es Ano
                    - **Sunburst/Treemap**: Para 3+ dimensiones (drill-down real)
                    - **Heatmap**: Para cruce de 2 dimensiones categoricas
                    - **Tabla Pivot**: Para analisis numerico detallado
                    """)
            else:
                st.warning("No se encontraron datos con los filtros y dimensiones seleccionadas. "
                          "Intente ampliar el rango de anos o cambiar las dimensiones.")
        else:
            st.info(":material/touch_app: Selecciona al menos una dimension para generar el grafico interactivo.")



        # =====================================================================
        # SECCIÓN COMPLEMENTARIA SIET/ETDH (Al final del TAB Académico)
        # P2 FIX: Ahora reacciona a filtros SNIES (NBC, Area, Campo Amplio)
        # via cadena estructural ML: NBC → CINE-F → Area CUOC → Areas SIET
        # =====================================================================
        if tiene_filtros_siet:
            st.markdown("---")
            st.markdown("### Contexto Complementario: Educación para el Trabajo (ETDH)")
            render_etdh_dashboard(
                areas_desempeno=effective_areas_siet,
                deptos=effective_deptos_siet,
                estados_siet=sel_estados_siet if sel_estados_siet else None,
                busqueda_nombre=busqueda_programa if busqueda_programa else None,
                ml_areas_siet=_ml_areas_siet,
                etdh_ml_stats=etdh_ml_stats,
                sel_nbcs=sel_nbcs, sel_campos_amplios=sel_campos_amplios, sel_areas=sel_areas,
                tiene_filtros_academicos_snies=tiene_filtros_academicos_snies,
                modalidades_siet=sel_modalidades_siet if sel_modalidades_siet else None,
                key_prefix="etdh_academic"
            )

    # =========================================================================
    with tab_lab:
        section_header("02", "Pertinencia Laboral", "La formacion se conecta con ocupaciones, competencias y oportunidades reales de insercion que fortalecen la empleabilidad y la permanencia?")
        
        # Obtener datos reales laborales
        # Si hay múltiples NBCs, se combinan los resultados de cada uno
        if len(sel_nbcs) > 1:
            _dfs_vac, _dfs_con, _dfs_des = [], [], []
            for _nbc_i in sel_nbcs[:5]:  # Máximo 5 para rendimiento
                _v = get_vacantes_reales(_nbc_i)
                if not _v.empty:
                    _dfs_vac.append(_v)
                _c, _d = get_competencias_cuoc(_nbc_i)
                if not _c.empty:
                    _dfs_con.append(_c)
                if not _d.empty:
                    _dfs_des.append(_d)
            df_vacantes = pd.concat(_dfs_vac, ignore_index=True).drop_duplicates(subset=['ocupacion']).head(20) if _dfs_vac else pd.DataFrame()
            df_conocimientos = pd.concat(_dfs_con, ignore_index=True).drop_duplicates().head(20) if _dfs_con else pd.DataFrame()
            df_destrezas = pd.concat(_dfs_des, ignore_index=True).drop_duplicates().head(20) if _dfs_des else pd.DataFrame()
        else:
            df_vacantes = get_vacantes_reales(sel_nbc)
            df_conocimientos, df_destrezas = get_competencias_cuoc(sel_nbc)
        
        # Salarios: nueva función que retorna datos REALES (dict con ole_ibc + sigep)
        _sel_depto_sal = sel_deptos[0] if sel_deptos and len(sel_deptos) > 0 else None
        if sel_deptos and len(sel_deptos) > 1:
            st.warning(f"Salarios: mostrando datos para **{html.escape(sel_deptos[0])}** (primer departamento seleccionado de {len(sel_deptos)}).")
        datos_salarios = get_salarios_reales(sel_nbc, departamento=_sel_depto_sal)
        
        # Tendencias laborales APE (vacantes/inscritos/colocados 2017-2019)
        df_tend_vac, df_tend_ins, df_tend_col = get_tendencia_laboral_nbc(sel_nbc)
        
        # Graduados NBC historico (datos complementarios SNIES consolidados)
        df_graduados_nbc = get_graduados_nbc_historico(sel_nbc, filtros=filtros_seleccionados)
        
        col_abs, col_sal = st.columns(2)
        
        with col_abs:
            st.markdown("#### Ratio de Absorcion Laboral (Nacional)")
            
            # Usar vacantes reales si hay datos
            if not df_vacantes.empty:
                vacantes_reales = int(df_vacantes['vacantes_2024'].sum())
            else:
                vacantes_reales = vacantes_est
            
            # IMPORTANTE: Las vacantes APE son a nivel NACIONAL
            es_analisis_territorial = sel_deptos is not None and len(sel_deptos) > 0
            
            if es_analisis_territorial and vacantes_reales > 0:
                graduados_nacionales = get_graduados_nacionales(sel_nbcs if sel_nbcs else sel_nbc, filtros=filtros_seleccionados)
                graduados_para_ratio = graduados_nacionales if graduados_nacionales > 0 else graduados_anual
                nota_territorial = True
            else:
                graduados_para_ratio = graduados_anual
                graduados_nacionales = graduados_anual
                nota_territorial = False
            
            ratio_abs_real, ratio_interp_real = calcular_ratio_absorcion(graduados_para_ratio, vacantes_reales)
            
            fig_abs = go.Figure()
            fig_abs.add_trace(go.Bar(
                name=f'Graduados/ano {"(Nacional)" if nota_territorial else ""}',
                x=['Oferta vs Demanda'],
                y=[graduados_para_ratio],
                marker_color='#9b1b30',
                text=[f'{graduados_para_ratio:,}'],
                textposition='auto'
            ))
            fig_abs.add_trace(go.Bar(
                name='Vacantes APE 2024 (Nacional)',
                x=['Oferta vs Demanda'],
                y=[vacantes_reales],
                marker_color='#6B9080',
                text=[f'{vacantes_reales:,}'],
                textposition='auto'
            ))
            fig_abs.update_layout(
                barmode='group',
                height=300,
                title=f"Ratio: {ratio_abs_real}"
            )
            st.plotly_chart(fig_abs, use_container_width=True)
            df_absorcion = pd.DataFrame({
                'Concepto': ['Graduados/ano', 'Vacantes APE 2024'],
                'Cantidad': [graduados_para_ratio, vacantes_reales]
            })
            descargar_datos_grafico(df_absorcion, "ratio_absorcion_laboral", "Descargar datos")
            st.caption(get_citacion("vacantes_ape"))
            st.info(ratio_interp_real)
            
            if nota_territorial:
                st.caption(f"""
                **Nota metodologica:** Las vacantes APE son a nivel nacional. 
                Se usan graduados nacionales ({graduados_nacionales:,}) 
                en lugar de graduados solo de {arg_depto} ({graduados_anual:,.0f}).
                """)
            
            if etdh_ml_stats and etdh_ml_stats.get('tiene_datos', False):
                siet_cert = etdh_ml_stats.get('certificados_siet', 0)
                siet_mat = etdh_ml_stats.get('matricula_siet', 0)
                if siet_cert > 0 or siet_mat > 0:
                    total_formados = int(graduados_para_ratio + siet_cert)
                    st.caption(f"""
                    Incluyendo ETDH/SENA: Total formados: {total_formados:,} 
                    ({graduados_para_ratio:,} graduados SNIES + {siet_cert:,} certificados SIET).
                    Matricula ETDH relacionada: {siet_mat:,}.
                    """)
            
            # Mostrar top vacantes
            if not df_vacantes.empty:
                st.markdown("**Top Ocupaciones con Vacantes:**")
                st.dataframe(
                    df_vacantes.head(5)[['ocupacion', 'vacantes_2024', 'vacantes_2023']].rename(
                        columns={'ocupacion': 'Ocupacion', 'vacantes_2024': 'Vacantes 2024', 'vacantes_2023': 'Vacantes 2023'}
                    ),
                    hide_index=True,
                    use_container_width=True
                )
        
        with col_sal:
            st.markdown("#### Referencia Salarial (Datos Oficiales)")
            
            smlv = 1_423_500  # SMLV 2026
            
            if datos_salarios['tiene_datos']:
                # === FUENTE 1: OLE IBC (Ingreso Base de Cotizacion de graduados) ===
                df_ibc = datos_salarios.get('ole_ibc', pd.DataFrame())
                if not df_ibc.empty:
                    # Filtrar por nivel de formacion (Pregrado/Posgrado)
                    ibc_formacion = df_ibc[df_ibc['tipo'] == 'nivel_formacion']
                    
                    if not ibc_formacion.empty:
                        fig_sal = go.Figure()
                        for _, row in ibc_formacion.iterrows():
                            fig_sal.add_trace(go.Bar(
                                name=str(row['categoria']),
                                x=[str(row['categoria'])],
                                y=[float(row['ibc_max_pesos'])],
                                base=[float(row['ibc_min_pesos'])],
                                text=[f"${float(row['ibc_min_pesos']):,.0f} - ${float(row['ibc_max_pesos']):,.0f}"],
                                textposition='auto',
                                marker_color='#a0522d' if 'Pregrado' in str(row['categoria']) else '#9b1b30'
                            ))
                        
                        fig_sal.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                         annotation_text=f"SMLV: ${smlv:,}")
                        fig_sal.update_layout(
                            height=300,
                            title="IBC Graduados (OLE - MinEducacion)",
                            yaxis_title="Ingreso Base Cotizacion ($)",
                            showlegend=False
                        )
                        st.plotly_chart(fig_sal, use_container_width=True)
                        
                        ano_seg = df_ibc['ano_seguimiento'].iloc[0] if 'ano_seguimiento' in df_ibc.columns else '?'
                        cohorte = df_ibc['cohorte_graduados'].iloc[0] if 'cohorte_graduados' in df_ibc.columns else '?'
                        st.caption(f"**Fuente:** OLE - Observatorio Laboral para la Educacion (MinEducacion). "
                                  f"Seguimiento {ano_seg}, cohorte graduados {cohorte}. "
                                  f"IBC = Ingreso Base de Cotizacion al sistema de seguridad social.")
                    
                    # Mostrar también por sector
                    ibc_sector = df_ibc[df_ibc['tipo'] == 'sector']
                    if not ibc_sector.empty:
                        cols_sector = st.columns(len(ibc_sector))
                        for idx, (_, row) in enumerate(ibc_sector.iterrows()):
                            with cols_sector[idx]:
                                rango = f"{float(row['ibc_min_smmlv']):.1f}-{float(row['ibc_max_smmlv']):.1f}x SMLV"
                                st.metric(str(row['categoria']), rango,
                                         delta=f"${float(row['ibc_min_pesos']):,.0f} - ${float(row['ibc_max_pesos']):,.0f}")
                
                # === FUENTE 2: SIGEP por nivel educativo ===
                df_sigep = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame())
                if not df_sigep.empty:
                    with st.expander("Ver salarios por nivel educativo (SIGEP - Empleo publico)", expanded=df_ibc.empty):
                        fig_sigep = go.Figure()
                        fig_sigep.add_trace(go.Bar(
                            x=df_sigep['nivel_educativo'],
                            y=df_sigep['salario_promedio'],
                            name='Promedio',
                            marker_color='#9b1b30',
                            text=[f"${v:,.0f}" for v in df_sigep['salario_promedio']],
                            textposition='auto'
                        ))
                        fig_sigep.add_trace(go.Bar(
                            x=df_sigep['nivel_educativo'],
                            y=df_sigep['salario_mediana'],
                            name='Mediana',
                            marker_color='#6B9080',
                            text=[f"${v:,.0f}" for v in df_sigep['salario_mediana']],
                            textposition='auto'
                        ))
                        fig_sigep.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                           annotation_text=f"SMLV: ${smlv:,}")
                        fig_sigep.update_layout(
                            barmode='group', height=350,
                            title="Salarios reales por nivel educativo",
                            yaxis_title="Salario ($)"
                        )
                        st.plotly_chart(fig_sigep, use_container_width=True)
                        
                        total_emps = int(df_sigep['cantidad_empleados'].sum())
                        st.caption(f"**Fuente:** SIGEP (Sistema de Informacion y Gestion del Empleo Publico). "
                                  f"Muestra: {total_emps:,} empleados. Sector publico colombiano.")
                
                # === FUENTE 3: SIGEP departamental ===
                df_depto = datos_salarios.get('sigep_departamental', pd.DataFrame())
                if not df_depto.empty:
                    with st.expander(f"Ver salarios en {_sel_depto_sal} (SIGEP)", expanded=False):
                        st.dataframe(df_depto.rename(columns={
                            'nivel_educativo': 'Nivel Educativo',
                            'salario_promedio': 'Salario Promedio',
                            'salario_mediana': 'Salario Mediana',
                            'cantidad_empleados': 'N Empleados'
                        }), hide_index=True, use_container_width=True)
            else:
                st.warning("No se encontraron datos salariales de referencia en las fuentes oficiales (OLE/SIGEP).")
        st.markdown("---")
        st.markdown("#### Radar de Competencias Requeridas - Skills Gap (Nacional)")
        st.caption("Conocimientos y destrezas que el mercado laboral exige para las ocupaciones vinculadas a este NBC.")
        
        # Preparar datos SIET del skills bridge (si disponibles)
        _bridge_con_names = set()
        _bridge_des_names = set()
        if skills_bridge and skills_bridge.get('has_data'):
            _bridge_con_names = set(s['nombre'] for s in skills_bridge.get('siet_conocimientos', []))
            _bridge_des_names = set(s['nombre'] for s in skills_bridge.get('siet_destrezas', []))
        
        col_conocimientos, col_destrezas = st.columns(2)
        
        with col_conocimientos:
            st.markdown("**Conocimientos Clave:**")
            if not df_conocimientos.empty:
                # Radar Chart de Conocimientos con overlay SIET
                fig_radar_con = go.Figure()
                # Traza principal: SNIES/CUOC (educación formal)
                fig_radar_con.add_trace(go.Scatterpolar(
                    r=df_conocimientos['frecuencia'].values,
                    theta=df_conocimientos['conocimiento'].values,
                    fill='toself',
                    name='SNIES (Ed. Formal)',
                    marker_color='#9b1b30',
                    opacity=0.7
                ))
                # Overlay SIET si hay datos del puente de competencias
                if _bridge_con_names and skills_bridge.get('siet_conocimientos'):
                    con_col = 'conocimiento' if 'conocimiento' in df_conocimientos.columns else df_conocimientos.columns[0]
                    snies_con_names = df_conocimientos[con_col].values
                    siet_values = []
                    for cn in snies_con_names:
                        if cn in _bridge_con_names:
                            match_item = next((s for s in skills_bridge['siet_conocimientos'] if s['nombre'] == cn), None)
                            siet_values.append(match_item['n_ocupaciones'] if match_item else 0)
                        else:
                            siet_values.append(0)
                    if any(v > 0 for v in siet_values):
                        fig_radar_con.add_trace(go.Scatterpolar(
                            r=siet_values,
                            theta=snies_con_names,
                            fill='toself',
                            name='SIET/ETDH (Ed. Trabajo)',
                            marker_color='#cc8800',
                            opacity=0.4,
                            line=dict(dash='dot')
                        ))
                show_legend = bool(_bridge_con_names)
                fig_radar_con.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, df_conocimientos['frecuencia'].max() * 1.2])),
                    showlegend=show_legend,
                    height=400 if show_legend else 350,
                    margin=dict(l=50, r=50, t=60, b=50),
                    title="Conocimientos más demandados (Nacional)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_radar_con, use_container_width=True)
                descargar_datos_grafico(df_conocimientos, "conocimientos_requeridos", "Descargar datos")
                st.caption(get_citacion("competencias_cuoc"))
            else:
                st.warning("Sin datos de conocimientos para este NBC")
        
        with col_destrezas:
            st.markdown("**Destrezas Clave:**")
            if not df_destrezas.empty:
                # Radar Chart de Destrezas con overlay SIET
                fig_radar_des = go.Figure()
                fig_radar_des.add_trace(go.Scatterpolar(
                    r=df_destrezas['frecuencia'].values,
                    theta=df_destrezas['destreza'].values,
                    fill='toself',
                    name='SNIES (Ed. Formal)',
                    marker_color='#6B9080',
                    opacity=0.7
                ))
                if _bridge_des_names and skills_bridge.get('siet_destrezas'):
                    des_col = 'destreza' if 'destreza' in df_destrezas.columns else df_destrezas.columns[0]
                    snies_des_names = df_destrezas[des_col].values
                    siet_des_values = []
                    for dn in snies_des_names:
                        if dn in _bridge_des_names:
                            match_item = next((s for s in skills_bridge['siet_destrezas'] if s['nombre'] == dn), None)
                            siet_des_values.append(match_item['n_ocupaciones'] if match_item else 0)
                        else:
                            siet_des_values.append(0)
                    if any(v > 0 for v in siet_des_values):
                        fig_radar_des.add_trace(go.Scatterpolar(
                            r=siet_des_values,
                            theta=snies_des_names,
                            fill='toself',
                            name='SIET/ETDH (Ed. Trabajo)',
                            marker_color='#cc8800',
                            opacity=0.4,
                            line=dict(dash='dot')
                        ))
                show_legend_des = bool(_bridge_des_names)
                fig_radar_des.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, df_destrezas['frecuencia'].max() * 1.2])),
                    showlegend=show_legend_des,
                    height=400 if show_legend_des else 350,
                    margin=dict(l=50, r=50, t=60, b=50),
                    title="Destrezas más demandadas (Nacional)",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_radar_des, use_container_width=True)
                descargar_datos_grafico(df_destrezas, "destrezas_requeridas", "Descargar datos")
                st.caption(get_citacion("competencias_cuoc"))
            else:
                st.warning("Sin datos de destrezas para este NBC")
        
        # =================================================================
        # PUENTE DE COMPETENCIAS SNIES ↔ SIET/ETDH (Cross-Education Analysis)
        # =================================================================
        if skills_bridge and skills_bridge.get('has_data'):
            st.markdown("---")
            st.markdown('<h4 class="icon-header"><i class="fas fa-arrows-left-right"></i> '
                        'Puente de Competencias: Educacion Formal - Educacion para el Trabajo</h4>', 
                        unsafe_allow_html=True)
            
            # KPIs del puente (compactos)
            align_global = skills_bridge.get('alignment_score_global', 0)
            compl_siet = skills_bridge.get('complementarity_siet', 0)
            n_shared_con = len(skills_bridge.get('shared_conocimientos', []))
            n_shared_des = len(skills_bridge.get('shared_destrezas', []))
            n_snies_ocp = len(skills_bridge.get('snies_ocupaciones', []))
            n_siet_ocp = len(skills_bridge.get('siet_ocupaciones', []))
            
            col_b1, col_b2, col_b3, col_b4 = st.columns(4)
            col_b1.metric("Alineacion SNIES-SIET", f"{align_global:.0%}", 
                         help="Jaccard similarity entre competencias SNIES y SIET (CUOC)")
            col_b2.metric("Complementariedad SIET", f"{compl_siet:.0%}",
                         help="% de competencias que SIET/ETDH aporta y NO estan en SNIES")
            col_b3.metric("Ocupaciones SNIES", f"{n_snies_ocp}",
                         help="Ocupaciones CUOC identificadas via educacion formal")
            col_b4.metric("Ocupaciones SIET", f"{n_siet_ocp}",
                         help="Ocupaciones CUOC identificadas via educacion para el trabajo")
            
            # Resumen compacto de competencias compartidas
            if n_shared_con > 0 or n_shared_des > 0:
                shared_con_list = skills_bridge.get('shared_conocimientos', [])[:5]
                shared_des_list = skills_bridge.get('shared_destrezas', [])[:5]
                resumen_parts = []
                if shared_con_list:
                    resumen_parts.append(f"**Conocimientos compartidos ({n_shared_con}):** " + ", ".join(shared_con_list[:5]))
                if shared_des_list:
                    resumen_parts.append(f"**Destrezas compartidas ({n_shared_des}):** " + ", ".join(shared_des_list[:5]))
                st.markdown(" | ".join(resumen_parts))
            
            # CIIU Sectores Economicos (linea compacta)
            ciiu_from_bridge = skills_bridge.get('ciiu_sectors', [])
            if ciiu_from_bridge:
                ciiu_labels = {
                    'A': 'Agropecuario', 'B': 'Mineria', 'C': 'Manufactura', 'D': 'Energia',
                    'E': 'Agua/Saneamiento', 'F': 'Construccion', 'G': 'Comercio', 'H': 'Transporte',
                    'I': 'Hoteleria/Turismo', 'J': 'TIC/Comunicaciones', 'K': 'Financiero',
                    'L': 'Inmobiliario', 'M': 'Profesionales', 'N': 'Administrativos', 'O': 'Gobierno',
                    'P': 'Educacion', 'Q': 'Salud', 'R': 'Arte/Entretenimiento',
                    'S': 'Otros servicios', 'T': 'Hogares', 'U': 'Organismos Int.'
                }
                sectores_str = ", ".join([f"**{s.get('seccion','?')}**-{ciiu_labels.get(s.get('seccion',''), s.get('nombre','')[:20])}" for s in ciiu_from_bridge[:6]])
                st.markdown(f"**Sectores CIIU relacionados:** {sectores_str}")
            
            # Detalle expandible (ocupaciones y notas)
            with st.expander("Ver detalle de ocupaciones CUOC identificadas", expanded=False):
                col_bridge_l, col_bridge_r = st.columns(2)
                
                with col_bridge_l:
                    st.markdown("**Via SNIES (Ed. Formal):**")
                    if skills_bridge.get('snies_ocupaciones'):
                        for ocp in skills_bridge['snies_ocupaciones'][:10]:
                            score = ocp.get('score', 0)
                            area = ocp.get('area', '')
                            area_tag = f" *({area[:30]})*" if area else ""
                            st.markdown(f"- {ocp['nombre']} `{score:.2f}`{area_tag}")
                    else:
                        st.caption("Sin datos")
                
                with col_bridge_r:
                    st.markdown("**Via SIET (Ed. Trabajo):**")
                    if skills_bridge.get('siet_ocupaciones'):
                        for ocp in skills_bridge['siet_ocupaciones'][:10]:
                            st.markdown(f"- {ocp['nombre']}")
                    else:
                        st.caption("Sin datos")
                
                n_shared_ocp = len(skills_bridge.get('shared_ocupaciones', []))
                if n_shared_ocp > 0:
                    st.markdown(f"**Ocupaciones en comun ({n_shared_ocp}):** " + 
                               ", ".join(skills_bridge['shared_ocupaciones'][:5]))
                
                if skills_bridge.get('notas'):
                    for nota in skills_bridge['notas']:
                        st.caption(f"Nota: {nota}")
                
                st.caption("Fuente: CUOC (MinTrabajo), CIIU Rev. 4 (DANE), matching ML con paraphrase-multilingual-MiniLM-L12-v2")
        elif sel_nbcs:
            st.markdown("---")
            st.caption("Datos de educacion formal (SNIES). Active SIET en filtros para cruce con ETDH.")
        
        st.markdown("#### Tendencia de Graduados")
        # Datos SNIES filtrados (departamental o nacional segun filtros)
        if not df_graduados.empty:
            fig_grad = px.bar(df_graduados, x='anio', y='graduados', 
                            title=f"Graduados por Ano ({label_ambito})")
            st.plotly_chart(fig_grad, use_container_width=True)
            descargar_datos_grafico(df_graduados, "tendencia_graduados_barras", "Descargar datos")
            st.caption(get_citacion("snies_graduados"))
        
        # Datos NBC consolidados nacionales (datos complementarios)
        if not df_graduados_nbc.empty:
            with st.expander("Ver graduados NBC consolidado nacional (SNIES)", expanded=False):
                col_gnbc1, col_gnbc2 = st.columns([2, 1])
                with col_gnbc1:
                    fig_gnbc = px.line(df_graduados_nbc, x='anio', y='graduados',
                                     title=f"Graduados Nacionales - {df_graduados_nbc['NBC'].iloc[0]}",
                                     markers=True)
                    fig_gnbc.update_layout( xaxis_title="Ano", yaxis_title="Graduados")
                    st.plotly_chart(fig_gnbc, use_container_width=True)
                with col_gnbc2:
                    ult_grad = df_graduados_nbc.iloc[-1]['graduados']
                    prom_grad = df_graduados_nbc['graduados'].mean()
                    st.metric("Ultimo ano", f"{int(ult_grad):,}")
                    st.metric("Promedio anual", f"{int(prom_grad):,}")
                    if len(df_graduados_nbc) >= 2:
                        var_pct = ((df_graduados_nbc.iloc[-1]['graduados'] - df_graduados_nbc.iloc[0]['graduados']) 
                                  / df_graduados_nbc.iloc[0]['graduados'] * 100)
                        st.metric("Variacion periodo", f"{var_pct:+.1f}%")
                st.caption("Fuente: SNIES - MEN (consolidado nacional por NBC)")
        elif df_graduados.empty:
            st.info("No se encontraron datos de graduados para los filtros seleccionados.")
        
        # =====================================================================
        # TENDENCIA LABORAL APE (Vacantes / Inscritos / Colocados)
        # =====================================================================
        if not df_tend_vac.empty or not df_tend_col.empty:
            st.markdown("---")
            st.markdown("#### Tendencia del Mercado Laboral APE (Nacional)")
            st.caption("Datos reales de la Agencia Publica de Empleo (SENA) - Ocupaciones relacionadas al NBC via ML matching")
            
            col_tv, col_tc = st.columns(2)
            
            with col_tv:
                if not df_tend_vac.empty:
                    # Agrupar por ano
                    df_tv_año = df_tend_vac.groupby('ano').agg(
                        vacantes=('vacantes', 'sum')
                    ).reset_index()
                    df_tv_año['ano'] = df_tv_año['ano'].astype(int)
                    
                    fig_tv = px.bar(df_tv_año, x='ano', y='vacantes',
                                   title="Vacantes APE por ano",
                                   text='vacantes')
                    fig_tv.update_layout( xaxis_title="Ano", yaxis_title="Vacantes")
                    fig_tv.update_traces(texttemplate='%{text:,.0f}', textposition='auto')
                    st.plotly_chart(fig_tv, use_container_width=True)
                    descargar_datos_grafico(df_tv_año, "tendencia_vacantes_ape", "Descargar datos")
            
            with col_tc:
                if not df_tend_col.empty:
                    df_tc_año = df_tend_col.groupby('ano').agg(
                        colocados=('colocados', 'sum')
                    ).reset_index()
                    df_tc_año['ano'] = df_tc_año['ano'].astype(int)
                    
                    fig_tc = px.bar(df_tc_año, x='ano', y='colocados',
                                   title="Colocados APE por ano",
                                   text='colocados',
                                   color_discrete_sequence=['#6B9080'])
                    fig_tc.update_layout( xaxis_title="Ano", yaxis_title="Colocados")
                    fig_tc.update_traces(texttemplate='%{text:,.0f}', textposition='auto')
                    st.plotly_chart(fig_tc, use_container_width=True)
                    descargar_datos_grafico(df_tc_año, "tendencia_colocados_ape", "Descargar datos")
            
            # Tasa de colocacion
            if not df_tend_vac.empty and not df_tend_col.empty:
                try:
                    df_tv_a = df_tend_vac.groupby('ano')['vacantes'].sum().reset_index()
                    df_tc_a = df_tend_col.groupby('ano')['colocados'].sum().reset_index()
                    df_tasa = df_tv_a.merge(df_tc_a, on='ano', how='inner')
                    df_tasa['tasa_colocacion'] = (df_tasa['colocados'] / df_tasa['vacantes'] * 100).round(1)
                    if not df_tasa.empty:
                        tasa_ultima = df_tasa.iloc[-1]['tasa_colocacion']
                        st.metric("Tasa de colocacion (ultimo ano)", f"{tasa_ultima:.1f}%",
                                 help="Porcentaje de vacantes que resultaron en colocacion efectiva (APE)")
                except Exception:
                    pass
            
            # Detalle de ocupaciones con tendencia
            with st.expander("Ver detalle de ocupaciones en tendencia", expanded=False):
                if not df_tend_vac.empty:
                    # Ultimo año disponible
                    ultimo_ano = df_tend_vac['ano'].max()
                    df_ultimo = df_tend_vac[df_tend_vac['ano'] == ultimo_ano].sort_values('vacantes', ascending=False).head(10)
                    st.dataframe(
                        df_ultimo[['ocupacion', 'vacantes']].rename(columns={
                            'ocupacion': 'Ocupacion', 'vacantes': f'Vacantes {ultimo_ano}'
                        }),
                        hide_index=True, use_container_width=True
                    )
            
            st.caption("**Fuente:** Agencia Publica de Empleo (APE) - SENA. Consolidados anuales 2017-2019.")
        
        # =====================================================================
        # NUEVA SECCIÓN: CUALIFICACIONES MEN (Marco Nacional de Cualificaciones)
        # =====================================================================
        st.markdown("---")
        st.markdown("### Cualificaciones MEN (Nacional)")
        st.caption("Catalogo oficial de cualificaciones laborales del Ministerio de Educacion. Cada cualificacion define las competencias minimas exigidas por el mercado.")
        
        # Obtener cualificaciones relacionadas al NBC seleccionado (combinar si multi-NBC)
        if len(sel_nbcs) > 1:
            _dfs_cual = [get_cualificaciones_por_nbc(n) for n in sel_nbcs[:5]]
            _dfs_cual = [d for d in _dfs_cual if not d.empty]
            df_cualif_nbc = pd.concat(_dfs_cual, ignore_index=True).drop_duplicates(subset=['Codigo_MEN']) if _dfs_cual else pd.DataFrame()
        else:
            df_cualif_nbc = get_cualificaciones_por_nbc(sel_nbc)
        
        # FILTRO CRITICO: Respetar sel_niveles (SNIES) -> niveles MNC
        _mnc_filtrados = mapear_niveles_snies_a_mnc(sel_niveles)
        _cualif_filtro_aplicado = False
        if _mnc_filtrados and not df_cualif_nbc.empty:
            _pre_filter_count = len(df_cualif_nbc)
            df_cualif_nbc = df_cualif_nbc[df_cualif_nbc['Nivel_MNC'].isin(_mnc_filtrados)].copy()
            _cualif_filtro_aplicado = _pre_filter_count != len(df_cualif_nbc)
        
        if not df_cualif_nbc.empty:
            # KPIs de Cualificaciones
            col_q1, col_q2, col_q3 = st.columns(3)
            
            n_cualif = len(df_cualif_nbc)
            niveles_cubiertos = df_cualif_nbc['Nivel_MNC'].unique()
            areas_conectadas = df_cualif_nbc['Sigla_Area'].unique()
            
            col_q1.metric("Cualificaciones Relacionadas", f"{n_cualif}")
            _niv_label = f"{len(niveles_cubiertos)} ({min(niveles_cubiertos)}-{max(niveles_cubiertos)})"
            if _cualif_filtro_aplicado:
                _niv_label += " (filtrado)"
            col_q2.metric("Niveles MNC Cubiertos", _niv_label)
            col_q3.metric("Áreas CUOC Conectadas", f"{len(areas_conectadas)}")
            
            # Distribución por Nivel MNC
            col_nivel, col_trayectoria = st.columns(2)
            
            with col_nivel:
                st.markdown("#### Distribución por Nivel MNC")
                df_nivel_cualif = df_cualif_nbc.groupby('Nivel_MNC').size().reset_index(name='N')
                
                # Mapeo de niveles a tipos de formación
                nivel_labels = {
                    2: 'Nivel 2 - Operativo',
                    3: 'Nivel 3 - Técnico Básico',
                    4: 'Nivel 4 - Técnico',
                    5: 'Nivel 5 - Tecnológico',
                    6: 'Nivel 6 - Profesional',
                    7: 'Nivel 7 - Especialización/Maestría'
                }
                df_nivel_cualif['Nivel_Label'] = df_nivel_cualif['Nivel_MNC'].map(nivel_labels)
                
                fig_nivel_cualif = px.bar(
                    df_nivel_cualif,
                    x='Nivel_MNC',
                    y='N',
                    text='N',
                    title="Cualificaciones por Nivel MNC",
                    color='Nivel_MNC',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                )
                fig_nivel_cualif.update_layout(
                    height=300,
                    xaxis_title="Nivel MNC",
                    yaxis_title="N° Cualificaciones",
                    showlegend=False,
                    coloraxis_showscale=False
                )
                fig_nivel_cualif.update_traces(textposition='auto')
                st.plotly_chart(fig_nivel_cualif, use_container_width=True)
                descargar_datos_grafico(df_nivel_cualif, "cualificaciones_nivel_mnc", "Descargar datos")
                st.caption(get_citacion("cualificaciones_men"))
            
            with col_trayectoria:
                st.markdown("#### Trayectoria Formativa Sugerida")
                st.caption("Ruta de cualificación desde nivel operativo hasta especialización")
                
                # Mostrar trayectoria visual
                for nivel in sorted(niveles_cubiertos):
                    cualif_nivel = df_cualif_nbc[df_cualif_nbc['Nivel_MNC'] == nivel]
                    n_cualif_nivel = len(cualif_nivel)
                    
                    nivel_nombre = nivel_labels.get(nivel, f'Nivel {nivel}')
                    # Indicador visual por nivel sin emojis
                    nivel_indicator = ['[2]', '[3]', '[4]', '[5]', '[6]', '[7]'][nivel - 2] if nivel <= 7 else '[N]'
                    
                    st.markdown(f"**{nivel_indicator} {nivel_nombre}** ({n_cualif_nivel} cualificaciones)")
                    
                    # Mostrar ejemplos (máximo 2 por nivel)
                    ejemplos = cualif_nivel['Cualificacion'].head(2).tolist()
                    for ej in ejemplos:
                        st.caption(f"   → {ej[:60]}{'...' if len(ej) > 60 else ''}")
            
            # Tabla detallada con expander
            with st.expander(f"Ver todas las {n_cualif} cualificaciones relacionadas al NBC", expanded=False):
                # Preparar dataframe para visualización
                df_display = df_cualif_nbc[['Codigo_MEN', 'Cualificacion', 'Nivel_MNC', 'Sector', 'Sigla_Area']].copy()
                df_display.columns = ['Código MEN', 'Cualificación', 'Nivel MNC', 'Sector', 'Área CUOC']
                
                st.dataframe(
                    df_display,
                    hide_index=True,
                    use_container_width=True,
                    height=400
                )
                
                # Botón de descarga
                csv_cualif = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Descargar Cualificaciones (CSV)",
                    csv_cualif,
                    f"cualificaciones_men_{(sel_nbc or 'filtro').replace(' ', '_')}.csv",
                    "text/csv"
                )
            
            # Insight de articulación
            _rango_mnc = f"niveles MNC {min(niveles_cubiertos)} a {max(niveles_cubiertos)}" if len(niveles_cubiertos) > 1 else f"nivel MNC {min(niveles_cubiertos)}"
            _nota_filtro = f"\n            - *Filtrado por nivel de formación: {', '.join(sel_niveles)}*" if _cualif_filtro_aplicado else ""
            st.info(f"""
            **Articulación Educación-Empleo:**
            - **{filtro_label}** se conecta con **{n_cualif}** estándares oficiales de cualificación
            - Abarca {_rango_mnc}
            - Las áreas CUOC relacionadas son: **{', '.join(areas_conectadas)}**
            - Estas cualificaciones definen las competencias mínimas exigidas por el mercado laboral colombiano{_nota_filtro}
            """)
            
        else:
            st.warning(f"No se encontraron cualificaciones MEN directamente relacionadas con: **{filtro_label}**")
            
            # Mostrar estadísticas generales de Cualificaciones MEN
            with st.expander("Ver catálogo completo de Cualificaciones MEN"):
                stats_men = get_estadisticas_cualificaciones_men()
                
                st.metric("Total Cualificaciones MEN", f"{stats_men['total']}")
                
                col_stat1, col_stat2 = st.columns(2)
                
                with col_stat1:
                    st.markdown("**Por Nivel MNC:**")
                    if not stats_men['por_nivel'].empty:
                        st.dataframe(stats_men['por_nivel'], hide_index=True)
                
                with col_stat2:
                    st.markdown("**Por Área de Cualificación:**")
                    if not stats_men['por_area'].empty:
                        st.dataframe(stats_men['por_area'].head(10), hide_index=True)
        
        # =====================================================================
        # NUEVA SECCIÓN: ACTIVIDADES Y TAREAS OCUPACIONALES
        # =====================================================================
        st.markdown("---")
        st.markdown('<h3 class="icon-header"><i class="fas fa-tasks"></i> Actividades y Tareas Ocupacionales (Nacional)</h3>', unsafe_allow_html=True)
        st.caption("Perfil ocupacional detallado según la Clasificación Única de Ocupaciones para Colombia (CUOC)")
        
        # Obtener actividades y tareas para los NBCs seleccionados
        if len(sel_nbcs) > 1:
            _dfs_act = [get_actividades_tareas_nbc(n) for n in sel_nbcs[:5]]
            _dfs_act = [d for d in _dfs_act if not d.empty]
            df_actividades = pd.concat(_dfs_act, ignore_index=True).drop_duplicates(subset=['codigo_cuoc']) if _dfs_act else pd.DataFrame()
        else:
            df_actividades = get_actividades_tareas_nbc(sel_nbc)
        
        if not df_actividades.empty:
            # Filtrar solo las que tienen descripción
            df_con_desc = df_actividades[df_actividades['descripcion_actividades'].notna()].copy()
            n_perfiles = len(df_con_desc)
            
            if n_perfiles > 0:
                st.success(f"Se identificaron **{n_perfiles} perfiles ocupacionales** relacionados con {filtro_label}")
                
                # Mostrar perfiles con descripción de actividades
                for i, row in df_con_desc.head(5).iterrows():
                    titulo = str(row['titulo_ocupacion'])[:80]
                    codigo = str(row['codigo_cuoc'])
                    descripcion = str(row['descripcion_actividades'])
                    
                    with st.expander(f"**[{codigo}]** {titulo}", expanded=(i == 0)):
                        st.markdown(f"""
                        **Actividades y tareas principales:**
                        
                        {descripcion}
                        """)
                
                # Si hay más de 5, mostrar opción de ver todos
                if n_perfiles > 5:
                    with st.expander(f"Ver los {n_perfiles - 5} perfiles ocupacionales restantes"):
                        for i, row in df_con_desc.iloc[5:].iterrows():
                            titulo = str(row['titulo_ocupacion'])[:80]
                            codigo = str(row['codigo_cuoc'])
                            descripcion = str(row['descripcion_actividades'])[:200]
                            st.markdown(f"**[{codigo}] {titulo}**")
                            st.caption(f"{descripcion}...")
                            st.markdown("---")
                
                st.caption(get_citacion("cuoc_perfiles"))
            else:
                st.info(f"No se encontraron descripciones de actividades para {filtro_label}. Puede que los programas tengan ocupaciones relacionadas sin perfil detallado.")
        else:
            st.warning(f"No se encontraron perfiles ocupacionales directamente mapeados para: **{filtro_label}**")
            st.caption("<i class='fas fa-lightbulb icon-hint'></i> Los perfiles ocupacionales se basan en el mapeo oficial NBC → CUOC del Ministerio de Trabajo.", unsafe_allow_html=True)

    # =========================================================================
    # TAB 3: SÍNTESIS TERRITORIAL (Datos reales departamentales)
    # =========================================================================
    with tab_terr:
        nivel_territorial = "departamental" if arg_depto else "nacional"
        etiqueta_territorio = arg_depto or "Colombia (Nacional)"
        st.markdown(f'<div class="section-header"><span class="section-eyebrow">03</span><h2>Pertinencia Territorial y Social</h2><p>El territorio cuenta con condiciones de acceso, conectividad y demanda que favorezcan trayectorias educativas viables?</p></div>', unsafe_allow_html=True)
        if sel_deptos and len(sel_deptos) > 1:
            st.warning(f"Análisis territorial enfocado en **{html.escape(sel_deptos[0])}**. Los demás departamentos ({html.escape(', '.join(sel_deptos[1:3]))}{' …' if len(sel_deptos) > 3 else ''}) se incluyen en filtros de oferta y matriculados pero los indicadores territoriales corresponden al primero.")
        st.markdown(f"""
        **Pregunta clave:** ¿El territorio soporta este programa?
        
        Análisis **{nivel_territorial}** con datos reales: indicadores educativos,
        oferta académica, infraestructura digital, tejido empresarial y contexto socioeconómico.
        {"" if arg_depto else "<i class='fas fa-info-circle' style='margin-right:0.3rem'></i> *Seleccione un departamento en filtros para detallar a nivel territorial.*"}
        """)
        
        # =================================================================
        # OBTENCIÓN DE TODOS LOS DATOS TERRITORIALES
        # depto=None → datos nacionales (queries ya lo manejan internamente)
        # =================================================================
        
        # Indicadores educativos (nacional o departamental)
        with st.spinner("Consultando datos territoriales..."):
            datos_edu_depto = get_indicadores_educativos_depto(arg_depto)
        
        # Graduados y matriculados del NBC (nacional o departamental)
        if sel_nbc:
            df_grad_depto = get_graduados_depto_nbc(sel_nbc, arg_depto, filtros=filtros_seleccionados)
            df_mat_depto = get_matriculados_depto_nbc(sel_nbc, arg_depto, filtros=filtros_seleccionados)
            df_oferta_depto = get_oferta_programas_depto(sel_nbc, arg_depto, filtros=filtros_seleccionados)
            df_ranking_nbc = get_ranking_departamental_nbc(sel_nbc, filtros=filtros_seleccionados)
        else:
            df_grad_depto = pd.DataFrame()
            df_mat_depto = pd.DataFrame()
            df_oferta_depto = pd.DataFrame()
            df_ranking_nbc = pd.DataFrame()
        
        # Datos PDET (solo con depto — PDET es inherentemente territorial)
        df_pdet = get_municipios_pdet(arg_depto) if arg_depto else pd.DataFrame()
        es_territorio_pdet = not df_pdet.empty
        n_municipios_pdet = len(df_pdet) if es_territorio_pdet else 0
        
        # Datos DNP (solo con depto — MDM es municipal)
        if TERRITORIAL_ROBUST and arg_depto:
            datos_dnp = get_desempeno_dnp(arg_depto)
            en_plan_desarrollo = datos_dnp['en_plan_desarrollo']
            mdm_score = datos_dnp['puntaje_mdm']
        else:
            datos_dnp = {}
            en_plan_desarrollo = False
            mdm_score = None
        
        # Datos Cluster empresarial (solo con depto — RUES es territorial)
        if TERRITORIAL_ROBUST and sel_nbc and arg_depto:
            datos_cluster = get_cluster_empresarial(sel_nbc, arg_depto)
            hay_cluster = datos_cluster['hay_cluster']
            n_empresas_cluster = datos_cluster['total_empresas']
            sectores_ciiu = datos_cluster['sectores_relacionados']
        else:
            datos_cluster = {}
            hay_cluster = False
            n_empresas_cluster = 0
            sectores_ciiu = []
        
        # Salarios (nacional o departamental — queries manejan depto=None)
        datos_sal_depto = get_salarios_depto(arg_depto)
        
        # Región geográfica
        if TERRITORIAL_ROBUST and arg_depto:
            region_depto = get_region(arg_depto)
        else:
            region_depto = None
        
        # Conectividad (usa el df_conectividad ya cargado arriba — misma llamada)
        df_conectividad_terr = df_conectividad
        if not df_conectividad_terr.empty:
            avg_conectividad = df_conectividad_terr['indice_conectividad'].mean()
            avg_4g = df_conectividad_terr['cobertura_4g_pct'].mean() if 'cobertura_4g_pct' in df_conectividad_terr.columns else 0
        else:
            avg_conectividad = 0.5
            avg_4g = 0.5
        
        # =================================================================
        # SECCIÓN 1: INDICADORES EDUCATIVOS DEL DEPARTAMENTO
        # =================================================================
        
        st.markdown("---")
        st.markdown(f"#### Indicadores Educativos: {etiqueta_territorio}")
        
        if datos_edu_depto.get('tiene_datos'):
            # KPIs principales
            col_tcb, col_tti, col_mat = st.columns(3)
            
            with col_tcb:
                tcb_val = datos_edu_depto.get('tcb_actual')
                st.metric(
                    "Tasa Cobertura Bruta ES",
                    f"{tcb_val:.1f}%" if tcb_val else "N/D",
                    help="Porcentaje de la población en edad de estudiar que está matriculada en educación superior"
                )
                if tcb_val:
                    if tcb_val >= 50:
                        st.success("Por encima del promedio nacional (~55%)")
                    else:
                        st.warning("Por debajo del promedio nacional (~55%)")
            
            with col_tti:
                tti_val = datos_edu_depto.get('tti_actual')
                st.metric(
                    "Tasa Tránsito Inmediato",
                    f"{tti_val:.1f}%" if tti_val else "N/D",
                    help="Porcentaje de bachilleres que ingresan a educación superior al año siguiente"
                )
                if tti_val:
                    if tti_val >= 40:
                        st.success("Buen tránsito a educación superior")
                    else:
                        st.warning("Bajo tránsito — potencial demanda insatisfecha")
            
            with col_mat:
                mat_val = datos_edu_depto.get('matricula_actual')
                st.metric(
                    "Matrícula ES Total",
                    f"{mat_val:,}" if mat_val else "N/D",
                    help="Total de estudiantes matriculados en educación superior en el departamento"
                )
            
            # Graficos historicos
            col_hist1, col_hist2 = st.columns(2)
            
            with col_hist1:
                df_tcb_hist = datos_edu_depto.get('tcb_historico', pd.DataFrame())
                df_tti_hist = datos_edu_depto.get('tti_historico', pd.DataFrame())
                
                if not df_tcb_hist.empty or not df_tti_hist.empty:
                    fig_tasas = go.Figure()
                    if not df_tcb_hist.empty:
                        fig_tasas.add_trace(go.Scatter(
                            x=df_tcb_hist['anio'], y=df_tcb_hist['tasa'],
                            mode='lines+markers', name='Cobertura Bruta ES (%)',
                            marker_color='#9b1b30', line=dict(width=2)
                        ))
                    if not df_tti_hist.empty:
                        fig_tasas.add_trace(go.Scatter(
                            x=df_tti_hist['anio'], y=df_tti_hist['tasa'],
                            mode='lines+markers', name='Tránsito Inmediato (%)',
                            marker_color='#6B9080', line=dict(width=2, dash='dot')
                        ))
                    fig_tasas.update_layout(
                        height=300, title=f"Evolución Tasas Educativas — {etiqueta_territorio}",
                        yaxis_title="Porcentaje (%)", xaxis_title="Año",
                        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
                    )
                    st.plotly_chart(fig_tasas, use_container_width=True)
                    # Descargar datos combinados
                    df_tasas_export = pd.DataFrame()
                    if not df_tcb_hist.empty:
                        df_tasas_export = df_tcb_hist.rename(columns={'tasa': 'TCB_%'})
                    if not df_tti_hist.empty:
                        if not df_tasas_export.empty:
                            df_tasas_export = df_tasas_export.merge(
                                df_tti_hist.rename(columns={'tasa': 'TTI_%'}), on='anio', how='outer'
                            )
                        else:
                            df_tasas_export = df_tti_hist.rename(columns={'tasa': 'TTI_%'})
                    descargar_datos_grafico(df_tasas_export, "tasas_educativas_depto", "Descargar datos")
            
            with col_hist2:
                df_mat_hist = datos_edu_depto.get('matricula_historico', pd.DataFrame())
                if not df_mat_hist.empty:
                    fig_mat = go.Figure()
                    fig_mat.add_trace(go.Bar(
                        x=df_mat_hist['anio'], y=df_mat_hist['matriculados'],
                        marker_color='#a0522d',
                        text=[f"{v:,}" for v in df_mat_hist['matriculados']],
                        textposition='auto'
                    ))
                    fig_mat.update_layout(
                        height=300, title=f"Matrícula ES Total — {etiqueta_territorio}",
                        yaxis_title="Estudiantes", xaxis_title="Año"
                    )
                    st.plotly_chart(fig_mat, use_container_width=True)
                    descargar_datos_grafico(df_mat_hist, "matricula_es_depto", "Descargar datos")
            
            st.caption(f"**Fuente:** {datos_edu_depto['fuente']}")
        else:
            st.info("No se encontraron indicadores educativos con los filtros actuales.")
        
        # =================================================================
        # SECCIÓN 2: OFERTA ACADÉMICA DEL NBC EN EL TERRITORIO
        # =================================================================
        st.markdown("---")
        st.markdown(f"#### Oferta y Demanda del NBC en el Territorio")
        
        col_oferta1, col_oferta2 = st.columns(2)
        
        with col_oferta1:
            # Graduados + Matriculados del NBC en el depto
            if not df_grad_depto.empty or not df_mat_depto.empty:
                fig_nbc_depto = go.Figure()
                if not df_mat_depto.empty:
                    fig_nbc_depto.add_trace(go.Bar(
                        x=df_mat_depto['anio'], y=df_mat_depto['matriculados'],
                        name='Matriculados', marker_color='#9b1b30',
                        text=[f"{v:,}" for v in df_mat_depto['matriculados']],
                        textposition='auto'
                    ))
                if not df_grad_depto.empty:
                    fig_nbc_depto.add_trace(go.Bar(
                        x=df_grad_depto['anio'], y=df_grad_depto['graduados'],
                        name='Graduados', marker_color='#6B9080',
                        text=[f"{v:,}" for v in df_grad_depto['graduados']],
                        textposition='auto'
                    ))
                fig_nbc_depto.update_layout(
                    barmode='group', height=320,
                    title=f"{filtro_label} en {etiqueta_territorio}",
                    yaxis_title="Estudiantes", xaxis_title="Año",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25)
                )
                st.plotly_chart(fig_nbc_depto, use_container_width=True)
                # Exportar datos combinados
                df_nbc_depto_export = pd.DataFrame()
                if not df_mat_depto.empty:
                    df_nbc_depto_export = df_mat_depto.copy()
                if not df_grad_depto.empty:
                    if not df_nbc_depto_export.empty:
                        df_nbc_depto_export = df_nbc_depto_export.merge(df_grad_depto, on='anio', how='outer')
                    else:
                        df_nbc_depto_export = df_grad_depto.copy()
                descargar_datos_grafico(df_nbc_depto_export, "nbc_depto_historico", "Descargar datos")
                st.caption(get_citacion("snies_graduados"))
            elif sel_nbc:
                st.warning(f"Sin datos de graduados/matriculados de este NBC en {etiqueta_territorio}")
            else:
                st.info("Seleccione un NBC para ver la oferta académica")
        
        with col_oferta2:
            # Ranking departamental del NBC
            if not df_ranking_nbc.empty:
                # Resaltar el departamento seleccionado
                df_rank_top = df_ranking_nbc.head(15).copy()
                df_rank_top['color'] = df_rank_top['departamento'].apply(
                    lambda x: '#a0522d' if arg_depto and arg_depto.upper() in str(x).upper() else '#A09088'
                )
                
                fig_rank = go.Figure()
                fig_rank.add_trace(go.Bar(
                    y=df_rank_top['departamento'],
                    x=df_rank_top['graduados'],
                    orientation='h',
                    marker_color=df_rank_top['color'],
                    text=[f"{v:,}" for v in df_rank_top['graduados']],
                    textposition='auto'
                ))
                fig_rank.update_layout(
                    height=400,
                    title=f"Ranking Departamental: {filtro_label}",
                    xaxis_title="Graduados acumulados (2019-2024)",
                    yaxis={'categoryorder': 'total ascending'},
                )
                st.plotly_chart(fig_rank, use_container_width=True)
                descargar_datos_grafico(df_ranking_nbc, "ranking_depto_nbc", "Descargar datos")
                
                # Calcular posición del depto
                if arg_depto:
                    pos = df_ranking_nbc[df_ranking_nbc['departamento'].str.upper().str.contains(arg_depto.upper(), na=False)]
                    if not pos.empty:
                        idx = df_ranking_nbc.index.get_loc(pos.index[0]) + 1
                        total = len(df_ranking_nbc)
                        st.caption(f"**{arg_depto}** ocupa la posición **#{idx}** de {total} departamentos en graduados de este NBC.")
            elif sel_nbc:
                st.info("Sin datos de ranking departamental para este NBC")
        # Programas activos en el depto
        if not df_oferta_depto.empty:
            n_activos = len(df_oferta_depto[df_oferta_depto['estado'] == 'ACTIVO']) if 'estado' in df_oferta_depto.columns else len(df_oferta_depto)
            n_total = len(df_oferta_depto)
            with st.expander(f"Ver programas de {filtro_label} en {etiqueta_territorio} ({n_activos} activos / {n_total} total)", expanded=False):
                df_display = df_oferta_depto.rename(columns={
                    'ies': 'IES', 'programa': 'Programa', 'nivel': 'Nivel',
                    'metodologia': 'Metodología', 'estado': 'Estado', 'municipio': 'Municipio'
                })
                st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        # =================================================================
        # SECCIÓN 3: INFRAESTRUCTURA Y CONTEXTO TERRITORIAL
        # =================================================================
        st.markdown("---")
        st.markdown("#### Infraestructura y Contexto Territorial")
        st.caption("Conectividad digital, municipios PDET y capacidad institucional (MDM) del departamento.")
        
        col_conect, col_contexto = st.columns(2)
        
        with col_conect:
            st.markdown("##### Conectividad Digital")
            
            if not df_conectividad_terr.empty:
                # Top municipios/departamentos por conectividad
                df_con_top = df_conectividad_terr.nlargest(10, 'indice_conectividad')
                
                fig_con = go.Figure()
                fig_con.add_trace(go.Bar(
                    y=df_con_top['municipio'],
                    x=df_con_top['indice_conectividad'],
                    orientation='h',
                    marker_color='#6B9080',
                    text=[f"{v:.2f}" for v in df_con_top['indice_conectividad']],
                    textposition='auto'
                ))
                fig_con.update_layout(
                    height=300, title=f"Conectividad — {etiqueta_territorio}",
                    xaxis_title="Índice (0-1)",
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig_con, use_container_width=True)
                
                col_4g, col_inet = st.columns(2)
                col_4g.metric("Cobertura 4G/LTE promedio", f"{avg_4g*100:.1f}%")
                col_inet.metric(f"{'Municipios' if arg_depto else 'Departamentos'} con datos", f"{len(df_conectividad_terr)}")
                
                # Recomendación de modalidad
                if avg_conectividad > 0.7:
                    st.success("Alta conectividad — viable modalidad virtual 100%")
                    modalidad_recomendada = "Virtual 100%"
                    potencial_virtual = 100
                elif avg_conectividad > 0.4:
                    st.warning("Conectividad media — recomendable modalidad híbrida")
                    modalidad_recomendada = "Híbrida"
                    potencial_virtual = 60
                else:
                    st.warning("Baja conectividad — priorizar modalidad presencial")
                    modalidad_recomendada = "Presencial"
                    potencial_virtual = 20
                
                descargar_datos_grafico(df_conectividad_terr, "conectividad_municipal", "Descargar datos")
                st.caption(get_citacion("internet_fijo") + " | " + get_citacion("cobertura_movil"))
            else:
                st.warning("Sin datos de conectividad disponibles")
                modalidad_recomendada = "N/D"
                potencial_virtual = 50
        
        with col_contexto:
            st.markdown("##### Contexto Socioinstitucional")
            
            # Región
            if region_depto:
                st.info(f"**Región:** {region_depto}  |  **Departamento:** {arg_depto}")
            elif not arg_depto:
                st.info("**Nivel:** Nacional — seleccione departamento para detalle territorial")
            
            # PDET
            if es_territorio_pdet:
                st.success(f"Territorio PDET: {n_municipios_pdet} municipios priorizados para el postconflicto")
                with st.expander("Ver municipios PDET"):
                    if 'subregion' in df_pdet.columns:
                        st.dataframe(
                            df_pdet[['municipio', 'subregion']].rename(
                                columns={'municipio': 'Municipio', 'subregion': 'Subregión'}
                            ), hide_index=True, use_container_width=True
                        )
                    else:
                        st.dataframe(df_pdet, hide_index=True, use_container_width=True)
                st.caption(get_citacion("pdet"))
            elif arg_depto:
                st.info("No es territorio PDET")
            # DNP
            if en_plan_desarrollo and mdm_score is not None:
                if mdm_score >= 70:
                    mdm_texto = "Alta capacidad institucional"
                    st.success(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
                elif mdm_score >= 50:
                    mdm_texto = "Capacidad institucional media"
                    st.warning(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
                else:
                    mdm_texto = "Capacidad institucional limitada"
                    st.error(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
                st.caption(f"Medición de Desempeño Municipal (DNP) — {datos_dnp.get('municipios_evaluados', 0)} municipios evaluados")
            elif arg_depto:
                st.info("Sin datos de desempeño municipal (DNP)")
        # =================================================================
        # SECCIÓN 4: CLUSTER EMPRESARIAL + SALARIOS TERRITORIALES
        # =================================================================
        st.markdown("---")
        st.markdown("#### Contexto Económico y Laboral del Territorio")
        
        col_cluster, col_sal_terr = st.columns(2)
        
        with col_cluster:
            st.markdown(f"##### Clúster Empresarial: {filtro_label}")
            
            if hay_cluster:
                st.success(f"**{n_empresas_cluster:,} empresas** en sectores relacionados")
                
                # Sectores CIIU relacionados
                if sectores_ciiu:
                    seccion_nombres = {
                        'A': 'Agropecuario', 'B': 'Minería', 'C': 'Manufactura',
                        'D': 'Energía', 'E': 'Agua/Saneamiento', 'F': 'Construcción',
                        'G': 'Comercio', 'H': 'Transporte', 'I': 'Hotelería/Turismo',
                        'J': 'TIC/Comunicaciones', 'K': 'Financiero', 'L': 'Inmobiliario',
                        'M': 'Profesionales', 'N': 'Administrativos', 'O': 'Gobierno',
                        'P': 'Educación', 'Q': 'Salud', 'R': 'Arte/Entretenimiento',
                        'S': 'Otros servicios', 'T': 'Hogares', 'U': 'Organismos Int.'
                    }
                    st.markdown("**Sectores CIIU relacionados:** " + ", ".join(
                        [f"{seccion_nombres.get(s, s)} ({s})" for s in sectores_ciiu[:5]]
                    ))
                
                if datos_cluster.get('top_sectores'):
                    df_top_sect = pd.DataFrame(datos_cluster['top_sectores'])
                    if not df_top_sect.empty:
                        fig_cluster = px.bar(
                            df_top_sect.head(5),
                            x='empresas', y='sector', orientation='h',
                            title="Top Sectores CIIU Relacionados",
                            color='empresas', color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                        )
                        fig_cluster.update_layout( showlegend=False, yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig_cluster, use_container_width=True)
                        descargar_datos_grafico(df_top_sect, "cluster_empresarial", "Descargar datos")
                
                st.caption(get_citacion("rues"))
            elif sel_nbc and arg_depto:
                st.warning("Bajo tejido empresarial del sector en el territorio")
                st.markdown("Considerar: migración laboral a otros dptos o modalidad virtual para ampliar alcance.")
            elif sel_nbc:
                st.info("Clúster empresarial disponible al seleccionar un departamento")
            else:
                st.info("Seleccione un NBC para analizar el clúster empresarial")
        
        with col_sal_terr:
            st.markdown(f"##### Referencia Salarial: {etiqueta_territorio}")
            
            if datos_sal_depto.get('tiene_datos'):
                smlv = 1_423_500
                sal_prom = datos_sal_depto['salario_promedio']
                sal_med = datos_sal_depto['salario_mediana']
                n_emps = datos_sal_depto['cantidad_empleados']
                
                col_s1, col_s2 = st.columns(2)
                col_s1.metric("Salario Promedio", f"${sal_prom:,.0f}" if sal_prom else "N/D")
                col_s2.metric("Salario Mediana", f"${sal_med:,.0f}" if sal_med else "N/D")
                
                if sal_med and smlv:
                    st.caption(f"Mediana = **{sal_med/smlv:.1f}x SMLV** (${smlv:,}). Muestra: {n_emps:,} empleados públicos (SIGEP).")
                
                # Salarios por nivel educativo
                df_sal_edu = datos_sal_depto.get('por_nivel_educativo', pd.DataFrame())
                if not df_sal_edu.empty:
                    fig_sal_edu = go.Figure()
                    fig_sal_edu.add_trace(go.Bar(
                        x=df_sal_edu['nivel_educativo'],
                        y=df_sal_edu['salario_promedio'],
                        name='Promedio', marker_color='#9b1b30',
                        text=[f"${v:,.0f}" for v in df_sal_edu['salario_promedio']],
                        textposition='auto'
                    ))
                    fig_sal_edu.add_trace(go.Bar(
                        x=df_sal_edu['nivel_educativo'],
                        y=df_sal_edu['salario_mediana'],
                        name='Mediana', marker_color='#6B9080',
                        text=[f"${v:,.0f}" for v in df_sal_edu['salario_mediana']],
                        textposition='auto'
                    ))
                    fig_sal_edu.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                         annotation_text=f"SMLV: ${smlv:,}")
                    fig_sal_edu.update_layout(
                        barmode='group', height=300,
                        title=f"Salarios por Nivel Educativo — {etiqueta_territorio}",
                        yaxis_title="Salario ($)"
                    )
                    st.plotly_chart(fig_sal_edu, use_container_width=True)
                    descargar_datos_grafico(df_sal_edu, "salarios_nivel_educativo_depto", "Descargar datos")
                
                st.caption(f"**Fuente:** {datos_sal_depto['fuente']}")
            else:
                st.warning(f"Sin datos salariales de referencia para {etiqueta_territorio}")
        
        # =================================================================
        # SÍNTESIS TERRITORIAL - SCORE INTEGRADO
        # =================================================================
        st.markdown("---")
        st.markdown("#### Síntesis de Pertinencia Territorial")
        
        # Calcular scores parciales basados en datos reales
        # Score 1: Indicadores educativos (TCB + TTI)
        score_educativo = 0
        if datos_edu_depto.get('tiene_datos'):
            tcb = datos_edu_depto.get('tcb_actual', 0) or 0
            tti = datos_edu_depto.get('tti_actual', 0) or 0
            score_educativo = min(100, (tcb / 55 * 50) + (tti / 50 * 50))  # Normalizado a promedios nacionales
        
        # Score 2: Oferta académica del NBC
        score_oferta = 0
        if not df_grad_depto.empty:
            grad_total = df_grad_depto['graduados'].sum()
            if grad_total > 5000: score_oferta = 100
            elif grad_total > 1000: score_oferta = 70
            elif grad_total > 100: score_oferta = 40
            else: score_oferta = 20
        
        # Score 3: Infraestructura digital
        score_conectividad = avg_conectividad * 100
        
        # Score 4: Contexto institucional (PDET + DNP) — solo departamental
        score_contexto = 0
        tiene_contexto = False
        if arg_depto:
            tiene_contexto = True
            if region_depto: score_contexto += 20
            if es_territorio_pdet: score_contexto += 30
            if en_plan_desarrollo and mdm_score and mdm_score >= 50: score_contexto += 50
            elif en_plan_desarrollo: score_contexto += 25
            score_contexto = min(score_contexto, 100)
        
        # Score 5: Cluster empresarial — solo departamental
        tiene_cluster = bool(arg_depto and sel_nbc)
        score_cluster = min(100, (n_empresas_cluster / 50) * 100) if n_empresas_cluster > 0 else (20 if tiene_cluster else 0)
        
        # Score territorial integrado (ponderado dinámicamente)
        # Si estamos a nivel nacional, redistribuir peso de contexto/cluster a los demás
        if arg_depto:
            # Departamental: todos los componentes
            score_territorial_total = (
                score_educativo * 0.25 +
                score_oferta * 0.20 +
                score_conectividad * 0.20 +
                score_contexto * 0.15 +
                score_cluster * 0.20
            )
        else:
            # Nacional: solo componentes disponibles (edu, oferta, conectividad)
            # Redistribuir 35% (contexto 15% + cluster 20%) proporcionalmente
            score_territorial_total = (
                score_educativo * 0.35 +
                score_oferta * 0.35 +
                score_conectividad * 0.30
            )
        
        col_sint1, col_sint2 = st.columns([2, 1])
        
        with col_sint1:
            # Tabla de síntesis — ajustar componentes según nivel
            if arg_depto:
                componentes = ['Indicadores Educativos (TCB/TTI)', 'Oferta Académica NBC',
                               'Infraestructura Digital', 'Contexto Institucional', 'Clúster Empresarial']
                scores = [round(score_educativo, 1), round(score_oferta, 1),
                          round(score_conectividad, 1), round(score_contexto, 1), round(score_cluster, 1)]
                pesos = ['25%', '20%', '20%', '15%', '20%']
            else:
                componentes = ['Indicadores Educativos (TCB/TTI)', 'Oferta Académica NBC',
                               'Infraestructura Digital']
                scores = [round(score_educativo, 1), round(score_oferta, 1), round(score_conectividad, 1)]
                pesos = ['35%', '35%', '30%']
            
            niveles = ['Alto' if s >= 70 else ('Medio' if s >= 40 else 'Bajo') for s in scores]
            
            sintesis_df = pd.DataFrame({
                'Componente': componentes,
                'Score': scores,
                'Peso': pesos,
                'Nivel': niveles
            })
            st.dataframe(sintesis_df, hide_index=True, use_container_width=True)
            descargar_datos_grafico(sintesis_df, "sintesis_territorial", "Descargar síntesis")
            
            # Justificación territorial basada en datos
            st.markdown("**Hallazgos territoriales:**")
            hallazgos = []
            if datos_edu_depto.get('tiene_datos'):
                tcb = datos_edu_depto.get('tcb_actual', 0) or 0
                tti = datos_edu_depto.get('tti_actual', 0) or 0
                if tcb < 40:
                    hallazgos.append(f"Baja cobertura ES ({tcb:.1f}%) — hay demanda potencial insatisfecha")
                elif tcb >= 50:
                    hallazgos.append(f"Cobertura ES adecuada ({tcb:.1f}%) — ecosistema educativo consolidado")
                if tti < 35:
                    hallazgos.append(f"Bajo tránsito inmediato ({tti:.1f}%) — programas técnicos pueden captar esta población")
            if not df_grad_depto.empty:
                grad_total = df_grad_depto['graduados'].sum()
                hallazgos.append(f"{int(grad_total):,} graduados acumulados del NBC en {etiqueta_territorio}")
            if es_territorio_pdet:
                hallazgos.append(f"Territorio PDET con {n_municipios_pdet} municipios priorizados")
            if hay_cluster:
                hallazgos.append(f"Clúster empresarial con {n_empresas_cluster:,} empresas del sector")
            if avg_conectividad > 0.6:
                hallazgos.append("Conectividad digital adecuada para educación virtual")
            elif avg_conectividad < 0.3:
                hallazgos.append("Baja conectividad — priorizar modalidad presencial o centros de acceso")
            
            if hallazgos:
                for h in hallazgos:
                    st.markdown(f"- {h}")
            else:
                st.markdown("_Seleccione filtros territoriales para generar hallazgos_")
            
            st.markdown(f"**Modalidad recomendada:** {modalidad_recomendada}")
        
        with col_sint2:
            # Gauge final territorial
            fig_sint = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_territorial_total,
                title={'text': "SCORE TERRITORIAL", 'font': {'size': 14, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
                number={'font': {'size': 28, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#A09088'},
                    'bar': {'color': "#9B1B30"},
                    'steps': [
                        {'range': [0, 50], 'color': "#F0EAE4"},
                        {'range': [50, 75], 'color': "#E5DDD6"},
                        {'range': [75, 100], 'color': "#F9F7F4"}
                    ],
                },
                domain={'x': [0.05, 0.95], 'y': [0.08, 0.92]}
            ))
            fig_sint.update_layout( margin=dict(l=10, r=10, t=45, b=0))
            st.plotly_chart(fig_sint, use_container_width=True)
            
            if score_territorial_total >= 75:
                st.success("Alta pertinencia territorial")
            elif score_territorial_total >= 50:
                st.warning("Pertinencia territorial media")
            else:
                st.warning("Baja pertinencia territorial")

    # =========================================================================
    # TAB 4: DECISIÓN FINAL
    # =========================================================================
    with tab_decision:
        section_header("04", "Decision Final: Score de Pertinencia", "Score = (Acad x 0.30) + (Lab x 0.40) + (Terr x 0.20) + (Glob x 0.10)")
        
        # =================================================================
        # SAFE DEFAULTS — variables de tabs anteriores que podrían faltar
        # =================================================================
        try:
            _ = df_vacantes
        except NameError:
            df_vacantes = pd.DataFrame()
        try:
            _ = df_conocimientos
        except NameError:
            df_conocimientos = pd.DataFrame()
        try:
            _ = df_destrezas
        except NameError:
            df_destrezas = pd.DataFrame()
        try:
            _ = datos_salarios
        except NameError:
            datos_salarios = {}
        try:
            _ = df_actividades
        except NameError:
            df_actividades = pd.DataFrame()
        try:
            _ = stats_originales
        except NameError:
            stats_originales = {}
        
        # Obtener datos globales reales
        df_global_decision = get_indicadores_globales()
        # Usar función filtrada por NBC para habilidades del futuro
        df_habilidades_decision = get_habilidades_futuro_filtradas(sel_nbc)
        
        # =================================================================
        # SCORE ACADÉMICO (30%): Concentración de mercado + Crecimiento
        # =================================================================
        _hhi = float(hhi) if hhi and hhi > 0 else 1000.0  # default moderado
        _cagr = float(cagr) if cagr is not None else 0.0
        # HHI: mercado competitivo (<1500) = bueno, concentrado (>2500) = riesgo
        hhi_score = max(0, min(100, 100 - (_hhi / 40)))  # 100@0, 0@4000
        # CAGR: crecimiento enriquece, declive penaliza
        cagr_score = max(0, min(100, 50 + _cagr * 10))   # 50 base, +/-10 por pto%
        score_acad = round(hhi_score * 0.60 + cagr_score * 0.40, 1)
        
        # =================================================================
        # SCORE LABORAL (40%): Vacantes + Absorción + Salarios + Competencias
        # Multi-componente para evitar sesgo por ratio simple en NBCs masivos
        # =================================================================
        smlv_decision = 1_423_500
        
        # C1: Volumen de vacantes (señal de mercado activo)
        _vacantes_real = 0
        _ratio_real = 0.0
        if not df_vacantes.empty and 'vacantes_2024' in df_vacantes.columns:
            _vacantes_real = int(df_vacantes['vacantes_2024'].sum())
            _ratio_real, _ = calcular_ratio_absorcion(graduados_anual, _vacantes_real)
        else:
            _ratio_real = ratio_abs if ratio_abs else 0.0
        
        if _vacantes_real > 50000:   comp_volumen = 100
        elif _vacantes_real > 20000: comp_volumen = 80
        elif _vacantes_real > 5000:  comp_volumen = 60
        elif _vacantes_real > 1000:  comp_volumen = 40
        elif _vacantes_real > 100:   comp_volumen = 20
        else:                        comp_volumen = 5
        
        # C2: Ratio absorción ajustado (SPE capta ~30-40% del mercado real)
        _ratio_ajust = min(2.0, _ratio_real * 3)  # corregir sub-reporte SPE
        comp_absorcion = min(100, _ratio_ajust * 50)
        
        # C3: Señal salarial — salarios altos indican que el mercado valora la formación
        comp_salario = 50  # neutral por defecto
        if datos_salarios and datos_salarios.get('tiene_datos'):
            _df_sigep_d = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame())
            if not _df_sigep_d.empty and 'salario_mediana' in _df_sigep_d.columns:
                _sal_med = _df_sigep_d['salario_mediana'].mean()
                if _sal_med and _sal_med > 0:
                    comp_salario = min(100, (_sal_med / smlv_decision / 3) * 100)
            else:
                _df_ole = datos_salarios.get('ole_ibc', pd.DataFrame())
                if not _df_ole.empty and 'ibc_min_smmlv' in _df_ole.columns:
                    _ibc_avg = _df_ole['ibc_min_smmlv'].mean()
                    if _ibc_avg and _ibc_avg > 0:
                        comp_salario = min(100, (_ibc_avg / 3) * 100)
        
        # C4: Demanda de competencias (más competencias CUOC = mercado más definido)
        _n_comp_dec = (len(df_conocimientos) + len(df_destrezas)) if not df_conocimientos.empty else 0
        comp_skills = min(100, _n_comp_dec * 5)  # 20 competencias = 100
        
        score_lab = round(
            comp_volumen * 0.30 +
            comp_absorcion * 0.20 +
            comp_salario * 0.25 +
            comp_skills * 0.25,
            1
        )
        
        # Bonus por alineación SNIES↔SIET (si disponible)
        if skills_bridge and skills_bridge.get('has_data'):
            alignment = skills_bridge.get('alignment_score_global', 0)
            complementarity = skills_bridge.get('complementarity_siet', 0)
            alignment_bonus = max(0, (alignment - 0.15) * 15)  # 0-13 pts
            complementarity_bonus = max(0, (complementarity - 0.1) * 8)  # 0-7 pts
            score_lab = min(100, round(score_lab + alignment_bonus + complementarity_bonus, 1))
        
        # =================================================================
        # SCORE TERRITORIAL (20%): Reusa cálculo de Tab 3
        # =================================================================
        try:
            score_terr = score_territorial_total
        except NameError:
            try:
                avg_con = df_conectividad['indice_conectividad'].mean() if not df_conectividad.empty else 0.5
                score_terr = avg_con * 100
            except NameError:
                score_terr = 50  # neutral
        score_terr = round(float(score_terr), 1)
        
        # =================================================================
        # SCORE GLOBAL (10%): Desempleo juvenil Colombia
        # =================================================================
        if not df_global_decision.empty and 'desempleo_jovenes' in df_global_decision.columns:
            desempleo_actual = df_global_decision.iloc[0]['desempleo_jovenes']
            score_glob = max(20, min(90, 100 - desempleo_actual * 2))
        else:
            score_glob = 50  # neutral, no asumir optimismo
        
        score_final, veredicto, color = calcular_score_final(score_acad, score_lab, score_terr, score_glob)
        
        g1, g2, g3, g4 = st.columns(4)
        
        with g1:
            st.plotly_chart(crear_gauge(score_acad, "Académico (30%)"), use_container_width=True)
        with g2:
            st.plotly_chart(crear_gauge(score_lab, "Laboral (40%)"), use_container_width=True)
        with g3:
            st.plotly_chart(crear_gauge(score_terr, "Territorial (20%)"), use_container_width=True)
        with g4:
            st.plotly_chart(crear_gauge(score_glob, "Global (10%)"), use_container_width=True)
        
        st.caption("Pesos de la decision final: Academica 30% | Laboral 40% | Territorial 20% | Global 10%. El score laboral tiene mayor peso por reflejar empleabilidad real.")
        
        insight_card("chart-simple", "Desglose del score",
            f"Academico: {score_acad:.0f}/100 | Laboral: {score_lab:.0f}/100 | Territorial: {score_terr:.0f}/100 | Global: {score_glob:.0f}/100",
            tone="insight")
        
        st.divider()
        
        col_score, col_veredicto = st.columns([1, 2])
        
        with col_score:
            st.markdown("### Score Final")
            fig_final = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_final,
                title={'text': "SCORE DE PERTINENCIA", 'font': {'size': 16, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
                number={'font': {'size': 34, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#A09088'},
                    'bar': {'color': "#9b1b30"},
                    'steps': [
                        {'range': [0, 50], 'color': "#F0EAE4"},
                        {'range': [50, 80], 'color': "#e0cd9e"},
                        {'range': [80, 100], 'color': "#F0EAE4"}
                    ],
                },
                domain={'x': [0.05, 0.95], 'y': [0.08, 0.92]}
            ))
            fig_final.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=45, b=0),
                paper_bgcolor="#FFFFFF",
                font_family="Inter, sans-serif",
                font_color="#0B0F19"
            )
            st.plotly_chart(fig_final, use_container_width=True)
        
        with col_veredicto:
            st.markdown("### Veredicto")
            
            if color == "green":
                st.markdown(f"""
                <div class="score-green">
                    <h2><i class="fas fa-check-circle veredicto-ok"></i> {veredicto}</h2>
                </div>
                """, unsafe_allow_html=True)
            elif color == "yellow":
                st.markdown(f"""
                <div class="score-yellow">
                    <h2><i class="fas fa-exclamation-triangle veredicto-warn"></i> {veredicto}</h2>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="score-red">
                    <h2><i class="fas fa-times-circle veredicto-err"></i> {veredicto}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("**Desglose del Score:**")
            desglose_score = pd.DataFrame({
                'Síntesis': ['Académica', 'Laboral', 'Territorial', 'Global'],
                'Score': [round(score_acad, 1), round(score_lab, 1), round(score_terr, 1), round(score_glob, 1)],
                'Peso': ['30%', '40%', '20%', '10%'],
                'Aporte': [round(score_acad*0.3, 1), round(score_lab*0.4, 1), round(score_terr*0.2, 1), round(score_glob*0.1, 1)]
            })
            st.dataframe(desglose_score, hide_index=True, use_container_width=True)
            descargar_datos_grafico(desglose_score, "desglose_score_pertinencia", "Descargar desglose")
            
            # Nota sobre integración SNIES↔SIET en score laboral
            if skills_bridge and skills_bridge.get('has_data'):
                _align = skills_bridge.get('alignment_score_global', 0)
                _compl = skills_bridge.get('complementarity_siet', 0)
                st.caption(f"El score laboral incluye bonus por alineación SNIES↔SIET ({_align:.0%}) "
                          f"y complementariedad ETDH ({_compl:.0%}) via cadena estructural CUOC.")
        
        # =====================================================================
        # TIPO DE OFERTA RECOMENDADA (Lógica de negocio basada en scores)
        # =====================================================================
        st.markdown("---")
        st.markdown('<h3 class="icon-header"><i class="fas fa-signs-post"></i> Tipo de Oferta Recomendada</h3>', unsafe_allow_html=True)
        st.caption("Recomendación basada en la combinación de las 4 síntesis evaluativas")
        
        # Calcular número de competencias identificadas (proxy de brechas)
        n_competencias = (len(df_conocimientos) + len(df_destrezas)) if not df_conocimientos.empty else 0
        
        # Obtener tipo de oferta recomendada
        tipo_oferta, justificacion_oferta, icono_oferta = determinar_tipo_oferta(
            score_acad, score_lab, score_terr, n_competencias
        )
        
        # Mapeo de colores por tipo de oferta
        color_tipo = {
            "PROGRAMA_COMPLETO": "#6B9080",      # Verde
            "RUTA_FORMATIVA": "#d4835a",          # Azul
            "MICROCREDENCIAL": "#cc8800",         # Púrpura
            "EDUCACION_CONTINUA": "#d97706",      # Amarillo
            "EVALUAR_VIABILIDAD": "#52423C",      # Gris
            "NO_RECOMENDADO": "#9b1b30"           # Rojo
        }
        
        # Descripción extendida de cada tipo
        descripcion_tipos = {
            "PROGRAMA_COMPLETO": "Programa formal de educación superior (pregrado, especialización, maestría o doctorado) con registro calificado.",
            "RUTA_FORMATIVA": "Secuencia articulada de diplomados, cursos de extensión o certificaciones que construyen competencias progresivamente.",
            "MICROCREDENCIAL": "Certificaciones cortas y específicas orientadas a competencias puntuales demandadas por el mercado laboral.",
            "EDUCACION_CONTINUA": "Actualización permanente para profesionales ya vinculados laboralmente. Énfasis en upskilling y reskilling.",
            "EVALUAR_VIABILIDAD": "Se requiere un análisis más profundo antes de definir el tipo de oferta más adecuado.",
            "NO_RECOMENDADO": "Los indicadores sugieren que la oferta no sería viable en las condiciones actuales."
        }
        
        col_tipo, col_just = st.columns([1, 2])
        
        with col_tipo:
            color_actual = color_tipo.get(tipo_oferta, "#52423C")
            st.markdown(f"""
            <div class="rec-card" style="--rec-bg: {color_actual}10; --rec-accent: {color_actual};">
                <h4 class="rec-title">
                    <i class="fas fa-{icono_oferta}"></i> {tipo_oferta.replace('_', ' ')}
                </h4>
                <p class="rec-text">
                    {descripcion_tipos.get(tipo_oferta, '')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_just:
            st.markdown("**Justificación de la recomendación:**")
            st.info(justificacion_oferta)
            
            # Mostrar indicadores clave que influyeron en la decisión
            st.markdown("**Indicadores considerados:**")
            
            _etdh_progs = etdh_ml_stats.get('programas_siet_relacionados', 0) if etdh_ml_stats and etdh_ml_stats.get('tiene_datos') else 0
            _bridge_align = f"{skills_bridge.get('alignment_score_global', 0):.0%}" if skills_bridge and skills_bridge.get('has_data') else 'N/A'
            
            indicadores_md = f"""
            | Indicador | Valor | Interpretación |
            |-----------|-------|----------------|
            | HHI (concentración) | {_hhi:,.0f} | {'Competitivo' if _hhi < 1500 else 'Moderado' if _hhi < 2500 else 'Concentrado'} |
            | CAGR matrícula | {_cagr:+.1f}% | {'Crecimiento' if _cagr > 2 else 'Estable' if _cagr > -1 else 'Declive'} |
            | Vacantes SPE | {_vacantes_real:,} | {'Alto volumen' if _vacantes_real > 20000 else 'Moderado' if _vacantes_real > 5000 else 'Bajo'} |
            | Ratio absorción (×3 ajust.) | {_ratio_ajust:.2f} | {'Favorable' if _ratio_ajust > 1 else 'Equilibrado' if _ratio_ajust > 0.5 else 'Competido'} |
            | Competencias CUOC | {_n_comp_dec} | {'Múltiples' if _n_comp_dec > 8 else 'Moderadas' if _n_comp_dec > 4 else 'Pocas'} |
            | Score Territorial | {score_terr:.0f}/100 | {'Favorable' if score_terr >= 60 else 'Moderado' if score_terr >= 40 else 'Limitado'} |
            | Alineación SNIES↔SIET | {_bridge_align} | {'Alta' if _bridge_align != 'N/A' and skills_bridge and skills_bridge.get('alignment_score_global', 0) > 0.3 else 'Media' if _bridge_align != 'N/A' and skills_bridge and skills_bridge.get('alignment_score_global', 0) > 0.15 else 'Baja o N/A'} |
            | Programas ETDH afines | {_etdh_progs} | {'Complemento fuerte' if _etdh_progs > 10 else 'Complemento moderado' if _etdh_progs > 3 else 'Sin complemento'} |
            """
            st.markdown(indicadores_md)
        
        # === SECCIÓN DE CONTEXTO GLOBAL ===
        st.markdown("---")
        st.markdown("### Contexto Global y Tendencias")
        st.caption("Información macroeconómica de Colombia y tendencias globales filtradas por relevancia para el programa")
        
        col_bm, col_hab = st.columns(2)
        
        with col_bm:
            st.markdown("#### Indicadores Banco Mundial (Colombia)")
            st.markdown("<i class='fas fa-chart-line' style='margin-right:0.3rem'></i> Contexto macroeconómico país - No varía por programa", unsafe_allow_html=True)
            if not df_global_decision.empty:
                fig_desempleo = px.line(
                    df_global_decision, x='anio', y='desempleo_jovenes',
                    title="Desempleo Juvenil (15-24 años)",
                    markers=True
                )
                fig_desempleo.update_layout( yaxis_title="% Desempleo")
                st.plotly_chart(fig_desempleo, use_container_width=True)
                descargar_datos_grafico(df_global_decision, "desempleo_juvenil_colombia", "Descargar datos")
                
                ultimo_dato = df_global_decision.iloc[0]
                st.metric(
                    f"Desempleo Juvenil {int(ultimo_dato['anio'])}",
                    f"{ultimo_dato['desempleo_jovenes']:.1f}%"
                )
            else:
                st.warning("Sin datos de indicadores globales disponibles")
        
        with col_hab:
            st.markdown(f"#### Destrezas Laborales para {filtro_label}")
            st.markdown("<i class='fas fa-bullseye' style='margin-right:0.3rem'></i> Basadas en ocupaciones CUOC filtradas por relevancia (ML)", unsafe_allow_html=True)
            
            # Obtener destrezas CUOC (combinar si multi-NBC)
            if len(sel_nbcs) > 1:
                _dfs_dest = [get_destrezas_cuoc_nbc(n) for n in sel_nbcs[:5]]
                _dfs_dest = [d for d in _dfs_dest if not d.empty]
                df_destrezas_cuoc = pd.concat(_dfs_dest, ignore_index=True).drop_duplicates(subset=['destreza']).head(20) if _dfs_dest else pd.DataFrame()
            else:
                df_destrezas_cuoc = get_destrezas_cuoc_nbc(sel_nbc)
            
            if not df_destrezas_cuoc.empty:
                df_top = df_destrezas_cuoc.head(10).copy()
                fig_hab = px.bar(
                    df_top,
                    x='relevancia',
                    y='destreza',
                    orientation='h',
                    title=f"Destrezas Relevantes para {filtro_label[:30]}...",
                    color='relevancia',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                    labels={'relevancia': 'Relevancia (%)', 'destreza': 'Destreza', 'n_ocupaciones': 'Ocupaciones'}
                )
                fig_hab.update_layout( yaxis={'categoryorder': 'total ascending'})
                fig_hab.update_traces(
                    hovertemplate='<b>%{y}</b><br>Relevancia: %{x:.0f}%<extra></extra>'
                )
                st.plotly_chart(fig_hab, use_container_width=True)
                descargar_datos_grafico(df_top, "destrezas_cuoc_nbc", "Descargar datos")
                
                # Mostrar nota metodológica
                with st.expander("Metodología CUOC", expanded=False, icon=":material/info:"):
                    st.markdown(f"""
                    **Destrezas extraídas de ocupaciones CUOC reales para {filtro_label}**
                    
                    1. Se obtienen las ocupaciones asociadas al NBC desde el mapeo oficial NBC→CUOC
                    2. Se filtran las **top 20 ocupaciones más relevantes** usando similitud semántica (ML)
                    3. Se extraen las destrezas de esas ocupaciones filtradas
                    4. **Relevancia** = % de ocupaciones filtradas que requieren esta destreza
                    
                    *Fuente: CUOC - Clasificación Única de Ocupaciones Colombia (DANE)*
                    """)
                    
                    # Mostrar conocimientos complementarios (multi-NBC si aplica)
                    if len(sel_nbcs) > 1:
                        _dfs_conoc = [get_conocimientos_cuoc_nbc(n) for n in sel_nbcs[:5]]
                        _dfs_conoc = [d for d in _dfs_conoc if not d.empty]
                        df_conocimientos_cuoc = pd.concat(_dfs_conoc, ignore_index=True).drop_duplicates(subset=['conocimiento']).head(20) if _dfs_conoc else pd.DataFrame()
                    else:
                        df_conocimientos_cuoc = get_conocimientos_cuoc_nbc(sel_nbc)
                    if not df_conocimientos_cuoc.empty:
                        st.markdown("**Conocimientos asociados (Top 8):**")
                        for _, row in df_conocimientos_cuoc.head(8).iterrows():
                            st.markdown(f"- {row['conocimiento']} ({row['relevancia']:.0f}%)")
            else:
                # Fallback a habilidades genéricas si CUOC falla
                if not df_habilidades_decision.empty:
                    fig_hab = px.bar(
                        df_habilidades_decision.head(8),
                        x='demanda_2024_score',
                        y='habilidad',
                        orientation='h',
                        title="Top Habilidades por Demanda Global (Fallback)",
                        color='crecimiento_anual_pct',
                        color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                    )
                    fig_hab.update_layout( yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_hab, use_container_width=True)
                else:
                    st.warning("Sin datos de destrezas disponibles para este NBC")
        
        # =====================================================================
        # SECCIÓN ESCO - Tendencias Globales de Habilidades Demandadas
        # Fuente: ESCO v1.2.0 (European Commission) — 13,939 skills
        # =====================================================================
        st.markdown("---")
        st.markdown("### Tendencias Globales de Habilidades Demandadas (ESCO)")
        _esco_sector_label = ', '.join(sel_areas[:2]) if sel_areas else filtro_label
        st.markdown(f"<i class='fas fa-globe' style='margin-right:0.3rem'></i> Habilidades más demandadas a nivel global según la taxonomía europea ESCO, filtradas por: **{html.escape(_esco_sector_label)}**", unsafe_allow_html=True)
        
        try:
            df_esco_top, df_esco_all = get_habilidades_esco(sel_areas=sel_areas, top_n=15)
        except Exception:
            df_esco_top, df_esco_all = pd.DataFrame(), pd.DataFrame()
        
        if not df_esco_top.empty:
            fig_esco = px.bar(
                df_esco_top.sort_values('n_ocupaciones_total', ascending=True),
                x='n_ocupaciones_total',
                y='habilidad',
                orientation='h',
                title=f"Top 15 Habilidades Globales — {_esco_sector_label[:40]}",
                color='n_ocupaciones_total',
                color_continuous_scale=[[0, '#F0EAE4'], [0.3, '#C7A951'], [0.6, '#D97706'], [0.85, '#9B1B30'], [1, '#7A1525']],
                labels={
                    'n_ocupaciones_total': 'N° Ocupaciones Asociadas',
                    'habilidad': '',
                },
                hover_data={'tipo_skill': True, 'sector': True, 'categoria': True}
            )
            fig_esco.update_layout(
                height=480,
                yaxis={'categoryorder': 'total ascending'},
                coloraxis_colorbar_title="Ocupaciones"
            )
            fig_esco.update_traces(
                hovertemplate='<b>%{y}</b><br>Ocupaciones: %{x}<br>Tipo: %{customdata[0]}<br>Sector: %{customdata[1]}<br>Categoría: %{customdata[2]}<extra></extra>'
            )
            st.plotly_chart(fig_esco, use_container_width=True)
            
            # Métricas resumen
            _col_m1, _col_m2, _col_m3 = st.columns(3)
            with _col_m1:
                st.metric("Habilidades en sector", f"{len(df_esco_all):,}")
            with _col_m2:
                _avg_ocup = df_esco_all['n_ocupaciones_total'].mean() if not df_esco_all.empty else 0
                st.metric("Promedio ocupaciones/habilidad", f"{_avg_ocup:.1f}")
            with _col_m3:
                _top_skill = df_esco_top.iloc[0]['habilidad'] if len(df_esco_top) > 0 else "N/A"
                st.metric("Habilidad más demandada", _top_skill[:30])
            
            # Botón descargar TODAS las habilidades del sector
            if not df_esco_all.empty:
                _csv_esco = df_esco_all.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"Descargar todas las habilidades ESCO del sector ({len(df_esco_all):,} registros)",
                    data=_csv_esco,
                    file_name=f"habilidades_esco_{_esco_sector_label[:20].replace(' ', '_').replace(',', '')}.csv",
                    mime="text/csv",
                    key="download_esco_all"
                )
            
            with st.expander("Fuente y Metodología ESCO", expanded=False, icon=":material/info:"):
                st.markdown("""
                **Fuente:** [ESCO v1.2.0](https://esco.ec.europa.eu/) — European Skills, Competences, 
                Qualifications and Occupations (Comisión Europea).
                
                - Taxonomía oficial de **13,939 habilidades** clasificadas por la Comisión Europea.
                - **N° Ocupaciones Asociadas**: cantidad de ocupaciones europeas que requieren esta habilidad 
                  (como esencial u opcional), indicador de demanda transversal.
                - Las habilidades se cruzan con el **Área de Conocimiento SNIES** seleccionada mediante 
                  mapeo ISCED-F → SNIES (clasificación internacional de campos de educación).
                - Pilares ESCO: **S** (competencias/capacidades), **K** (conocimientos), **T** (transversales), **L** (lingüísticas).
                
                *Los datos reflejan demanda estructural europea; aplicabilidad a Colombia es referencial.*
                """)
        else:
            st.info("No se encontraron habilidades ESCO para los filtros seleccionados.")
        
        # =====================================================================
        # SECCIÓN SIET COMPLEMENTARIA (dentro del análisis principal)
        # Usa effective_areas_siet (derivado de filtros SNIES vía ML/mapeo)
        # =====================================================================
        if tiene_filtros_siet:
            st.markdown("---")
            st.markdown('<h4 class="icon-header"><i class="fas fa-tools"></i> Contexto SIET / ETDH (Educación para el Trabajo)</h4>', unsafe_allow_html=True)
            
            # Caption contextual según origen del filtro
            _safe_areas = [a for a in _ml_areas_siet if a is not None] if _ml_areas_siet else []
            if _safe_areas:
                if sel_nbcs:
                    st.caption(f"Filtrado por cadena NBC → SIET: **{', '.join(_safe_areas)}**")
                elif sel_campos_amplios:
                    st.caption(f"Filtrado por Campo Amplio → SIET: **{', '.join(_safe_areas)}**")
                elif sel_areas:
                    st.caption(f"Filtrado por Área Conocimiento → SIET: **{', '.join(_safe_areas)}**")
                else:
                    st.caption(f"Áreas SIET derivadas: **{', '.join(_safe_areas)}**")
            else:
                st.caption("Información complementaria de educación técnica no formal")
            
            # Obtener estadísticas SIET (con áreas efectivas derivadas de SNIES)
            stats_siet = get_estadisticas_siet(
                areas_desempeno=effective_areas_siet,
                deptos=effective_deptos_siet,
                estados=sel_estados_siet if sel_estados_siet else None,
                busqueda_nombre=busqueda_programa if busqueda_programa else None
            )
            
            # KPIs SIET en contexto
            col_siet_k1, col_siet_k2, col_siet_k3, col_siet_k4 = st.columns(4)
            col_siet_k1.metric("Programas ETDH", f"{stats_siet['total_programas']:,}")
            col_siet_k2.metric("Instituciones ETDH", f"{stats_siet['total_instituciones']:,}")
            col_siet_k3.metric("Duración Promedio", f"{stats_siet['duracion_promedio']:,} hrs")
            col_siet_k4.metric("Certificados 2023", f"{stats_siet['total_certificados']:,}")
            
            # Gráficos SIET (usa effective_areas_siet derivado de SNIES)
            desglose_siet = get_desglose_siet(effective_areas_siet, effective_deptos_siet, busqueda_programa, modalidades_siet=sel_modalidades_siet if sel_modalidades_siet else None, estados=sel_estados_siet if sel_estados_siet else None)
            
            with st.expander("Ver distribución detallada SIET", expanded=False):
                col_exp1, col_exp2 = st.columns(2)
                
                with col_exp1:
                    df_area_siet = desglose_siet.get('por_area', pd.DataFrame())
                    if not df_area_siet.empty:
                        fig_area_siet = px.pie(
                            df_area_siet,
                            values='programas',
                            names='area',
                            title="Programas por Área de Desempeño SIET",
                            hole=0.3
                        )
                        fig_area_siet.update_layout( legend=dict(font=dict(size=8)))
                        fig_area_siet.update_traces(textposition='inside', textinfo='percent')
                        st.plotly_chart(fig_area_siet, use_container_width=True)
                        descargar_datos_grafico(df_area_siet, "siet_areas_decision", "Datos")
                
                with col_exp2:
                    df_depto_siet = desglose_siet.get('por_depto', pd.DataFrame())
                    if not df_depto_siet.empty:
                        fig_depto_siet = px.bar(
                            df_depto_siet.head(10),
                            x='programas',
                            y='departamento',
                            orientation='h',
                            title="Top 10 Departamentos ETDH",
                            color='programas',
                            color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                        )
                        fig_depto_siet.update_layout( yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig_depto_siet, use_container_width=True)
                        descargar_datos_grafico(df_depto_siet, "siet_deptos_decision", "Datos")
            
            # =================================================================
            # ML MATCHING: Programas ETDH más relacionados al NBC
            # =================================================================
            if etdh_ml_stats and etdh_ml_stats.get('tiene_datos'):
                st.markdown("---")
                st.markdown('<h3 class="icon-header"><i class="fas fa-link"></i> Programas ETDH Relacionados (Matching Inteligente)</h3>', unsafe_allow_html=True)
                st.caption(f"Programas de Educación para el Trabajo más afines a **{filtro_label}** identificados por similitud semántica + puente estructural")
                
                # KPIs de matching
                col_ml1, col_ml2, col_ml3, col_ml4 = st.columns(4)
                col_ml1.metric("Programas ETDH Afines", f"{etdh_ml_stats['programas_siet_relacionados']}")
                col_ml2.metric("Matrícula ETDH 2023", f"{etdh_ml_stats['matricula_siet']:,}")
                col_ml3.metric("Certificados 2023", f"{etdh_ml_stats['certificados_siet']:,}")
                areas_txt = ', '.join([a for a in etdh_ml_stats.get('areas_desempeno', []) if a is not None][:3])
                col_ml4.metric("Áreas SIET", areas_txt if areas_txt else "—")
                
                # Tabla de top programas
                top_progs = etdh_ml_stats.get('top_programas', [])
                if top_progs:
                    with st.expander("Ver programas ETDH más afines", expanded=True):
                        # Build display table
                        rows = []
                        for p in top_progs:
                            relevancia = "Alta" if p['score'] >= 0.6 else "Media" if p['score'] >= 0.45 else "Baja"
                            rows.append({
                                'Programa ETDH': p['nombre'],
                                'Área Desempeño': p['area'],
                                'Relevancia': relevancia,
                                'Similitud': f"{p['score']:.1%}",
                                'Matrícula 2023': f"{p['matricula']:,}" if p['matricula'] else "—",
                                'Certificados': f"{p['certificados']:,}" if p['certificados'] else "—",
                            })
                        df_ml_display = pd.DataFrame(rows)
                        st.dataframe(df_ml_display, use_container_width=True, hide_index=True)
                        
                        # Insight contextual
                        n_alta = sum(1 for p in top_progs if p['score'] >= 0.6)
                        n_media = sum(1 for p in top_progs if 0.45 <= p['score'] < 0.6)
                        mat_total = etdh_ml_stats['matricula_siet']
                        
                        if n_alta >= 3:
                            st.success(f"""
                            **Alta complementariedad SNIES↔ETDH:** Se encontraron **{n_alta} programas ETDH** altamente 
                            afines a {filtro_label}, con matrícula combinada de **{mat_total:,}** estudiantes en 2023. 
                            Esto indica una ruta formativa ETDH→Educación Superior bien articulada.
                            """)
                        elif n_alta >= 1 or n_media >= 3:
                            st.info(f"""
                            **Complementariedad moderada:** Se identificaron programas ETDH relacionados a {filtro_label} 
                            con matrícula de **{mat_total:,}** estudiantes. La formación técnica laboral cubre 
                            nichos complementarios a la educación superior formal.
                            """)
                        else:
                            st.warning(f"""
                            **Baja complementariedad directa:** Pocos programas ETDH tienen relación directa con 
                            {filtro_label}. Esto puede indicar un nicho no cubierto por la educación para el trabajo, 
                            o que la formación en este campo es predominantemente universitaria.
                            """)
            
            # =================================================================
            # GRÁFICOS COMPARATIVOS SNIES vs SIET
            # =================================================================
            st.markdown("---")
            st.markdown("### Comparativa SNIES vs SIET: Oferta Educativa Complementaria")
            st.caption("Análisis de complementariedad entre educación superior formal (SNIES) y educación para el trabajo (SIET/ETDH)")
            
            col_comp1, col_comp2 = st.columns([3, 2])
            
            with col_comp1:
                # Gráfico comparativo por departamento
                df_comp_depto = get_comparativa_snies_siet_por_depto(filtros=filtros_seleccionados, areas_desempeno_siet=effective_areas_siet)
                if not df_comp_depto.empty:
                    # Preparar datos para gráfico agrupado
                    df_melt = df_comp_depto.melt(
                        id_vars=['departamento'],
                        value_vars=['programas_snies', 'programas_siet'],
                        var_name='fuente',
                        value_name='programas'
                    )
                    df_melt['fuente'] = df_melt['fuente'].map({
                        'programas_snies': 'SNIES (Edu. Superior)',
                        'programas_siet': 'SIET (ETDH)'
                    })
                    
                    fig_comp = px.bar(
                        df_melt,
                        x='programas',
                        y='departamento',
                        color='fuente',
                        orientation='h',
                        title="Programas por Departamento: SNIES vs SIET",
                        barmode='group',
                        color_discrete_map={
                            'SNIES (Edu. Superior)': '#d4835a',
                            'SIET (ETDH)': '#6B9080'
                        }
                    )
                    fig_comp.update_layout(
                        height=400,
                        yaxis={'categoryorder': 'total ascending'},
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)
                    descargar_datos_grafico(df_comp_depto, "comparativa_snies_siet_depto", "Descargar datos")
                else:
                    st.info("Sin datos comparativos disponibles")
            
            with col_comp2:
                # Gráfico de tipos de formación
                df_tipos = get_comparativa_tipo_formacion(filtros=filtros_seleccionados, areas_desempeno_siet=effective_areas_siet)
                if not df_tipos.empty:
                    fig_tipos = px.treemap(
                        df_tipos,
                        path=['fuente', 'tipo_formacion'],
                        values='programas',
                        title="Distribución por Tipo de Formación",
                        color='fuente',
                        color_discrete_map={
                            'SNIES (Edu. Superior)': '#d4835a',
                            'SIET (ETDH)': '#6B9080'
                        }
                    )
                    fig_tipos.update_layout(
                        height=400,
                        margin=dict(l=10, r=10, t=50, b=30),
                        paper_bgcolor="#FFFFFF",
                        font_color="#0B0F19"
                    )
                    st.plotly_chart(fig_tipos, use_container_width=True)
                    descargar_datos_grafico(df_tipos, "comparativa_tipo_formacion", "Descargar datos")
                else:
                    st.info("Sin datos de tipos de formacion disponibles")
            
            # =====================================================================
            # BOTON DE ANALISIS CON LLM
            # =====================================================================
        
        st.markdown("---")
        st.markdown("### Analisis Inteligente con IA")
        st.caption("Genera un analisis de pertinencia usando inteligencia artificial (Gemini)")
        
        # Campo de instrucciones adicionales del usuario
        instrucciones_usuario = st.text_area(
            "Instrucciones adicionales (opcional)",
            placeholder="Ej: Profundiza en microcredenciales para IA, enfocate en el sector fintech, compara con tendencias en Chile y Mexico, explica mas sobre empleabilidad en startups...",
            height=80,
            help="Agrega indicaciones especificas para enfocar o expandir el analisis. El modelo mantendra su estructura base."
        )
        
        col_btn, col_info = st.columns([1, 2])
        
        with col_btn:
            analizar_btn = st.button(
                "Analizar con IA",
                type="primary",
                use_container_width=True,
                help="Genera un analisis completo usando el LLM de Gemini"
            )
        
        with col_info:
            st.caption("""
            El analisis incluye:
            - Sintesis ejecutiva del estado del campo
            - Oportunidades y riesgos identificados
            - Recomendacion de pertinencia
            - Conexion SNIES-SIET
            """)
        
        if analizar_btn:
            with loading_overlay("Generando análisis con IA..."):
                # Preparar estadísticas para el contexto usando stats_originales
                matriculados_ultimo = df_tendencia['matriculados'].iloc[-1] if not df_tendencia.empty else 0
                stats_snies_ctx = {
                    'total_programas': stats_originales.get('total_programas', 0),
                    'total_instituciones': stats_originales.get('total_ies', 0),
                    'hhi': round(hhi, 2) if hhi else 'N/A',
                    'cagr': round(cagr, 2) if cagr else 'N/A',
                    'graduados_anual': graduados_anual,
                    'matriculados': matriculados_ultimo
                }
                
                # Obtener stats SIET para contexto (reusar si existe)
                try:
                    stats_siet_ctx = stats_siet
                except NameError:
                    stats_siet_ctx = get_estadisticas_siet()
                
                # Obtener desglose SIET (reusar si existe)
                try:
                    desglose_siet_ctx = desglose_siet
                except NameError:
                    desglose_siet_ctx = get_desglose_siet()
                
                # =========================================================
                # OBTENER DATOS ADICIONALES PARA CONTEXTO ENRIQUECIDO
                # =========================================================
                
                # Reusar datos laborales del TAB 2 (ya calculados con multi-NBC)
                df_vacantes_ctx = df_vacantes
                df_conocimientos_ctx = df_conocimientos
                df_destrezas_ctx = df_destrezas
                # Salarios ahora es un dict con fuentes reales (OLE/SIGEP)
                df_salarios_ctx = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame()) if datos_salarios and datos_salarios.get('tiene_datos') else pd.DataFrame()
                
                # Reusar actividades ya calculadas
                df_actividades_ctx = df_actividades
                
                # Tipo de oferta recomendada
                # Reusar scores ya calculados en Tab 4 (score_acad, score_lab, score_terr)
                n_competencias_ctx = (len(df_conocimientos_ctx) + len(df_destrezas_ctx)) if not df_conocimientos_ctx.empty else 0
                
                tipo_oferta, justificacion, icono = determinar_tipo_oferta(
                    score_acad, score_lab, score_terr, n_competencias_ctx
                )
                tipo_oferta_ctx = {
                    'tipo': tipo_oferta,
                    'justificacion': justificacion,
                    'icono': icono
                }
                
                # Generar contexto ENRIQUECIDO con todos los datos disponibles
                contexto = generar_contexto_analisis(
                    nbc=nbc_display or sel_nbc,
                    depto=depto_display or arg_depto,
                    stats_snies=stats_snies_ctx,
                    stats_siet=stats_siet_ctx,
                    score_final=score_final,
                    veredicto=veredicto,
                    df_market=df_market,
                    df_tendencia=df_tendencia,
                    df_graduados=df_graduados,
                    desglose=desglose,
                    desglose_siet=desglose_siet_ctx,
                    hhi_data={'valor': hhi, 'interpretacion': hhi_interp},
                    cagr_data={'valor': cagr, 'interpretacion': cagr_interp},
                    # Nuevos datos laborales y de competencias
                    df_vacantes=df_vacantes_ctx,
                    df_conocimientos=df_conocimientos_ctx,
                    df_destrezas=df_destrezas_ctx,
                    df_salarios=df_salarios_ctx,
                    df_actividades=df_actividades_ctx,
                    tipo_oferta_data=tipo_oferta_ctx,
                    filtros_activos=filtros_seleccionados,
                    skills_bridge=skills_bridge
                )
                
                # Enriquecer contexto con ML matching SNIES↔ETDH
                if etdh_ml_stats and etdh_ml_stats.get('tiene_datos'):
                    ml_ctx = "\n\n## MATCHING INTELIGENTE SNIES↔ETDH\n"
                    ml_ctx += f"Programas ETDH afines a {nbc_display or sel_nbc}: {etdh_ml_stats['programas_siet_relacionados']}\n"
                    ml_ctx += f"Matrícula ETDH 2023 en programas afines: {etdh_ml_stats['matricula_siet']:,}\n"
                    ml_ctx += f"Certificados ETDH 2023: {etdh_ml_stats['certificados_siet']:,}\n"
                    ml_ctx += f"Áreas SIET relacionadas: {', '.join([a for a in etdh_ml_stats.get('areas_desempeno', []) if a])}\n"
                    top_progs = etdh_ml_stats.get('top_programas', [])[:5]
                    if top_progs:
                        ml_ctx += "Top programas ETDH más afines:\n"
                        for p in top_progs:
                            ml_ctx += f"  - {p['nombre']} (similitud: {p['score']:.1%}, matrícula: {p['matricula']:,})\n"
                    contexto += ml_ctx
                
                # Enriquecer con Skills Bridge Analysis (puente de competencias)
                if skills_bridge and skills_bridge.get('has_data'):
                    bridge_ctx = "\n\n## PUENTE DE COMPETENCIAS SNIES ↔ SIET/ETDH (vía CUOC)\n"
                    bridge_ctx += f"Alineación global de competencias: {skills_bridge.get('alignment_score_global', 0):.0%}\n"
                    bridge_ctx += f"Complementariedad SIET: {skills_bridge.get('complementarity_siet', 0):.0%}\n"
                    bridge_ctx += f"Conocimientos compartidos: {len(skills_bridge.get('shared_conocimientos', []))}\n"
                    bridge_ctx += f"Destrezas compartidas: {len(skills_bridge.get('shared_destrezas', []))}\n"
                    bridge_ctx += f"Ocupaciones CUOC vía SNIES: {len(skills_bridge.get('snies_ocupaciones', []))}\n"
                    bridge_ctx += f"Ocupaciones CUOC vía SIET: {len(skills_bridge.get('siet_ocupaciones', []))}\n"
                    if skills_bridge.get('ciiu_sectors'):
                        ciiu_list = [f"{s.get('seccion', '?')}: {s.get('nombre', '?')[:40]}" for s in skills_bridge['ciiu_sectors'][:5]]
                        bridge_ctx += f"Sectores CIIU relacionados: {', '.join(ciiu_list)}\n"
                    if skills_bridge.get('shared_conocimientos'):
                        bridge_ctx += f"Conocimientos en común SNIES-SIET: {', '.join(skills_bridge['shared_conocimientos'][:8])}\n"
                    if skills_bridge.get('shared_destrezas'):
                        bridge_ctx += f"Destrezas en común SNIES-SIET: {', '.join(skills_bridge['shared_destrezas'][:8])}\n"
                    contexto += bridge_ctx
                
                # Llamar al LLM con RAG enriquecido y instrucciones adicionales del usuario
                resultado_analisis = analizar_con_llm(
                    contexto, 
                    nbc_codigo=sel_nbc, 
                    departamento=arg_depto,
                    filtros_activos=filtros_seleccionados,
                    instrucciones_adicionales=instrucciones_usuario
                )
                
                # Mostrar resultado
                st.markdown("---")
                st.markdown("#### Informe de Pertinencia Educativa")
                st.markdown(resultado_analisis)
                
                # Boton de descarga en formato DOCX profesional
                st.markdown("---")
                col_dl1, col_dl2 = st.columns([1, 2])
                with col_dl1:
                    try:
                        docx_bytes = generar_reporte_docx(
                            contenido_markdown=resultado_analisis,
                            nbc=nbc_display or sel_nbc,
                            depto=depto_display or arg_depto or "Nacional"
                        )
                        nombre_archivo = f"informe_pertinencia_{(nbc_display or sel_nbc or 'analisis').replace(' ', '_')[:40]}.docx"
                        st.download_button(
                            label="Descargar Informe Word",
                            data=docx_bytes,
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            use_container_width=True,
                            icon=":material/download:"
                        )
                    except Exception as e_docx:
                        st.error(f"No se pudo generar el documento: {e_docx}")
                with col_dl2:
                    st.caption("Documento Word profesional con portada institucional, marca de agua, "
                              "encabezados, tabla de metricas, referencias APA y diseno editorial completo.")
                
                # Opcion para ver el contexto enviado
                with st.expander("Ver datos enviados al modelo", expanded=False):
                    st.code(contexto, language="markdown")
                    if instrucciones_usuario:
                        st.markdown("**Instrucciones adicionales del usuario:**")
                        st.info(instrucciones_usuario)

if __name__ == "__main__":
    main()

