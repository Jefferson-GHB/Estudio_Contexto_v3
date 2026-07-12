"""Business logic services — decision engines, scoring, context building."""

from .decision_engine import determinar_tipo_oferta
from .context_builder import generar_contexto_analisis
from .scoring import calcular_hhi, calcular_cagr, calcular_ratio_absorcion, calcular_score_final

__all__ = [
    "determinar_tipo_oferta",
    "generar_contexto_analisis",
    "calcular_hhi",
    "calcular_cagr",
    "calcular_ratio_absorcion",
    "calcular_score_final",
]
