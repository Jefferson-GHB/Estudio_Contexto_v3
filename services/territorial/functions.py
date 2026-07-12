"""
Funciones territoriales robustas con normalización + ML.
Se integra con app_streamlit.py para el Eje Territorial.
"""
import duckdb
from typing import Dict, Optional, Tuple, List
from functools import lru_cache
from pathlib import Path

import os

# Importar normalización
from services.territorial.normalization import (
    get_codigo_dane,
    get_depto_from_dane,
    get_region,
    robust_depto_match,
    normalize_text,
    DEPTO_TO_DANE,
    DANE_TO_DEPTO,
)

# Path a la base de datos - detectar según entorno
def _get_db_path():
    if os.environ.get('DUCKDB_PATH'):
        return Path(os.environ.get('DUCKDB_PATH'))
    hf_path = Path(__file__).parent.parent / "data" / "repositorio.duckdb"
    if hf_path.exists():
        return hf_path
    fallback = Path(__file__).parent.parent / "repositorio.duckdb"
    if fallback.exists():
        return fallback
    return Path(__file__).parent.parent / "data" / "repositorio.duckdb"

DB_PATH = _get_db_path()


# ============================================================================
# DESEMPEÑO DNP
# ============================================================================

def get_desempeno_dnp(depto: str, conn: duckdb.DuckDBPyConnection = None) -> Dict:
    """
    Obtiene indicadores de desempeño municipal del DNP para un departamento.
    Usa código DANE para matching robusto.
    
    Args:
        depto: Nombre del departamento (cualquier variación)
        conn: Conexión DuckDB opcional
    
    Returns:
        Dict con:
            - en_plan_desarrollo: bool
            - puntaje_mdm: float (promedio departamental)
            - componente_gestion: float
            - componente_resultados: float
            - municipios_evaluados: int
            - fuente: str
    """
    result = {
        'en_plan_desarrollo': False,
        'puntaje_mdm': None,
        'componente_gestion': None,
        'componente_resultados': None,
        'municipios_evaluados': 0,
        'fuente': 'DNP - Medición de Desempeño Municipal 2023',
    }
    
    # Obtener código DANE
    codigo_dane = get_codigo_dane(depto)
    if codigo_dane is None:
        # Fallback con ML
        canonical, codigo_dane = robust_depto_match(depto, use_ml=True)
        if codigo_dane is None:
            return result
    
    # Query
    close_conn = False
    if conn is None:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        close_conn = True
    
    try:
        # DNP tiene estructura: indicador, departamento (código), dato
        # Indicadores: MDM, Componente de gestión, Componente de resultados
        query = """
            SELECT 
                indicador,
                AVG(CAST(dato AS FLOAT)) as avg_valor,
                COUNT(DISTINCT codigo_entidad) as n_municipios
            FROM dnp_planes_desarrollo.dnp_medicion_desempeno_municipal
            WHERE departamento = ?
              AND indicador IN ('MDM', 'Componente de gestión', 'Componente de resultados')
              AND dato IS NOT NULL
            GROUP BY indicador
        """
        
        df = conn.execute(query, [str(codigo_dane)]).fetchdf()
        
        if not df.empty:
            result['en_plan_desarrollo'] = True
            result['municipios_evaluados'] = int(df['n_municipios'].max())
            
            for _, row in df.iterrows():
                ind = row['indicador']
                val = row['avg_valor']
                if ind == 'MDM':
                    result['puntaje_mdm'] = round(val, 2) if val else None
                elif ind == 'Componente de gestión':
                    result['componente_gestion'] = round(val, 2) if val else None
                elif ind == 'Componente de resultados':
                    result['componente_resultados'] = round(val, 2) if val else None
    
    except Exception as e:
        print(f"Error consultando DNP: {e}")
    
    finally:
        if close_conn:
            conn.close()
    
    return result


# ============================================================================
# CLUSTER EMPRESARIAL
# ============================================================================

