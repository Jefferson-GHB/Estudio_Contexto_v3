"""
Puente SNIES <-> SIET/ETDH via embeddings semanticos (v2 — Julio 2026).

ARQUITECTURA v2 (Pipeline ML Unificado):
  NBC -> competencias CUOC (DB) -> embedding -> busqueda semantica 
  -> two-stage retrieval -> threshold adaptativo -> Bridge dict

  Funciones principales:
    - _get_nbc_skills_profile():    NBC -> skills via SQL puro (sin cadena estructural)
    - match_nbc_to_siet_v2():       Pipeline ML unificado de matching
    - get_skills_bridge_analysis_v2(): Puente de competencias completo
    - validate_bridge():            4 checks automaticos de coherencia
    - precompute_siet_corpus():     Cache de embeddings del corpus SIET

LEGACY (v1, mantenido por compatibilidad):
    - get_siet_areas_from_campos_amplios(): Cadena estructural CINE-F -> SIET
    - _match_nbc_to_cuoc_structural():      Matching estructural NBC -> CUOC
    - _match_programs_to_cuoc():            Camino inverso SIET -> CUOC
    - match_nbc_to_siet():                  Matching v1 con pre-filtro estructural
    - get_skills_bridge_analysis():         Puente v1 con dos caminos

Tablas fuente en repositorio.duckdb:
  - catalogo_curado.catalogo_nbc_snies: NBC -> Area_Conocimiento, CINE_Campo_Amplio
  - catalogo_curado.mapeo_cuoc_cinef_amplio: CINE -> Area_Cualificacion_CUOC
  - catalogo_curado.mapeo_cuoc_area_cualificacion: Area -> Ocupaciones CUOC
  - competencias.cuoc_conocimientos: Ocupacion -> conocimientos
  - competencias.cuoc_destrezas: Ocupacion -> destrezas
  - catalogo_curado.mapeo_cuoc_ciiu: Area_Cualificacion -> Sectores CIIU
  - siet.siet_programas: Programas ETDH con Area de Desempeno
"""

import unicodedata
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple

from data.constants import STOPWORDS, SIET_PREFIXES_NORM, ML_SIMILARITY


def _normalize_text(text: str) -> str:
    """Remove accents and normalize for comparison."""
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


# ==============================================================================
# 1. CADENA ESTRUCTURAL: NBC -> CINE-F -> Area Cualificacion -> Ocupaciones
#    Basado 100% en tablas oficiales (catalogo_nbc_snies + mapeo_cuoc_cinef_amplio)
# ==============================================================================

# Caches globales para evitar re-queries
_structural_chain_cache: Dict[str, Dict] = {}
_skills_profile_cache: Dict[str, Dict] = {}

def _query_siet_areas_from_campo_amplio(campo_amplio: str, conn) -> List[str]:
    """Obtiene areas SIET para un Campo Amplio via JOIN SQL directo."""
    if not campo_amplio:
        return []
    try:
        campo_norm = _normalize_text(campo_amplio)
        df = conn.execute("""
            SELECT DISTINCT snies.CAMPO_AMPLIO, siet.Area_Desempeno_SIET
            FROM catalogo_curado.mapeo_cinef_snies_codigo snies
            JOIN catalogo_curado.mapeo_cinef_detallado_siet siet
                ON snies.CINE_F_SNIES = siet.CINE_F_Campo_Detallado
            ORDER BY siet.Area_Desempeno_SIET
        """).fetchdf()
        if df.empty:
            return []
        df_norm_col = df['CAMPO_AMPLIO'].apply(_normalize_text)
        matched = df[df_norm_col == campo_norm]
        if matched.empty:
            for i, row in df.iterrows():
                if campo_norm in df_norm_col.iloc[i] or df_norm_col.iloc[i] in campo_norm:
                    matched = df[df_norm_col == df_norm_col.iloc[i]]
                    break
        return matched['Area_Desempeno_SIET'].unique().tolist() if not matched.empty else []
    except Exception as e:
        print(f"[Structural] Error querying SIET areas for '{campo_amplio}': {e}")
        return []


def _resolve_structural_chain(nbc_nombre: str, conn) -> Dict:
    """
    Resolucion ESTRUCTURAL completa: NBC -> CINE-F -> Area MNC/CNC -> Ocupaciones CUOC.

    Usa SOLO tablas oficiales (JOINs en DB), cero ML en este paso.
    Es la base sobre la que luego se aplica ML para matching con SIET.

    Cadena:
    1. NBC -> catalogo_nbc_snies -> CINE_Campo_Amplio + Area_Conocimiento
    2. CINE_Campo_Amplio -> mapeo_cuoc_cinef_amplio -> [Area_Cualificacion_CUOC]
    3. Area_Cualificacion -> mapeo_cuoc_area_cualificacion -> [Ocupaciones CUOC]
    4. CINE_Campo_Amplio -> MAPEO_CINEF_DETALLADO_SIET -> [Areas_Desempeno_SIET]

    Returns:
        {
            'nbc': str,
            'cine_campo_amplio': str,
            'area_conocimiento': str,
            'areas_cualificacion': [str],   # Areas MNC/CNC
            'ocupaciones_df': DataFrame,     # [codigo_cuoc, nombre_ocupacion, area_cualificacion]
            'areas_desempeno_siet': [str],   # Areas SIET para pre-filtrado
        }
    """
    global _structural_chain_cache
    cache_key = nbc_nombre.strip().upper()
    if cache_key in _structural_chain_cache:
        return _structural_chain_cache[cache_key]

    result = {
        'nbc': nbc_nombre,
        'cine_campo_amplio': None,
        'area_conocimiento': None,
        'areas_cualificacion': [],
        'ocupaciones_df': pd.DataFrame(),
        'areas_desempeno_siet': [],
    }

    try:
        nbc_esc = nbc_nombre.replace("'", "''")
        nbc_norm = _normalize_text(nbc_nombre)

        # --- PASO 1: NBC -> CINE_Campo_Amplio ---
        # Prioridad: tabla corregida (57 NBCs auditados), luego tabla original (fallback)
        df_nbc = pd.DataFrame()
        used_corrected = False

        # Intentar primero con tabla corregida
        try:
            df_corrected = conn.execute("""
                SELECT NBC, AREA_CONOCIMIENTO as Area_Conocimiento, CINE_Campo_Amplio
                FROM catalogo_curado.catalogo_nbc_snies_corregido
            """).fetchdf()
            if not df_corrected.empty:
                df_corrected['_norm'] = df_corrected['NBC'].apply(_normalize_text)
                mask = df_corrected['_norm'] == nbc_norm
                if mask.any():
                    df_nbc = df_corrected[mask].drop(columns=['_norm']).head(1)
                    used_corrected = True
        except Exception:
            pass  # Tabla corregida no existe aún, usar original

        # Fallback a tabla original
        if df_nbc.empty:
            df_all_nbcs = conn.execute("""
                SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio
                FROM catalogo_curado.catalogo_nbc_snies
            """).fetchdf()
            if not df_all_nbcs.empty:
                df_all_nbcs['_norm'] = df_all_nbcs['NBC'].apply(_normalize_text)
                mask = df_all_nbcs['_norm'] == nbc_norm
                if mask.any():
                    df_nbc = df_all_nbcs[mask].drop(columns=['_norm']).head(1)
                else:
                    first_part = nbc_norm.split(',')[0].strip()
                    if first_part:
                        mask2 = df_all_nbcs['_norm'].str.contains(first_part, na=False)
                        if mask2.any():
                            df_nbc = df_all_nbcs[mask2].drop(columns=['_norm']).head(1)

        if df_nbc.empty:
            print(f"[Structural] NBC '{nbc_nombre}' no encontrado en catalogo")
            _structural_chain_cache[cache_key] = result
            return result

        result['cine_campo_amplio'] = df_nbc['CINE_Campo_Amplio'].iloc[0]
        result['area_conocimiento'] = df_nbc['Area_Conocimiento'].iloc[0]
        cine = result['cine_campo_amplio']

        print(f"[Structural] NBC '{nbc_nombre}' -> corrected={used_corrected}, "
              f"CINE={result['cine_campo_amplio']}")

        if not cine or str(cine) == 'None':
            print(f"[Structural] NBC '{nbc_nombre}' sin CINE_Campo_Amplio")
            _structural_chain_cache[cache_key] = result
            return result

        # --- PASO 2: CINE -> Areas_Cualificacion (tabla mapeo_cuoc_cinef_amplio) ---
        cine_esc = cine.replace("'", "''")
        cine_norm = _normalize_text(cine)

        df_areas_all = conn.execute("""
            SELECT CINE_Campo_Amplio, Area_Cualificacion_CUOC, Total_Ocupaciones
            FROM catalogo_curado.mapeo_cuoc_cinef_amplio
        """).fetchdf()

        df_areas = pd.DataFrame()
        if not df_areas_all.empty:
            df_areas_all['_norm'] = df_areas_all['CINE_Campo_Amplio'].apply(_normalize_text)
            mask_cine = df_areas_all['_norm'] == cine_norm
            if mask_cine.any():
                df_areas = df_areas_all[mask_cine].drop(columns=['_norm'])
            else:
                # Partial match
                for _, row in df_areas_all.iterrows():
                    if cine_norm in row['_norm'] or row['_norm'] in cine_norm:
                        df_areas = df_areas_all[df_areas_all['_norm'] == row['_norm']].drop(columns=['_norm'])
                        break

        result['areas_cualificacion'] = df_areas['Area_Cualificacion_CUOC'].tolist() if not df_areas.empty else []

        # --- PASO 3: Areas -> Ocupaciones CUOC (tabla mapeo_cuoc_area_cualificacion) ---
        if result['areas_cualificacion']:
            areas_sql = ", ".join([f"'{a.replace(chr(39), chr(39)*2)}'" for a in result['areas_cualificacion']])
            df_occ = conn.execute(f"""
                SELECT DISTINCT
                    CAST(Codigo_CUOC AS VARCHAR) as codigo_cuoc,
                    Nombre_Ocupacion as nombre_ocupacion,
                    Area_Cualificacion as area_cualificacion
                FROM catalogo_curado.mapeo_cuoc_area_cualificacion
                WHERE Area_Cualificacion IN ({areas_sql})
            """).fetchdf()
            result['ocupaciones_df'] = df_occ

        # --- PASO 4: CINE -> Areas_Desempeno_SIET (via SQL) ---
        siet_areas = _query_siet_areas_from_campo_amplio(cine, conn)
        result['areas_desempeno_siet'] = siet_areas

        n_occ = len(result['ocupaciones_df'])
        n_areas = len(result['areas_cualificacion'])
        n_siet = len(result['areas_desempeno_siet'])
        print(f"[Structural] {nbc_nombre} -> CINE={cine} -> {n_areas} areas MNC -> {n_occ} ocupaciones -> {n_siet} areas SIET")

    except Exception as e:
        print(f"[Structural] Error resolviendo cadena para '{nbc_nombre}': {e}")
        import traceback
        traceback.print_exc()

    _structural_chain_cache[cache_key] = result
    return result


