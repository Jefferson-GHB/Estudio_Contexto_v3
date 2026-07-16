"""Constants and SQL normalization expressions.

Los catalogos (modalidades, sectores, niveles) se obtienen via SELECT DISTINCT de la base
de datos. La resolucion entre tablas con valores distintos se hace via subquery puente
por CODIGO_SNIES_DEL_PROGRAMA -> COD_SNIES_PROGRAMA.
"""

# Paleta de colores para graficos Plotly (usada por todos los tabs)
TEMPLATE_COLORS = ["#9B1B30", "#C7A951", "#6B9080", "#52423C", "#C5304A", "#D97706", "#0D9488", "#7C3AED"]

# SQL expression for sex normalization
SEXO_NORMALIZE_SQL = """CASE WHEN UPPER("SEXO") IN ('HOMBRE','MASCULINO','M') THEN 'MASCULINO' WHEN UPPER("SEXO") IN ('MUJER','FEMENINO','F') THEN 'FEMENINO' ELSE UPPER("SEXO") END"""