def get_sectores_ciiu_for_nbc(nbc: str, conn: duckdb.DuckDBPyConnection = None) -> List[str]:
    """
    Obtiene secciones CIIU relacionadas con un NBC usando la cadena de mapeo:
    NBC -> Areas_Cualificacion_CUOC -> Seccion_CIIU
    
    Args:
        nbc: Nombre del Núcleo Básico de Conocimiento
        conn: Conexión DuckDB opcional
    
    Returns:
        Lista de códigos de sección CIIU (ej: ['J', 'R'])
    """
    close_conn = False
    if conn is None:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        close_conn = True
    
    try:
        # 1. Obtener áreas de cualificación para el NBC
        # Columna es NBC no NBC_SNIES
        query_areas = """
            SELECT DISTINCT Areas_Cualificacion_CUOC
            FROM catalogo_curado.mapeo_nbc_cuoc
            WHERE NBC ILIKE ?
        """
        df_areas = conn.execute(query_areas, [f"%{nbc}%"]).fetchdf()
        
        if df_areas.empty:
            return []
        
        # Extraer áreas (pueden venir separadas por |)
        areas = set()
        for row in df_areas['Areas_Cualificacion_CUOC'].tolist():
            if row:
                for a in str(row).split('|'):
                    areas.add(a.strip())
        
        if not areas:
            return []
        
        # 2. Obtener secciones CIIU para esas áreas
        # Usar ML para matching de áreas (pueden tener variaciones)
        query_ciiu = """
            SELECT DISTINCT Seccion_CIIU
            FROM catalogo_curado.mapeo_cuoc_ciiu
            WHERE Area_Cualificacion_CUOC IN ({})
        """.format(','.join(['?'] * len(areas)))
        
        df_ciiu = conn.execute(query_ciiu, list(areas)).fetchdf()
        
        # Si no hay match exacto, intentar con normalización
        if df_ciiu.empty:
            # Obtener todas las áreas en el mapeo CIIU
            df_all_areas = conn.execute("""
                SELECT DISTINCT Area_Cualificacion_CUOC
                FROM catalogo_curado.mapeo_cuoc_ciiu
            """).fetchdf()
            
            # Match normalizado
            ciiu_areas_normalized = {
                normalize_text(a): a 
                for a in df_all_areas['Area_Cualificacion_CUOC'].tolist()
            }
            
            matched_areas = []
            for area in areas:
                norm_area = normalize_text(area)
                if norm_area in ciiu_areas_normalized:
                    matched_areas.append(ciiu_areas_normalized[norm_area])
            
            if matched_areas:
                df_ciiu = conn.execute("""
                    SELECT DISTINCT Seccion_CIIU
                    FROM catalogo_curado.mapeo_cuoc_ciiu
                    WHERE Area_Cualificacion_CUOC IN ({})
                """.format(','.join(['?'] * len(matched_areas))), matched_areas).fetchdf()
        
        sectores = df_ciiu['Seccion_CIIU'].tolist() if not df_ciiu.empty else []
        return sectores
    
    except Exception as e:
        print(f"Error obteniendo sectores CIIU: {e}")
        return []
    
    finally:
        if close_conn:
            conn.close()


