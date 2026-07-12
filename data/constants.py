"""Constantes compartidas del data layer. Evita literales duplicados entre modulos."""

# Palabras vacias para extraccion de keywords desde nombres de NBC
# Usadas en queries de matching semantico y busqueda por palabras clave
STOPWORDS = {'afines', 'otros', 'otras', 'para', 'como', 'desde', 'hasta', 'entre', 'sobre', 'bajo', 'sin', 'y'}

# Prefijos comunes de programas SIET (normalizados, sin acentos)
# _strip_siet_prefix() normaliza el nombre antes de comparar contra estos
SIET_PREFIXES_NORM = [
    'TECNICO LABORAL POR COMPETENCIA EN ',
    'TECNICO LABORAL POR COMPETENCIAS EN ',
    'TECNICO LABORALPOR COMPETENCIAS EN ',
    'TECNICO LABORAL COMO ',
    'TECNICO LABORAL EN ',
    'TECNICO LABORAL ',
    'AUXILIAR EN ',
    'AUXILIAR DE ',
]

# Umbrales de similitud para matching semantico ML
ML_SIMILARITY = {
    'ocupaciones_structural': 0.20,    # NBC -> CUOC via cadena estructural
    'siet_programa_min': 0.25,         # Minimo para considerar match SIET
    'siet_fallback': 0.30,             # Fallback cuando skills-query falla
    'siet_principal': 0.35,            # Threshold principal SIET
    'siet_stats': 0.25,                # Threshold para get_siet_stats_for_nbc
    'programa_to_cuoc': 0.30,          # Programa SIET -> ocupacion CUOC
    'competencias_skills': 0.40,       # Conocimientos/destrezas skills profile
}

# Salario Minimo Legal Vigente Colombia 2026 (Decreto 1572/2025)
SMLV_2026 = 1_423_500
