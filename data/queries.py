"""
Sistema de Análisis para Estudio de Contexto - Módulo de Consultas de Base de Datos
====================================================================================

Este módulo contiene todas las funciones de consulta (get_*) extraídas del dashboard principal.
Organiza las queries por categoría para facilitar mantenimiento y testing.

Categorías de funciones:
- SIET/ETDH: Queries sobre educación para el trabajo y desarrollo humano
- Explorador Interactivo: Consultas dinámicas multidimensionales
- SNIES Académico: Queries sobre programas de educación superior
- Territorial: Consultas geográficas y de contexto territorial
- Laboral: Queries sobre mercado laboral (vacantes, salarios, competencias)
- Global: Indicadores internacionales y habilidades del futuro
- Cualificaciones MEN: Marco Nacional de Cualificaciones

Todas las funciones retornan DataFrames de pandas o diccionarios con datos estructurados.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity

# Imports de módulos propios
from config.database import get_conn
from config.constants import SEXO_NORMALIZE_SQL
from data.filters import (
    build_where_clause,
    build_where_clause_matriculados,
    build_nbc_match_condition,
    _esc
)
from data.constants import STOPWORDS

# Importar módulo de ML para matching semántico NBC↔CUOC
try:
    from services.ml.matching import match_nbc_to_vacantes, match_nbc_to_competencias, match_nbc_to_ocupaciones, get_model
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[Warning] ML matching no disponible - usando fallback de keywords")






def _depto_where(col: str, depto, prefix: str = "AND") -> str:
    """Construye clausula WHERE para filtro departamental con strip_accents."""
    if not depto:
        return ""  # Nacional — sin filtro
    return f"{prefix} UPPER(strip_accents(\"{col}\")) LIKE '%' || UPPER(strip_accents('{_esc(depto)}')) || '%'"


# ==============================================================================
# SIET/ETDH - Educación para el Trabajo y Desarrollo Humano
# ==============================================================================

def get_estadisticas_siet(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """
    Obtiene estadísticas de la oferta SIET/ETDH con filtros opcionales.
    Base disyuntiva: no se cruza con SNIES, solo contextual.
    
    Usa _build_siet_where para construir WHERE consistente con todas las queries SIET.
    Todos los filtros (area, depto, estado, búsqueda, modalidad) se propagan a
    TODAS las sub-consultas (programas, instituciones, matrícula, certificados).
    """
    conn = get_conn()
    stats = {
        'total_programas': 0,
        'total_instituciones': 0,
        'total_matriculados': 0,
        'total_certificados': 0,
        'duracion_promedio': 0
    }
    
    try:
        # Usar _build_siet_where para consistencia total de filtros
        where_prog = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre,
                                       modalidades_siet=modalidades_siet, for_table='programas')
        where_mat = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre,
                                      modalidades_siet=modalidades_siet, for_table='matricula')
        where_cert = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre,
                                       modalidades_siet=modalidades_siet, for_table='certificados')
        
        # Total programas + duración promedio (ahora incluye TODOS los filtros: area, depto, estado, búsqueda, modalidad)
        result_prog = conn.execute(f'''
            SELECT COUNT(*) as total, AVG("Duración Horas") as duracion_prom
            FROM siet.siet_programas WHERE {where_prog}
        ''').fetchone()
        stats['total_programas'] = result_prog[0] or 0
        stats['duracion_promedio'] = int(result_prog[1] or 0)
        
        # Total instituciones (mismos filtros que programas, conteo distinto)
        stats['total_instituciones'] = conn.execute(f'''
            SELECT COUNT(DISTINCT "Código Institución") FROM siet.siet_programas WHERE {where_prog}
        ''').fetchone()[0] or 0
        
        # Matrícula total 2023 (ahora incluye TODOS los filtros: area, depto, estado, búsqueda, modalidad)
        result_mat = conn.execute(f'''
            SELECT SUM("Total Matrícula 2023") FROM siet.siet_matricula_programa_ WHERE {where_mat}
        ''').fetchone()[0]
        stats['total_matriculados'] = int(result_mat or 0)
        
        # Certificados total 2023 (mismos filtros)
        result_cert = conn.execute(f'''
            SELECT SUM("Total Certificado 2023") FROM siet.siet_estudiantes_certificados_progr WHERE {where_cert}
        ''').fetchone()[0]
        stats['total_certificados'] = int(result_cert or 0)
        
    except Exception as e:
        print(f"[SIET] Stats no disponibles: {e}")
    finally:
        conn.close()
    
    return stats


@st.cache_data
def get_desglose_siet(areas_desempeno=None, deptos=None, busqueda_nombre=None, modalidades_siet=None, estados=None):
    """Obtiene desglose de programas SIET por área de desempeño.
    
    Usa _build_siet_where para consistencia con todas las queries SIET.
    """
    conn = get_conn()
    resultado = {'por_area': pd.DataFrame(), 'por_depto': pd.DataFrame()}
    
    try:
        # Usar _build_siet_where para consistencia total de filtros
        where_full = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre,
                                       modalidades_siet=modalidades_siet, for_table='programas')
        extra_where = f" AND {where_full}" if where_full != "1=1" else ""
        
        # Distribución por área de desempeño
        query_area = f'''
            SELECT "Area de Desempeño" as area, COUNT(*) as programas
            FROM siet.siet_programas
            WHERE "Area de Desempeño" IS NOT NULL{extra_where}
            GROUP BY "Area de Desempeño"
            ORDER BY programas DESC
        '''
        resultado['por_area'] = conn.execute(query_area).df()
        
        # Distribución por departamento (top 15)
        query_depto = f'''
            SELECT "Departamento" as departamento, COUNT(*) as programas
            FROM siet.siet_programas
            WHERE "Departamento" IS NOT NULL{extra_where}
            GROUP BY "Departamento"
            ORDER BY programas DESC
            LIMIT 15
        '''
        resultado['por_depto'] = conn.execute(query_depto).df()
        
    except Exception as e:
        print(f"[SIET] Detalle no disponible: {e}")
    finally:
        conn.close()
    
    return resultado


def get_programas_detalle_siet(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Obtiene detalle completo de programas SIET/ETDH con filtros aplicados.
    
    Returns:
        DataFrame con columnas: Institución, Programa, Departamento, Municipio,
        Área Desempeño, Estado, Tipo Certificado, Metodología, Duración (Hrs), Costo
    """
    conn = get_conn()
    try:
        conditions = []
        if areas_desempeno and len(areas_desempeno) > 0:
            areas_str = "', '".join([a.replace("'", "''") for a in areas_desempeno])
            conditions.append(f'"Area de Desempeño" IN (\'{areas_str}\')')
        if deptos and len(deptos) > 0:
            deptos_str = "', '".join([d.replace("'", "''") for d in deptos])
            conditions.append(f'"Departamento" IN (\'{deptos_str}\')')
        if estados and len(estados) > 0:
            estados_str = "', '".join([e.replace("'", "''") for e in estados])
            conditions.append(f'"Estado Programa" IN (\'{estados_str}\')')
        if busqueda_nombre and busqueda_nombre.strip():
            texto_escaped = busqueda_nombre.strip().replace("'", "''")
            conditions.append(f'UPPER("Nombre Programa") LIKE UPPER(\'%{texto_escaped}%\')')
        # Modalidad directa (siet_programas tiene Metodología 1/2/3)
        if modalidades_siet and len(modalidades_siet) > 0:
            mod_cond = _build_siet_modalidad_condition(modalidades_siet)
            if mod_cond:
                conditions.append(mod_cond)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT 
            "Nombre Institución" as "Institución",
            "Nombre Programa" as "Programa",
            "Departamento",
            "Municipio",
            "Area de Desempeño" as "Área Desempeño",
            "Estado Programa" as "Estado",
            "Tipo de Certificado" as "Tipo Certificado",
            "Metodología 1" as "Metodología",
            "Duración Horas" as "Duración (Hrs)",
            "Costo"
        FROM siet.siet_programas
        WHERE {where_clause}
        ORDER BY "Nombre Institución", "Nombre Programa"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


# =============================================================================
# SIET ADVANCED ANALYTICS — Tendencias, Rankings, Desgloses completos
# =============================================================================

def _build_siet_modalidad_condition(modalidades_siet):
    """Helper: genera condición SQL para filtrar por Metodología 1/2/3 en siet_programas."""
    if not modalidades_siet or len(modalidades_siet) == 0:
        return ""
    mods_clean = [m for m in modalidades_siet if m is not None]
    if not mods_clean:
        return ""
    mods_str = "', '".join([m.replace("'", "''") for m in mods_clean])
    return (f'("Metodología 1" IN (\'{mods_str}\') '
            f'OR "Metodología 2" IN (\'{mods_str}\') '
            f'OR "Metodología 3" IN (\'{mods_str}\'))')


def _build_siet_modalidad_subquery(modalidades_siet, col_prefix=''):
    """Helper: genera subquery para filtrar matrícula/certificados por modalidad via siet_programas.
    
    Usa subquery porque siet_matricula_programa_ y siet_estudiantes_certificados_progr
    NO tienen columnas de Metodología; solo siet_programas las tiene.
    
    Args:
        modalidades_siet: Lista de modalidades (PRESENCIAL, VIRTUAL, A DISTANCIA)
        col_prefix: Alias de tabla (e.g. 'm' para m."Código Programa")
    """
    if not modalidades_siet or len(modalidades_siet) == 0:
        return ""
    mods_clean = [m for m in modalidades_siet if m is not None]
    if not mods_clean:
        return ""
    mods_str = "', '".join([m.replace("'", "''") for m in mods_clean])
    p = f'{col_prefix}.' if col_prefix else ''
    return (f' AND ({p}"Código Programa", {p}"Código Institución") IN ('
            f'SELECT "Código Programa", "Código Institución" FROM siet.siet_programas '
            f'WHERE "Metodología 1" IN (\'{mods_str}\') '
            f'OR "Metodología 2" IN (\'{mods_str}\') '
            f'OR "Metodología 3" IN (\'{mods_str}\'))')


def _build_siet_where(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None,
                      modalidades_siet=None, for_table='programas'):
    """Helper: construye cláusula WHERE reutilizable para queries SIET.
    
    Args:
        for_table: 'programas' (filtro directo Metodología) o 'matricula'/'certificados' (subquery)
    """
    conditions = []
    if areas_desempeno and len(areas_desempeno) > 0:
        areas_clean = [a for a in areas_desempeno if a is not None]
        if areas_clean:
            areas_str = "', '".join([a.replace("'", "''") for a in areas_clean])
            conditions.append(f'"Area de Desempeño" IN (\'{areas_str}\')')
    if deptos and len(deptos) > 0:
        deptos_clean = [d for d in deptos if d is not None]
        if deptos_clean:
            deptos_str = "', '".join([d.replace("'", "''") for d in deptos_clean])
            conditions.append(f'"Departamento" IN (\'{deptos_str}\')')
    if estados and len(estados) > 0:
        estados_str = "', '".join([e.replace("'", "''") for e in estados])
        conditions.append(f'"Estado Programa" IN (\'{estados_str}\')')
    if busqueda_nombre and busqueda_nombre.strip():
        texto_escaped = busqueda_nombre.strip().replace("'", "''")
        conditions.append(f'UPPER("Nombre Programa") LIKE UPPER(\'%{texto_escaped}%\')')
    # Modalidad: filtro directo para siet_programas, subquery para matrícula/certificados
    if modalidades_siet and len(modalidades_siet) > 0:
        if for_table == 'programas':
            mod_cond = _build_siet_modalidad_condition(modalidades_siet)
            if mod_cond:
                conditions.append(mod_cond)
        else:
            # for_table in ('matricula', 'certificados') — subquery via siet_programas
            sub = _build_siet_modalidad_subquery(modalidades_siet)
            if sub:
                # sub starts with ' AND ...' so strip leading AND
                conditions.append(sub.strip().lstrip('AND').strip())
    return " AND ".join(conditions) if conditions else "1=1"