def get_cluster_empresarial(nbc: str, depto: str, conn: duckdb.DuckDBPyConnection = None, 
                            threshold: int = 10) -> Dict:
    """
    Determina si existe un cluster empresarial en el departamento
    para los sectores relacionados con el NBC.
    
    Usa la cadena: NBC -> CUOC -> CIIU -> RUES
    
    Args:
        nbc: Nombre del NBC
        depto: Departamento
        conn: Conexión DuckDB opcional
        threshold: Mínimo de empresas para considerar cluster
    
    Returns:
        Dict con:
            - hay_cluster: bool
            - total_empresas: int
            - sectores_relacionados: List[str]
            - top_sectores: List[Dict] con sector y count
            - fuente: str
    """
    result = {
        'hay_cluster': False,
        'total_empresas': 0,
        'sectores_relacionados': [],
        'top_sectores': [],
        'fuente': 'RUES - Cámaras de Comercio 2024',
    }
    
    close_conn = False
    if conn is None:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        close_conn = True
    
    try:
        # 1. Obtener sectores CIIU para el NBC
        sectores = get_sectores_ciiu_for_nbc(nbc, conn)
        
        if not sectores:
            # Fallback: usar ML para encontrar sectores relacionados
            sectores = _get_sectores_ciiu_ml(nbc, conn)
        
        result['sectores_relacionados'] = sectores
        
        if not sectores:
            return result
        
        # 2. Normalizar departamento
        canonical, _ = robust_depto_match(depto, use_ml=True)
        if not canonical:
            return result
        
        # Construir variaciones del nombre para el query
        depto_variations = _build_depto_sql_variations(canonical)
        
        # 3. Contar empresas en RUES
        # sector_ciiu en RUES son códigos como "4631", necesitamos extraer la sección
        # La sección CIIU es la primera letra para divisiones 01-99
        # Pero en RUES puede ser código numérico de 4 dígitos
        
        # Construir condiciones para sectores
        # Los sectores son secciones CIIU (letras A-U), pero RUES tiene códigos numéricos
        # Necesitamos el mapeo Sección -> División
        seccion_to_division = _get_seccion_division_map()
        
        divisiones = []
        for seccion in sectores:
            if seccion in seccion_to_division:
                divisiones.extend(seccion_to_division[seccion])
        
        if not divisiones:
            return result
        
        # Query RUES con divisiones
        division_conditions = ' OR '.join([f"sector_ciiu LIKE '{d}%'" for d in divisiones])
        depto_condition = ' OR '.join([f"departamento ILIKE ?" for _ in depto_variations])
        
        query = f"""
            SELECT 
                sector_ciiu,
                COUNT(*) as n_empresas
            FROM rues_camaras_comercio.top_10000_empresas_mas_grandes_colombia
            WHERE ({depto_condition})
              AND ({division_conditions})
            GROUP BY sector_ciiu
            ORDER BY n_empresas DESC
        """
        
        df = conn.execute(query, list(depto_variations)).fetchdf()
        
        if not df.empty:
            total = df['n_empresas'].sum()
            result['total_empresas'] = int(total)
            result['hay_cluster'] = total >= threshold
            result['top_sectores'] = [
                {'sector': row['sector_ciiu'], 'empresas': int(row['n_empresas'])}
                for _, row in df.head(5).iterrows()
            ]
    
    except Exception as e:
        print(f"Error obteniendo cluster empresarial: {e}")
    
    finally:
        if close_conn:
            conn.close()
    
    return result


def _build_depto_sql_variations(canonical: str) -> List[str]:
    """Construye lista de variaciones para SQL ILIKE."""
    variations = [
        canonical,
        canonical.upper(),
        canonical.title(),
    ]
    
    # Agregar versiones con tildes comunes
    tilde_map = {
        'narino': 'nariño',
        'cordoba': 'córdoba',
        'bolivar': 'bolívar',
        'boyaca': 'boyacá',
        'caqueta': 'caquetá',
        'choco': 'chocó',
        'quindio': 'quindío',
        'atlantico': 'atlántico',
        'bogota': 'bogotá',
    }
    
    for sin_tilde, con_tilde in tilde_map.items():
        if sin_tilde in canonical:
            with_tilde = canonical.replace(sin_tilde, con_tilde)
            variations.append(with_tilde)
            variations.append(with_tilde.upper())
            variations.append(with_tilde.title())
    
    return list(set(variations))


