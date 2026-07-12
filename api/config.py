"""
Configuración centralizada del Backend DSS v3.0
Todas las rutas y constantes se definen aquí.
"""
from pathlib import Path
import os

# ============================================================
# RUTAS BASE - Detección automática de entorno
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Detectar si estamos en HuggingFace Spaces (la BD esta en data/)
if (BASE_DIR / "data" / "repositorio.duckdb").exists():
    DUCKDB_PATH = BASE_DIR / "data" / "repositorio.duckdb"
elif (BASE_DIR / "repositorio.duckdb").exists():
    # Fallback: BD en raiz
    DUCKDB_PATH = BASE_DIR / "repositorio.duckdb"
elif (BASE_DIR / "DuckDB" / "repositorio.duckdb").exists():
    DUCKDB_PATH = BASE_DIR / "DuckDB" / "repositorio.duckdb"
elif (BASE_DIR / "DuckDB" / "repositorio_ligero.duckdb").exists():
    DUCKDB_PATH = BASE_DIR / "DuckDB" / "repositorio_ligero.duckdb"
else:
    # Fallback
    DUCKDB_PATH = BASE_DIR / "data" / "repositorio.duckdb"

# Catálogos — cargados desde DuckDB (catalogo_curado.*)
# El mapeo DSS (81 variables) está en catalogo_curado.mapeo_dss_variables

# ============================================================
# SCHEMAS POR PUNTO CRÍTICO
# ============================================================
# PUNTO 10: Tendencias Globales y LATAM
SCHEMAS_INTERNACIONALES = [
    'indicadores_globales',      # 22 indicadores Banco Mundial
    'oecd_internacional',        # 13 países OECD
    'ilo_internacional',         # OIT empleo global
    'unesco_internacional',      # UNESCO educación (12K+ registros)
    'banco_mundial_internacional',  # Consolidado global (30K registros)
    'tendencias_tecnologicas',   # IA, Industria 4.0, microcredenciales
]

# PUNTO 11: Tendencias Nacionales y Regionales
SCHEMAS_NACIONALES = [
    'snies',                     # 2.8M+ registros, 30,660 programas
    'tendencias_ocupacionales',  # 160 tablas, demanda laboral
    'dnp_planes_desarrollo',     # 2.9M+ registros planes desarrollo
    'estadisticas_es',           # Estadísticas ES consolidadas
    'dane',                      # ODS y demografía
    'divipola',                  # División territorial
    'territorial',               # PDET y zonas especiales
    'conectividad',              # Internet y acceso
    'siet',                      # ETDH programas técnicos
]

# PUNTO 12: Transformaciones Sectoriales CIIU
SCHEMAS_SECTORIALES = [
    'clasificadores',            # CIIU Rev4 (700 códigos)
    'economia',                  # RUES estructura empresarial (9.1M)
    'cuoc',                      # 14,462 ocupaciones
    'competencias',              # Mesas sectoriales, competencias
    'catalogo_curado',           # Mapeos NBC-CUOC-CIIU
]

# ============================================================
# CONSTANTES DSS
# ============================================================
EJES = {
    "EJE_1_PERTINENCIA_ACADEMICA": {
        "id": 1,
        "nombre": "Pertinencia Académica",
        "descripcion": "Evalúa la coherencia del programa con estándares educativos nacionales e internacionales",
        "dominios": ["D1_ACADEMICO_FORMATIVO", "D2_NORMATIVO_INSTITUCIONAL", "D3_OFERTA_COMPARADA"]
    },
    "EJE_2_PERTINENCIA_LABORAL": {
        "id": 2,
        "nombre": "Pertinencia Laboral",
        "descripcion": "Analiza la alineación con demandas del mercado laboral y competencias ocupacionales",
        "dominios": ["D4_OCUPACIONAL_LABORAL", "D5_COMPETENCIAS"]
    },
    "EJE_3_PERTINENCIA_TERRITORIAL": {
        "id": 3,
        "nombre": "Pertinencia Territorial",
        "descripcion": "Examina la relevancia regional, planes de desarrollo y contexto local",
        "dominios": ["D6_TERRITORIAL_ESTRATEGICO"]
    },
    "EJE_4_GLOBAL": {
        "id": 4,
        "nombre": "Global y Tendencias",
        "descripcion": "Analiza tendencias internacionales, brechas de talento y tecnología",
        "dominios": ["D7_GLOBAL"]
    },
    "EJE_5_DECISION_VIRTUAL": {
        "id": 5,
        "nombre": "Decisión Virtual",
        "descripcion": "Integra los análisis previos mediante IA para generar recomendaciones",
        "dominios": ["D8_DECISION_INTEGRADOR"]
    }
}

