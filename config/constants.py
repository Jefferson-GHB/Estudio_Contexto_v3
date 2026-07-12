"""Constants and SQL normalization expressions.

Los catalogos (modalidades, sectores, niveles) se obtienen via SELECT DISTINCT de la base
de datos. La resolucion entre tablas con valores distintos se hace via subquery puente
por CODIGO_SNIES_DEL_PROGRAMA -> COD_SNIES_PROGRAMA.
"""

# SQL expression for sex normalization
SEXO_NORMALIZE_SQL = """CASE WHEN UPPER("SEXO") IN ('HOMBRE','MASCULINO','M') THEN 'MASCULINO' WHEN UPPER("SEXO") IN ('MUJER','FEMENINO','F') THEN 'FEMENINO' ELSE UPPER("SEXO") END"""