def get_siet_areas_from_campos_amplios(campos_amplios: List[str], conn=None) -> List[str]:
    """
    Mapea campos amplios CINE-F a áreas de desempeño SIET usando cadena oficial en DB.
    
    Cadena estructural (100% tablas oficiales, cero ML):
      Campo Amplio CINE-F
        → catalogo_curado.mapeo_cinef_snies_codigo (CAMPO_AMPLIO → CINE_F_SNIES)
        → catalogo_curado.mapeo_cinef_detallado_siet (CINE_F_Campo_Detallado → Area_Desempeno_SIET)
    
    Esta cadena usa clasificaciones oficiales colombianas:
      - CINE-F UNESCO 2013 (campo amplio → campo detallado)
      - Áreas de Desempeño SIET/CNO (9 macro-áreas ocupacionales)
    
    Args:
        campos_amplios: Lista de campos amplios seleccionados en el sidebar SNIES
                        (Title Case, ej: "Ingeniería, Industria y Construcción")
        conn: Conexión DuckDB opcional (se crea una si no se proporciona)
    
    Returns:
        Lista única de áreas de desempeño SIET correspondientes (valores exactos de la DB)
    """
    if not campos_amplios:
        return []
    
    close_conn = False
    if conn is None:
        try:
            from config.database import get_conn
            conn = get_conn()
            close_conn = True
        except Exception as e:
            print(f"[SIET-Filter] No se pudo obtener conexion DB: {e}")
            return []
    
    try:
        # 1. Obtener todos los CAMPO_AMPLIO del mapeo para match normalizado
        all_campos = conn.execute(
            "SELECT DISTINCT CAMPO_AMPLIO FROM catalogo_curado.mapeo_cinef_snies_codigo WHERE CAMPO_AMPLIO IS NOT NULL"
        ).fetchall()
        
        # 2. Match normalizado (accent + case insensitive) en Python
        matched_campos = []
        for ca_input in campos_amplios:
            ca_norm = _normalize_text(ca_input)
            for (ca_db,) in all_campos:
                if _normalize_text(ca_db) == ca_norm:
                    matched_campos.append(ca_db)
                    break
            else:
                # Fuzzy: match por palabras significativas (ignora stopwords)
                stopwords = {'Y', 'DE', 'LA', 'LAS', 'LOS', 'DEL', 'EN', 'E', 'EL'}
                ca_words = set(ca_norm.split()) - stopwords
                best_db, best_score = None, 0
                for (ca_db,) in all_campos:
                    db_norm = _normalize_text(ca_db)
                    db_words = set(db_norm.split()) - stopwords
                    # Contar coincidencias con tolerancia singular/plural (±1 char)
                    hits = 0
                    for w in ca_words:
                        for dw in db_words:
                            if w == dw or w.startswith(dw) or dw.startswith(w):
                                hits += 1
                                break
                    score = hits / max(len(ca_words | db_words), 1)
                    if score > best_score:
                        best_score = score
                        best_db = ca_db
                if best_db and best_score >= 0.4:
                    matched_campos.append(best_db)
                else:
                    print(f"[SIET-Filter] Sin match fuzzy para: {ca_input} (best={best_score:.0%})")
        
        if not matched_campos:
            print(f"[SIET-Filter] No se encontro match para campos amplios: {campos_amplios}")
            return []
        
        # 3. SQL JOIN con los valores exactos encontrados
        campos_sql = ", ".join([f"'{ca.replace(chr(39), chr(39)*2)}'" for ca in matched_campos])
        query = f"""
            SELECT DISTINCT siet.Area_Desempeno_SIET
            FROM catalogo_curado.mapeo_cinef_snies_codigo snies
            JOIN catalogo_curado.mapeo_cinef_detallado_siet siet
                ON snies.CINE_F_SNIES = siet.CINE_F_Campo_Detallado
            WHERE snies.CAMPO_AMPLIO IN ({campos_sql})
            ORDER BY 1
        """
        df = conn.execute(query).fetchdf()
        result = df['Area_Desempeno_SIET'].tolist() if not df.empty else []
        
        if result:
            print(f"[SIET-Filter] Campo Amplio ({', '.join(campos_amplios[:3])}) -> {len(result)} SIET areas")
        else:
            print(f"[SIET-Filter] JOIN vacio para campos: {matched_campos}")
        
        return result
        
    except Exception as e:
        print(f"[SIET-Filter] Error en mapeo Campo Amplio -> SIET: {e}")
        return []
    finally:
        if close_conn:
            conn.close()


# ==============================================================================
# 2. PERFIL DE COMPETENCIAS OCUPACIONALES (conocimientos + destrezas CUOC)
# ==============================================================================

def _get_occupational_skills_profile(
    occupation_names: List[str],
    conn,
) -> Dict:
    """
    Extrae el perfil de competencias de un conjunto de ocupaciones CUOC.

    Usa tablas:
    - competencias.cuoc_conocimientos: Ocupacion -> conocimientos
    - competencias.cuoc_destrezas: Ocupacion -> destrezas

    Returns:
        {
            'conocimientos': [{'nombre': X, 'n_ocupaciones': N, 'relevancia': R}, ...],
            'destrezas': [{'nombre': Y, 'n_ocupaciones': N, 'relevancia': R}, ...],
            'top_conocimientos_text': [str],
            'top_destrezas_text': [str],
            'occupation_names_text': [str],
        }
    """
    result = {
        'conocimientos': [],
        'destrezas': [],
        'top_conocimientos_text': [],
        'top_destrezas_text': [],
        'occupation_names_text': [],
    }
    if not occupation_names:
        return result

    # Cache key
    cache_key = "|".join(sorted(set(occupation_names)))[:200]
    if cache_key in _skills_profile_cache:
        return _skills_profile_cache[cache_key]

    names_sql = ", ".join([f"'{n.replace(chr(39), chr(39)*2)}'" for n in occupation_names])

    # Conocimientos
    try:
        df_con = conn.execute(f"""
            SELECT conocimiento as nombre, COUNT(DISTINCT nombre_ocupacion) as n_ocupaciones
            FROM competencias.cuoc_conocimientos
            WHERE nombre_ocupacion IN ({names_sql})
            AND conocimiento IS NOT NULL
            GROUP BY conocimiento
            ORDER BY n_ocupaciones DESC
        """).fetchdf()
        if not df_con.empty:
            max_val = max(df_con['n_ocupaciones'].max(), 1)
            result['conocimientos'] = [
                {'nombre': row['nombre'], 'n_ocupaciones': int(row['n_ocupaciones']),
                 'relevancia': round(row['n_ocupaciones'] / max_val * 100, 1)}
                for _, row in df_con.iterrows()
            ]
            result['top_conocimientos_text'] = df_con.head(20)['nombre'].tolist()
    except Exception as e:
        print(f"[Skills] Error conocimientos: {e}")

    # Destrezas
    try:
        df_des = conn.execute(f"""
            SELECT destreza as nombre, COUNT(DISTINCT nombre_ocupacion) as n_ocupaciones
            FROM competencias.cuoc_destrezas
            WHERE nombre_ocupacion IN ({names_sql})
            AND destreza IS NOT NULL
            GROUP BY destreza
            ORDER BY n_ocupaciones DESC
        """).fetchdf()
        if not df_des.empty:
            max_val = max(df_des['n_ocupaciones'].max(), 1)
            result['destrezas'] = [
                {'nombre': row['nombre'], 'n_ocupaciones': int(row['n_ocupaciones']),
                 'relevancia': round(row['n_ocupaciones'] / max_val * 100, 1)}
                for _, row in df_des.iterrows()
            ]
            result['top_destrezas_text'] = df_des.head(15)['nombre'].tolist()
    except Exception as e:
        print(f"[Skills] Error destrezas: {e}")

    result['occupation_names_text'] = occupation_names[:20]

    _skills_profile_cache[cache_key] = result
    return result