DOMINIOS = {
    "D1_ACADEMICO_FORMATIVO": {
        "id": 1,
        "nombre": "Académico Formativo",
        "eje": "EJE_1_PERTINENCIA_ACADEMICA",
        "descripcion": "Estructura curricular, NBC, niveles de formación y rutas formativas"
    },
    "D2_NORMATIVO_INSTITUCIONAL": {
        "id": 2,
        "nombre": "Normativo Institucional",
        "eje": "EJE_1_PERTINENCIA_ACADEMICA",
        "descripcion": "Registro calificado, acreditación y marco legal del programa"
    },
    "D3_OFERTA_COMPARADA": {
        "id": 3,
        "nombre": "Oferta Comparada",
        "eje": "EJE_1_PERTINENCIA_ACADEMICA",
        "descripcion": "Análisis comparativo con programas similares a nivel nacional e internacional"
    },
    "D4_OCUPACIONAL_LABORAL": {
        "id": 4,
        "nombre": "Ocupacional Laboral",
        "eje": "EJE_2_PERTINENCIA_LABORAL",
        "descripcion": "Ocupaciones CUOC, sectores CIIU y demanda laboral"
    },
    "D5_COMPETENCIAS": {
        "id": 5,
        "nombre": "Competencias",
        "eje": "EJE_2_PERTINENCIA_LABORAL",
        "descripcion": "Competencias técnicas, transversales y brechas identificadas"
    },
    "D6_TERRITORIAL_ESTRATEGICO": {
        "id": 6,
        "nombre": "Territorial Estratégico",
        "eje": "EJE_3_PERTINENCIA_TERRITORIAL",
        "descripcion": "Cobertura geográfica, planes de desarrollo y sectores priorizados"
    },
    "D7_GLOBAL": {
        "id": 7,
        "nombre": "Global y Tendencias",
        "eje": "EJE_4_GLOBAL",
        "descripcion": "Tendencias tecnológicas, referentes internacionales e indicadores globales"
    },
    "D8_DECISION_INTEGRADOR": {
        "id": 8,
        "nombre": "Decisión Integrador",
        "eje": "EJE_5_DECISION_VIRTUAL",
        "descripcion": "Síntesis de juicios por eje y recomendación final"
    }
}

# ============================================================
# ESTADOS DE VARIABLES
# ============================================================
ESTADO_DISPONIBLE = " DISPONIBLE"
ESTADO_PROXY = " PROXY"
ESTADO_PARCIAL = " PARCIAL"
ESTADO_LLM = " LLM"
ESTADO_CALC = " CALC"

ESTADOS_CONSULTABLES = [ESTADO_DISPONIBLE, ESTADO_PROXY, ESTADO_PARCIAL]
ESTADOS_GENERADOS = [ESTADO_LLM, ESTADO_CALC]

# ============================================================
# API CONFIG
# ============================================================
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# CORS
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8501",  # Streamlit
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8501",
]

# ============================================================
# VALIDACIÓN
# ============================================================
def validar_configuracion() -> dict:
    """Valida que todos los archivos y rutas necesarios existan."""
    errores = []
    warnings = []
    
    if not DUCKDB_PATH.exists():
        errores.append(f"DuckDB no encontrado: {DUCKDB_PATH}")
    
    return {
        "valido": len(errores) == 0,
        "errores": errores,
        "warnings": warnings,
        "paths": {
            "duckdb": str(DUCKDB_PATH),
            "base_dir": str(BASE_DIR)
        }
    }