def _get_seccion_division_map() -> Dict[str, List[str]]:
    """
    Mapeo de sección CIIU (letra) a divisiones (2 dígitos).
    Basado en CIIU Rev 4.
    """
    return {
        'A': ['01', '02', '03'],  # Agricultura
        'B': ['05', '06', '07', '08', '09'],  # Minería
        'C': ['10', '11', '12', '13', '14', '15', '16', '17', '18', '19', 
              '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', 
              '30', '31', '32', '33'],  # Manufactura
        'D': ['35'],  # Electricidad
        'E': ['36', '37', '38', '39'],  # Agua/saneamiento
        'F': ['41', '42', '43'],  # Construcción
        'G': ['45', '46', '47'],  # Comercio
        'H': ['49', '50', '51', '52', '53'],  # Transporte
        'I': ['55', '56'],  # Alojamiento/comida
        'J': ['58', '59', '60', '61', '62', '63'],  # Información/comunicaciones
        'K': ['64', '65', '66'],  # Financiero
        'L': ['68'],  # Inmobiliario
        'M': ['69', '70', '71', '72', '73', '74', '75'],  # Profesionales
        'N': ['77', '78', '79', '80', '81', '82'],  # Administrativos
        'O': ['84'],  # Administración pública
        'P': ['85'],  # Educación
        'Q': ['86', '87', '88'],  # Salud
        'R': ['90', '91', '92', '93'],  # Arte/entretenimiento
        'S': ['94', '95', '96'],  # Otros servicios
        'T': ['97', '98'],  # Hogares empleadores
        'U': ['99'],  # Organismos extraterritoriales
    }


def _get_sectores_ciiu_ml(nbc: str, conn: duckdb.DuckDBPyConnection) -> List[str]:
    """
    Fallback ML: encuentra sectores CIIU relacionados con un NBC
    usando embeddings cuando el mapeo directo falla.
    """
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Cargar descripciones de secciones CIIU
        seccion_descriptions = {
            'A': 'agricultura ganadería silvicultura pesca',
            'B': 'explotación minas canteras minería',
            'C': 'industrias manufactureras fabricación producción',
            'D': 'suministro electricidad gas vapor',
            'E': 'agua alcantarillado gestión desechos',
            'F': 'construcción edificación obra civil',
            'G': 'comercio reparación vehículos retail',
            'H': 'transporte almacenamiento logística',
            'I': 'alojamiento hoteles restaurantes comida',
            'J': 'información comunicaciones software medios',
            'K': 'actividades financieras seguros banca',
            'L': 'actividades inmobiliarias bienes raíces',
            'M': 'actividades profesionales científicas técnicas consultoría',
            'N': 'actividades administrativas servicios apoyo',
            'O': 'administración pública defensa gobierno',
            'P': 'educación enseñanza formación',
            'Q': 'salud atención médica asistencia social',
            'R': 'arte entretenimiento recreación cultura música',
            'S': 'otras actividades servicios personales',
            'T': 'actividades hogares empleadores domésticos',
            'U': 'actividades organizaciones extraterritoriales',
        }
        
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Embedding del NBC
        nbc_emb = model.encode([nbc.lower()])
        
        # Embeddings de secciones
        sections = list(seccion_descriptions.keys())
        descs = list(seccion_descriptions.values())
        desc_embs = model.encode(descs)
        
        # Similitud
        sims = cosine_similarity(nbc_emb, desc_embs)[0]
        
        # Retornar secciones con similitud > 0.3
        related = []
        for i, sim in enumerate(sims):
            if sim > 0.3:
                related.append((sections[i], sim))
        
        related.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in related[:3]]  # Top 3
    
    except Exception as e:
        print(f"Error en ML fallback: {e}")
        return []


# ============================================================================
# CONECTIVIDAD TERRITORIAL MEJORADA
# ============================================================================