def _build_skills_enriched_query(
    nbc_nombre: str,
    skills_profile: Dict,
    max_skills: int = 12,
    max_occupations: int = 5
) -> str:
    """
    Construye un query enriquecido con competencias ocupacionales para matching ML.

    En vez de buscar "Ingenieria de sistemas" (nombre de NBC),
    busca "programacion, bases de datos, redes, algoritmos, desarrollo de software..."

    Esto es matching por COMPETENCIAS, no por nombre.
    """
    parts = []

    # Incluir top conocimientos (skills)
    top_con = skills_profile.get('top_conocimientos_text', [])[:max_skills]
    if top_con:
        parts.append("Competencias: " + ", ".join(top_con))

    # Incluir top destrezas (abilities)
    top_des = skills_profile.get('top_destrezas_text', [])[:max_skills]
    if top_des:
        parts.append("Destrezas: " + ", ".join(top_des))

    # Incluir nombres de ocupaciones representativas
    top_occ = skills_profile.get('occupation_names_text', [])[:max_occupations]
    if top_occ:
        clean_occ = []
        for occ in top_occ:
            name = occ.split(' / ')[0].strip()
            clean_occ.append(name)
        parts.append("Ocupaciones: " + ", ".join(clean_occ))

    if not parts:
        # Fallback: usar NBC nombre directamente
        nbc_core = nbc_nombre.replace(' Y AFINES', '').replace(' Y RELACIONADOS', '').strip()
        return f"Formacion tecnica laboral en {nbc_core.lower()}. Certificacion laboral en {nbc_core.lower()}."

    return ". ".join(parts) + "."


# ==============================================================================
# 3. MATCHING NBC -> OCUPACIONES CUOC (Estructural + Semantic Re-ranking)
# ==============================================================================

def _match_nbc_to_cuoc_structural(
    nbc_nombre: str,
    conn,
    top_k: int = 15,
    threshold: float = 0.20
) -> pd.DataFrame:
    """
    Matching NBC -> Ocupaciones CUOC usando cadena ESTRUCTURAL + re-ranking semantico.

    Pipeline:
    1. ESTRUCTURAL: NBC -> CINE-F -> Area_Cualificacion -> Ocupaciones CUOC
       (solo tablas oficiales, da el SUBCONJUNTO correcto de ocupaciones)
    2. ML: Semantic re-ranking de las ocupaciones dentro del subconjunto
       (da el ORDEN de relevancia usando embeddings)

    Esto resuelve:
    - "Ing. de sistemas" -> solo 20 ocupaciones TIC (no meteorologos ni biologos)
    - "Medicina" -> solo 46 ocupaciones Salud y Bienestar
    - El re-ranking ML dentro del subset correcto da precision fina.

    Returns:
        DataFrame con [codigo_cuoc, nombre_ocupacion, area_cualificacion, similitud_ml]
    """
    chain = _resolve_structural_chain(nbc_nombre, conn)

    if chain['ocupaciones_df'].empty:
        return pd.DataFrame()

    df_occ = chain['ocupaciones_df']

    # Si pocas ocupaciones, retornar todas sin re-ranking
    if len(df_occ) <= top_k:
        df_occ = df_occ.copy()
        df_occ['similitud_ml'] = 0.5
        return df_occ

    # Semantic re-ranking dentro del subconjunto estructural
    try:
        from services.ml.matching import semantic_search

        corpus_texts = df_occ['nombre_ocupacion'].tolist()
        corpus_ids = df_occ['codigo_cuoc'].tolist()

        nbc_core = nbc_nombre.replace(' Y AFINES', '').replace(' Y RELACIONADOS', '').strip()
        query = f"Profesional en {nbc_core}. Egresado de programa de {nbc_core}."

        results = semantic_search(
            query=query,
            corpus_texts=corpus_texts,
            corpus_ids=corpus_ids,
            top_k=top_k,
            threshold=threshold,
            cache_name="cuoc_occ_structural"
        )

        if results:
            result_codes = [r['id'] for r in results]
            result_scores = {r['id']: r['score'] for r in results}
            matched_df = df_occ[df_occ['codigo_cuoc'].isin(result_codes)].copy()
            matched_df['similitud_ml'] = matched_df['codigo_cuoc'].map(result_scores)
            matched_df = matched_df.sort_values('similitud_ml', ascending=False)
            return matched_df

    except ImportError:
        pass
    except Exception as e:
        print(f"[ML-CUOC] Error en re-ranking: {e}")

    # Fallback: retornar todas sin re-ranking
    df_occ = df_occ.copy()
    df_occ['similitud_ml'] = 0.5
    return df_occ.head(top_k)


# Legacy alias for backward compatibility
def _match_nbc_to_cuoc_via_areas(nbc_nombre, conn, top_areas=5, top_k=15, threshold=0.20):
    """Alias -> _match_nbc_to_cuoc_structural (mantiene compatibilidad)."""
    return _match_nbc_to_cuoc_structural(nbc_nombre, conn, top_k=top_k, threshold=threshold)


# ==============================================================================
# 4. MATCHING NBC -> PROGRAMAS SIET/ETDH (Skills-Based)
#    Este es el matching ML real: usa perfil de competencias como query
# ==============================================================================

def _strip_siet_prefix(name: str) -> str:
    """Strip common SIET program prefixes using normalized comparison."""
    name_norm = _normalize_text(name)
    for prefix in SIET_PREFIXES_NORM:
        if name_norm.startswith(prefix):
            return name[len(prefix):].strip()
    return name


# ==============================================================================
# PRE-COMPUTO DE CORPUS SIET (v2 — Pipeline ML Unificado)
# ==============================================================================

_siet_corpus_cache = None  # (clean_texts, canonical_names, ids, embeddings)
_siet_canonical_map = None  # Dict[raw_name -> canonical_name]

def precompute_siet_corpus(conn) -> tuple:
    """
    Pre-computa embeddings de programas SIET normalizados (pipeline v2).

    Usa la capa de transformacion inteligente (data/transform.py) para:
      1. Detectar variantes de acento/case del mismo programa
      2. Elegir forma canonica (la mas frecuente)
      3. Deducplicar por nombre canonico
      4. Limpiar prefijos "TECNICO LABORAL EN..."

    Returns:
        (clean_texts, canonical_names, ids, embeddings)
    """
    global _siet_corpus_cache, _siet_canonical_map
    if _siet_corpus_cache is not None:
        return _siet_corpus_cache

    from data.transform import build_canonical_siet_mapping, build_siet_corpus_clean

    # Construir mapeo canonico (agrupa variantes de acento/case)
    if _siet_canonical_map is None:
        _siet_canonical_map = build_canonical_siet_mapping(conn)

    # Construir corpus limpio
    clean_texts, canonical_names = build_siet_corpus_clean(conn, _siet_canonical_map)

    print(f"[SIET-Corpus] {len(clean_texts)} programas canonicos")

    # Pre-computar embeddings
    from services.ml.matching import get_or_compute_embeddings
    corpus_embeddings = get_or_compute_embeddings(
        clean_texts, cache_name="siet_corpus_v2"
    )
    corpus_ids = list(range(len(clean_texts)))

    if corpus_embeddings is None:
        _siet_corpus_cache = (clean_texts, canonical_names, corpus_ids, None)
    else:
        _siet_corpus_cache = (clean_texts, canonical_names, corpus_ids, corpus_embeddings)

    return _siet_corpus_cache