@st.cache_data
def get_siet_tendencia_matricula(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Tendencia de matrícula ETDH 2010-2023 (UNPIVOT de columnas anuales)."""
    conn = get_conn()
    try:
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, modalidades_siet=modalidades_siet, for_table='matricula')
        years = list(range(2010, 2024))
        selects = ", ".join([f'SUM("Total Matrícula {y}") as "y{y}"' for y in years])
        query = f'SELECT {selects} FROM siet.siet_matricula_programa_ WHERE {where}'
        row = conn.execute(query).fetchone()
        data = [{'Año': y, 'Matriculados': int(row[i] or 0)} for i, y in enumerate(years)]
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[SIET] Tendencia matrícula error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_tendencia_certificados(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Tendencia de certificados ETDH 2010-2023."""
    conn = get_conn()
    try:
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, modalidades_siet=modalidades_siet, for_table='certificados')
        years = list(range(2010, 2024))
        selects = ", ".join([f'SUM("Total Certificado {y}") as "y{y}"' for y in years])
        query = f'SELECT {selects} FROM siet.siet_estudiantes_certificados_progr WHERE {where}'
        row = conn.execute(query).fetchone()
        data = [{'Año': y, 'Certificados': int(row[i] or 0)} for i, y in enumerate(years)]
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[SIET] Tendencia certificados error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_tendencia_por_area(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Tendencia matrícula ETDH por área de desempeño (series múltiples)."""
    conn = get_conn()
    try:
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, modalidades_siet=modalidades_siet, for_table='matricula')
        years = list(range(2010, 2024))
        selects = ", ".join([f'SUM("Total Matrícula {y}") as "y{y}"' for y in years])
        query = f'''
            SELECT "Area de Desempeño" as area, {selects}
            FROM siet.siet_matricula_programa_
            WHERE {where} AND "Area de Desempeño" IS NOT NULL
            GROUP BY 1
        '''
        df_raw = conn.execute(query).fetchdf()
        if df_raw.empty:
            return pd.DataFrame()
        rows = []
        for _, r in df_raw.iterrows():
            for i, y in enumerate(years):
                rows.append({'Área': r['area'], 'Año': y, 'Matriculados': int(r.iloc[i+1] or 0)})
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[SIET] Tendencia por área error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_top_instituciones(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None, top_n=15):
    """Top instituciones ETDH por matrícula 2023 con naturaleza."""
    conn = get_conn()
    try:
        # For JOIN queries, handle modalidad separately to avoid ambiguous column refs
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, for_table='matricula')
        where_aliased = where.replace('"Area de Desempeño"', 'm."Area de Desempeño"').replace('"Departamento"', 'm."Departamento"').replace('"Estado Programa"', 'm."Estado Programa"').replace('"Nombre Programa"', 'm."Nombre Programa"')
        # Add modalidad subquery with explicit 'm.' prefix
        modalidad_sql = _build_siet_modalidad_subquery(modalidades_siet, col_prefix='m')
        query = f'''
            SELECT 
                m."Nombre Institución" as institucion,
                COALESCE(i."Naturaleza", 'N/D') as naturaleza,
                COUNT(DISTINCT m."Código Programa") as programas,
                SUM(m."Total Matrícula 2023") as matricula_2023,
                SUM(m."Total Matrícula 2022") as matricula_2022,
                SUM(c."Total Certificado 2023") as certificados_2023
            FROM siet.siet_matricula_programa_ m
            LEFT JOIN siet.siet_instituciones i 
                ON m."Código Institución" = i."Código Institución"
            LEFT JOIN siet.siet_estudiantes_certificados_progr c
                ON m."Código Programa" = c."Código Programa"
                AND m."Código Institución" = c."Código Institución"
            WHERE {where_aliased}{modalidad_sql}
            GROUP BY 1, 2
            ORDER BY matricula_2023 DESC NULLS LAST
            LIMIT {top_n}
        '''
        df = conn.execute(query).fetchdf()
        if not df.empty:
            df['matricula_2023'] = df['matricula_2023'].fillna(0).astype(int)
            df['matricula_2022'] = df['matricula_2022'].fillna(0).astype(int)
            df['certificados_2023'] = df['certificados_2023'].fillna(0).astype(int)
            df['variacion_pct'] = ((df['matricula_2023'] - df['matricula_2022']) / 
                                   df['matricula_2022'].replace(0, 1) * 100).round(1)
        return df
    except Exception as e:
        print(f"[SIET] Top instituciones error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_top_programas(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None, top_n=20):
    """Top programas ETDH por matrícula 2023."""
    conn = get_conn()
    try:
        # For JOIN queries, handle modalidad separately to avoid ambiguous column refs
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, for_table='matricula')
        where_aliased = where.replace('"Area de Desempeño"', 'm."Area de Desempeño"').replace('"Departamento"', 'm."Departamento"').replace('"Estado Programa"', 'm."Estado Programa"').replace('"Nombre Programa"', 'm."Nombre Programa"')
        # Add modalidad subquery with explicit 'm.' prefix
        modalidad_sql = _build_siet_modalidad_subquery(modalidades_siet, col_prefix='m')
        query = f'''
            SELECT 
                m."Nombre Programa" as programa,
                m."Area de Desempeño" as area,
                m."Tipo Certificado" as tipo_certificado,
                COUNT(DISTINCT m."Código Institución") as instituciones,
                SUM(m."Total Matrícula 2023") as matricula_2023,
                SUM(c."Total Certificado 2023") as certificados_2023
            FROM siet.siet_matricula_programa_ m
            LEFT JOIN siet.siet_estudiantes_certificados_progr c
                ON m."Código Programa" = c."Código Programa"
                AND m."Código Institución" = c."Código Institución"
            WHERE {where_aliased}{modalidad_sql}
            GROUP BY 1, 2, 3
            ORDER BY matricula_2023 DESC NULLS LAST
            LIMIT {top_n}
        '''
        df = conn.execute(query).fetchdf()
        if not df.empty:
            df['matricula_2023'] = df['matricula_2023'].fillna(0).astype(int)
            df['certificados_2023'] = df['certificados_2023'].fillna(0).astype(int)
            df['tasa_certificacion'] = (df['certificados_2023'] / df['matricula_2023'].replace(0, 1) * 100).round(1)
        return df
    except Exception as e:
        print(f"[SIET] Top programas error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_desglose_oferta(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Desglose completo de la oferta ETDH: tipo certificado, escolaridad, jornada, metodología, costo."""
    conn = get_conn()
    try:
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, modalidades_siet=modalidades_siet, for_table='programas')
        
        resultado = {}
        
        # Por tipo de certificado
        resultado['tipo_certificado'] = conn.execute(f'''
            SELECT "Tipo de Certificado" as tipo, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} AND "Tipo de Certificado" IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Por subtipo de certificado  
        resultado['subtipo_certificado'] = conn.execute(f'''
            SELECT "Subtipo de Certificado" as subtipo, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} AND "Subtipo de Certificado" IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Por escolaridad requerida
        resultado['escolaridad'] = conn.execute(f'''
            SELECT "Escolaridad" as escolaridad, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} AND "Escolaridad" IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Por jornada
        resultado['jornada'] = conn.execute(f'''
            SELECT "Jornada 1" as jornada, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} AND "Jornada 1" IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Por metodología
        resultado['metodologia'] = conn.execute(f'''
            SELECT "Metodología 1" as metodologia, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} AND "Metodología 1" IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Por estado de programa
        resultado['estado'] = conn.execute(f'''
            SELECT "Estado Programa" as estado, COUNT(*) as programas
            FROM siet.siet_programas WHERE {where} GROUP BY 1 ORDER BY 2 DESC
        ''').fetchdf()
        
        # Distribución de costos (buckets)
        resultado['costos'] = conn.execute(f'''
            SELECT 
                CASE 
                    WHEN "Costo" IS NULL OR "Costo" = 0 THEN 'Sin información'
                    WHEN "Costo" < 500000 THEN '< $500K'
                    WHEN "Costo" < 1000000 THEN '$500K - $1M'
                    WHEN "Costo" < 2000000 THEN '$1M - $2M'
                    WHEN "Costo" < 4000000 THEN '$2M - $4M'
                    ELSE '> $4M'
                END as rango_costo,
                COUNT(*) as programas,
                ROUND(AVG("Duración Horas"), 0) as duracion_promedio
            FROM siet.siet_programas WHERE {where}
            GROUP BY 1
            ORDER BY MIN("Costo") NULLS FIRST
        ''').fetchdf()
        
        # Costo promedio y duración promedio por área
        resultado['costo_por_area'] = conn.execute(f'''
            SELECT 
                "Area de Desempeño" as area,
                ROUND(AVG("Costo"), 0) as costo_promedio,
                ROUND(AVG("Duración Horas"), 0) as duracion_promedio,
                COUNT(*) as programas
            FROM siet.siet_programas 
            WHERE {where} AND "Costo" > 0 AND "Area de Desempeño" IS NOT NULL
            GROUP BY 1
            ORDER BY costo_promedio DESC
        ''').fetchdf()
        
        return resultado
    except Exception as e:
        print(f"[SIET] Desglose oferta error: {e}")
        return {}
    finally:
        conn.close()


@st.cache_data
def get_siet_naturaleza_instituciones(areas_desempeno=None, deptos=None):
    """Distribución de instituciones ETDH por naturaleza jurídica."""
    conn = get_conn()
    try:
        conditions = []
        if deptos and len(deptos) > 0:
            deptos_str = "', '".join([d.replace("'", "''") for d in deptos])
            conditions.append(f'"Departamento" IN (\'{deptos_str}\')')
        where_inst = " AND ".join(conditions) if conditions else "1=1"
        
        df = conn.execute(f'''
            SELECT 
                "Naturaleza" as naturaleza,
                "Personalidad Jurídica" as personalidad_juridica,
                COUNT(*) as instituciones,
                SUM("Cantidad de Programas") as total_programas
            FROM siet.siet_instituciones
            WHERE {where_inst}
            GROUP BY 1, 2
            ORDER BY 3 DESC
        ''').fetchdf()
        return df
    except Exception as e:
        print(f"[SIET] Naturaleza instituciones error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_tasa_certificacion_historica(areas_desempeno=None, deptos=None, estados=None, busqueda_nombre=None, modalidades_siet=None):
    """Tasa de certificación histórica (certificados/matrícula) 2010-2023."""
    conn = get_conn()
    try:
        where = _build_siet_where(areas_desempeno, deptos, estados, busqueda_nombre, modalidades_siet=modalidades_siet, for_table='matricula')
        years = list(range(2010, 2024))
        
        mat_selects = ", ".join([f'SUM("Total Matrícula {y}")' for y in years])
        cert_selects = ", ".join([f'SUM("Total Certificado {y}")' for y in years])
        
        mat_row = conn.execute(f'SELECT {mat_selects} FROM siet.siet_matricula_programa_ WHERE {where}').fetchone()
        cert_row = conn.execute(f'SELECT {cert_selects} FROM siet.siet_estudiantes_certificados_progr WHERE {where}').fetchone()
        
        data = []
        for i, y in enumerate(years):
            mat = int(mat_row[i] or 0)
            cert = int(cert_row[i] or 0)
            tasa = round(cert / mat * 100, 1) if mat > 0 else 0
            data.append({'Año': y, 'Matriculados': mat, 'Certificados': cert, 'Tasa Certificación (%)': tasa})
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[SIET] Tasa certificación error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_siet_matricula_por_depto(areas_desempeno=None, estados=None, busqueda_nombre=None, modalidades_siet=None, top_n=15):
    """Top departamentos por matrícula 2023 con variación interanual."""
    conn = get_conn()
    try:
        conditions = []
        if areas_desempeno and len(areas_desempeno) > 0:
            areas_clean = [a for a in areas_desempeno if a is not None]
            if areas_clean:
                areas_str = "', '".join([a.replace("'", "''") for a in areas_clean])
                conditions.append(f'"Area de Desempeño" IN (\'{areas_str}\')')
        if estados and len(estados) > 0:
            estados_clean = [e for e in estados if e is not None]
            if estados_clean:
                estados_str = "', '".join([e.replace("'", "''") for e in estados_clean])
                conditions.append(f'"Estado Programa" IN (\'{estados_str}\')')
        if busqueda_nombre and busqueda_nombre.strip():
            texto_escaped = busqueda_nombre.strip().replace("'", "''")
            conditions.append(f'UPPER("Nombre Programa") LIKE UPPER(\'%{texto_escaped}%\')')
        # Modalidad via subquery (matrícula table has no Metodología columns)
        if modalidades_siet and len(modalidades_siet) > 0:
            sub = _build_siet_modalidad_subquery(modalidades_siet)
            if sub:
                conditions.append(sub.strip().lstrip('AND').strip())
        where = " AND ".join(conditions) if conditions else "1=1"
        
        df = conn.execute(f'''
            SELECT 
                "Departamento" as departamento,
                SUM("Total Matrícula 2023") as matricula_2023,
                SUM("Total Matrícula 2022") as matricula_2022,
                SUM("Total Matrícula 2019") as matricula_2019,
                COUNT(DISTINCT "Código Institución") as instituciones,
                COUNT(DISTINCT "Código Programa") as programas
            FROM siet.siet_matricula_programa_
            WHERE {where} AND "Departamento" IS NOT NULL
            GROUP BY 1
            ORDER BY matricula_2023 DESC NULLS LAST
            LIMIT {top_n}
        ''').fetchdf()
        if not df.empty:
            df = df.fillna(0)
            for c in ['matricula_2023', 'matricula_2022', 'matricula_2019', 'instituciones', 'programas']:
                df[c] = df[c].astype(int)
            df['variacion_anual_pct'] = ((df['matricula_2023'] - df['matricula_2022']) / 
                                          df['matricula_2022'].replace(0, 1) * 100).round(1)
            df['cagr_4y_pct'] = (((df['matricula_2023'] / df['matricula_2019'].replace(0, 1)) ** 0.25 - 1) * 100).round(1)
        return df
    except Exception as e:
        print(f"[SIET] Matrícula por depto error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_comparativa_snies_siet_por_depto(filtros=None, areas_desempeno_siet=None):
    """
    Genera comparativa de oferta educativa SNIES vs SIET por departamento.
    Permite ver complementariedad entre educación superior y ETDH.
    Filtra SNIES por filtros seleccionados si se proporcionan.
    Filtra SIET por áreas de desempeño derivadas (via ML/mapeo CINE-F) si se proporcionan.
    """
    conn = get_conn()
    try:
        # Programas SNIES por departamento (con filtros)
        where_snies = "1=1"
        if filtros:
            # Construir filtro sin deptos para que el GROUP BY por depto sea significativo
            filtros_sin_geo = {k: v for k, v in filtros.items() if k not in ('deptos', 'municipios')}
            extra = build_where_clause(filtros_sin_geo, "")
            if extra and extra != "1=1":
                where_snies = extra
        
        query_snies = f'''
            SELECT "DEPARTAMENTO_OFERTA_PROGRAMA" as departamento, 
                   COUNT(*) as programas_snies
            FROM snies.snies_programas
            WHERE {where_snies}
            AND "DEPARTAMENTO_OFERTA_PROGRAMA" IS NOT NULL
            GROUP BY "DEPARTAMENTO_OFERTA_PROGRAMA"
        '''
        df_snies = conn.execute(query_snies).df()
        
        # Programas SIET por departamento (filtrado por áreas derivadas de SNIES)
        where_siet = '"Departamento" IS NOT NULL'
        if areas_desempeno_siet:
            areas_sql = ", ".join([f"'{a.replace(chr(39), chr(39)*2)}'" for a in areas_desempeno_siet])
            where_siet += f' AND "Area de Desempeño" IN ({areas_sql})'
        query_siet = f'''
            SELECT "Departamento" as departamento, 
                   COUNT(*) as programas_siet
            FROM siet.siet_programas
            WHERE {where_siet}
            GROUP BY "Departamento"
        '''
        df_siet = conn.execute(query_siet).df()
        
        # Normalizar nombres de departamentos para join
        df_snies['departamento_norm'] = df_snies['departamento'].str.upper().str.strip()
        df_siet['departamento_norm'] = df_siet['departamento'].str.upper().str.strip()
        
        # Merge
        df_comp = pd.merge(
            df_snies[['departamento', 'departamento_norm', 'programas_snies']],
            df_siet[['departamento_norm', 'programas_siet']],
            on='departamento_norm',
            how='outer'
        ).fillna(0)
        
        df_comp['programas_snies'] = df_comp['programas_snies'].astype(int)
        df_comp['programas_siet'] = df_comp['programas_siet'].astype(int)
        df_comp['total'] = df_comp['programas_snies'] + df_comp['programas_siet']
        df_comp = df_comp.sort_values('total', ascending=False).head(15)
        
        return df_comp
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_comparativa_tipo_formacion(filtros=None, areas_desempeno_siet=None):
    """
    Compara niveles de formación SNIES vs tipos de certificado SIET.
    Muestra la distribución de la oferta por tipo de formación.
    Filtra SNIES por filtros seleccionados si se proporcionan.
    Filtra SIET por áreas de desempeño derivadas (via ML/mapeo CINE-F) si se proporcionan.
    """
    conn = get_conn()
    try:
        # Construir filtro SNIES (sin filtro de nivel para que el GROUP BY sea significativo)
        where_snies = "1=1"
        if filtros:
            filtros_sin_nivel = {k: v for k, v in filtros.items() if k != 'niveles'}
            extra = build_where_clause(filtros_sin_nivel, "")
            if extra and extra != "1=1":
                where_snies = extra
        
        # Niveles SNIES
        query_snies = f'''
            SELECT "NIVEL_DE_FORMACIÓN" as nivel, COUNT(*) as programas
            FROM snies.snies_programas
            WHERE {where_snies}
            AND "NIVEL_DE_FORMACIÓN" IS NOT NULL
            GROUP BY "NIVEL_DE_FORMACIÓN"
            ORDER BY programas DESC
        '''
        df_snies = conn.execute(query_snies).df()
        df_snies['fuente'] = 'SNIES (Edu. Superior)'
        df_snies.columns = ['tipo_formacion', 'programas', 'fuente']
        
        # Tipos SIET (filtrado por áreas derivadas de SNIES)
        where_siet_tipo = '"Tipo de Certificado" IS NOT NULL'
        if areas_desempeno_siet:
            areas_sql_t = ", ".join([f"'{a.replace(chr(39), chr(39)*2)}'" for a in areas_desempeno_siet])
            where_siet_tipo += f' AND "Area de Desempeño" IN ({areas_sql_t})'
        query_siet = f'''
            SELECT "Tipo de Certificado" as tipo, COUNT(*) as programas
            FROM siet.siet_programas
            WHERE {where_siet_tipo}
            GROUP BY "Tipo de Certificado"
            ORDER BY programas DESC
        '''
        df_siet = conn.execute(query_siet).df()
        df_siet['fuente'] = 'SIET (ETDH)'
        df_siet.columns = ['tipo_formacion', 'programas', 'fuente']
        
        # Combinar
        df_comp = pd.concat([df_snies, df_siet], ignore_index=True)
        return df_comp
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


# ==============================================================================
# EXPLORADOR INTERACTIVO - Consultas Multidimensionales Dinámicas
# ==============================================================================

def get_datos_explorador_interactivo(metrica, dimensiones, anio_inicio, anio_fin, filtros_base=None):
    """Consulta dinamica para el explorador interactivo.
    
    Args:
        metrica: str - 'Matriculados', 'Graduados', 'Inscritos', 'Admitidos', 'Primer Curso'
        dimensiones: list - Columnas de agrupacion en orden jerarquico
        anio_inicio: int
        anio_fin: int
        filtros_base: dict - Filtros del sidebar ya aplicados
    
    Returns:
        pd.DataFrame con las dimensiones y la metrica agregada
    """
    tabla_config = {
        'Matriculados': ('snies.snies_matriculados', 'MATRICULADOS'),
        'Graduados': ('snies.snies_graduados', 'GRADUADOS'),
        'Inscritos': ('snies.snies_inscritos', 'INSCRITOS'),
        'Admitidos': ('snies.snies_admitidos', 'ADMITIDOS'),
        'Primer Curso': ('snies.snies_matriculados_primer_curso', 'MATRICULADOS_PRIMER_CURSO'),
    }
    
    if metrica not in tabla_config:
        return pd.DataFrame()
    
    tabla, col_metrica = tabla_config[metrica]
    
    # Mapeo de nombres amigables a columnas reales
    dim_map = {
        'Ano': 'ANO',
        'Semestre': 'SEMESTRE',
        'Sexo': 'SEXO',
        'Nivel Academico': 'NIVEL_ACADEMICO',
        'Nivel Formacion': 'NIVEL_FORMACION',
        'Metodologia': 'METODOLOGIA',
        'Area Conocimiento': 'AREA_CONOCIMIENTO',
        'NBC': 'NBC',
        'Sector IES': 'SECTOR_IES',
        'Caracter IES': 'CARACTER_IES',
        'Departamento': 'DEPTO_PROGRAMA',
        'Municipio': 'MPIO_PROGRAMA',
        'Institucion': 'NOMBRE_IES',
        'IES Acreditada': 'IES_ACREDITADA',
        'Programa Acreditado': 'PROGRAMA_ACREDITADO',
    }
    
    cols_reales = []
    for d in dimensiones:
        if d in dim_map:
            cols_reales.append(dim_map[d])
    
    if not cols_reales:
        return pd.DataFrame()
    
    conn = get_conn()
    try:
        # SELECT: dimensiones + SUM(metrica) + COUNT(*)
        # Normalización de dimensiones con datos sucios en matriculados/graduados
        _normalize_sql = {
            'SECTOR_IES': "CASE WHEN UPPER(\"SECTOR_IES\") = 'PRIVADA' THEN 'PRIVADO' ELSE CAST(\"SECTOR_IES\" AS VARCHAR) END",
            'NIVEL_FORMACION': "CASE WHEN UPPER(\"NIVEL_FORMACION\") = 'TECNOLÓGICA' THEN 'TECNOLÓGICO' WHEN UPPER(\"NIVEL_FORMACION\") = 'UNIVERSITARIA' THEN 'UNIVERSITARIO' WHEN \"NIVEL_FORMACION\" LIKE 'ESPECIALIZACIÓN TÉCNICO PROFESION%' THEN 'ESPECIALIZACIÓN TÉCNICO PROFESIONAL' ELSE CAST(\"NIVEL_FORMACION\" AS VARCHAR) END",
            'CARACTER_IES': "CASE WHEN UPPER(\"CARACTER_IES\") = 'UNIVERSIDAD' THEN 'Universidad' WHEN UPPER(\"CARACTER_IES\") LIKE 'INSTITUCIÓN TECNOLÓG%' THEN 'Institución Tecnológica' WHEN UPPER(\"CARACTER_IES\") LIKE 'INSTITUCIÓN UNIVERSITARIA%' THEN 'Institución Universitaria/Escuela Tecnológica' WHEN UPPER(\"CARACTER_IES\") LIKE 'TÉCNICA PROF%' THEN 'Institución Técnica Profesional' ELSE CAST(\"CARACTER_IES\" AS VARCHAR) END",
        }
        select_parts = []
        for c, d in zip(cols_reales, dimensiones):
            if c in _normalize_sql:
                select_parts.append(f'{_normalize_sql[c]} as "{d}"')
            else:
                select_parts.append(f'CAST("{c}" AS VARCHAR) as "{d}"')
        select_parts.append(f'SUM(COALESCE(TRY_CAST("{col_metrica}" AS BIGINT), 0)) as valor')
        select_parts.append('COUNT(*) as registros')
        
        # WHERE — rango de años + filtros dinámicos via build_where_clause_matriculados
        condiciones = [f'TRY_CAST("ANO" AS INTEGER) >= {anio_inicio}', f'TRY_CAST("ANO" AS INTEGER) <= {anio_fin}']
        
        # Aplicar TODOS los filtros del sidebar (dinámico, sin mapeos hardcodeados)
        if filtros_base:
            extra_conds = build_where_clause_matriculados(filtros=filtros_base)
            condiciones.extend(extra_conds)
        
        where_clause = " AND ".join(condiciones)
        group_cols = []
        for c in cols_reales:
            if c in _normalize_sql:
                group_cols.append(_normalize_sql[c])
            else:
                group_cols.append(f'CAST("{c}" AS VARCHAR)')
        
        query = f"""
        SELECT {', '.join(select_parts)}
        FROM {tabla}
        WHERE {where_clause}
        GROUP BY {', '.join(group_cols)}
        HAVING SUM(COALESCE(TRY_CAST("{col_metrica}" AS BIGINT), 0)) > 0
        ORDER BY valor DESC
        """
        
        df = conn.execute(query).fetchdf()
        # Clean nulls in dimension columns
        for d in dimensiones:
            if d in df.columns:
                df[d] = df[d].fillna('Sin dato')
        return df
    except Exception as e:
        st.warning(f"Error en explorador: {e}")
        return pd.DataFrame()
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ==============================================================================
# SNIES ACADÉMICO - Educación Superior (Programas, Matriculados, Graduados)
# ==============================================================================

def get_benchmarking_data(nbc=None, depto=None, filtros=None):
    """Obtiene datos para Scatter Plot de benchmarking.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales (modalidades, sectores, niveles, caracteres)
    """
    conn = get_conn()
    try:
        where_parts = []
        if nbc:
            where_parts.append(f"p.\"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO\" = '{_esc(nbc)}'")
        if depto:
            where_parts.append(f"p.\"DEPARTAMENTO_OFERTA_PROGRAMA\" = '{_esc(depto)}'")
        if filtros:
            extra_where = build_where_clause(filtros, "p")
            if extra_where and extra_where != "1=1":
                where_parts.append(extra_where)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        query = f"""
        SELECT 
            p."NOMBRE_INSTITUCIÓN" as institucion,
            p."NOMBRE_DEL_PROGRAMA" as programa,
            COALESCE(p."NÚMERO_PERIODOS_DE_DURACIÓN", 0) as duracion,
            COALESCE(p."COSTO_MATRÍCULA_ESTUD_NUEVOS", 0) as costo,
            COALESCE(i."ACREDITADA_ALTA_CALIDAD", 'NO') as acreditada
        FROM snies.snies_programas p
        LEFT JOIN snies.snies_instituciones i ON p."CÓDIGO_INSTITUCIÓN" = i."CÓDIGO_INSTITUCIÓN"
        WHERE {where_clause}
        AND p."COSTO_MATRÍCULA_ESTUD_NUEVOS" > 0
        AND p."NÚMERO_PERIODOS_DE_DURACIÓN" > 0
        LIMIT 200
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error benchmarking: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_market_share(nbc=None, depto=None, filtros=None):
    """Obtiene cuota de mercado por IES basada en MATRICULADOS reales para HHI.
    
    P0 FIX: Usa build_where_clause_matriculados() para propagar TODOS los filtros
    (NBC, depto, municipio, area, busqueda) en vez de solo modalidades/sectores/niveles.
    
    Args:
        nbc: NBC escalar (legacy, se ignora si filtros['nbcs'] existe)
        depto: Depto escalar (legacy, se ignora si filtros['deptos'] existe) 
        filtros: Dict con filtros del panel
    """
    conn = get_conn()
    try:
        # P0 FIX: Delegar a build_where_clause_matriculados para TODOS los filtros
        condiciones = build_where_clause_matriculados(depto=depto, filtros=filtros)
        
        # Legacy: nbc escalar solo si no viene en filtros
        if nbc and not (filtros and filtros.get('nbcs')):
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        
        # Usar ultimo ano disponible DENTRO del subconjunto filtrado
        # (no el global MAX, que puede no tener datos para esta combinación)
        filtro_base = " AND ".join(condiciones) if condiciones else "1=1"
        condiciones.append(
            f'"ANO" = (SELECT MAX("ANO") FROM snies.snies_matriculados WHERE {filtro_base})'
        )
        
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        
        query = f"""
        WITH matricula_ies AS (
            SELECT 
                "NOMBRE_IES" as institucion,
                SUM(CAST("MATRICULADOS" AS BIGINT)) as matriculados
            FROM snies.snies_matriculados
            WHERE {where_clause}
            GROUP BY 1
        ),
        total AS (
            SELECT SUM(matriculados) as total FROM matricula_ies
        )
        SELECT 
            m.institucion,
            m.matriculados,
            (m.matriculados * 100.0 / NULLIF(t.total, 0)) as share
        FROM matricula_ies m, total t
        ORDER BY share DESC
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error market share: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_programas_detalle(nbc=None, filtros=None):
    """Obtiene detalle completo de programas con filtros aplicados.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        filtros: Dict opcional con filtros adicionales (modalidades, sectores, etc.)
    
    Returns:
        DataFrame con columnas: Institución, Programa, Nivel, Modalidad, Sector, 
        Carácter, Departamento, Municipio, Estado, Créditos
    """
    conn = get_conn()
    try:
        # Construir WHERE con filtros adicionales
        where_parts = []
        if nbc:
            where_parts.append(f"p.\"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO\" = '{_esc(nbc)}'")
        if filtros:
            extra_where = build_where_clause(filtros, "p")
            if extra_where and extra_where != "1=1":
                where_parts.append(extra_where)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        query = f"""
        SELECT 
            p."NOMBRE_INSTITUCIÓN" as "Institución",
            p."NOMBRE_DEL_PROGRAMA" as "Programa",
            p."NIVEL_DE_FORMACIÓN" as "Nivel",
            p."MODALIDAD" as "Modalidad",
            p."SECTOR" as "Sector",
            p."CARÁCTER_ACADÉMICO" as "Carácter",
            p."DEPARTAMENTO_OFERTA_PROGRAMA" as "Departamento",
            p."MUNICIPIO_OFERTA_PROGRAMA" as "Municipio",
            p."ESTADO_PROGRAMA" as "Estado",
            p."NÚMERO_CRÉDITOS" as "Créditos"
        FROM snies.snies_programas p
        WHERE {where_clause}
        ORDER BY p."NOMBRE_INSTITUCIÓN", p."NOMBRE_DEL_PROGRAMA"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error detalle programas: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_tendencia_matricula(nbc=None, depto=None, filtros=None):
    """Obtiene histórico de matrícula para calcular CAGR con filtros aplicados.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales
    
    CORRECCIÓN: Usa build_where_clause_matriculados() con IN exacto
    en lugar de LIKE inline para evitar inflación de datos.
    """
    conn = get_conn()
    try:
        condiciones = []
        if nbc:
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        
        # Usar función compartida (IN exacto, no LIKE)
        extra_conditions = build_where_clause_matriculados(depto, filtros)
        condiciones.extend(extra_conditions)
        
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        
        query = f"""
        SELECT 
            "ANO" as anio,
            SUM(CAST("MATRICULADOS" AS BIGINT)) as matriculados
        FROM snies.snies_matriculados
        WHERE {where_clause}
        GROUP BY "ANO"
        ORDER BY "ANO"
        """
        result = conn.execute(query).fetchdf()
        return result
    except Exception as e:
        st.warning(f"Error tendencia: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_tendencia_inscritos(nbc=None, depto=None, filtros=None):
    """Obtiene histórico de inscritos con filtros aplicados.
    CORRECCIÓN: Usa build_where_clause_matriculados() con IN exacto."""
    conn = get_conn()
    try:
        condiciones = []
        if nbc:
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        extra_conditions = build_where_clause_matriculados(depto, filtros)
        condiciones.extend(extra_conditions)
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        query = f"""
        SELECT "ANO" as anio, SUM(CAST("INSCRITOS" AS BIGINT)) as inscritos
        FROM snies.snies_inscritos WHERE {where_clause}
        GROUP BY "ANO" ORDER BY "ANO"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error inscritos: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_tendencia_admitidos(nbc=None, depto=None, filtros=None):
    """Obtiene histórico de admitidos con filtros aplicados.
    CORRECCIÓN: Usa build_where_clause_matriculados() con IN exacto."""
    conn = get_conn()
    try:
        condiciones = []
        if nbc:
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        extra_conditions = build_where_clause_matriculados(depto, filtros)
        condiciones.extend(extra_conditions)
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        query = f"""
        SELECT "ANO" as anio, SUM(CAST("ADMITIDOS" AS BIGINT)) as admitidos
        FROM snies.snies_admitidos WHERE {where_clause}
        GROUP BY "ANO" ORDER BY "ANO"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error admitidos: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_tendencia_primer_curso(nbc=None, depto=None, filtros=None):
    """Obtiene histórico de matriculados en primer curso con filtros aplicados.
    CORRECCIÓN: Usa build_where_clause_matriculados() con IN exacto."""
    conn = get_conn()
    try:
        condiciones = []
        if nbc:
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        extra_conditions = build_where_clause_matriculados(depto, filtros)
        condiciones.extend(extra_conditions)
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        query = f"""
        SELECT "ANO" as anio, SUM(CAST("MATRICULADOS_PRIMER_CURSO" AS BIGINT)) as primer_curso
        FROM snies.snies_matriculados_primer_curso WHERE {where_clause}
        GROUP BY "ANO" ORDER BY "ANO"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error primer curso: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_graduados_historico(nbc=None, depto=None, filtros=None):
    """Obtiene histórico de graduados con filtros aplicados.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales:
            - modalidades: lista de modalidades → mapea a METODOLOGIA
            - sectores: lista de sectores → mapea a SECTOR_IES
            - niveles: lista de niveles → mapea a NIVEL_FORMACION
    
    NOTA: snies_graduados tiene columnas diferente a snies_programas:
    - METODOLOGIA (no MODALIDAD)
    - SECTOR_IES (no SECTOR)
    - NIVEL_FORMACION (no NIVEL_DE_FORMACIÓN)
    - DEPTO_PROGRAMA (no DEPARTAMENTO_OFERTA_PROGRAMA)
    """
    conn = get_conn()
    try:
        # Condición base para NBC (opcional)
        condiciones = []
        if nbc:
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{_esc(nbc)}')")
        
        # Agregar filtros de territorio, modalidad, sector, nivel
        extra_conditions = build_where_clause_matriculados(depto, filtros)
        condiciones.extend(extra_conditions)
        
        where_clause = " AND ".join(condiciones) if condiciones else "1=1"
        
        query = f"""
        SELECT 
            "ANO" as anio,
            SUM(CAST("GRADUADOS" AS BIGINT)) as graduados
        FROM snies.snies_graduados
        WHERE {where_clause}
        GROUP BY "ANO"
        ORDER BY "ANO"
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        st.warning(f"Error graduados: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_graduados_nacionales(nbc_or_list, filtros=None):
    """Obtiene graduados del último año a nivel NACIONAL (sin filtro de departamento).
    
    Esto es necesario para comparar con vacantes APE que también son nacionales.
    
    Args:
        nbc_or_list: NBC string o lista de NBCs
        filtros: Dict opcional con filtros adicionales (niveles, estados, etc.)
            Se propagan via subquery puente a snies_programas para respetar
            nivel de formación, estado del programa, etc.
        
    Returns:
        int: Número de graduados del último año disponible a nivel nacional
    """
    conn = get_conn()
    try:
        # Construir condición NBC para tabla snies_graduados (columna "NBC", no "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO")
        condiciones = []
        if isinstance(nbc_or_list, list):
            if len(nbc_or_list) == 0:
                return 0
            escaped = [n.replace("'", "''") for n in nbc_or_list]
            values_in = ", ".join(f"UPPER('{e}')" for e in escaped)
            condiciones.append(f'UPPER("NBC") IN ({values_in})')
        else:
            safe_nbc = nbc_or_list.replace("'", "''")
            condiciones.append(f"UPPER(\"NBC\") = UPPER('{safe_nbc}')")

        # Propagar filtros adicionales (niveles, estados, etc.) via subquery puente
        if filtros:
            extra_conditions = build_where_clause_matriculados(filtros=filtros)
            # Excluir condiciones de NBC (ya las tenemos arriba) y de deptos (queremos nacional)
            for cond in extra_conditions:
                if '"NBC"' not in cond and '"DEPTO_PROGRAMA"' not in cond and '"MPIO_PROGRAMA"' not in cond:
                    condiciones.append(cond)

        nbc_cond = " AND ".join(condiciones) if condiciones else "1=1"
        
        query = f"""
        SELECT SUM(CAST("GRADUADOS" AS BIGINT)) as graduados
        FROM snies.snies_graduados
        WHERE {nbc_cond}
          AND "ANO" = (
              SELECT MAX("ANO") FROM snies.snies_graduados 
              WHERE {nbc_cond}
          )
        """
        result = conn.execute(query).fetchdf()
        return int(result['graduados'].iloc[0]) if not result.empty and result['graduados'].iloc[0] else 0
    except Exception as e:
        return 0
    finally:
        conn.close()


def get_estadisticas_basicas(nbc=None, depto=None, filtros=None):
    """Obtiene estadísticas básicas del NBC o filtros generales.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento opcional
        filtros: Dict opcional con filtros adicionales (modalidades, sectores, etc.)
    """
    conn = get_conn()
    try:
        where_parts = []
        if nbc:
            where_parts.append(f"\"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO\" = '{_esc(nbc)}'")
        if depto:
            where_parts.append(f"\"DEPARTAMENTO_OFERTA_PROGRAMA\" = '{_esc(depto)}'")
        if filtros:
            extra_where = build_where_clause(filtros, "")
            if extra_where and extra_where != "1=1":
                where_parts.append(extra_where)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        query = f"""
        SELECT 
            COUNT(*) as total_programas,
            COUNT(DISTINCT "NOMBRE_INSTITUCIÓN") as total_ies,
            AVG("COSTO_MATRÍCULA_ESTUD_NUEVOS") as costo_promedio,
            COUNT(DISTINCT "MODALIDAD") as modalidades
        FROM snies.snies_programas
        WHERE {where_clause}
        """
        result = conn.execute(query).fetchone()
        return {
            "total_programas": result[0] or 0,
            "total_ies": result[1] or 0,
            "costo_promedio": result[2] or 0,
            "modalidades": result[3] or 0
        }
    except Exception as e:
        return {"total_programas": 0, "total_ies": 0, "costo_promedio": 0, "modalidades": 0}
    finally:
        conn.close()


def get_desglose_academico(nbc=None, depto=None, filtros=None):
    """
    Obtiene desgloses por modalidad, sector, nivel formación, 
    créditos, periodicidad y carácter académico para gráficos de torta/barras.
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento opcional
        filtros: Dict opcional con filtros adicionales (modalidades, sectores, etc.)
    """
    conn = get_conn()
    desgloses = {}
    
    try:
        # Construir cláusula WHERE base
        where_parts = []
        if nbc:
            where_parts.append(f"\"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO\" = '{_esc(nbc)}'")
        if depto:
            where_parts.append(f"\"DEPARTAMENTO_OFERTA_PROGRAMA\" = '{_esc(depto)}'")
        if filtros:
            extra_where = build_where_clause(filtros, "")
            if extra_where and extra_where != "1=1":
                where_parts.append(extra_where)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        
        # 1. Desglose por MODALIDAD (Presencial, Virtual, Distancia)
        query_modalidad = f"""
        SELECT 
            "MODALIDAD" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "MODALIDAD" IS NOT NULL
        GROUP BY "MODALIDAD"
        ORDER BY cantidad DESC
        """
        desgloses['modalidad'] = conn.execute(query_modalidad).fetchdf()
        
        # 2. Desglose por SECTOR (Oficial/Privado)
        query_sector = f"""
        SELECT 
            "SECTOR" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "SECTOR" IS NOT NULL
        GROUP BY "SECTOR"
        ORDER BY cantidad DESC
        """
        desgloses['sector'] = conn.execute(query_sector).fetchdf()
        
        # 3. Desglose por NIVEL DE FORMACIÓN
        query_nivel = f"""
        SELECT 
            "NIVEL_DE_FORMACIÓN" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "NIVEL_DE_FORMACIÓN" IS NOT NULL
        GROUP BY "NIVEL_DE_FORMACIÓN"
        ORDER BY cantidad DESC
        """
        desgloses['nivel_formacion'] = conn.execute(query_nivel).fetchdf()
        
        # 4. Desglose por CARÁCTER ACADÉMICO (Universidad, Inst. Universitaria, etc.)
        query_caracter = f"""
        SELECT 
            "CARÁCTER_ACADÉMICO" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "CARÁCTER_ACADÉMICO" IS NOT NULL
        GROUP BY "CARÁCTER_ACADÉMICO"
        ORDER BY cantidad DESC
        """
        desgloses['caracter_academico'] = conn.execute(query_caracter).fetchdf()
        
        # 5. Distribución de CRÉDITOS (rangos)
        query_creditos = f"""
        SELECT 
            CASE 
                WHEN "NÚMERO_CRÉDITOS" IS NULL OR "NÚMERO_CRÉDITOS" = 0 THEN 'Sin info'
                WHEN "NÚMERO_CRÉDITOS" < 60 THEN '< 60 créditos'
                WHEN "NÚMERO_CRÉDITOS" < 100 THEN '60-99 créditos'
                WHEN "NÚMERO_CRÉDITOS" < 150 THEN '100-149 créditos'
                WHEN "NÚMERO_CRÉDITOS" < 180 THEN '150-179 créditos'
                ELSE '180+ créditos'
            END as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        GROUP BY 1
        ORDER BY 
            CASE categoria
                WHEN '< 60 créditos' THEN 1
                WHEN '60-99 créditos' THEN 2
                WHEN '100-149 créditos' THEN 3
                WHEN '150-179 créditos' THEN 4
                WHEN '180+ créditos' THEN 5
                ELSE 6
            END
        """
        desgloses['creditos'] = conn.execute(query_creditos).fetchdf()
        
        # 6. Distribución de DURACIÓN (períodos/semestres)
        query_duracion = f"""
        SELECT 
            CASE 
                WHEN "NÚMERO_PERIODOS_DE_DURACIÓN" IS NULL OR "NÚMERO_PERIODOS_DE_DURACIÓN" = 0 THEN 'Sin info'
                WHEN "NÚMERO_PERIODOS_DE_DURACIÓN" <= 4 THEN '1-4 semestres'
                WHEN "NÚMERO_PERIODOS_DE_DURACIÓN" <= 6 THEN '5-6 semestres'
                WHEN "NÚMERO_PERIODOS_DE_DURACIÓN" <= 8 THEN '7-8 semestres'
                WHEN "NÚMERO_PERIODOS_DE_DURACIÓN" <= 10 THEN '9-10 semestres'
                ELSE '11+ semestres'
            END as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        GROUP BY 1
        ORDER BY 
            CASE categoria
                WHEN '1-4 semestres' THEN 1
                WHEN '5-6 semestres' THEN 2
                WHEN '7-8 semestres' THEN 3
                WHEN '9-10 semestres' THEN 4
                WHEN '11+ semestres' THEN 5
                ELSE 6
            END
        """
        desgloses['duracion'] = conn.execute(query_duracion).fetchdf()
        
        # 7. Desglose por PERIODICIDAD (Semestral, Anual, etc.)
        query_periodicidad = f"""
        SELECT 
            COALESCE("PERIODICIDAD", 'Sin info') as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        GROUP BY "PERIODICIDAD"
        ORDER BY cantidad DESC
        """
        desgloses['periodicidad'] = conn.execute(query_periodicidad).fetchdf()
        
        # 8. Desglose por ESTADO PROGRAMA (Activo/Inactivo)
        query_estado = f"""
        SELECT 
            "ESTADO_PROGRAMA" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "ESTADO_PROGRAMA" IS NOT NULL
        GROUP BY "ESTADO_PROGRAMA"
        ORDER BY cantidad DESC
        """
        desgloses['estado'] = conn.execute(query_estado).fetchdf()
        
        # 9. Desglose por CICLOS PROPEDÉUTICOS
        query_ciclos = f"""
        SELECT 
            CASE 
                WHEN "SE_OFRECE_POR_CICLOS_PROPEDÉUT" = 'SI' THEN 'Sí ofrece'
                WHEN "SE_OFRECE_POR_CICLOS_PROPEDÉUT" = 'NO' THEN 'No ofrece'
                ELSE 'Sin info'
            END as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        GROUP BY 1
        ORDER BY cantidad DESC
        """
        desgloses['ciclos_propedeuticos'] = conn.execute(query_ciclos).fetchdf()
        
        # 10. Distribución geográfica (top departamentos)
        # P1 FIX: Usa where_clause en vez de raw nbc para respetar TODOS los filtros
        query_deptos = f"""
        SELECT 
            "DEPARTAMENTO_OFERTA_PROGRAMA" as categoria,
            COUNT(*) as cantidad
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "DEPARTAMENTO_OFERTA_PROGRAMA" IS NOT NULL
        GROUP BY "DEPARTAMENTO_OFERTA_PROGRAMA"
        ORDER BY cantidad DESC
        LIMIT 10
        """
        desgloses['departamentos'] = conn.execute(query_deptos).fetchdf()
        
        # 11. Estadísticas numéricas adicionales
        query_stats = f"""
        SELECT 
            AVG("NÚMERO_CRÉDITOS") as creditos_promedio,
            AVG("NÚMERO_PERIODOS_DE_DURACIÓN") as duracion_promedio,
            AVG("COSTO_MATRÍCULA_ESTUD_NUEVOS") as costo_promedio,
            MIN("COSTO_MATRÍCULA_ESTUD_NUEVOS") as costo_min,
            MAX("COSTO_MATRÍCULA_ESTUD_NUEVOS") as costo_max,
            AVG("VIGENCIA_AÑOS") as vigencia_promedio
        FROM snies.snies_programas
        WHERE {where_clause}
        AND "NÚMERO_CRÉDITOS" > 0
        """
        stats_result = conn.execute(query_stats).fetchone()
        desgloses['estadisticas'] = {
            'creditos_promedio': round(stats_result[0] or 0, 1),
            'duracion_promedio': round(stats_result[1] or 0, 1),
            'costo_promedio': round(stats_result[2] or 0, 0),
            'costo_min': round(stats_result[3] or 0, 0),
            'costo_max': round(stats_result[4] or 0, 0),
            'vigencia_promedio': round(stats_result[5] or 0, 1)
        }
        
        return desgloses
        
    except Exception as e:
        st.warning(f"Error obteniendo desglose académico: {e}")
        return desgloses
    finally:
        conn.close()


# ==============================================================================
# TERRITORIAL - Conectividad, PDET, Contexto Geográfico
# ==============================================================================

def get_conectividad_territorial(depto=None):
    """Obtiene datos de conectividad por departamento incluyendo 4G.
    Si depto=None, agrega a nivel nacional por departamento.
    
    Fuentes:
    - conectividad.cobertura_movil_tecnologia (columna departamento_1 = nombre)
    - conectividad.internet_fijo_accesos (columna departamento = nombre)
    """
    conn = get_conn()
    try:
        # Nivel de agrupación: municipio si hay depto, departamento si nacional
        if depto:
            group_col_4g = "municipio_1"
            group_col_inet = "municipio_1"
            group_label = "municipio"
            where_4g = _depto_where("departamento_1", depto, "WHERE")
            where_inet = _depto_where("departamento", depto, "WHERE")
        else:
            group_col_4g = "departamento_1"
            group_col_inet = "departamento"
            group_label = "municipio"  # keep column name for compatibility
            where_4g = ""
            where_inet = ""
        
        query_4g = f"""
        SELECT 
            "{group_col_4g}" as {group_label},
            COUNT(*) as registros,
            SUM(CASE WHEN cobertuta_4g = 'S' THEN 1 ELSE 0 END) as con_4g,
            SUM(CASE WHEN cobertura_lte = 'S' THEN 1 ELSE 0 END) as con_lte,
            SUM(CASE WHEN cobertura_5g = 'S' THEN 1 ELSE 0 END) as con_5g
        FROM conectividad.cobertura_movil_tecnologia
        {where_4g}
        GROUP BY "{group_col_4g}"
        """
        df_4g = conn.execute(query_4g).fetchdf()
        
        query_internet = f"""
        SELECT 
            "{group_col_inet}" as {group_label},
            SUM(CAST(REPLACE(no_de_accesos, ',', '') AS BIGINT)) as accesos_internet
        FROM conectividad.internet_fijo_accesos
        {where_inet}
        GROUP BY "{group_col_inet}"
        """
        df_internet = conn.execute(query_internet).fetchdf()
        
        if df_4g.empty and df_internet.empty:
            return pd.DataFrame(columns=['municipio', 'accesos_internet', 'cobertura_4g_pct', 'indice_conectividad'])

        # Combinar datos
        if not df_4g.empty:
            df_4g['cobertura_4g_pct'] = (df_4g['con_4g'] + df_4g['con_lte']).clip(upper=df_4g['registros']) / df_4g['registros'].replace(0, 1)
        
        if not df_internet.empty and not df_4g.empty:
            df = pd.merge(df_internet, df_4g[['municipio', 'cobertura_4g_pct']], on='municipio', how='outer').fillna(0)
        elif not df_4g.empty:
            df = df_4g.rename(columns={'registros': 'accesos_internet'})
        else:
            df = df_internet
            df['cobertura_4g_pct'] = 0.5
        
        # Calcular índice: Internet×0.6 + 4G×0.4
        max_internet = df['accesos_internet'].max() if df['accesos_internet'].max() > 0 else 1
        df['norm_internet'] = df['accesos_internet'] / max_internet
        df['indice_conectividad'] = (df['norm_internet'] * 0.6) + (df['cobertura_4g_pct'] * 0.4)
        
        return df
    except Exception as e:
        print(f"[Conectividad] Error: {e}")
        return pd.DataFrame(columns=['municipio', 'accesos_internet', 'cobertura_4g_pct', 'indice_conectividad'])
    finally:
        conn.close()


def get_municipios_pdet(depto=None):
    """Obtiene municipios PDET del territorio."""
    conn = get_conn()
    try:
        where = _depto_where("NombreDepartamento", depto, "WHERE")
        query = f"""
        SELECT 
            "NombreDepartamento" as departamento,
            "NombreMunicipio" as municipio,
            "NombreSubregion" as subregion
        FROM territorial.municipios_pdet
        {where}
        """
        df = conn.execute(query).fetchdf()
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# ==============================================================================
# TERRITORIAL - Indicadores Educativos y Socioeconómicos por Departamento
# ==============================================================================

def get_indicadores_educativos_depto(depto):
    """Obtiene indicadores educativos departamentales: TCB, TTI, Matrícula.
    
    Fuentes:
    - estadisticas_es.es_tcb_departamento (Tasa Cobertura Bruta ES)
    - estadisticas_es.es_tti_departamento (Tasa Tránsito Inmediato)
    - estadisticas_es.es_matricula_departamento (Matrícula ES)
    
    Returns:
        Dict con DataFrames históricos y valores más recientes.
    """
    result = {
        'tcb_actual': None,
        'tcb_historico': pd.DataFrame(),
        'tti_actual': None,
        'tti_historico': pd.DataFrame(),
        'matricula_actual': None,
        'matricula_historico': pd.DataFrame(),
        'tiene_datos': False,
        'fuente': 'SNIES - MinEducación (Estadísticas ES Colombia)',
        'nivel': 'departamental' if depto else 'nacional',
    }
    
    conn = get_conn()
    try:
        # Si hay depto: filtrar con strip_accents matching
        # Si no hay depto: promediar a nivel nacional
        where_clause = _depto_where("DEPARTAMENTO", depto, "WHERE")
        
        if depto:
            # Departamental: valores directos
            df_tcb = conn.execute(f"""
                SELECT "AÑO" as anio, CAST(TASA_COBERTURA_BRUTA AS FLOAT) as tasa
                FROM estadisticas_es.es_tcb_departamento
                {where_clause}
                ORDER BY "AÑO"
            """).fetchdf()
        else:
            # Nacional: promedio ponderado de todos los departamentos por año
            df_tcb = conn.execute("""
                SELECT "AÑO" as anio, AVG(CAST(TASA_COBERTURA_BRUTA AS FLOAT)) as tasa
                FROM estadisticas_es.es_tcb_departamento
                GROUP BY "AÑO" ORDER BY "AÑO"
            """).fetchdf()
        if not df_tcb.empty:
            result['tcb_historico'] = df_tcb
            result['tcb_actual'] = float(df_tcb.iloc[-1]['tasa'])
            result['tiene_datos'] = True
        
        if depto:
            df_tti = conn.execute(f"""
                SELECT "AÑO" as anio, CAST(TASA_TRANSITO_INMEDIATO AS FLOAT) as tasa
                FROM estadisticas_es.es_tti_departamento
                {where_clause}
                ORDER BY "AÑO"
            """).fetchdf()
        else:
            df_tti = conn.execute("""
                SELECT "AÑO" as anio, AVG(CAST(TASA_TRANSITO_INMEDIATO AS FLOAT)) as tasa
                FROM estadisticas_es.es_tti_departamento
                GROUP BY "AÑO" ORDER BY "AÑO"
            """).fetchdf()
        if not df_tti.empty:
            result['tti_historico'] = df_tti
            result['tti_actual'] = float(df_tti.iloc[-1]['tasa'])
            result['tiene_datos'] = True
        
        if depto:
            df_mat = conn.execute(f"""
                SELECT "AÑO" as anio, CAST(CANTIDAD_MATRICULADOS AS INTEGER) as matriculados
                FROM estadisticas_es.es_matricula_departamento
                {where_clause}
                ORDER BY "AÑO"
            """).fetchdf()
        else:
            df_mat = conn.execute("""
                SELECT "AÑO" as anio, SUM(CAST(CANTIDAD_MATRICULADOS AS INTEGER)) as matriculados
                FROM estadisticas_es.es_matricula_departamento
                GROUP BY "AÑO" ORDER BY "AÑO"
            """).fetchdf()
        if not df_mat.empty:
            result['matricula_historico'] = df_mat
            result['matricula_actual'] = int(df_mat.iloc[-1]['matriculados'])
            result['tiene_datos'] = True
        
        return result
    except Exception as e:
        print(f"[IndicadoresED] Error: {e}")
        return result
    finally:
        conn.close()


def get_graduados_depto_nbc(nbc, depto=None, filtros=None):
    """Graduados del NBC por año. Si depto=None, agrega a nivel nacional.
    
    Args:
        nbc: NBC string
        depto: Departamento opcional
        filtros: Dict con filtros (niveles, estados, etc.) propagados via subquery puente
    
    Returns:
        DataFrame con columnas [anio, graduados].
    """
    if not nbc:
        return pd.DataFrame()
    conn = get_conn()
    try:
        where_depto = _depto_where("DEPTO_PROGRAMA", depto)
        condiciones = [
            build_nbc_match_condition(nbc)
        ]
        if filtros:
            extra = build_where_clause_matriculados(filtros=filtros)
            for cond in extra:
                if '"NBC"' not in cond and '"DEPTO_PROGRAMA"' not in cond and '"MPIO_PROGRAMA"' not in cond:
                    condiciones.append(cond)
        where_base = " AND ".join(condiciones)
        df = conn.execute(f"""
            SELECT "ANO" as anio, SUM(CAST("GRADUADOS" AS INTEGER)) as graduados
            FROM snies.snies_graduados
            WHERE {where_base}
            {where_depto}
            GROUP BY "ANO"
            ORDER BY "ANO"
        """).fetchdf()
        return df
    except Exception as e:
        print(f"[GradDeptoNBC] Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_matriculados_depto_nbc(nbc, depto=None, filtros=None):
    """Matriculados del NBC por año. Si depto=None, agrega a nivel nacional.
    
    Args:
        nbc: NBC string
        depto: Departamento opcional
        filtros: Dict con filtros (niveles, estados, etc.) propagados via subquery puente
    
    Returns:
        DataFrame con columnas [anio, matriculados].
    """
    if not nbc:
        return pd.DataFrame()
    conn = get_conn()
    try:
        where_depto = _depto_where("DEPTO_PROGRAMA", depto)
        condiciones = [
            build_nbc_match_condition(nbc)
        ]
        if filtros:
            extra = build_where_clause_matriculados(filtros=filtros)
            for cond in extra:
                if '"NBC"' not in cond and '"DEPTO_PROGRAMA"' not in cond and '"MPIO_PROGRAMA"' not in cond:
                    condiciones.append(cond)
        where_base = " AND ".join(condiciones)
        df = conn.execute(f"""
            SELECT "ANO" as anio, SUM(CAST("MATRICULADOS" AS INTEGER)) as matriculados
            FROM snies.snies_matriculados
            WHERE {where_base}
            {where_depto}
            GROUP BY "ANO"
            ORDER BY "ANO"
        """).fetchdf()
        return df
    except Exception as e:
        print(f"[MatDeptoNBC] Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_oferta_programas_depto(nbc, depto=None, filtros=None):
    """Programas del NBC. Si depto=None, todos los departamentos.
    
    Args:
        nbc: NBC string
        depto: Departamento opcional
        filtros: Dict con filtros (niveles, estados, etc.) aplicados directamente
    
    Returns:
        DataFrame con detalle de programas ofertados.
    """
    if not nbc:
        return pd.DataFrame()
    conn = get_conn()
    try:
        where_depto = _depto_where("DEPARTAMENTO_OFERTA_PROGRAMA", depto)
        condiciones = [
            build_nbc_match_condition(nbc, '"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO"')
        ]
        # snies_programas: match directo (no necesita subquery puente)
        if filtros:
            if filtros.get('niveles'):
                vals = "', '".join([n.replace("'", "''") for n in filtros['niveles']])
                condiciones.append(f'"NIVEL_DE_FORMACIÓN" IN (\'{vals}\')')
            if filtros.get('estados'):
                vals = "', '".join([e.replace("'", "''") for e in filtros['estados']])
                condiciones.append(f'"ESTADO_PROGRAMA" IN (\'{vals}\')')
            if filtros.get('modalidades'):
                vals = "', '".join([m.replace("'", "''") for m in filtros['modalidades']])
                condiciones.append(f'"MODALIDAD" IN (\'{vals}\')')
            if filtros.get('sectores'):
                vals = "', '".join([s.replace("'", "''") for s in filtros['sectores']])
                condiciones.append(f'"SECTOR" IN (\'{vals}\')')
            if filtros.get('caracteres'):
                vals = "', '".join([c.replace("'", "''") for c in filtros['caracteres']])
                condiciones.append(f'"CARÁCTER_ACADÉMICO" IN (\'{vals}\')')
        where_base = " AND ".join(condiciones)
        df = conn.execute(f"""
            SELECT 
                "NOMBRE_INSTITUCIÓN" as ies,
                "NOMBRE_DEL_PROGRAMA" as programa,
                "NIVEL_DE_FORMACIÓN" as nivel,
                "MODALIDAD" as metodologia,
                "ESTADO_PROGRAMA" as estado,
                "DEPARTAMENTO_OFERTA_PROGRAMA" as departamento,
                "MUNICIPIO_OFERTA_PROGRAMA" as municipio
            FROM snies.snies_programas
            WHERE {where_base}
            {where_depto}
            ORDER BY "ESTADO_PROGRAMA", "NIVEL_DE_FORMACIÓN"
        """).fetchdf()
        return df
    except Exception as e:
        print(f"[OfertaDepto] Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_salarios_depto(depto=None):
    """Salarios promedio del sector público. Si depto=None, promedio nacional.
    
    Returns:
        Dict con salario general y por nivel educativo.
    """
    result = {
        'salario_promedio': None,
        'salario_mediana': None,
        'cantidad_empleados': 0,
        'por_nivel_educativo': pd.DataFrame(),
        'tiene_datos': False,
        'fuente': 'SIGEP - Función Pública',
        'nivel': 'departamental' if depto else 'nacional',
    }
    conn = get_conn()
    try:
        if depto:
            where_gen = _depto_where("departamentodenacimiento", depto, "WHERE")
            df_gen = conn.execute(f"""
                SELECT salario_promedio, salario_mediana, cantidad_empleados
                FROM datos_complementarios.salarios_por_departamento
                {where_gen}
                LIMIT 1
            """).fetchdf()
        else:
            # Nacional: promedio de todos los departamentos
            df_gen = conn.execute("""
                SELECT AVG(salario_promedio) as salario_promedio,
                       AVG(salario_mediana) as salario_mediana,
                       SUM(cantidad_empleados) as cantidad_empleados
                FROM datos_complementarios.salarios_por_departamento
            """).fetchdf()
        if not df_gen.empty and df_gen.iloc[0]['salario_promedio'] is not None:
            result['salario_promedio'] = float(df_gen.iloc[0]['salario_promedio'])
            result['salario_mediana'] = float(df_gen.iloc[0]['salario_mediana'])
            result['cantidad_empleados'] = int(df_gen.iloc[0]['cantidad_empleados'])
            result['tiene_datos'] = True
        
        if depto:
            where_edu = _depto_where("departamentodenacimiento", depto, "WHERE")
            df_edu = conn.execute(f"""
                SELECT nivel_edu_principal as nivel_educativo, 
                       salario_promedio, salario_mediana, cantidad_empleados
                FROM datos_complementarios.salarios_educacion_x_departamento
                {where_edu}
                ORDER BY salario_promedio DESC
            """).fetchdf()
        else:
            df_edu = conn.execute("""
                SELECT nivel_edu_principal as nivel_educativo,
                       AVG(salario_promedio) as salario_promedio,
                       AVG(salario_mediana) as salario_mediana,
                       SUM(cantidad_empleados) as cantidad_empleados
                FROM datos_complementarios.salarios_educacion_x_departamento
                GROUP BY nivel_edu_principal
                ORDER BY salario_promedio DESC
            """).fetchdf()
        if not df_edu.empty:
            result['por_nivel_educativo'] = df_edu
            result['tiene_datos'] = True
        
        return result
    except Exception as e:
        print(f"[SalariosDepto] Error: {e}")
        return result
    finally:
        conn.close()


def get_ranking_departamental_nbc(nbc, filtros=None):
    """Ranking de departamentos por graduados del NBC.
    
    Args:
        nbc: NBC string
        filtros: Dict con filtros (niveles, estados, etc.) propagados via subquery puente
    
    Returns:
        DataFrame con [departamento, graduados] ordenado descendente.
    """
    if not nbc:
        return pd.DataFrame()
    conn = get_conn()
    try:
        condiciones = [
            build_nbc_match_condition(nbc)
        ]
        if filtros:
            extra = build_where_clause_matriculados(filtros=filtros)
            for cond in extra:
                if '"NBC"' not in cond and '"DEPTO_PROGRAMA"' not in cond and '"MPIO_PROGRAMA"' not in cond:
                    condiciones.append(cond)
        where_base = " AND ".join(condiciones)
        df = conn.execute(f"""
            SELECT "DEPTO_PROGRAMA" as departamento, 
                   SUM(CAST("GRADUADOS" AS INTEGER)) as graduados
            FROM snies.snies_graduados
            WHERE {where_base}
            GROUP BY "DEPTO_PROGRAMA"
            ORDER BY graduados DESC
        """).fetchdf()
        return df
    except Exception as e:
        print(f"[RankingDepto] Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


# ==============================================================================
# LABORAL - Mercado Laboral (Vacantes, Salarios, Competencias)
# ==============================================================================

def get_vacantes_reales(nbc=None):
    """Obtiene vacantes reales del APE por ocupaciones relacionadas al NBC.
    
    Estrategia de conexión (ordenada por prioridad):
    1. ML: Matching semántico con sentence-transformers (si disponible)
    2. Búsqueda por palabras clave del NBC en nombre de ocupación
    3. Áreas de cualificación -> prefijos de código CUOC
    4. Fallback: Top vacantes generales
    
    Fuente: APE - Agencia Pública de Empleo (SENA)
    """
    conn = get_conn()
    try:
        if nbc:
            # ESTRATEGIA 1: ML Matching Semántico (prioridad máxima)
            if ML_AVAILABLE:
                try:
                    # Cargar todas las vacantes para ML matching
                    query_all = """
                    SELECT 
                        codigo_cuoc,
                        ocupacion as nombre_ocupacion,
                        COALESCE(vacantes_2024, 0) as vacantes_2024,
                        COALESCE(vacantes_2023, 0) as vacantes_2023
                    FROM tendencias_laborales.vacantes_ape_clean
                    WHERE ocupacion IS NOT NULL
                    """
                    all_vacantes = conn.execute(query_all).fetchdf()
                    
                    if not all_vacantes.empty:
                        # Matching semántico con threshold adaptativo
                        contexto_enriquecido = _enriquecer_contexto_nbc(nbc)
                        query_ml = f"Profesional en {contexto_enriquecido}. Egresado de programas de {contexto_enriquecido}."
                        matched = match_nbc_to_vacantes(nbc, all_vacantes, top_k=30, threshold=0.62, query_override=query_ml)
                        
                        # Si hay pocos resultados, bajar threshold para NBCs con pocas ocupaciones directas
                        if matched.empty or len(matched) < 3:
                            matched = match_nbc_to_vacantes(nbc, all_vacantes, top_k=30, threshold=0.50, query_override=query_ml)
                        
                        if not matched.empty:
                            # Filtrar ocupaciones genéricas/ruidosas
                            ruido = ['operario acuicola', 'audiologos', 'instrumentadores',
                                    'otros instructores', 'otros artistas nca', 'sommeliers',
                                    'metrologia', 'quirurgicos', 'transcriptores', 'meseros',
                                    'zapateros', 'regentes de farmacia',
                                    'vendedor', 'auxiliar de almacen', 'secretaria', 'recepcionista',
                                    'mensajero', 'conserje', 'vigilante', 'aseador', 'camarero',
                                    'cajero', 'conductor', 'operario de produccion']
                            matched = matched[~matched["nombre_ocupacion"].str.lower().str.contains('|'.join(ruido), na=False)]
                            # Renombrar columna para consistencia
                            matched = matched.rename(columns={"nombre_ocupacion": "ocupacion"})
                            matched = matched.sort_values("vacantes_2024", ascending=False).head(20)
                            if not matched.empty:
                                return matched[["codigo_cuoc", "ocupacion", "vacantes_2024", "vacantes_2023", "similitud_ml"]]
                except Exception as e:
                    st.warning(f"ML matching falló, usando fallback: {e}")
            
            # ESTRATEGIA 2: Búsqueda semántica por palabras del NBC
            # Extraer palabras clave del nombre del NBC (>3 caracteres, excluir conectores)
            stopwords = STOPWORDS
            palabras = [p.lower() for p in nbc.split() if len(p) > 3 and p.lower() not in stopwords]
            
            if palabras:
                like_clauses = " OR ".join([f"LOWER(ocupacion) LIKE '%{p}%'" for p in palabras[:3]])
                query_semantica = f"""
                SELECT 
                    codigo_cuoc,
                    ocupacion,
                    COALESCE(vacantes_2024, 0) as vacantes_2024,
                    COALESCE(vacantes_2023, 0) as vacantes_2023
                FROM tendencias_laborales.vacantes_ape_clean
                WHERE {like_clauses}
                ORDER BY vacantes_2024 DESC
                LIMIT 20
                """
                df = conn.execute(query_semantica).fetchdf()
                if not df.empty:
                    return df
            
            # NOTA: Se eliminó estrategia 3 (mapeo_nbc_cuoc) por tener datos incorrectos
            # El ML matching (estrategia 1) es suficiente y más preciso
        
        # FALLBACK: Top vacantes generales
        query_general = """
        SELECT 
            codigo_cuoc,
            ocupacion,
            COALESCE(vacantes_2024, 0) as vacantes_2024,
            COALESCE(vacantes_2023, 0) as vacantes_2023
        FROM tendencias_laborales.vacantes_ape_clean
        ORDER BY vacantes_2024 DESC
        LIMIT 20
        """
        return conn.execute(query_general).fetchdf()
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


def get_competencias_cuoc(nbc):
    """Obtiene conocimientos y destrezas de ocupaciones asociadas al NBC.
    
    Estrategia mejorada:
    1. ML: Matching semántico con sentence-transformers (si disponible)
    2. Si no hay resultados significativos, busca por nombre de ocupación similar al NBC
    3. Usa códigos del mapeo NBC->CUOC como fallback
    
    Fuente: CUOC - Clasificación Única de Ocupaciones para Colombia (MinTrabajo)
    """
    conn = get_conn()
    try:
        df_conocimientos = pd.DataFrame()
        df_destrezas = pd.DataFrame()
        
        # ESTRATEGIA 1: ML Matching Semántico (prioridad máxima)
        if ML_AVAILABLE:
            try:
                # Cargar conocimientos para ML matching
                query_all_conocimientos = """
                SELECT codigo_ocupacion, nombre_ocupacion, conocimiento
                FROM competencias.cuoc_conocimientos
                WHERE conocimiento IS NOT NULL
                """
                all_conocimientos = conn.execute(query_all_conocimientos).fetchdf()
                
                if not all_conocimientos.empty:
                    matched_conocimientos = match_nbc_to_competencias(nbc, all_conocimientos, tipo="conocimientos", top_k=50, threshold=0.40)
                    if not matched_conocimientos.empty:
                        df_conocimientos = matched_conocimientos.groupby("conocimiento").agg(
                            frecuencia=("conocimiento", "count"),
                            similitud_max=("similitud_ml", "max")
                        ).reset_index().sort_values("similitud_max", ascending=False).head(10)
                
                # Cargar destrezas para ML matching
                query_all_destrezas = """
                SELECT codigo_ocupacion, nombre_ocupacion, destreza
                FROM competencias.cuoc_destrezas
                WHERE destreza IS NOT NULL
                """
                all_destrezas = conn.execute(query_all_destrezas).fetchdf()
                
                if not all_destrezas.empty:
                    matched_destrezas = match_nbc_to_competencias(nbc, all_destrezas, tipo="destrezas", top_k=50, threshold=0.40)
                    if not matched_destrezas.empty:
                        df_destrezas = matched_destrezas.groupby("destreza").agg(
                            frecuencia=("destreza", "count"),
                            similitud_max=("similitud_ml", "max")
                        ).reset_index().sort_values("similitud_max", ascending=False).head(10)
                
                if not df_conocimientos.empty:
                    return df_conocimientos, df_destrezas
            except Exception as e:
                pass  # Fallback a estrategias tradicionales
        
        # ESTRATEGIA 2: Buscar ocupaciones por nombre similar al NBC
        # Extraer palabras clave del NBC
        palabras_nbc = [p.lower() for p in nbc.split() if len(p) > 3]
        if palabras_nbc:
            like_clauses = " OR ".join([f"LOWER(nombre_ocupacion) LIKE '%{p}%'" for p in palabras_nbc[:3]])
            
            # Obtener conocimientos
            query_conocimientos = f"""
            SELECT conocimiento, COUNT(*) as frecuencia
            FROM competencias.cuoc_conocimientos
            WHERE {like_clauses}
            GROUP BY conocimiento
            ORDER BY frecuencia DESC
            LIMIT 10
            """
            df_conocimientos = conn.execute(query_conocimientos).fetchdf()
            
            # Obtener destrezas
            query_destrezas = f"""
            SELECT destreza, COUNT(*) as frecuencia
            FROM competencias.cuoc_destrezas
            WHERE {like_clauses}
            GROUP BY destreza
            ORDER BY frecuencia DESC
            LIMIT 10
            """
            df_destrezas = conn.execute(query_destrezas).fetchdf()
            
            if not df_conocimientos.empty:
                return df_conocimientos, df_destrezas
        
        # NOTA: Se eliminó estrategia 3 (mapeo_nbc_cuoc) por tener datos incorrectos
        # Las estrategias 1 (ML) y 2 (búsqueda por nombre) son suficientes
        
        return df_conocimientos, df_destrezas
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()


def get_salarios_reales(nbc=None, departamento=None):
    """Obtiene datos REALES de referencia salarial de múltiples fuentes oficiales.
    
    Fuentes de datos reales (en orden de prioridad):
    1. OLE IBC: Ingreso Base de Cotización de graduados (MEN - OLE)
       - Rangos por nivel de formación (Pregrado/Posgrado) y sector (Oficial/Privado)
    2. SIGEP: Salarios reales por nivel educativo (sector público, 48,630 empleados)
       - Promedio, mediana, mín, máx por nivel educativo
    3. SIGEP Departamental: Salarios por nivel educativo y departamento
    
    NO se fabrican salarios. Se retornan datos reales con su fuente explícita.
    """
    conn = get_conn()
    try:
        resultado = {
            'ole_ibc': pd.DataFrame(),
            'sigep_nivel_educativo': pd.DataFrame(),
            'sigep_departamental': pd.DataFrame(),
            'fuente_principal': 'Sin datos',
            'tiene_datos': False
        }
        
        # --- FUENTE 1: OLE IBC (Ingreso Base de Cotización de graduados) ---
        try:
            query_ibc = """
            SELECT categoria, ibc_rango_smmlv, ibc_min_smmlv, ibc_max_smmlv, tipo,
                   ibc_min_pesos, ibc_max_pesos, ano_seguimiento, cohorte_graduados
            FROM datos_complementarios.ole_ibc_rangos
            ORDER BY tipo, categoria
            """
            df_ibc = conn.execute(query_ibc).fetchdf()
            if not df_ibc.empty:
                resultado['ole_ibc'] = df_ibc
                resultado['fuente_principal'] = 'OLE - MinEducacion (IBC graduados)'
                resultado['tiene_datos'] = True
        except Exception:
            pass
        
        # --- FUENTE 2: SIGEP - Salarios por nivel educativo ---
        try:
            query_sigep = """
            SELECT nivel_edu_principal as nivel_educativo,
                   salario_promedio, salario_mediana, 
                   salario_min, salario_max, cantidad_empleados
            FROM datos_complementarios.salarios_por_nivel_educativo
            WHERE salario_promedio IS NOT NULL
            ORDER BY salario_promedio
            """
            df_sigep = conn.execute(query_sigep).fetchdf()
            if not df_sigep.empty:
                resultado['sigep_nivel_educativo'] = df_sigep
                if not resultado['tiene_datos']:
                    resultado['fuente_principal'] = 'SIGEP (Empleo publico)'
                resultado['tiene_datos'] = True
        except Exception:
            pass
        
        # --- FUENTE 3: SIGEP Departamental (si se especificó departamento) ---
        if departamento:
            try:
                depto_esc = _esc(departamento)
                query_depto = f"""
                SELECT nivel_edu_principal as nivel_educativo,
                       salario_promedio, salario_mediana, cantidad_empleados
                FROM datos_complementarios.salarios_educacion_x_departamento
                WHERE UPPER(departamentodenacimiento) = UPPER('{depto_esc}')
                  AND salario_promedio IS NOT NULL
                ORDER BY salario_promedio
                """
                df_depto = conn.execute(query_depto).fetchdf()
                if not df_depto.empty:
                    resultado['sigep_departamental'] = df_depto
            except Exception:
                pass
        
        return resultado
    except Exception as e:
        return {'ole_ibc': pd.DataFrame(), 'sigep_nivel_educativo': pd.DataFrame(),
                'sigep_departamental': pd.DataFrame(), 'fuente_principal': 'Error',
                'tiene_datos': False}
    finally:
        conn.close()


def get_tendencia_laboral_nbc(nbc=None):
    """Obtiene tendencias de vacantes, inscritos y colocados APE por ocupaciones del NBC.
    
    Usa ML matching para identificar ocupaciones relevantes al NBC en las tablas
    de tendencia APE (2017-2019), que contienen datos REALES del mercado laboral.
    
    Fuente: Agencia Publica de Empleo (APE) - SENA, consolidado anual
    """
    conn = get_conn()
    try:
        if not nbc:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Obtener todas las ocupaciones de tendencia_vacantes para ML matching
        df_ocup = conn.execute("""
            SELECT DISTINCT ocupacion as nombre_ocupacion 
            FROM datos_complementarios.tendencia_vacantes_anual
            WHERE ocupacion IS NOT NULL
        """).fetchdf()
        
        if df_ocup.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # ML matching para encontrar ocupaciones relevantes
        ocupaciones_filtro = []
        if ML_AVAILABLE:
            try:
                model = get_model()
                contexto_nbc = _enriquecer_contexto_nbc(nbc)
                nbc_emb = model.encode([f"Profesional en {contexto_nbc}. Egresado de programas de {contexto_nbc}."], show_progress_bar=False)[0]
                ocup_embs = model.encode(df_ocup['nombre_ocupacion'].tolist(), show_progress_bar=False)
                sims = cosine_similarity([nbc_emb], ocup_embs)[0]
                df_ocup['sim'] = sims
                matched = df_ocup[df_ocup['sim'] >= 0.50].nlargest(15, 'sim')
                if not matched.empty:
                    ocupaciones_filtro = matched['nombre_ocupacion'].tolist()
                    # Filtrar ruido ocupacional no relacionado con el NBC
                    ruido_tendencia = ['jardineria', 'viverismo', 'alojamiento', 'hospedaje',
                                      'vendedor', 'cajero', 'mensajero', 'conserje', 'vigilante']
                    ocupaciones_filtro = [o for o in ocupaciones_filtro
                                         if not any(r in o.lower() for r in ruido_tendencia)]
            except Exception:
                pass
        
        # Fallback: keyword matching
        if not ocupaciones_filtro:
            stopwords = STOPWORDS
            palabras = [p.lower() for p in nbc.split() if len(p) > 3 and p.lower() not in stopwords]
            if palabras:
                like_clauses = " OR ".join([f"LOWER(ocupacion) LIKE '%{p}%'" for p in palabras[:3]])
                kw_df = conn.execute(f"""
                    SELECT DISTINCT ocupacion FROM datos_complementarios.tendencia_vacantes_anual
                    WHERE {like_clauses}
                """).fetchdf()
                if not kw_df.empty:
                    ocupaciones_filtro = kw_df['ocupacion'].tolist()
        
        if not ocupaciones_filtro:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Construir filtro SQL
        ocup_sql = ', '.join([f"'{_esc(o)}'" for o in ocupaciones_filtro])
        
        df_vacantes = conn.execute(f"""
            SELECT ano, ocupacion, vacantes, pct_participacion
            FROM datos_complementarios.tendencia_vacantes_anual
            WHERE ocupacion IN ({ocup_sql})
            ORDER BY ano, vacantes DESC
        """).fetchdf()
        
        df_inscritos = conn.execute(f"""
            SELECT ano, ocupacion, inscritos, pct_participacion
            FROM datos_complementarios.tendencia_inscritos_anual
            WHERE ocupacion IN ({ocup_sql})
            ORDER BY ano, inscritos DESC
        """).fetchdf()
        
        df_colocados = conn.execute(f"""
            SELECT ano, ocupacion, colocados, pct_participacion
            FROM datos_complementarios.tendencia_colocados_anual
            WHERE ocupacion IN ({ocup_sql})
            ORDER BY ano, colocados DESC
        """).fetchdf()
        
        return df_vacantes, df_inscritos, df_colocados
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()


def get_graduados_nbc_historico(nbc=None, filtros=None):
    """Obtiene serie histórica de graduados por NBC desde datos_complementarios.
    
    Fuente: SNIES - MEN (datos consolidados por NBC y año)
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional)
        filtros: Dict opcional — si tiene 'niveles' o 'estados', se filtra
            vía snies_graduados (tabla principal con subquery puente) en lugar
            de datos_complementarios (que no tiene esas columnas).
    """
    conn = get_conn()
    try:
        if not nbc:
            return pd.DataFrame()
        
        nbc_esc = _esc(nbc)

        # Si hay filtros que requieren puente (niveles, estados, etc.), usar snies_graduados
        # en lugar de datos_complementarios que no tiene esas dimensiones.
        needs_bridge = filtros and any(filtros.get(k) for k in ('niveles', 'estados', 'modalidades', 'sectores', 'caracteres'))
        
        if needs_bridge:
            condiciones = [f"UPPER(\"NBC\") = UPPER('{nbc_esc}')"]
            extra = build_where_clause_matriculados(filtros=filtros)
            # Excluir condiciones de NBC y depto (ya las tenemos / queremos nacional)
            for cond in extra:
                if '"NBC"' not in cond and '"DEPTO_PROGRAMA"' not in cond and '"MPIO_PROGRAMA"' not in cond:
                    condiciones.append(cond)
            where = " AND ".join(condiciones)
            df = conn.execute(f"""
                SELECT "NBC" as NBC, CAST("ANO" AS INTEGER) as anio,
                       SUM(CAST("GRADUADOS" AS BIGINT)) as graduados
                FROM snies.snies_graduados
                WHERE {where}
                GROUP BY "NBC", "ANO"
                ORDER BY "ANO"
            """).fetchdf()
        else:
            # Usar datos_complementarios (tabla consolidada, más rápida)
            df = conn.execute(f"""
                SELECT NBC, CAST(ANO AS INTEGER) as anio, GRADUADOS as graduados
                FROM datos_complementarios.graduados_nbc_ano
                WHERE STRIP_ACCENTS(UPPER(NBC)) LIKE STRIP_ACCENTS(UPPER('%{nbc_esc}%'))
                ORDER BY ANO
            """).fetchdf()
        
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def get_actividades_tareas_nbc(nbc: str, top_k: int = 20) -> pd.DataFrame:
    """
    Obtiene actividades y tareas de ocupaciones relacionadas al NBC usando ML.
    
    Usa búsqueda semántica para encontrar ocupaciones relevantes en lugar de
    depender del mapeo NBC→CUOC que puede tener errores.
    
    Args:
        nbc: Nombre del Núcleo Básico del Conocimiento
        top_k: Número máximo de ocupaciones a retornar
        
    Returns:
        DataFrame con código CUOC, título ocupación y descripción de actividades/tareas
    """
    if not nbc:
        return pd.DataFrame()
    
    conn = get_conn()
    try:
        # Obtener TODAS las ocupaciones disponibles
        query_perfiles = """
            SELECT DISTINCT
                "Unnamed: 2" as titulo_ocupacion,
                CAST("Unnamed: 1" AS VARCHAR) as codigo_cuoc,
                "Unnamed: 3" as descripcion_actividades
            FROM cuoc.perfilesocupacionales_excel_cuoc_2025
            WHERE "Unnamed: 2" IS NOT NULL
              AND "Unnamed: 2" != 'Nombre de la Ocupación'
              AND "Unnamed: 1" IS NOT NULL
        """
        df_perfiles = conn.execute(query_perfiles).fetchdf()
        
        if df_perfiles.empty:
            return pd.DataFrame()
        
        # Usar ML para filtrar las ocupaciones más relevantes al NBC
        try:
            model = get_model()
            contexto_nbc = _enriquecer_contexto_nbc(nbc)
            
            # Calcular embeddings
            nbc_embedding = model.encode([contexto_nbc], show_progress_bar=False)[0]
            ocupacion_texts = df_perfiles['titulo_ocupacion'].tolist()
            ocupacion_embeddings = model.encode(ocupacion_texts, show_progress_bar=False)
            
            # Calcular similitud
            similitudes = cosine_similarity([nbc_embedding], ocupacion_embeddings)[0]
            df_perfiles['similitud_ml'] = similitudes
            
            # Filtrar top_k ocupaciones más relevantes
            df_perfiles = df_perfiles.nlargest(top_k, 'similitud_ml')
            
            # Umbral mínimo de similitud (0.25)
            df_perfiles = df_perfiles[df_perfiles['similitud_ml'] >= 0.25]
            
            print(f"[ACTIVIDADES] NBC: {nbc[:40]}... | Ocupaciones ML: {len(df_perfiles)}")
            
        except Exception as e:
            print(f"[ACTIVIDADES] Error ML: {e}")
            # Fallback: retornar primeras ocupaciones
            df_perfiles = df_perfiles.head(top_k)
        
        return df_perfiles
        
    except Exception as e:
        print(f"[ACTIVIDADES] Error general: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def _enriquecer_contexto_nbc(nbc: str) -> str:
    """Genera contexto enriquecido para ML matching según el tipo de NBC.
    Función compartida para evitar duplicación del bloque if/elif."""
    nbc_lower = nbc.lower()
    enrichments = {
        ('sistema', 'telemática', 'informática'): "software programacion desarrollo aplicaciones datos tecnologia computacion redes telecomunicaciones bases de datos web",
        ('contadur', 'contador'): "contabilidad finanzas auditoria impuestos fiscal balance estados financieros contador",
        ('administración',): "administracion gerencia gestion empresas direccion negocios recursos humanos",
        ('medicina',): "medicina salud medico paciente hospital clinica diagnostico tratamiento",
        ('enfermería',): "enfermeria cuidado paciente salud hospital clinica enfermero",
        ('derecho',): "derecho leyes juridico abogado legislacion tribunales",
        ('psicología', 'psicolog'): "psicologia comportamiento mente terapia salud mental psicologo",
        ('economía',): "economia mercados analisis economico finanzas macro micro",
        ('música', 'music'): "musica instrumentos composicion interpretacion musical canto musico",
        ('arquitectura',): "arquitectura construccion edificios urbanismo planos diseño arquitectonico",
        ('diseño',): "diseño grafico visual creativo arte diseñador",
        ('educación', 'pedagogía', 'licenciatura'): "educacion enseñanza pedagogia didactica docencia profesor maestro",
        ('comunicación', 'periodismo'): "comunicacion medios periodismo audiovisual periodista",
        ('mecánica', 'mecatrónica'): "mecanica maquinas ingenieria mecanica automotriz manufactura",
        ('electrónica', 'eléctrica'): "electronica electrica circuitos automatizacion control",
        ('civil',): "civil construccion obras infraestructura estructuras",
        ('industrial',): "industrial procesos produccion manufactura calidad logistica",
        ('química',): "quimica laboratorio analisis quimico sustancias",
        ('biología', 'ecología', 'ambiental'): "biologia medio ambiente ecologia ecosistemas",
        ('filosof', 'teolog'): "filosofia etica pensamiento reflexion humanidades religion teologia",
        ('física',): "fisica matematicas investigacion ciencias exactas",
        ('agronóm', 'agropecuar', 'agrícol'): "agronomia agricultura campo cultivos pecuario ganaderia",
    }
    for keywords, extra in enrichments.items():
        if any(kw in nbc_lower for kw in keywords):
            return f"{nbc} {extra}"
    return nbc


def get_destrezas_cuoc_nbc(nbc: str, top_ocupaciones: int = 20) -> pd.DataFrame:
    """
    Obtiene destrezas CUOC reales usando ML-first para un NBC específico.
    
    Enfoque ML-first (sin depender de mapeo_nbc_cuoc genérico):
    1. Carga todas las ocupaciones con destrezas desde CUOC
    2. Usa ML para identificar las ocupaciones más relevantes al NBC
    3. Extrae destrezas de las ocupaciones filtradas
    
    Args:
        nbc: Nombre del NBC seleccionado
        top_ocupaciones: Número de ocupaciones top a considerar
    
    Returns:
        DataFrame con destrezas ordenadas por relevancia
    """
    if not nbc:
        return pd.DataFrame()
    
    conn = get_conn()
    try:
        # Obtener todas las ocupaciones distintas con destrezas
        ocupaciones = conn.execute("""
            SELECT DISTINCT codigo_ocupacion, nombre_ocupacion
            FROM competencias.cuoc_destrezas
            WHERE nombre_ocupacion IS NOT NULL
        """).fetchdf()
        
        if ocupaciones.empty:
            return pd.DataFrame()
        
        # Filtrar ocupaciones por ML
        codigos_top = ocupaciones['codigo_ocupacion'].tolist()
        try:
            model = get_model()
            contexto_nbc = _enriquecer_contexto_nbc(nbc)
            nbc_embedding = model.encode([contexto_nbc], show_progress_bar=False)[0]
            ocupacion_embeddings = model.encode(ocupaciones['nombre_ocupacion'].tolist(), show_progress_bar=False)
            similitudes = cosine_similarity([nbc_embedding], ocupacion_embeddings)[0]
            ocupaciones['similitud'] = similitudes
            ocupaciones_top = ocupaciones.nlargest(top_ocupaciones, 'similitud')
            # Umbral mínimo
            ocupaciones_top = ocupaciones_top[ocupaciones_top['similitud'] >= 0.30]
            if not ocupaciones_top.empty:
                codigos_top = ocupaciones_top['codigo_ocupacion'].tolist()
            else:
                codigos_top = ocupaciones.nlargest(10, 'similitud')['codigo_ocupacion'].tolist()
        except Exception as e:
            # Fallback keyword
            stopwords = STOPWORDS
            palabras = [p.lower() for p in nbc.split() if len(p) > 3 and p.lower() not in stopwords]
            if palabras:
                mask = ocupaciones['nombre_ocupacion'].str.lower().apply(
                    lambda x: any(p in x for p in palabras))
                kw_matched = ocupaciones[mask]
                if not kw_matched.empty:
                    codigos_top = kw_matched['codigo_ocupacion'].tolist()
        
        # Extraer destrezas
        codigos_top_sql = ', '.join([f"'{c}'" for c in codigos_top])
        
        destrezas = conn.execute(f"""
            SELECT 
                d.destreza,
                COUNT(DISTINCT d.codigo_ocupacion) as n_ocupaciones
            FROM competencias.cuoc_destrezas d
            WHERE d.codigo_ocupacion IN ({codigos_top_sql})
            GROUP BY d.destreza
            ORDER BY n_ocupaciones DESC
        """).fetchdf()
        
        if not destrezas.empty:
            max_val = destrezas['n_ocupaciones'].max()
            destrezas['relevancia'] = (destrezas['n_ocupaciones'] / max_val * 100).round(1)
        
        return destrezas
        
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


def get_conocimientos_cuoc_nbc(nbc: str, top_ocupaciones: int = 20) -> pd.DataFrame:
    """
    Obtiene conocimientos CUOC reales usando ML-first para un NBC específico.
    Mismo enfoque que get_destrezas_cuoc_nbc() pero para conocimientos.
    """
    if not nbc:
        return pd.DataFrame()
    
    conn = get_conn()
    try:
        # Obtener todas las ocupaciones distintas con conocimientos
        ocupaciones = conn.execute("""
            SELECT DISTINCT codigo_ocupacion, nombre_ocupacion
            FROM competencias.cuoc_conocimientos
            WHERE nombre_ocupacion IS NOT NULL
        """).fetchdf()
        
        if ocupaciones.empty:
            return pd.DataFrame()
        
        # Filtrar por ML
        codigos_top = ocupaciones['codigo_ocupacion'].tolist()
        try:
            model = get_model()
            contexto_nbc = _enriquecer_contexto_nbc(nbc)
            nbc_embedding = model.encode([contexto_nbc], show_progress_bar=False)[0]
            ocupacion_embeddings = model.encode(ocupaciones['nombre_ocupacion'].tolist(), show_progress_bar=False)
            similitudes = cosine_similarity([nbc_embedding], ocupacion_embeddings)[0]
            ocupaciones['similitud'] = similitudes
            ocupaciones_top = ocupaciones.nlargest(top_ocupaciones, 'similitud')
            ocupaciones_top = ocupaciones_top[ocupaciones_top['similitud'] >= 0.30]
            if not ocupaciones_top.empty:
                codigos_top = ocupaciones_top['codigo_ocupacion'].tolist()
            else:
                codigos_top = ocupaciones.nlargest(10, 'similitud')['codigo_ocupacion'].tolist()
        except Exception:
            stopwords = STOPWORDS
            palabras = [p.lower() for p in nbc.split() if len(p) > 3 and p.lower() not in stopwords]
            if palabras:
                mask = ocupaciones['nombre_ocupacion'].str.lower().apply(
                    lambda x: any(p in x for p in palabras))
                kw_matched = ocupaciones[mask]
                if not kw_matched.empty:
                    codigos_top = kw_matched['codigo_ocupacion'].tolist()
        
        # Extraer conocimientos
        codigos_top_sql = ', '.join([f"'{c}'" for c in codigos_top])
        
        conocimientos = conn.execute(f"""
            SELECT 
                c.conocimiento,
                COUNT(DISTINCT c.codigo_ocupacion) as n_ocupaciones
            FROM competencias.cuoc_conocimientos c
            WHERE c.codigo_ocupacion IN ({codigos_top_sql})
            GROUP BY c.conocimiento
            ORDER BY n_ocupaciones DESC
        """).fetchdf()
        
        if not conocimientos.empty:
            max_val = conocimientos['n_ocupaciones'].max()
            conocimientos['relevancia'] = (conocimientos['n_ocupaciones'] / max_val * 100).round(1)
        
        return conocimientos
        
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


# ==============================================================================
# GLOBAL - Indicadores Internacionales y Habilidades del Futuro
# ==============================================================================

def get_indicadores_globales():
    """Obtiene indicadores del Banco Mundial para Colombia."""
    conn = get_conn()
    try:
        query = """
        SELECT a_o as anio, valor as desempleo_jovenes
        FROM indicadores_globales.bm_desempleo_jovenes
        WHERE pais = 'Colombia'
        ORDER BY a_o DESC
        LIMIT 10
        """
        df = conn.execute(query).fetchdf()
        return df
    except:
        return pd.DataFrame()
    finally:
        conn.close()


def get_habilidades_futuro():
    """Obtiene tendencias de habilidades del futuro."""
    conn = get_conn()
    try:
        query = """
        SELECT 
            habilidad,
            categoria,
            demanda_2024_score,
            crecimiento_anual_pct,
            brecha_talento_score,
            empleos_globales_millones
        FROM tendencias_tecnologicas.habilidades_futuro
        ORDER BY demanda_2024_score DESC
        """
        df = conn.execute(query).fetchdf()
        return df
    except:
        return pd.DataFrame()
    finally:
        conn.close()


def get_habilidades_futuro_filtradas(nbc: str) -> pd.DataFrame:
    """
    DEPRECATED: Usar get_destrezas_cuoc_nbc() en su lugar.
    Se mantiene por compatibilidad con código existente.
    """
    df_hab = get_habilidades_futuro()
    if df_hab.empty or not nbc:
        return df_hab
    
    # Delegar a la nueva función CUOC
    df_cuoc = get_destrezas_cuoc_nbc(nbc)
    if not df_cuoc.empty and 'relevancia' in df_cuoc.columns:
        # Guardar relevancia antes de renombrar
        relevancia_values = df_cuoc['relevancia'].copy()
        # Convertir formato CUOC al formato esperado por el gráfico
        df_cuoc = df_cuoc.rename(columns={
            'destreza': 'habilidad',
            'relevancia': 'relevancia_normalizada'
        })
        df_cuoc['demanda_2024_score'] = relevancia_values
        df_cuoc['score_contextualizado'] = relevancia_values
        df_cuoc['relevancia_nbc'] = relevancia_values / 100
        df_cuoc['crecimiento_anual_pct'] = 10.0  # Valor fijo para color
        return df_cuoc
    
    # Fallback al método original si CUOC falla
    return df_hab


# ==============================================================================
# ESCO - European Skills, Competences, Qualifications and Occupations
# ==============================================================================

# Mapeo SNIES Área de Conocimiento → ESCO sector_snies (case-insensitive)
_SNIES_AREA_TO_ESCO_SECTOR = {
    "agronomía, veterinaria y afines": "Agronomía, Veterinaria y Afines",
    "bellas artes": "Bellas Artes",
    "ciencias de la educación": "Educación",
    "ciencias de la salud": "Ciencias de la Salud",
    "ciencias sociales y humanas": "Ciencias Sociales y Humanas",
    "economía, administración, contaduría y afines": "Economía, Administración, Contaduría y Afines",
    "ingeniería, arquitectura, urbanismo y afines": "Ingeniería, Arquitectura, Urbanismo y Afines",
    "matemáticas y ciencias naturales": "Matemáticas y Ciencias Naturales",
    "sin clasificar": "Transversal",
}


def _mapear_areas_snies_a_esco(sel_areas: list) -> list:
    """Convierte áreas SNIES (case-insensitive) a sectores ESCO."""
    if not sel_areas:
        return []
    sectores = set()
    for area in sel_areas:
        key = area.strip().lower()
        sector = _SNIES_AREA_TO_ESCO_SECTOR.get(key)
        if sector:
            sectores.add(sector)
        else:
            # Fuzzy fallback: buscar por substring
            for k, v in _SNIES_AREA_TO_ESCO_SECTOR.items():
                if k in key or key in k:
                    sectores.add(v)
                    break
    return list(sectores)


def get_habilidades_esco(sel_areas: list = None, top_n: int = 15) -> tuple:
    """
    Obtiene habilidades globales de la taxonomía ESCO filtradas por sector SNIES.
    
    Args:
        sel_areas: Lista de áreas de conocimiento SNIES seleccionadas.
                   Se mapean a los sectores ESCO correspondientes.
                   Si es None/vacío, retorna las habilidades transversales.
        top_n: Número de habilidades top a retornar para el gráfico.
    
    Returns:
        Tupla (df_top, df_all):
        - df_top: DataFrame con las top_n habilidades para el gráfico
        - df_all: DataFrame con TODAS las habilidades del sector para descarga
    """
    conn = get_conn()
    try:
        # Mapear áreas SNIES a sectores ESCO
        sectores = _mapear_areas_snies_a_esco(sel_areas) if sel_areas else []
        
        if sectores:
            # Filtrar por sectores mapeados + siempre incluir Transversal
            sectores_set = set(sectores)
            sectores_set.add("Transversal")
            placeholders = ', '.join([f"'{s}'" for s in sectores_set])
            where_clause = f"WHERE sector IN ({placeholders})"
            # Priorizar sector específico sobre transversal en ranking
            order_clause = f"""
                ORDER BY 
                    CASE WHEN sector != 'Transversal' THEN 0 ELSE 1 END,
                    n_ocupaciones_total DESC
            """
        else:
            # Sin filtro de área: mostrar top general (todos los sectores)
            where_clause = ""
            order_clause = "ORDER BY n_ocupaciones_total DESC"
        
        # Query para TODAS las habilidades del sector (para descarga)
        df_all = conn.execute(f"""
            SELECT 
                habilidad,
                categoria,
                sector,
                pilar,
                tipo_skill,
                nivel_reutilizacion,
                n_ocupaciones_esencial,
                n_ocupaciones_opcional,
                n_ocupaciones_total,
                descripcion,
                fuente
            FROM esco.skills_por_sector
            {where_clause}
            ORDER BY n_ocupaciones_total DESC
        """).fetchdf()
        
        # Top N para el gráfico (sin duplicados, priorizando sector específico)
        df_top = conn.execute(f"""
            SELECT 
                habilidad,
                categoria,
                sector,
                tipo_skill,
                n_ocupaciones_total
            FROM esco.skills_por_sector
            {where_clause}
            {order_clause}
            LIMIT {top_n}
        """).fetchdf()
        
        return df_top, df_all
        
    except Exception as e:
        print(f"[ESCO] Error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()


# ==============================================================================
# CUALIFICACIONES MEN - Marco Nacional de Cualificaciones
# ==============================================================================

@st.cache_data
def get_cualificaciones_men(sigla_area=None, nivel_mnc=None, sector=None):
    """
    Obtiene cualificaciones del Marco Nacional de Cualificaciones (MEN).
    Permite filtrar por sigla de área CUOC, nivel MNC o sector.
    """
    conn = get_conn()
    try:
        conditions = []
        if sigla_area:
            if isinstance(sigla_area, list):
                siglas_str = "', '".join([s.replace("'", "''") for s in sigla_area])
                conditions.append(f"Sigla_Area IN ('{siglas_str}')")
            else:
                conditions.append(f"Sigla_Area = '{_esc(sigla_area)}'")
        
        if nivel_mnc:
            if isinstance(nivel_mnc, list):
                niveles_str = ", ".join([str(n) for n in nivel_mnc])
                conditions.append(f"Nivel_MNC IN ({niveles_str})")
            else:
                conditions.append(f"Nivel_MNC = {nivel_mnc}")
        
        if sector:
            conditions.append(f"Sector ILIKE '%{_esc(sector)}%'")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT 
            ID,
            Codigo_MEN,
            Cualificacion,
            Nivel_MNC,
            Titulo_Otorga,
            Sector,
            Area_Cualificacion,
            Sigla_Area
        FROM catalogo_curado.cualificaciones_men
        WHERE {where_clause}
        ORDER BY Nivel_MNC, Sigla_Area, Cualificacion
        """
        return conn.execute(query).fetchdf()
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


@st.cache_data
def get_estadisticas_cualificaciones_men():
    """Obtiene estadísticas agregadas de las Cualificaciones MEN."""
    conn = get_conn()
    try:
        # Por nivel MNC
        query_nivel = """
        SELECT Nivel_MNC, COUNT(*) as N
        FROM catalogo_curado.cualificaciones_men
        GROUP BY Nivel_MNC
        ORDER BY Nivel_MNC
        """
        df_nivel = conn.execute(query_nivel).fetchdf()
        
        # Por Sigla Área
        query_area = """
        SELECT Sigla_Area, Area_Cualificacion, COUNT(*) as N
        FROM catalogo_curado.cualificaciones_men
        WHERE Sigla_Area IS NOT NULL AND Sigla_Area != ''
        GROUP BY Sigla_Area, Area_Cualificacion
        ORDER BY N DESC
        """
        df_area = conn.execute(query_area).fetchdf()
        
        # Por Sector (top 15)
        query_sector = """
        SELECT Sector, COUNT(*) as N
        FROM catalogo_curado.cualificaciones_men
        WHERE Sector IS NOT NULL AND Sector != ''
        GROUP BY Sector
        ORDER BY N DESC
        LIMIT 15
        """
        df_sector = conn.execute(query_sector).fetchdf()
        
        # Totales
        total = conn.execute("SELECT COUNT(*) FROM catalogo_curado.cualificaciones_men").fetchone()[0]
        
        return {
            'total': total,
            'por_nivel': df_nivel,
            'por_area': df_area,
            'por_sector': df_sector
        }
    except Exception as e:
        return {'total': 0, 'por_nivel': pd.DataFrame(), 'por_area': pd.DataFrame(), 'por_sector': pd.DataFrame()}
    finally:
        conn.close()


@st.cache_data
def get_cualificaciones_por_nbc(nbc):
    """
    Obtiene cualificaciones MEN relacionadas con un NBC específico
    usando ML semántico para encontrar las más relevantes.
    
    Estrategia:
    1. ML: Busca cualificaciones cuyo nombre sea semánticamente similar al NBC
    2. Fallback: Búsqueda por palabras clave del NBC
    
    Fuente: Marco Nacional de Cualificaciones - MEN Colombia
    """
    conn = get_conn()
    try:
        # Cargar todas las cualificaciones MEN
        query_todas = """
        SELECT 
            Codigo_MEN,
            Cualificacion,
            Nivel_MNC,
            Sector,
            Sigla_Area,
            Area_Cualificacion
        FROM catalogo_curado.cualificaciones_men
        WHERE Cualificacion IS NOT NULL
        """
        df_todas = conn.execute(query_todas).fetchdf()
        
        if df_todas.empty:
            return pd.DataFrame()
        
        # ESTRATEGIA 1: ML Matching Semántico
        if ML_AVAILABLE:
            try:
                model = get_model()
                if model is not None:
                    # Crear embeddings del NBC enriquecido y las cualificaciones
                    contexto_nbc = _enriquecer_contexto_nbc(nbc)
                    query = f"Profesional en {contexto_nbc}. Cualificacion laboral de {contexto_nbc}."
                    nbc_embedding = model.encode([query], convert_to_numpy=True, show_progress_bar=False)
                    cualif_embeddings = model.encode(
                        df_todas['Cualificacion'].tolist(), 
                        convert_to_numpy=True, 
                        show_progress_bar=False,
                        batch_size=64
                    )
                    
                    # Calcular similitud coseno
                    similarities = cosine_similarity(nbc_embedding, cualif_embeddings)[0]
                    
                    df_todas['similitud_ml'] = similarities
                    
                    # Filtrar con threshold adaptativo: precision primero, recall despues
                    for umbral in [0.40, 0.30, 0.28]:
                        df_relevantes = df_todas[df_todas['similitud_ml'] >= umbral].copy()
                        df_relevantes = df_relevantes.sort_values('similitud_ml', ascending=False).head(15)
                        if len(df_relevantes) >= 1:
                            break
                    
                    if not df_relevantes.empty:
                        return df_relevantes.drop(columns=['similitud_ml'])
            except Exception as e:
                pass  # Fallback a estrategia tradicional
        
        # ESTRATEGIA 2: Búsqueda por palabras clave del NBC
        stopwords = STOPWORDS
        palabras = [p.lower() for p in nbc.split() if len(p) > 3 and p.lower() not in stopwords]
        
        if palabras:
            # Buscar cualificaciones que contengan palabras del NBC
            mask = df_todas['Cualificacion'].str.lower().str.contains('|'.join(palabras), na=False, regex=True)
            df_match = df_todas[mask].copy()
            
            if not df_match.empty:
                return df_match.sort_values('Nivel_MNC').head(15)
        
        # Si no hay resultados, retornar vacío (mejor que datos incorrectos)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()


# ===================================================================
# SABER PRO — Calidad academica via matching semantico
# ===================================================================

def get_saber_pro_stats(filtros=None):
    """Obtiene estadisticas de calidad academica desde Saber PRO usando matching semantico.
    
    Batch cosine similarity entre programas SNIES filtrados y nombres Saber PRO.
    Usa embeddings precomputados en data.search (cache en disco, carga instantanea).
    """
    import duckdb
    import numpy as np
    from config.database import DUCKDB_PATH
    
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        where = build_where_clause(filtros or {}, "p")
        snies_progs = conn.execute(f"""
            SELECT DISTINCT "NOMBRE_DEL_PROGRAMA" as nombre
            FROM snies.snies_programas p WHERE {where}
        """).fetchdf()
        
        if snies_progs.empty:
            return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0}
        
        # Cargar embeddings precomputados (SNIES + SIET + SABER)
        from data.search import _obtener_embeddings_raw, _cargar_modelo
        nombres, fuentes, embeddings = _obtener_embeddings_raw()
        if embeddings is None or len(nombres) == 0:
            return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0}
        
        model = _cargar_modelo()
        if model is None:
            return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0}
        
        # Batch encode: todos los nombres SNIES filtrados de una vez
        snies_list = snies_progs['nombre'].tolist()
        snies_emb = model.encode(snies_list, convert_to_numpy=True, show_progress_bar=False)
        
        # Indices de programas SABER en el array de embeddings
        saber_indices = [i for i, f in enumerate(fuentes) if f == 'SABER']
        if not saber_indices:
            return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0}
        
        saber_embs = embeddings[saber_indices]
        saber_nombres = [nombres[i] for i in saber_indices]
        
        # Cosine similarity: SNIES_filtrados x SABER
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(snies_emb, saber_embs)
        
        # Matching con threshold 0.55 (bajado de 0.7 para capturar mas variaciones de nombre)
        saber_matches = set()
        for i in range(len(snies_list)):
            best_idx = np.argmax(sims[i])
            if sims[i][best_idx] > 0.55:
                saber_matches.add(saber_nombres[best_idx])
        
        # Fallback con threshold 0.45 si hay pocos o ningun match
        if len(saber_matches) < 3:
            for i in range(len(snies_list)):
                best_idx = np.argmax(sims[i])
                if 0.45 < sims[i][best_idx] <= 0.55:
                    saber_matches.add(saber_nombres[best_idx])
        
        if not saber_matches:
            return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0, 'periodo': None}
        
        # Consultar puntajes Saber PRO con distribucion (ultimos 3 anos: 2020-2022)
        escaped = "', '".join([m.replace("'", "''") for m in saber_matches])
        df = conn.execute(f"""
            SELECT COUNT(*) as n_evaluados,
                   AVG(CAST("total_17" AS DOUBLE)) as puntaje_promedio,
                   AVG(CAST("indicador" AS DOUBLE)) as percentil_promedio,
                   MIN(CAST("total_17" AS DOUBLE)) as puntaje_min,
                   MAX(CAST("total_17" AS DOUBLE)) as puntaje_max,
                   PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY CAST("total_17" AS DOUBLE)) as q1,
                   PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY CAST("total_17" AS DOUBLE)) as mediana,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY CAST("total_17" AS DOUBLE)) as q3
            FROM icfes_saber.icfes_saber_pro_resultados
            WHERE estu_prgm_academico IN ('{escaped}')
              AND LEFT(periodo::VARCHAR, 4) IN ('2020', '2021', '2022')
        """).fetchdf()
        
        # Puntaje nacional de referencia (mismo periodo 2020-2022)
        ref = conn.execute("""
            SELECT AVG(CAST("total_17" AS DOUBLE)) as nacional_promedio
            FROM icfes_saber.icfes_saber_pro_resultados
            WHERE LEFT(periodo::VARCHAR, 4) IN ('2020', '2021', '2022')
        """).fetchdf()
        nacional_promedio = round(ref['nacional_promedio'].iloc[0], 1) if not ref.empty else None
        
        return {
            'puntaje_promedio': round(df['puntaje_promedio'].iloc[0], 1) if not df.empty else None,
            'n_evaluados': int(df['n_evaluados'].iloc[0]) if not df.empty else 0,
            'puntaje_min': round(df['puntaje_min'].iloc[0], 1) if not df.empty else None,
            'puntaje_max': round(df['puntaje_max'].iloc[0], 1) if not df.empty else None,
            'q1': round(df['q1'].iloc[0], 1) if not df.empty else None,
            'mediana': round(df['mediana'].iloc[0], 1) if not df.empty else None,
            'q3': round(df['q3'].iloc[0], 1) if not df.empty else None,
            'percentil': round(df['percentil_promedio'].iloc[0], 1) if not df.empty else None,
            'nacional_promedio': nacional_promedio,
            'programas_match': len(saber_matches),
            'periodo': '2020-2022'
        }
        
    except Exception as e:
        return {'puntaje_promedio': None, 'n_evaluados': 0, 'percentil': None, 'programas_match': 0, 'error': str(e)}
    finally:
        conn.close()
