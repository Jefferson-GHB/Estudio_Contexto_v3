"""
DICCIONARIO DE FUENTES DE DATOS — Estudio Contexto
=====================================================
Centraliza todas las fuentes de datos con su información de citación.
Usar para mostrar en gráficos y asegurar transparencia al cliente.

Actualizado: 2026-01-20
"""

# ==============================================================================
# FUENTES DE DATOS CON METADATOS DE CITACIÓN
# ==============================================================================

FUENTES = {
    # -------------------------------------------------------------------------
    # EJE 1: PERTINENCIA ACADÉMICA
    # -------------------------------------------------------------------------
    "snies_programas": {
        "nombre": "SNIES - Programas Académicos",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2024",
        "actualizacion": "Corte Dic 2024",
        "citacion": "Fuente: SNIES - MEN (2024)"
    },
    "snies_graduados": {
        "nombre": "SNIES - Graduados Educación Superior",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2018-2024",
        "actualizacion": "Serie histórica a 2024",
        "citacion": "Fuente: SNIES - MEN (2018-2024)"
    },
    "snies_matriculados": {
        "nombre": "SNIES - Matriculados Educación Superior",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2019-2024",
        "actualizacion": "Serie histórica a 2024",
        "citacion": "Fuente: SNIES - MEN (2019-2024)"
    },
    "snies_inscritos": {
        "nombre": "SNIES - Inscritos Educación Superior",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2019-2024",
        "actualizacion": "Serie histórica a 2024",
        "citacion": "Fuente: SNIES - MEN (2019-2024)"
    },
    "snies_admitidos": {
        "nombre": "SNIES - Admitidos Educación Superior",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2019-2024",
        "actualizacion": "Serie histórica a 2024",
        "citacion": "Fuente: SNIES - MEN (2019-2024)"
    },
    "snies_matriculados_primer_curso": {
        "nombre": "SNIES - Matriculados Primer Curso",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2019-2024",
        "actualizacion": "Serie histórica a 2024",
        "citacion": "Fuente: SNIES - MEN (2019-2024)"
    },
    "snies_instituciones": {
        "nombre": "SNIES - Instituciones de Educación Superior",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://snies.mineducacion.gov.co/",
        "periodo": "2024",
        "actualizacion": "Corte Dic 2024",
        "citacion": "Fuente: SNIES - MEN (2024)"
    },
    "siet_programas": {
        "nombre": "SIET - Programas ETDH",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://siet.mineducacion.gov.co/",
        "periodo": "2024",
        "actualizacion": "Corte Dic 2024",
        "citacion": "Fuente: SIET - MEN (2024)"
    },
    "siet_instituciones": {
        "nombre": "SIET - Instituciones ETDH",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://siet.mineducacion.gov.co/",
        "periodo": "2024",
        "actualizacion": "Corte Dic 2024",
        "citacion": "Fuente: SIET - MEN (2024)"
    },
    
    # -------------------------------------------------------------------------
    # EJE 2: PERTINENCIA LABORAL
    # -------------------------------------------------------------------------
    "cuoc_2025": {
        "nombre": "CUOC - Clasificación Única de Ocupaciones",
        "entidad": "DANE / Mintrabajo",
        "url": "https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones/clasificacion-unica-de-ocupaciones-para-colombia-cuoc",
        "periodo": "2025",
        "actualizacion": "Versión vigente 2025",
        "citacion": "Fuente: CUOC - DANE (2025)"
    },
    "vacantes_ape": {
        "nombre": "Vacantes APE - Agencia Pública de Empleo",
        "entidad": "SENA - Observatorio Laboral",
        "url": "https://observatorio.sena.edu.co/",
        "periodo": "2023-2024",
        "actualizacion": "Acumulado a Dic 2024",
        "citacion": "Fuente: APE/SENA (2023-2024)"
    },
    "vacantes_2025": {
        "nombre": "Vacantes APE 2025",
        "entidad": "SENA - Observatorio Laboral",
        "url": "https://observatorio.sena.edu.co/",
        "periodo": "S1-T3 2025",
        "actualizacion": "Parcial 2025",
        "citacion": "Fuente: APE/SENA (2025 parcial)"
    },
    "colocados_2024": {
        "nombre": "Colocados APE 2024",
        "entidad": "SENA - Observatorio Laboral",
        "url": "https://observatorio.sena.edu.co/",
        "periodo": "2024",
        "actualizacion": "Anual 2024",
        "citacion": "Fuente: APE/SENA (2024)"
    },
    "inscritos_2024": {
        "nombre": "Inscritos APE 2024",
        "entidad": "SENA - Observatorio Laboral",
        "url": "https://observatorio.sena.edu.co/",
        "periodo": "2024",
        "actualizacion": "Anual 2024",
        "citacion": "Fuente: APE/SENA (2024)"
    },
    "competencias_cuoc": {
        "nombre": "Competencias por Ocupación",
        "entidad": "DANE / OIT",
        "url": "https://www.dane.gov.co/",
        "periodo": "2025",
        "actualizacion": "CUOC 2025",
        "citacion": "Fuente: CUOC/DANE (2025)"
    },
    "cuoc_perfiles": {
        "nombre": "Perfiles Ocupacionales CUOC",
        "entidad": "DANE / MinTrabajo",
        "url": "https://www.dane.gov.co/index.php/sistema-estadistico-nacional-sen/normas-y-estandares/nomenclaturas-y-clasificaciones/clasificaciones/clasificacion-unica-de-ocupaciones-para-colombia-cuoc",
        "periodo": "2025",
        "actualizacion": "CUOC 2025",
        "citacion": "Fuente: Perfiles Ocupacionales CUOC/DANE (2025)"
    },
    "cualificaciones_men": {
        "nombre": "Catálogo de Cualificaciones MEN",
        "entidad": "Ministerio de Educación Nacional",
        "url": "https://www.mineducacion.gov.co/portal/micrositios-superior/Marco-Nacional-de-Cualificaciones/",
        "periodo": "2024",
        "actualizacion": "Marco Nacional Cualificaciones",
        "citacion": "Fuente: MNC/MEN (2024)"
    },
    
    # -------------------------------------------------------------------------
    # EJE 3: PERTINENCIA TERRITORIAL
    # -------------------------------------------------------------------------
    "internet_fijo": {
        "nombre": "Accesos Internet Fijo",
        "entidad": "MinTIC - CRC",
        "url": "https://www.datos.gov.co/",
        "periodo": "2016-2023",
        "actualizacion": "Serie a 2023",
        "citacion": "Fuente: MinTIC/CRC (2023)"
    },
    "cobertura_movil": {
        "nombre": "Cobertura Móvil por Tecnología",
        "entidad": "MinTIC - ANE",
        "url": "https://www.datos.gov.co/",
        "periodo": "2015-2023",
        "actualizacion": "Serie a 2023",
        "citacion": "Fuente: MinTIC/ANE (2023)"
    },
    "divipola": {
        "nombre": "División Político-Administrativa",
        "entidad": "DANE",
        "url": "https://www.dane.gov.co/",
        "periodo": "2024",
        "actualizacion": "Vigente 2024",
        "citacion": "Fuente: DIVIPOLA/DANE (2024)"
    },
    "pdet": {
        "nombre": "Municipios PDET",
        "entidad": "ART - Agencia de Renovación del Territorio",
        "url": "https://www.renovacionterritorio.gov.co/",
        "periodo": "2024",
        "actualizacion": "170 municipios PDET",
        "citacion": "Fuente: ART (2024)"
    },
    "dnp_mdm": {
        "nombre": "Medición de Desempeño Municipal (MDM)",
        "entidad": "DNP - Departamento Nacional de Planeación",
        "url": "https://www.dnp.gov.co/",
        "periodo": "2023",
        "actualizacion": "Medición 2023",
        "citacion": "Fuente: DNP - MDM (2023)"
    },
    "rues": {
        "nombre": "RUES - Registro Único Empresarial",
        "entidad": "Confecámaras - Cámaras de Comercio",
        "url": "https://www.rues.org.co/",
        "periodo": "2024",
        "actualizacion": "Top 10,000 empresas",
        "citacion": "Fuente: RUES/Confecámaras (2024)"
    },
    
    # -------------------------------------------------------------------------
    # EJE 4: CONTEXTO GLOBAL
    # -------------------------------------------------------------------------
    "banco_mundial": {
        "nombre": "Indicadores Banco Mundial",
        "entidad": "Banco Mundial",
        "url": "https://datos.bancomundial.org/",
        "periodo": "2023",
        "actualizacion": "Último disponible",
        "citacion": "Fuente: Banco Mundial (2023)"
    },
    "habilidades_futuro": {
        "nombre": "Tendencias Tecnológicas y Habilidades",
        "entidad": "WEF / LinkedIn / Análisis propio",
        "url": "https://www.weforum.org/",
        "periodo": "2024-2027",
        "actualizacion": "Proyecciones",
        "citacion": "Fuente: WEF/LinkedIn (2024)"
    },
    "edtech": {
        "nombre": "Adopción EdTech Global",
        "entidad": "HolonIQ / UNESCO",
        "url": "https://www.holoniq.com/",
        "periodo": "2024",
        "actualizacion": "Proyecciones 2024-2027",
        "citacion": "Fuente: HolonIQ/UNESCO (2024)"
    },
    "industria40": {
        "nombre": "Índice Industria 4.0",
        "entidad": "WEF / McKinsey",
        "url": "https://www.weforum.org/",
        "periodo": "2024",
        "actualizacion": "Ranking global",
        "citacion": "Fuente: WEF (2024)"
    },
    
    # -------------------------------------------------------------------------
    # CATÁLOGOS CURADOS
    # -------------------------------------------------------------------------
    "mapeo_nbc_cuoc": {
        "nombre": "Mapeo NBC-CUOC",
        "entidad": "Elaboracion propia",
        "url": "",
        "periodo": "2024",
        "actualizacion": "Validado 2024",
        "citacion": "Fuente: Mapeo propio NBC-CUOC (2024)"
    },
    "mapeo_ciiu": {
        "nombre": "Mapeo CUOC-CIIU",
        "entidad": "DANE / Elaboración propia",
        "url": "",
        "periodo": "2024",
        "actualizacion": "CIIU Rev.4 - CUOC 2025",
        "citacion": "Fuente: DANE/CIIU Rev.4 (2024)"
    }
}