def _get_nbc_skills_profile(nbc_nombre: str, conn) -> Dict:
    """
    Obtiene perfil de competencias del NBC directamente desde DB.
    
    Pipeline SQL puro (sin _resolve_structural_chain):
      NBC -> mapeo_cuoc_cinef_amplio -> Area_Cualificacion ->
      mapeo_cuoc_area_cualificacion -> Ocupaciones CUOC ->
      cuoc_conocimientos + cuoc_destrezas -> Skills Profile
    
    Returns:
        Dict con: conocimientos, destrezas, ocupaciones (mismo formato que
        _get_occupational_skills_profile)
    """
    # Paso 1: Resolver NBC a nombre canonico via capa de transformacion
    from data.transform import normalize_nbc_name
    nbc_canonical = normalize_nbc_name(nbc_nombre, conn)
    nbc_esc = nbc_canonical.replace("'", "''")
    df_areas = conn.execute("""
        SELECT DISTINCT mc.Area_Cualificacion_CUOC
        FROM catalogo_curado.mapeo_cuoc_cinef_amplio mc
        JOIN catalogo_curado.catalogo_nbc_snies cn
            ON UPPER(mc.CINE_Campo_Amplio) = UPPER(cn.CINE_Campo_Amplio)
        WHERE STRIP_ACCENTS(UPPER(cn.NBC)) = STRIP_ACCENTS(UPPER(?))
    """, [nbc_esc]).fetchdf()

    if df_areas.empty:
        # Fallback: intentar con tabla corregida
        df_areas = conn.execute("""
            SELECT DISTINCT mc.Area_Cualificacion_CUOC
            FROM catalogo_curado.mapeo_cuoc_cinef_amplio mc
            JOIN catalogo_curado.catalogo_nbc_snies_corregido cn
                ON UPPER(mc.CINE_Campo_Amplio) = UPPER(cn.CINE_Campo_Amplio)
            WHERE STRIP_ACCENTS(UPPER(cn.NBC)) = STRIP_ACCENTS(UPPER(?))
        """, [nbc_esc]).fetchdf()

    if df_areas.empty:
        print(f"[Skills] NBC '{nbc_nombre}' sin areas CUOC — usando solo nombre NBC")
        return _get_occupational_skills_profile([], conn)

    # Paso 2: Areas -> Ocupaciones CUOC
    areas_list = [a.replace("'", "''") for a in df_areas['Area_Cualificacion_CUOC'].tolist()]
    areas_sql = ", ".join([f"'{a}'" for a in areas_list])
    df_occ = conn.execute(f"""
        SELECT DISTINCT Nombre_Ocupacion
        FROM catalogo_curado.mapeo_cuoc_area_cualificacion
        WHERE Area_Cualificacion IN ({areas_sql})
    """).fetchdf()

    if df_occ.empty:
        print(f"[Skills] NBC '{nbc_nombre}' sin ocupaciones CUOC")
        return _get_occupational_skills_profile([], conn)

    # Paso 3: Ocupaciones -> Competencias (usa funcion existente)
    occ_names = df_occ['Nombre_Ocupacion'].tolist()
    print(f"[Skills] NBC '{nbc_nombre}' -> {len(df_areas)} areas -> {len(occ_names)} ocupaciones")
    return _get_occupational_skills_profile(occ_names, conn)


def _build_skills_query(nbc_nombre: str, skills: Dict, max_skills: int = 15, max_occupations: int = 5) -> str:
    """
    Construye query enriquecido con competencias para busqueda semantica.
    
    Formato: "NBC: {nombre}. Conocimientos: {top_con}. Destrezas: {top_des}."
    """
    con_texts = skills.get('top_conocimientos_text', [])[:max_skills]
    des_texts = skills.get('top_destrezas_text', [])[:max_skills]
    occ_texts = skills.get('occupation_names_text', [])[:max_occupations]

    parts = [f"NBC: {nbc_nombre}"]
    if con_texts:
        parts.append(f"Conocimientos: {', '.join(con_texts)}")
    if des_texts:
        parts.append(f"Destrezas: {', '.join(des_texts)}")
    if occ_texts:
        parts.append(f"Ocupaciones relacionadas: {', '.join(occ_texts)}")
    return ". ".join(parts) + "."


# ==============================================================================
# PIPELINE ML UNIFICADO v2 — Reemplaza la cadena estructural + matching legacy
# ==============================================================================

def match_nbc_to_siet_v2(nbc_nombre: str, conn, top_k: int = 20) -> pd.DataFrame:
    """
    Pipeline hibrido: cadena estructural (pre-filtro) + ML (ranking).

    Estrategia:
      1. Usar catalogos oficiales colombianos (DB) para identificar
         las areas SIET correctas para este NBC. Precision 100%.
      2. Pre-filtrar corpus SIET a solo programas de esas areas.
      3. ML semantico rankea dentro del subset correcto.
    
    Esto combina lo mejor de ambos mundos:
    - Catalogos = precision de area (oficial, no hardcodeado)
    - ML = ranking por relevancia (embedding semantico)

    Etapas:
      1. Obtener areas SIET via cadena estructural (DB)
      2. Obtener perfil de competencias del NBC (DB)
      3. Pre-filtrar corpus SIET a solo el area correcta
      4. Semantic search + threshold adaptativo
      5. Enriquecer con matricula y certificados
    """
    # 1. Skills desde DB
    skills = _get_nbc_skills_profile(nbc_nombre, conn)
    
    # 2. Query enriquecido
    query = _build_skills_query(nbc_nombre, skills)
    
    # 3. Obtener areas SIET esperadas via catalogo oficial (DB, no hardcodeado)
    chain = _resolve_structural_chain(nbc_nombre, conn)
    expected_areas = set(_normalize_text(a) for a in chain.get('areas_desempeno_siet', []))
    
    # 4. Cargar corpus SIET con informacion de area
    df_siet = conn.execute("""
        SELECT DISTINCT "Nombre Programa" as nombre, "Area de Desempeño" as area
        FROM siet.siet_programas
        WHERE "Nombre Programa" IS NOT NULL AND LENGTH("Nombre Programa") > 5
        ORDER BY "Nombre Programa"
    """).fetchdf()
    
    # Aplicar mapeo canonico y pre-filtro de area
    from data.transform import build_canonical_siet_mapping
    canonical = build_canonical_siet_mapping(conn)
    df_siet['canonical'] = df_siet['nombre'].map(canonical).fillna(df_siet['nombre'])
    df_siet['area_norm'] = df_siet['area'].apply(_normalize_text)
    
    if expected_areas:
        df_siet = df_siet[df_siet['area_norm'].isin(expected_areas)]
        if df_siet.empty:
            print(f"[ML-v2] Sin programas SIET en areas esperadas {expected_areas}")
            return pd.DataFrame()
        print(f"[ML-v2] Pre-filtro: {len(df_siet)} programas en areas {sorted(expected_areas)[:3]}")
    else:
        print(f"[ML-v2] Sin areas esperadas — usando corpus completo ({len(df_siet)} programas)")
    
    # Deducplicar por nombre canonico + area
    df_siet = df_siet.drop_duplicates(subset=['canonical', 'area_norm'])
    
    # Limpiar prefijos
    corpus_texts = [_strip_siet_prefix(str(n)) for n in df_siet['canonical'].tolist()]
    corpus_ids = list(range(len(corpus_texts)))
    
    if len(corpus_texts) < 5:
        return pd.DataFrame()
    
    # 5. Semantic search (single-stage, corpus ya pre-filtrado)
    from services.ml.matching import semantic_search
    results = semantic_search(
        query=query,
        corpus_texts=corpus_texts,
        corpus_ids=corpus_ids,
        top_k=min(top_k * 3, len(corpus_texts)),
        threshold=0.15,
        cache_name="siet_corpus_v2"
    )
    
    if not results:
        return pd.DataFrame()
    
    # 6. Threshold adaptativo
    scores = [r['score'] for r in results]
    threshold = max(0.25, float(np.median(scores) + 1.5 * np.std(scores))) if len(scores) >= 3 else 0.25
    threshold = min(threshold, 0.70)
    
    # Construir resultado usando los indices del corpus pre-filtrado
    matched_indices = [int(r['id']) for r in results if r['score'] >= threshold]
    if not matched_indices:
        matched_indices = [int(r['id']) for r in results[:5]]
    
    result_names = [df_siet.iloc[i]['canonical'] for i in matched_indices]
    score_by_idx = {int(r['id']): r['score'] for r in results}
    result_scores = [score_by_idx.get(i, 0.0) for i in matched_indices]
    
    if not result_names:
        return pd.DataFrame()
    
    # Cargar datos completos por nombre canonico
    names_sql = "', '".join([n.replace("'", "''") for n in result_names])
    df_result = conn.execute(f"""
        SELECT DISTINCT
            "Nombre Programa" as nombre_programa,
            "Area de Desempeño" as area_desempeno,
            "Tipo de Certificado" as tipo_certificado
        FROM siet.siet_programas
        WHERE "Nombre Programa" IN ('{names_sql}')
    """).fetchdf()
    
    if df_result.empty:
        return pd.DataFrame()
    
    # Asignar scores
    score_map = dict(zip(result_names, result_scores))
    df_result['score_final'] = df_result['nombre_programa'].map(score_map).fillna(0.0)
    
    # Enriquecer con matricula y certificados por nombre de programa
    prog_names = df_result['nombre_programa'].tolist()
    names_sql = "', '".join([n.replace("'", "''") for n in prog_names])
    
    try:
        df_mat = conn.execute(f"""
            SELECT "Nombre Programa" as np, SUM("Total Matrícula 2023") as m
            FROM siet.siet_matricula_programa_
            WHERE "Nombre Programa" IN ('{names_sql}')
            GROUP BY 1
        """).fetchdf()
        mat_map = dict(zip(df_mat['np'], df_mat['m'].fillna(0).astype(int)))
        df_result['matricula_2023'] = df_result['nombre_programa'].map(mat_map).fillna(0).astype(int)
    except Exception as e:
        print(f"[ML-v2] Matricula error: {e}")
        df_result['matricula_2023'] = 0
    
    try:
        df_cert = conn.execute(f"""
            SELECT "Nombre Programa" as np, SUM("Total Certificado 2023") as c
            FROM siet.siet_estudiantes_certificados_progr
            WHERE "Nombre Programa" IN ('{names_sql}')
            GROUP BY 1
        """).fetchdf()
        cert_map = dict(zip(df_cert['np'], df_cert['c'].fillna(0).astype(int)))
        df_result['certificados_2023'] = df_result['nombre_programa'].map(cert_map).fillna(0).astype(int)
    except Exception as e:
        print(f"[ML-v2] Certificados error: {e}")
        df_result['certificados_2023'] = 0
    
    df_result = df_result.sort_values('score_final', ascending=False).head(top_k)
    
    print(f"[ML-v2] '{nbc_nombre}' -> {len(df_result)} programas SIET (threshold={threshold:.3f})")
    return df_result


