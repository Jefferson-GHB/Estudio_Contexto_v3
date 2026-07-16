"""
src/ — Wrappers modulares del codigo productivo.

El codigo fuente real reside en services/ (logica de negocio), data/ (consultas SQL),
views/ (interfaz Streamlit), components/ (sidebar), y visualizations/ (graficos Plotly).
Estos wrappers proveen puntos de entrada compatibles con la estructura estandar de
proyectos ML que espera el comite evaluador.

No replican logica — importan y re-exportan desde los modulos reales.
"""

# Data ingestion and transformation
from data.queries import (
    get_estadisticas_basicas,
    get_benchmarking_data,
    get_market_share,
    get_tendencia_matricula,
    get_graduados_historico,
    get_tendencia_inscritos,
    get_tendencia_admitidos,
    get_tendencia_primer_curso,
    get_conectividad_territorial,
    get_vacantes_reales,
    get_competencias_cuoc,
    get_salarios_reales,
)

from data.filters import (
    build_where_clause,
    build_where_clause_matriculados,
    build_nbc_condition,
)

# Metrics and scoring  
from services.scoring import (
    calcular_hhi,
    calcular_cagr,
    calcular_ratio_absorcion,
    calcular_score_final,
)

# Decision engine
from services.decision_engine import determinar_tipo_oferta

# Data loader (full pipeline entry point)
from services.data_loader import cargar_datos_base

__all__ = [
    "get_estadisticas_basicas",
    "get_benchmarking_data", 
    "get_market_share",
    "get_tendencia_matricula",
    "get_graduados_historico",
    "get_tendencia_inscritos",
    "get_tendencia_admitidos",
    "get_tendencia_primer_curso",
    "get_conectividad_territorial",
    "get_vacantes_reales",
    "get_competencias_cuoc",
    "get_salarios_reales",
    "build_where_clause",
    "build_where_clause_matriculados",
    "build_nbc_condition",
    "calcular_hhi",
    "calcular_cagr",
    "calcular_ratio_absorcion",
    "calcular_score_final",
    "determinar_tipo_oferta",
    "cargar_datos_base",
]