# ==============================================================================
# FUNCIONES HELPER
# ==============================================================================

def get_citacion(fuente_id: str) -> str:
    """Retorna la citación corta para una fuente."""
    if fuente_id in FUENTES:
        return FUENTES[fuente_id]["citacion"]
    return f"Fuente: {fuente_id}"

def get_citacion_completa(fuente_id: str) -> str:
    """Retorna citación completa con URL."""
    if fuente_id in FUENTES:
        f = FUENTES[fuente_id]
        return f"{f['nombre']} - {f['entidad']} ({f['periodo']})"
    return fuente_id

def get_periodo(fuente_id: str) -> str:
    """Retorna el período de los datos."""
    if fuente_id in FUENTES:
        return FUENTES[fuente_id]["periodo"]
    return "N/D"

def get_actualizacion(fuente_id: str) -> str:
    """Retorna info de última actualización."""
    if fuente_id in FUENTES:
        return FUENTES[fuente_id]["actualizacion"]
    return "N/D"

# ==============================================================================
# MAPEO DE TABLAS A FUENTES
# ==============================================================================

TABLA_A_FUENTE = {
    # SNIES
    "snies.snies_programas": "snies_programas",
    "snies.snies_graduados": "snies_graduados",
    "snies.snies_matriculados": "snies_matriculados",
    "snies.snies_instituciones": "snies_instituciones",
    "snies.snies_admitidos": "snies_programas",
    
    # SIET
    "siet.siet_programas": "siet_programas",
    "siet.siet_instituciones": "siet_instituciones",
    
    # CUOC
    "cuoc.cuoc_limpio_2025": "cuoc_2025",
    "cuoc.cuoc_estructura_2025": "cuoc_2025",
    "competencias.cuoc_conocimientos": "competencias_cuoc",
    "competencias.cuoc_destrezas": "competencias_cuoc",
    
    # Tendencias laborales
    "tendencias_laborales.vacantes_ape_clean": "vacantes_ape",
    "tendencias_ocupacionales.vacantes_anual_2024": "vacantes_ape",
    "tendencias_ocupacionales.vacantes_s1_2025": "vacantes_2025",
    "tendencias_ocupacionales.colocados_anual_2024": "colocados_2024",
    "tendencias_ocupacionales.inscritos_anual_2024": "inscritos_2024",
    
    # Conectividad
    "conectividad.internet_fijo_accesos": "internet_fijo",
    "conectividad.cobertura_movil_tecnologia": "cobertura_movil",
    "competencias_tic.cobertura_móvil_por_tecnología_departamento_y_muni": "cobertura_movil",
    
    # Catálogos curados
    "catalogo_curado.mapeo_nbc_cuoc": "mapeo_nbc_cuoc",
    "catalogo_curado.cualificaciones_men": "cualificaciones_men",
    "catalogo_curado.mapeo_cuoc_ciiu": "mapeo_ciiu",
    
    # Territorial
    "divipola.divipola_departamentos": "divipola",
    "territorial.municipios_pdet": "pdet",
    
    # Global
    "indicadores_globales.bm_desempleo_jovenes": "banco_mundial",
    "tendencias_tecnologicas.habilidades_futuro": "habilidades_futuro",
}

def get_fuente_por_tabla(tabla: str) -> str:
    """Dado un nombre de tabla, retorna la citación correspondiente."""
    if tabla in TABLA_A_FUENTE:
        return get_citacion(TABLA_A_FUENTE[tabla])
    return f"Fuente: {tabla}"


# ==============================================================================
# ADVERTENCIAS DE ACTUALIZACIÓN
# ==============================================================================

FUENTES_DESACTUALIZADAS = {
    "internet_fijo": {
        "ultimo_disponible": "2023",
        "actual_en_app": "2022",
        "accion": "Actualizar filtro a >= 2023"
    },
    "cobertura_movil": {
        "ultimo_disponible": "2023", 
        "actual_en_app": "2022",
        "accion": "Actualizar filtro a >= 2023"
    }
}

def verificar_actualizacion(fuente_id: str) -> dict:
    """Verifica si una fuente está desactualizada en la app."""
    if fuente_id in FUENTES_DESACTUALIZADAS:
        return {
            "desactualizada": True,
            **FUENTES_DESACTUALIZADAS[fuente_id]
        }
    return {"desactualizada": False}