def validate_bridge(nbc_nombre: str, df_results: pd.DataFrame, conn) -> Dict:
    """
    Valida los resultados del bridge ML contra criterios de coherencia.
    
    Checks:
      1. Area SIET coherente con CINE-F del NBC
      2. Score spread > 0.1 (evita overfitting: todos los scores identicos)
      3. Al menos 1 programa con matricula > 0
      4. Top match no es outlier total
    
    Returns:
        Dict con: is_valid, warnings, metrics
    """
    warnings = []
    metrics = {}
    
    if df_results.empty:
        return {'is_valid': False, 'warnings': ['Sin resultados'], 'metrics': {}}
    
    # Check 1: Coherencia de area SIET
    chain = _resolve_structural_chain(nbc_nombre, conn)
    expected_areas = set(_normalize_text(a) for a in chain.get('areas_desempeno_siet', []))
    if expected_areas:
        top_area = _normalize_text(str(df_results.iloc[0].get('area_desempeno', '')))
        if top_area not in expected_areas:
            warnings.append(f"Top match area '{df_results.iloc[0].get('area_desempeno','?')}' "
                          f"fuera de areas esperadas {sorted(expected_areas)[:3]}")
    
    # Check 2: Score spread
    if 'score_final' in df_results.columns and len(df_results) >= 3:
        scores = df_results['score_final'].dropna().values
        if len(scores) >= 3:
            spread = float(scores.max() - scores.min())
            metrics['score_spread'] = round(spread, 3)
            metrics['score_median'] = round(float(np.median(scores)), 3)
            metrics['score_mean'] = round(float(scores.mean()), 3)
            if spread < 0.05:
                warnings.append(f"Score spread muy bajo ({spread:.3f}): posible overfitting")
    
    # Check 3: Matricula minima
    if 'matricula_2023' in df_results.columns:
        total_mat = int(df_results['matricula_2023'].sum())
        metrics['total_matricula'] = total_mat
        if total_mat == 0:
            warnings.append("Cero matriculados en programas matcheados")
    
    # Check 4: Top match no es outlier
    if 'score_final' in df_results.columns and len(df_results) >= 5:
        top_score = float(df_results['score_final'].iloc[0])
        rest_mean = float(df_results['score_final'].iloc[1:].mean())
        if rest_mean > 0 and top_score / rest_mean > 3.0:
            warnings.append(f"Top match ({top_score:.3f}) es {top_score/rest_mean:.1f}x "
                          f"mayor que la media del resto ({rest_mean:.3f})")
    
    metrics['n_results'] = len(df_results)
    
    return {
        'is_valid': len(warnings) == 0,
        'warnings': warnings,
        'metrics': metrics
    }