def get_conectividad_territorial_mejorada(depto: str, conn: duckdb.DuckDBPyConnection = None) -> Dict:
    """
    Obtiene indicadores de conectividad territorial mejorados.
    Incluye velocidad y tecnología además de cobertura.
    
    Args:
        depto: Departamento
        conn: Conexión opcional
    
    Returns:
        Dict con indicadores de conectividad
    """
    result = {
        'indice_conectividad': 0,
        'accesos_internet': 0,
        'cobertura_4g': 0,
        'velocidad_promedio_mbps': None,
        'tecnologia_predominante': None,
        'fuente': 'MinTIC - Conectividad 2024',
    }
    
    # Normalizar departamento
    canonical, _ = robust_depto_match(depto, use_ml=True)
    if not canonical:
        return result
    
    depto_variations = _build_depto_sql_variations(canonical)
    
    close_conn = False
    if conn is None:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        close_conn = True
    
    try:
        # Query internet fijo
        # Columnas reales: departamento, tecnologia, velocidad_bajada, no_de_accesos
        depto_condition = ' OR '.join([f"departamento ILIKE ?" for _ in depto_variations])
        
        query_internet = f"""
            SELECT 
                SUM(CAST(REPLACE(no_de_accesos, ',', '') AS INTEGER)) as total_accesos,
                AVG(CAST(REPLACE(velocidad_bajada, ',', '.') AS FLOAT)) as avg_velocidad,
                tecnologia,
                COUNT(*) as n_registros
            FROM conectividad.internet_fijo_accesos
            WHERE {depto_condition}
            GROUP BY tecnologia
            ORDER BY n_registros DESC
        """
        
        df = conn.execute(query_internet, list(depto_variations)).fetchdf()
        
        if not df.empty:
            result['accesos_internet'] = int(df['total_accesos'].sum()) if df['total_accesos'].sum() else 0
            result['velocidad_promedio_mbps'] = round(df['avg_velocidad'].mean(), 1) if df['avg_velocidad'].mean() else None
            result['tecnologia_predominante'] = df.iloc[0]['tecnologia'] if not df.empty else None
        
        # Query cobertura 4G
        # Tabla: cobertura_móvil_por_tecnología_departamento_y_muni
        # Columnas: departamento, cobertuta_4g (S/N)
        query_4g = f"""
            SELECT 
                COUNT(CASE WHEN cobertuta_4g = 'S' THEN 1 END) * 100.0 / COUNT(*) as pct_4g
            FROM competencias_tic."cobertura_móvil_por_tecnología_departamento_y_muni"
            WHERE {depto_condition}
        """
        
        df_4g = conn.execute(query_4g, list(depto_variations)).fetchdf()
        
        if not df_4g.empty and df_4g['pct_4g'].iloc[0]:
            result['cobertura_4g'] = round(df_4g['pct_4g'].iloc[0], 1)
        
        # Calcular índice de conectividad
        # Normalizado: accesos/100000 habitantes (aprox) + cobertura 4G
        if result['cobertura_4g'] > 0 or result['accesos_internet'] > 0:
            idx_accesos = min(result['accesos_internet'] / 100000, 1) * 50
            idx_4g = result['cobertura_4g'] * 0.5
            result['indice_conectividad'] = round(idx_accesos + idx_4g, 1)
    
    except Exception as e:
        print(f"Error obteniendo conectividad: {e}")
    
    finally:
        if close_conn:
            conn.close()
    
    return result


# ============================================================================
# TEST
# ============================================================================

if __name__ == '__main__':
    print("=== TEST FUNCIONES TERRITORIALES ROBUSTAS ===\n")
    
    # Test DNP
    print("--- TEST DNP ---")
    for depto in ["NARIÑO", "Narino", "BOGOTÁ D.C.", "bogota", "Armenia"]:
        result = get_desempeno_dnp(depto)
        print(f"'{depto}' -> en_plan={result['en_plan_desarrollo']}, "
              f"MDM={result['puntaje_mdm']}, municipios={result['municipios_evaluados']}")
    
    # Test Cluster
    print("\n--- TEST CLUSTER EMPRESARIAL ---")
    for nbc, depto in [("Música", "ANTIOQUIA"), ("Ingeniería de sistemas", "BOGOTÁ D.C."), 
                       ("Medicina", "Valle")]:
        result = get_cluster_empresarial(nbc, depto)
        print(f"'{nbc}' en '{depto}' -> cluster={result['hay_cluster']}, "
              f"empresas={result['total_empresas']}, sectores={result['sectores_relacionados'][:2]}")
    
    # Test Conectividad
    print("\n--- TEST CONECTIVIDAD ---")
    for depto in ["NARIÑO", "Bogotá D.C.", "Armenia"]:
        result = get_conectividad_territorial_mejorada(depto)
        print(f"'{depto}' -> índice={result['indice_conectividad']}, "
              f"velocidad={result['velocidad_promedio_mbps']} Mbps")