def match_nbc_to_siet(
    nbc_nombre: str,
    conn,
    top_k: int = 20,
    threshold: float = 0.35,
    depto: str = None
) -> pd.DataFrame:
    """
    Matching NBC -> Programas SIET/ETDH usando PERFIL DE COMPETENCIAS como puente.

    Pipeline (siguiendo la metodologia):
    1. ESTRUCTURAL: NBC -> CINE-F -> Area_Cualificacion -> Ocupaciones CUOC
    2. COMPETENCIAS: Ocupaciones CUOC -> conocimientos + destrezas (perfil de skills)
    3. ML/NLP: Construir query ENRIQUECIDO con skills (no con nombre de NBC)
    4. PRE-FILTRO: Limitar SIET a Area_Desempeno_SIET compatibles
    5. SEMANTIC SEARCH: query de skills -> nombres programas SIET

    Esto es fundamentalmente diferente a buscar "Ing de sistemas" en nombres SIET.
    Busca: "programacion, bases de datos, redes, algoritmos..." en nombres SIET.

    Returns:
        DataFrame con: nombre_programa, area_desempeno, score_semantico,
        score_estructural, score_final, matricula_2023, certificados_2023
    """
    try:
        # --- PASO 1: Obtener cadena estructural ---
        chain = _resolve_structural_chain(nbc_nombre, conn)
        structural_areas_siet = chain.get('areas_desempeno_siet', [])
        areas_cualificacion = chain.get('areas_cualificacion', [])
        df_ocupaciones = chain.get('ocupaciones_df', pd.DataFrame())

        # --- PASO 2: Obtener perfil de competencias ---
        occ_names = df_ocupaciones['nombre_ocupacion'].tolist() if not df_ocupaciones.empty else []
        skills_profile = _get_occupational_skills_profile(occ_names, conn)

        # --- PASO 3: Construir query enriquecido con skills ---
        skills_query = _build_skills_enriched_query(nbc_nombre, skills_profile)
        print(f"[ML-SIET] Skills query: {skills_query[:120]}...")

        # --- PASO 4: Obtener programas SIET candidatos ---
        conditions = []
        if depto:
            conditions.append(f"UPPER(p.\"Departamento\") = UPPER('{depto}')")

        # Pre-filtrar por areas SIET estructurales
        if structural_areas_siet:
            areas_str = "', '".join([a.replace("'", "''") for a in structural_areas_siet])
            conditions.append(f"p.\"Area de Desempeño\" IN ('{areas_str}')")

        where = " AND ".join(conditions) if conditions else "1=1"

        query_sql = f"""
        SELECT DISTINCT
            p."Nombre Programa" as nombre_programa,
            p."Area de Desempeño" as area_desempeno,
            p."Tipo de Certificado" as tipo_certificado,
            p."Estado Programa" as estado,
            p."Duración Horas" as duracion_horas,
            p."Departamento" as departamento
        FROM siet.siet_programas p
        WHERE {where}
            AND p."Nombre Programa" IS NOT NULL
            AND LENGTH(p."Nombre Programa") > 5
        """

        df_candidatos = conn.execute(query_sql).fetchdf()

        if df_candidatos.empty and structural_areas_siet:
            # Retry without structural filter
            query_all = f"""
            SELECT DISTINCT
                p."Nombre Programa" as nombre_programa,
                p."Area de Desempeño" as area_desempeno,
                p."Tipo de Certificado" as tipo_certificado,
                p."Estado Programa" as estado,
                p."Duración Horas" as duracion_horas,
                p."Departamento" as departamento
            FROM siet.siet_programas p
            WHERE p."Nombre Programa" IS NOT NULL
                AND LENGTH(p."Nombre Programa") > 5
                {f"AND UPPER(p.\"Departamento\") = UPPER('{depto}')" if depto else ''}
            """
            df_candidatos = conn.execute(query_all).fetchdf()

        if df_candidatos.empty:
            return pd.DataFrame()

        # --- PASO 5: Matching semantico con query de skills ---
        nombres_unicos = df_candidatos['nombre_programa'].unique().tolist()
        nombres_limpios = [_strip_siet_prefix(n) for n in nombres_unicos]
        idx_to_original = {str(i): nombres_unicos[i] for i in range(len(nombres_unicos))}

        from services.ml.matching import semantic_search

        results = semantic_search(
            query=skills_query,
            corpus_texts=nombres_limpios,
            corpus_ids=[str(i) for i in range(len(nombres_limpios))],
            top_k=min(top_k * 2, len(nombres_limpios)),
            threshold=0.25,
            cache_name="siet_programas_skills"
        )

        if not results:
            # If skills-query fails, fallback to NBC-name query
            nbc_core = nbc_nombre.replace(' Y AFINES', '').replace(' Y RELACIONADOS', '').strip()
            fallback_query = (
                f"{nbc_core}. "
                f"Formacion tecnica laboral en {nbc_core.lower()}. "
                f"Certificacion laboral en {nbc_core.lower()}."
            )
            results = semantic_search(
                query=fallback_query,
                corpus_texts=nombres_limpios,
                corpus_ids=[str(i) for i in range(len(nombres_limpios))],
                top_k=min(top_k * 2, len(nombres_limpios)),
                threshold=0.3,
                cache_name="siet_programas_skills"
            )

        if not results:
            # Last resort: structural only
            if structural_areas_siet:
                df_result = df_candidatos.copy()
                df_result['score_semantico'] = 0.0
                df_result['score_estructural'] = 1.0
                df_result['score_final'] = 0.5
                return df_result.head(top_k)
            return pd.DataFrame()

        # --- PASO 6: Combinar scores ---
        semantic_scores = {}
        for r in results:
            prog_name = idx_to_original.get(r['id'], '')
            semantic_scores[prog_name] = r['score']

        matched_names = set(semantic_scores.keys())
        df_matched = df_candidatos[df_candidatos['nombre_programa'].isin(matched_names)].copy()

        if df_matched.empty:
            return pd.DataFrame()

        df_matched['score_semantico'] = df_matched['nombre_programa'].map(semantic_scores).fillna(0)

        # Structural bonus: programs in correct SIET area
        structural_areas_upper = [a.upper() for a in structural_areas_siet]
        df_matched['in_structural_area'] = df_matched['area_desempeno'].apply(
            lambda x: 1.0 if str(x).upper() in structural_areas_upper else 0.0
        )
        df_matched['score_estructural'] = df_matched['in_structural_area'] * 0.05
        df_matched['score_final'] = (
            df_matched['score_semantico'] + df_matched['score_estructural']
        ).clip(0, 1)

        # --- PASO 7: Agregar datos de matricula ---
        prog_names_str = "', '".join([n.replace("'", "''") for n in matched_names])
        try:
            query_mat = f"""
            SELECT "Nombre Programa" as nombre_programa,
                   SUM("Total Matrícula 2023") as matricula_2023
            FROM siet.siet_matricula_programa_
            WHERE "Nombre Programa" IN ('{prog_names_str}')
            GROUP BY 1
            """
            df_mat = conn.execute(query_mat).fetchdf()
            df_matched = df_matched.merge(df_mat, on='nombre_programa', how='left')
        except Exception:
            df_matched['matricula_2023'] = 0

        try:
            query_cert = f"""
            SELECT "Nombre Programa" as nombre_programa,
                   SUM("Total Certificado 2023") as certificados_2023
            FROM siet.siet_estudiantes_certificados_progr
            WHERE "Nombre Programa" IN ('{prog_names_str}')
            GROUP BY 1
            """
            df_cert = conn.execute(query_cert).fetchdf()
            df_matched = df_matched.merge(df_cert, on='nombre_programa', how='left')
        except Exception:
            df_matched['certificados_2023'] = 0

        # --- PASO 8: Deduplicar y ordenar ---
        df_matched = df_matched.sort_values('score_final', ascending=False)
        agg_dict = {
            'area_desempeno': 'first',
            'tipo_certificado': 'first',
            'duracion_horas': 'first',
            'score_semantico': 'max',
            'score_estructural': 'max',
            'score_final': 'max',
        }
        if 'matricula_2023' in df_matched.columns:
            agg_dict['matricula_2023'] = 'first'
        if 'certificados_2023' in df_matched.columns:
            agg_dict['certificados_2023'] = 'first'

        df_final = df_matched.groupby('nombre_programa').agg(agg_dict).reset_index()
        df_final = df_final[df_final['score_final'] >= threshold]
        df_final = df_final.sort_values('score_final', ascending=False).head(top_k)

        return df_final

    except Exception as e:
        print(f"[ML-SIET] Error en matching: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


# ==============================================================================
# 5. SIET STATS AGREGADOS
# ==============================================================================

def get_siet_stats_for_nbc(
    nbc_nombre: str,
    conn,
    depto: str = None
) -> Dict:
    """
    Obtiene estadisticas SIET/ETDH complementarias para un NBC.
    """
    result = {
        'programas_siet_relacionados': 0,
        'matricula_siet': 0,
        'certificados_siet': 0,
        'areas_desempeno': [],
        'top_programas': [],
        'tiene_datos': False
    }

    try:
        df_matched = match_nbc_to_siet(
            nbc_nombre=nbc_nombre,
            conn=conn,
            top_k=30,
            threshold=0.25,
            depto=depto
        )

        if df_matched.empty:
            return result

        def _safe_int(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return 0
            return int(val)

        result['tiene_datos'] = True
        result['programas_siet_relacionados'] = len(df_matched)
        result['matricula_siet'] = _safe_int(df_matched['matricula_2023'].sum()) if 'matricula_2023' in df_matched.columns else 0
        result['certificados_siet'] = _safe_int(df_matched['certificados_2023'].sum()) if 'certificados_2023' in df_matched.columns else 0
        result['areas_desempeno'] = [a for a in df_matched['area_desempeno'].unique().tolist() if a is not None]

        top = df_matched.head(10)
        result['top_programas'] = [
            {
                'nombre': row['nombre_programa'],
                'area': row.get('area_desempeno', ''),
                'score': round(row.get('score_final', 0), 3),
                'score_semantico': round(row.get('score_semantico', 0), 3),
                'matricula': _safe_int(row.get('matricula_2023', 0)),
                'certificados': _safe_int(row.get('certificados_2023', 0)),
                'duracion_horas': _safe_int(row.get('duracion_horas', 0)),
            }
            for _, row in top.iterrows()
        ]

    except Exception as e:
        print(f"[ML-SNIES-ETDH] Error obteniendo stats: {e}")

    return result


# ==============================================================================
# 6. PUENTE DE COMPETENCIAS SNIES <-> SIET/ETDH VIA CUOC (Analisis completo)
# ==============================================================================

def _match_programs_to_cuoc(
    program_names: List[str],
    conn,
    nbc_nombre: str = None,
    top_k_per_program: int = 5,
    threshold: float = 0.30
) -> List[str]:
    """
    Mapea programas SIET a ocupaciones CUOC via matching semantico.

    Usa pre-filtrado ESTRUCTURAL (cadena NBC -> Area -> ocupaciones)
    para restringir el espacio de busqueda.
    """
    try:
        from services.ml.matching import semantic_search
    except ImportError:
        return []

    # Get corpus: occupations from structural chain
    corpus_texts = []
    corpus_ids = []
    try:
        if nbc_nombre:
            chain = _resolve_structural_chain(nbc_nombre, conn)
            if not chain['ocupaciones_df'].empty:
                corpus_texts = chain['ocupaciones_df']['nombre_ocupacion'].tolist()
                corpus_ids = [str(i) for i in range(len(corpus_texts))]
            else:
                nbc_nombre = None  # fallback

        if not nbc_nombre:
            df_ocup = conn.execute("""
                SELECT DISTINCT nombre_ocupacion
                FROM competencias.cuoc_conocimientos
                WHERE nombre_ocupacion IS NOT NULL
            """).fetchdf()
            if df_ocup.empty:
                return []
            corpus_texts = df_ocup['nombre_ocupacion'].tolist()
            corpus_ids = [str(i) for i in range(len(corpus_texts))]
    except Exception as e:
        print(f"[ML-Bridge] Error cargando corpus CUOC: {e}")
        return []

    if not corpus_texts:
        return []

    matched_occupations = set()

    for prog_name in program_names[:15]:
        clean_name = _strip_siet_prefix(prog_name)
        query = f"Profesional en {clean_name}. Tecnico en {clean_name}."

        results = semantic_search(
            query=query,
            corpus_texts=corpus_texts,
            corpus_ids=corpus_ids,
            top_k=top_k_per_program,
            threshold=threshold,
            cache_name="cuoc_occ_structural"
        )

        for r in results:
            matched_occupations.add(r['text'])

    return list(matched_occupations)


# ==============================================================================
# PUENTE DE COMPETENCIAS v2 — Pipeline ML Unificado
# ==============================================================================

def get_skills_bridge_analysis_v2(nbc_nombre: str, conn, depto: str = None) -> Dict:
    """
    Puente de competencias SNIES <-> SIET via embeddings (v2).
    
    Pipeline unificado (sin cadena estructural, sin hardcodeos):
      1. Perfil de competencias SNIES desde DB (_get_nbc_skills_profile)
      2. Matching ML contra programas SIET (match_nbc_to_siet_v2)
      3. Perfil de competencias SIET desde DB
      4. Interseccion Jaccard: alineacion + complementariedad
      5. Sectores CIIU via DB
      6. Validacion automatica (validate_bridge)
    
    Mismo formato de salida que get_skills_bridge_analysis() original
    para compatibilidad con la UI existente.
    """
    result = {
        'has_data': False,
        'snies_ocupaciones': [],
        'siet_ocupaciones': [],
        'shared_ocupaciones': [],
        'snies_conocimientos': [],
        'snies_destrezas': [],
        'siet_conocimientos': [],
        'siet_destrezas': [],
        'shared_conocimientos': [],
        'shared_destrezas': [],
        'alignment_score_conocimientos': 0.0,
        'alignment_score_destrezas': 0.0,
        'alignment_score_global': 0.0,
        'complementarity_siet': 0.0,
        'siet_programs_matched': 0,
        'siet_programs': [],
        'siet_areas': [],
        'ciiu_sectors': [],
        'cine_campo_amplio': '',
        'areas_cualificacion': [],
        'notas': [],
        'validation': {},
    }
    
    try:
        # 1. Perfil SNIES desde DB
        snies_skills = _get_nbc_skills_profile(nbc_nombre, conn)
        result['snies_conocimientos'] = snies_skills.get('conocimientos', [])
        result['snies_destrezas'] = snies_skills.get('destrezas', [])
        
        # Metadata del NBC
        chain = _resolve_structural_chain(nbc_nombre, conn)
        result['cine_campo_amplio'] = chain.get('cine_campo_amplio', '')
        result['areas_cualificacion'] = chain.get('areas_cualificacion', [])
        
        # 2. Matching ML contra SIET
        df_siet = match_nbc_to_siet_v2(nbc_nombre, conn, top_k=20)
        
        if df_siet.empty:
            result['notas'].append("Sin programas SIET matcheados")
            result['validation'] = validate_bridge(nbc_nombre, df_siet, conn)
            return result
        
        result['has_data'] = True
        result['siet_programs_matched'] = len(df_siet)
        result['siet_programs'] = [
            {'nombre': row['nombre_programa'],
             'area': row.get('area_desempeno', ''),
             'score': round(float(row.get('score_final', 0)), 3)}
            for _, row in df_siet.head(10).iterrows()
        ]
        if 'area_desempeno' in df_siet.columns:
            result['siet_areas'] = df_siet['area_desempeno'].dropna().unique().tolist()
        
        # 3. Perfil SIET desde ocupaciones CUOC de los programas matcheados
        siet_prog_names = df_siet['nombre_programa'].tolist()
        siet_occ_names = _match_programs_to_cuoc(
            siet_prog_names, conn, nbc_nombre=nbc_nombre,
            top_k_per_program=5, threshold=0.30
        )
        result['siet_ocupaciones'] = [
            {'nombre': n, 'via': 'siet_program_match'}
            for n in siet_occ_names[:15]
        ]
        
        siet_skills = _get_occupational_skills_profile(siet_occ_names, conn)
        result['siet_conocimientos'] = siet_skills.get('conocimientos', [])
        result['siet_destrezas'] = siet_skills.get('destrezas', [])
        
        # 4. Interseccion Jaccard
        snies_con_set = set(s['nombre'] for s in result['snies_conocimientos'])
        siet_con_set = set(s['nombre'] for s in result['siet_conocimientos'])
        snies_des_set = set(s['nombre'] for s in result['snies_destrezas'])
        siet_des_set = set(s['nombre'] for s in result['siet_destrezas'])
        
        shared_con = snies_con_set & siet_con_set
        shared_des = snies_des_set & siet_des_set
        result['shared_conocimientos'] = list(shared_con)
        result['shared_destrezas'] = list(shared_des)
        
        union_con = snies_con_set | siet_con_set
        union_des = snies_des_set | siet_des_set
        
        if union_con:
            result['alignment_score_conocimientos'] = round(len(shared_con) / len(union_con), 3)
        if union_des:
            result['alignment_score_destrezas'] = round(len(shared_des) / len(union_des), 3)
        
        total_union = len(union_con) + len(union_des)
        total_shared = len(shared_con) + len(shared_des)
        if total_union > 0:
            result['alignment_score_global'] = round(total_shared / total_union, 3)
        
        # Complementariedad: % de skills SIET que NO estan en SNIES
        siet_only_con = siet_con_set - snies_con_set
        siet_only_des = siet_des_set - snies_des_set
        total_siet = len(siet_con_set) + len(siet_des_set)
        total_unique = len(siet_only_con) + len(siet_only_des)
        if total_siet > 0:
            result['complementarity_siet'] = round(total_unique / total_siet, 3)
        
        # 5. CIIU sectores economicos
        all_occ = list(snies_con_set | siet_con_set)  # usando nombres de skills como proxy
        # Usar ocupaciones reales para CIIU
        snies_occ_names = [o['nombre'] for o in result.get('snies_ocupaciones', [])]
        siet_occ_names_all = [o['nombre'] for o in result.get('siet_ocupaciones', [])]
        all_occ_names = list(set(snies_occ_names + siet_occ_names_all))
        if all_occ_names:
            result['ciiu_sectors'] = _get_ciiu_for_occupations(all_occ_names, conn)
        
        # 6. Validacion automatica
        result['validation'] = validate_bridge(nbc_nombre, df_siet, conn)
        
        if result.get('cine_campo_amplio'):
            result['notas'].append(
                f"NBC: {nbc_nombre} -> CINE-F: {result['cine_campo_amplio']} "
                f"-> {len(result['areas_cualificacion'])} area(s) MNC/CNC"
            )
        
        v = result['validation']
        if not v['is_valid']:
            result['notas'].extend(v.get('warnings', []))
    
    except Exception as e:
        print(f"[Bridge-v2] Error: {e}")
        result['notas'].append(f"Error en analisis: {str(e)[:100]}")
    
    return result


def get_skills_bridge_analysis(
    nbc_nombre: str,
    conn,
    depto: str = None
) -> Dict:
    """
    Analisis completo del puente de competencias SNIES <-> SIET/ETDH.

    Pipeline siguiendo la metodologia:

    CAMINO 1 (SNIES -> CUOC):
      NBC -> CINE-F -> Area_Cualificacion -> Ocupaciones CUOC -> Skills
      (cadena ESTRUCTURAL + semantic re-ranking)

    CAMINO 2 (SIET -> CUOC):
      NBC -> Skills Profile -> SIET Programs (via skills query ML)
      SIET Programs -> Ocupaciones CUOC -> Skills

    INTERSECCION:
      Skills compartidas = alineacion formacion formal <-> formacion trabajo
      Skills unicas SIET = complementariedad
    """
    result = {
        'has_data': False,
        'snies_ocupaciones': [],
        'siet_ocupaciones': [],
        'shared_ocupaciones': [],
        'snies_conocimientos': [],
        'snies_destrezas': [],
        'siet_conocimientos': [],
        'siet_destrezas': [],
        'shared_conocimientos': [],
        'shared_destrezas': [],
        'alignment_score_conocimientos': 0.0,
        'alignment_score_destrezas': 0.0,
        'alignment_score_global': 0.0,
        'complementarity_siet': 0.0,
        'siet_programs_matched': 0,
        'siet_programs': [],
        'siet_areas': [],
        'ciiu_sectors': [],
        # Info de cadena estructural
        'cine_campo_amplio': '',
        'areas_cualificacion': [],
        'notas': [],
    }

    try:
        # ====================================================
        # CAMINO 1: NBC -> Ocupaciones CUOC (via cadena estructural)
        # ====================================================
        chain = _resolve_structural_chain(nbc_nombre, conn)
        result['cine_campo_amplio'] = chain.get('cine_campo_amplio', '')
        result['areas_cualificacion'] = chain.get('areas_cualificacion', [])

        # Get top occupations with ML re-ranking
        snies_matched = _match_nbc_to_cuoc_structural(nbc_nombre, conn, top_k=20, threshold=0.20)
        snies_ocupacion_names = []

        if not snies_matched.empty and 'nombre_ocupacion' in snies_matched.columns:
            snies_ocupacion_names = snies_matched['nombre_ocupacion'].tolist()
            result['snies_ocupaciones'] = [
                {'nombre': row['nombre_ocupacion'],
                 'score': round(float(row.get('similitud_ml', 0)), 3),
                 'area': row.get('area_cualificacion', '')}
                for _, row in snies_matched.head(15).iterrows()
            ]

        # Get skills profile (conocimientos + destrezas)
        snies_skills = _get_occupational_skills_profile(snies_ocupacion_names, conn)
        result['snies_conocimientos'] = snies_skills['conocimientos']
        result['snies_destrezas'] = snies_skills['destrezas']

        # ====================================================
        # CAMINO 2: NBC -> Programas SIET (via skills query) -> CUOC
        # ====================================================
        df_siet = match_nbc_to_siet(nbc_nombre, conn, top_k=20, threshold=0.35, depto=depto)

        siet_ocupacion_names = []
        if not df_siet.empty:
            result['siet_programs_matched'] = len(df_siet)
            result['siet_programs'] = [
                {'nombre': row['nombre_programa'],
                 'area': row.get('area_desempeno', ''),
                 'score': round(float(row.get('score_final', 0)), 3)}
                for _, row in df_siet.head(10).iterrows()
            ]
            if 'area_desempeno' in df_siet.columns:
                result['siet_areas'] = df_siet['area_desempeno'].dropna().unique().tolist()

            # Map SIET programs to CUOC occupations
            siet_program_names = df_siet['nombre_programa'].tolist()
            siet_ocupacion_names = _match_programs_to_cuoc(
                siet_program_names, conn, nbc_nombre=nbc_nombre,
                top_k_per_program=5, threshold=0.30
            )
            result['siet_ocupaciones'] = [
                {'nombre': n, 'via': 'siet_program_match'}
                for n in siet_ocupacion_names[:15]
            ]

        # Get skills for SIET-path occupations
        siet_skills = _get_occupational_skills_profile(siet_ocupacion_names, conn)
        result['siet_conocimientos'] = siet_skills['conocimientos']
        result['siet_destrezas'] = siet_skills['destrezas']

        # ====================================================
        # ANALISIS DE INTERSECCION Y COMPLEMENTARIEDAD
        # ====================================================
        snies_con_set = set(s['nombre'] for s in result['snies_conocimientos'])
        siet_con_set = set(s['nombre'] for s in result['siet_conocimientos'])
        snies_des_set = set(s['nombre'] for s in result['snies_destrezas'])
        siet_des_set = set(s['nombre'] for s in result['siet_destrezas'])

        shared_con = snies_con_set & siet_con_set
        shared_des = snies_des_set & siet_des_set
        result['shared_conocimientos'] = list(shared_con)
        result['shared_destrezas'] = list(shared_des)

        snies_occ_set = set(snies_ocupacion_names)
        siet_occ_set = set(siet_ocupacion_names)
        shared_occ = snies_occ_set & siet_occ_set
        result['shared_ocupaciones'] = list(shared_occ)

        # Jaccard alignment
        union_con = snies_con_set | siet_con_set
        union_des = snies_des_set | siet_des_set
        if union_con:
            result['alignment_score_conocimientos'] = round(len(shared_con) / len(union_con), 3)
        if union_des:
            result['alignment_score_destrezas'] = round(len(shared_des) / len(union_des), 3)

        total_union = len(union_con) + len(union_des)
        total_shared = len(shared_con) + len(shared_des)
        if total_union > 0:
            result['alignment_score_global'] = round(total_shared / total_union, 3)

        # Complementarity
        siet_only_con = siet_con_set - snies_con_set
        siet_only_des = siet_des_set - snies_des_set
        if siet_con_set or siet_des_set:
            total_siet = len(siet_con_set) + len(siet_des_set)
            total_unique = len(siet_only_con) + len(siet_only_des)
            result['complementarity_siet'] = round(total_unique / max(total_siet, 1), 3)

        # ====================================================
        # CIIU SECTORES ECONOMICOS (via CUOC -> Area -> CIIU)
        # ====================================================
        all_ocup_names = list(snies_occ_set | siet_occ_set)
        if all_ocup_names:
            result['ciiu_sectors'] = _get_ciiu_for_occupations(all_ocup_names, conn)

        # ====================================================
        # NOTAS
        # ====================================================
        if not snies_ocupacion_names:
            result['notas'].append("No se encontraron ocupaciones CUOC para el NBC seleccionado")
        if not siet_ocupacion_names:
            result['notas'].append("No se encontraron ocupaciones CUOC desde programas SIET")
        if not result['ciiu_sectors']:
            result['notas'].append("No se pudo determinar sectores CIIU para las ocupaciones encontradas")

        if chain.get('cine_campo_amplio'):
            result['notas'].append(
                f"Cadena: {nbc_nombre} -> CINE-F: {chain['cine_campo_amplio']} "
                f"-> {len(result['areas_cualificacion'])} area(s) MNC/CNC"
            )

        if result['snies_conocimientos'] or result['siet_conocimientos']:
            result['has_data'] = True

    except Exception as e:
        print(f"[ML-Bridge] Error en skills bridge analysis: {e}")
        import traceback
        traceback.print_exc()
        result['notas'].append(f"Error en analisis: {str(e)[:100]}")

    return result


# ==============================================================================
# 7. CIIU SECTORES ECONOMICOS (via CUOC -> Area_Cualificacion -> CIIU)
# ==============================================================================

def _get_ciiu_for_occupations(occupation_names: List[str], conn) -> List[Dict]:
    """Mapea ocupaciones CUOC a sectores CIIU via Area_Cualificacion."""
    if not occupation_names:
        return []

    try:
        names_sql = ", ".join([f"'{n.replace(chr(39), chr(39)*2)}'" for n in occupation_names])

        df = conn.execute(f"""
            SELECT DISTINCT
                mc.Seccion_CIIU as seccion,
                mc.Nombre_Seccion_CIIU as nombre
            FROM catalogo_curado.mapeo_cuoc_area_cualificacion ma
            JOIN catalogo_curado.mapeo_cuoc_ciiu mc
                ON UPPER(ma.Area_Cualificacion) = UPPER(mc.Area_Cualificacion_CUOC)
            WHERE ma.Nombre_Ocupacion IN ({names_sql})
            ORDER BY mc.Seccion_CIIU
        """).fetchdf()

        if df.empty:
            df = conn.execute(f"""
                SELECT DISTINCT
                    mc.Seccion_CIIU as seccion,
                    mc.Nombre_Seccion_CIIU as nombre
                FROM catalogo_curado.mapeo_cuoc_area_cualificacion ma
                JOIN catalogo_curado.mapeo_cuoc_ciiu mc
                    ON UPPER(ma.Area_Cualificacion) = UPPER(mc.Area_Cualificacion_CUOC)
                WHERE EXISTS (
                    SELECT 1 FROM (VALUES {', '.join([f"('{n.replace(chr(39), chr(39)*2)}')" for n in occupation_names[:10]])}) AS v(nm)
                    WHERE LOWER(ma.Nombre_Ocupacion) LIKE '%' || LOWER(SUBSTRING(v.nm, 1, 20)) || '%'
                )
                ORDER BY mc.Seccion_CIIU
            """).fetchdf()

        if not df.empty:
            return [
                {'seccion': row['seccion'], 'nombre': row['nombre']}
                for _, row in df.iterrows()
            ]
    except Exception as e:
        print(f"[CIIU] Error: {e}")

    return []


def get_ciiu_for_nbc(nbc_nombre: str, conn) -> List[Dict]:
    """
    Sectores CIIU para un NBC usando cadena estructural completa:
    NBC -> CINE-F -> Area_Cualificacion -> Ocupaciones CUOC -> CIIU
    """
    try:
        matched = _match_nbc_to_cuoc_structural(nbc_nombre, conn, top_k=15)
        if matched.empty:
            return []
        occ_names = matched['nombre_ocupacion'].tolist()
        return _get_ciiu_for_occupations(occ_names, conn)
    except Exception as e:
        print(f"[CIIU-NBC] Error: {e}")
        return []


# ==============================================================================
# 8. ESTADISTICAS UNIFICADAS SNIES + SIET
# ==============================================================================

def get_unified_education_stats(
    nbc_nombre: str,
    conn,
    depto: str = None
) -> Dict:
    """
    Estadisticas unificadas de formacion (SNIES + SIET/ETDH) para un NBC.
    """
    result = {
        'snies_graduados': 0,
        'siet_certificados': 0,
        'total_formados': 0,
        'ratio_snies_siet': 0.0,
        'siet_matricula': 0,
        'nota_cobertura': '',
    }

    try:
        nbc_esc = nbc_nombre.replace("'", "''")
        conditions = [f"UPPER(\"NBC\") = UPPER('{nbc_esc}')"]
        if depto:
            depto_esc = depto.replace("'", "''")
            conditions.append(f"UPPER(\"DEPTO_PROGRAMA\") = UPPER('{depto_esc}')")
        where = " AND ".join(conditions)

        grad_df = conn.execute(f"""
            SELECT COALESCE(SUM("GRADUADOS"), 0) as total
            FROM snies.snies_graduados WHERE {where}
        """).fetchdf()
        result['snies_graduados'] = int(grad_df['total'].iloc[0]) if not grad_df.empty else 0

        siet_stats = get_siet_stats_for_nbc(nbc_nombre, conn, depto=depto)
        result['siet_certificados'] = siet_stats.get('certificados_siet', 0)
        result['siet_matricula'] = siet_stats.get('matricula_siet', 0)

        result['total_formados'] = result['snies_graduados'] + result['siet_certificados']

        if result['snies_graduados'] > 0 and result['siet_certificados'] > 0:
            result['ratio_snies_siet'] = round(
                result['snies_graduados'] / result['siet_certificados'], 2
            )

        if result['siet_certificados'] == 0:
            result['nota_cobertura'] = (
                "No se encontraron programas ETDH/SIET relacionados. "
                "Las estadisticas reflejan solo educacion formal (SNIES)."
            )
        else:
            result['nota_cobertura'] = (
                f"Incluye {result['snies_graduados']:,} graduados SNIES + "
                f"{result['siet_certificados']:,} certificados SIET/ETDH."
            )
    except Exception as e:
        print(f"[Unified-Stats] Error: {e}")
        result['nota_cobertura'] = "Error calculando estadisticas unificadas"

    return result


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == "__main__":
    import duckdb

    DB_PATH = Path(__file__).parent.parent / "data" / "repositorio.duckdb"
    conn = duckdb.connect(str(DB_PATH), read_only=True)

    test_nbcs = [
        "Ingenieria de sistemas, telematica y afines",
        "Administracion",
        "Medicina",
        "Derecho y afines",
        "Educacion",
    ]

    for nbc in test_nbcs:
        print(f"\n{'=' * 70}")
        print(f"TEST: {nbc}")
        print(f"{'=' * 70}")

        # Test structural chain
        chain = _resolve_structural_chain(nbc, conn)
        print(f"  CINE: {chain['cine_campo_amplio']}")
        print(f"  Areas MNC: {chain['areas_cualificacion']}")
        n_occ = len(chain['ocupaciones_df'])
        print(f"  Ocupaciones CUOC: {n_occ}")
        print(f"  Areas SIET: {chain['areas_desempeno_siet']}")

        if not chain['ocupaciones_df'].empty:
            occ_names = chain['ocupaciones_df']['nombre_ocupacion'].tolist()
            profile = _get_occupational_skills_profile(occ_names[:10], conn)
            print(f"  Top conocimientos: {profile['top_conocimientos_text'][:5]}")
            print(f"  Top destrezas: {profile['top_destrezas_text'][:5]}")

            skills_query = _build_skills_enriched_query(nbc, profile)
            print(f"  Skills query: {skills_query[:120]}...")

        # Test SIET matching
        stats = get_siet_stats_for_nbc(nbc, conn)
        print(f"  SIET programas: {stats['programas_siet_relacionados']}")
        print(f"  SIET matricula: {stats['matricula_siet']:,}")
        if stats['top_programas']:
            print(f"  Top SIET:")
            for p in stats['top_programas'][:3]:
                print(f"    [{p['score']:.3f}] {p['nombre']}")

    conn.close()
