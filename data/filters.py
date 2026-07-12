"""
SQL filter builders for SNIES database queries — 100% dinámico
==============================================================

Enfoque dinámico SIN mapeos hardcodeados:
- build_where_clause: Para snies_programas → match directo (los filtros vienen de programas)
- build_where_clause_matriculados: Para snies_matriculados/graduados → usa subquery puente
  vía CÓDIGO_SNIES_DEL_PROGRAMA ↔ COD_SNIES_PROGRAMA para resolver diferencias
  de nomenclatura entre tablas (MODALIDAD↔METODOLOGIA, SECTOR↔SECTOR_IES, etc.)
  sin necesidad de mapeos estáticos.
- resolver_nbcs_desde_filtros: Resuelve NBCs cuando solo se seleccionan Area o Campo Amplio
"""

import functools


@functools.lru_cache(maxsize=64)
def _resolver_nbcs_cached(areas_tuple, campos_tuple, estados_tuple):
    """Cache interno — las tuplas son hashables para lru_cache."""
    from config.database import get_conn
    conn = get_conn()
    try:
        conditions = []
        if areas_tuple:
            escaped = "', '".join([v.replace("'", "''").upper() for v in areas_tuple])
            conditions.append(f"""UPPER("ÁREA_DE_CONOCIMIENTO") IN ('{escaped}')""")
        if campos_tuple:
            escaped = "', '".join([v.replace("'", "''").upper() for v in campos_tuple])
            conditions.append(f"""UPPER("CINE_F_2013_AC_CAMPO_AMPLIO") IN ('{escaped}')""")
        if estados_tuple:
            escaped = "', '".join([v.replace("'", "''").upper() for v in estados_tuple])
            conditions.append(f"""UPPER("ESTADO_PROGRAMA") IN ('{escaped}')""")
        if not conditions:
            return ()
        where = " AND ".join(conditions)
        sql = f"""
            SELECT DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" as nbc
            FROM snies.snies_programas
            WHERE {where}
              AND "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL
            ORDER BY nbc
        """
        df = conn.execute(sql).fetchdf()
        return tuple(df['nbc'].tolist()) if not df.empty else ()
    except Exception:
        return ()
    finally:
        conn.close()


def resolver_nbcs_desde_filtros(filtros: dict) -> list:
    """Resuelve NBCs a partir de los filtros seleccionados.
    
    Relación MANY-TO-MANY (ver RELACION.MD):
      Area de Conocimiento ←→ NBC ←→ Campo Amplio CINE-F
    
    Si ya hay NBCs explícitos → los retorna tal cual.
    Si solo hay Area y/o Campo Amplio → consulta snies_programas para
    obtener los NBCs que corresponden a esa combinación de filtros.
    
    Args:
        filtros: Dict con claves 'nbcs', 'areas', 'campos_amplios', 'estados'
    
    Returns:
        Lista de NBCs resueltos (puede estar vacía si no hay filtros académicos)
    """
    # Si ya hay NBCs explícitos, retornarlos directamente
    nbcs = filtros.get('nbcs', [])
    if nbcs:
        return list(nbcs)
    
    # Resolver desde Area y/o Campo Amplio
    areas = filtros.get('areas', [])
    campos = filtros.get('campos_amplios', [])
    estados = filtros.get('estados', [])
    busqueda = filtros.get('busqueda_nombre', '').strip()
    
    # Si hay busqueda por nombre, consultar NBCs desde programas que matchean el LIKE
    if not areas and not campos and busqueda:
        from config.database import get_conn
        conn = get_conn()
        try:
            texto = busqueda.replace("'", "''")
            df = conn.execute(f"""
                SELECT DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" as nbc
                FROM snies.snies_programas
                WHERE UPPER("NOMBRE_DEL_PROGRAMA") LIKE '%' || UPPER('{texto}') || '%'
                  AND "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL
                ORDER BY nbc
                LIMIT 20
            """).fetchdf()
            return df['nbc'].tolist() if not df.empty else []
        except Exception:
            return []
        finally:
            conn.close()
    
    if not areas and not campos:
        return []
    
    result = _resolver_nbcs_cached(
        tuple(areas) if areas else (),
        tuple(campos) if campos else (),
        tuple(estados) if estados else ()
    )
    return list(result)


def _esc(val: str) -> str:
    """Escapa comillas simples para SQL."""
    return val.replace("'", "''")


def _in_clause(prefix: str, col: str, values: list, *, upper: bool = False) -> str:
    """Genera condicion IN (...) con escape. Si upper=True normaliza a UPPER."""
    escaped = [_esc(v).upper() if upper else _esc(v) for v in values]
    vals = "', '".join(escaped)
    expr = f'UPPER({prefix}"{col}")' if upper else f'{prefix}"{col}"'
    return f"{expr} IN ('{vals}')"


def build_nbc_match_condition(nbc: str, col: str = '"NBC"') -> str:
    """Tokeniza el nombre del NBC y construye LIKE '%palabra%' para cada token.
    Mas robusto que un LIKE unico: 'Ing Sistemas' encuentra 'Ingenieria de Sistemas'.
    """
    if not nbc:
        return "1=1"
    tokens = [t.strip() for t in nbc.split() if len(t.strip()) >= 3]
    if not tokens:
        return f"UPPER(strip_accents({col})) LIKE '%' || UPPER(strip_accents('{_esc(nbc)}')) || '%'"
    conditions = []
    for token in tokens:
        t = _esc(token)
        conditions.append(f"UPPER(strip_accents({col})) LIKE '%' || UPPER(strip_accents('{t}')) || '%'")
    return " AND ".join(conditions)


def build_where_clause(filtros: dict, tabla_alias: str = "") -> str:
    """
    Construye cláusula WHERE para snies_programas.
    Match directo — los valores del sidebar provienen de esta misma tabla.

    Args:
        filtros: Dict con claves como 'nbcs', 'deptos', 'modalidades', etc.
        tabla_alias: Prefijo de tabla (ej: "p" para snies_programas)

    Returns:
        String con la cláusula WHERE (sin el WHERE inicial)
    """
    prefix = f"{tabla_alias}." if tabla_alias and not tabla_alias.endswith('.') else tabla_alias
    conditions = []

    # Mapeo directo: clave de filtro → nombre de columna en snies_programas
    column_map = {
        'campos_amplios': 'CINE_F_2013_AC_CAMPO_AMPLIO',
        'areas':          'ÁREA_DE_CONOCIMIENTO',
        'nbcs':           'NÚCLEO_BÁSICO_DEL_CONOCIMIENTO',
        'deptos':         'DEPARTAMENTO_OFERTA_PROGRAMA',
        'municipios':     'MUNICIPIO_OFERTA_PROGRAMA',
        'modalidades':    'MODALIDAD',
        'sectores':       'SECTOR',
        'niveles':        'NIVEL_DE_FORMACIÓN',
        'caracteres':     'CARÁCTER_ACADÉMICO',
        'estados':        'ESTADO_PROGRAMA',
    }

    for key, col in column_map.items():
        values = filtros.get(key)
        if values and len(values) > 0:
            conditions.append(_in_clause(prefix, col, values))

    # Búsqueda por nombre de programa (LIKE case-insensitive)
    if filtros.get('busqueda_nombre'):
        texto = filtros['busqueda_nombre'].strip()
        if texto:
            col_nombre = filtros.get('_columna_nombre', 'NOMBRE_DEL_PROGRAMA')
            conditions.append(
                f'UPPER({prefix}"{col_nombre}") LIKE UPPER(\'%{_esc(texto)}%\')'
            )

    # Código SNIES de programas específicos
    if filtros.get('cod_snies_programas'):
        codes = filtros['cod_snies_programas']
        escaped_codes = "', '".join([_esc(c) for c in codes])
        conditions.append(
            f'CAST({prefix}"CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) IN (\'{escaped_codes}\')'
        )

    return " AND ".join(conditions) if conditions else "1=1"


def build_nbc_condition(nbc_or_list, prefix: str = "") -> str:
    """Construye condición WHERE para NBC (acepta string o lista)."""
    if isinstance(nbc_or_list, list):
        if len(nbc_or_list) == 0:
            return "1=1"
        escaped = [_esc(n) for n in nbc_or_list]
        return f'{prefix}"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IN (\'{"\', \'".join(escaped)}\')'
    else:
        return f'{prefix}"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" = \'{_esc(nbc_or_list)}\''


# =====================================================================
# MAPEO SNIES Nivel de Formación → Niveles MNC (Marco Nacional Cualificaciones)
# Fuente: MEN Colombia - Decreto 1075/2015, Ley 1955/2019
# Keys: valores EXACTOS de la columna NIVEL_DE_FORMACIÓN en snies.snies_programas (ALL CAPS)
# =====================================================================
SNIES_NIVEL_A_MNC = {
    # --- Keys exactos de la BD (ALL CAPS) ---
    'FORMACIÓN TÉCNICA PROFESIONAL':           [4, 5],
    'TECNOLÓGICO':                             [5],
    'ESPECIALIZACIÓN TECNOLÓGICA':             [5, 6],
    'ESPECIALIZACIÓN TÉCNICO PROFESIONAL':     [5, 6],
    'UNIVERSITARIO':                           [6],
    'ESPECIALIZACIÓN UNIVERSITARIA':           [7],
    'ESPECIALIZACIÓN MÉDICO QUIRÚRGICA':       [7],
    'MAESTRÍA':                                [7],
    'DOCTORADO':                               [8],
    # --- Variantes legacy (por compatibilidad) ---
    'Técnica Profesional':                     [4, 5],
    'Tecnológica':                             [5],
    'Tecnologica':                             [5],
    'Universitaria':                           [6],
    'Especialización Tecnológica':             [5, 6],
    'Especialización':                         [7],
    'Especializacion Tecnologica':             [5, 6],
    'Especializacion':                         [7],
    'Maestría':                                [7],
    'Maestria':                                [7],
    'Doctorado':                               [8],
    'Tecnica Profesional':                     [4, 5],
}


def mapear_niveles_snies_a_mnc(sel_niveles):
    """
    Convierte una lista de niveles de formación SNIES a niveles MNC.

    Args:
        sel_niveles: lista de strings (e.g. ['TECNOLÓGICO', 'FORMACIÓN TÉCNICA PROFESIONAL'])

    Returns:
        set de ints con niveles MNC correspondientes, o None si no hay filtro.
    """
    if not sel_niveles:
        return None

    mnc_levels = set()
    for nivel in sel_niveles:
        nivel_strip = nivel.strip()
        # Match exacto (cubre keys ALL CAPS y legacy)
        if nivel_strip in SNIES_NIVEL_A_MNC:
            mnc_levels.update(SNIES_NIVEL_A_MNC[nivel_strip])
            continue
        
        # Fallback: case-insensitive
        nivel_upper = nivel_strip.upper()
        for key, vals in SNIES_NIVEL_A_MNC.items():
            if key.upper() == nivel_upper:
                mnc_levels.update(vals)
                break
        else:
            # Fallback 2: substring match (e.g. "TECNOLÓGICO" in "ESPECIALIZACIÓN TECNOLÓGICA")
            for key, vals in SNIES_NIVEL_A_MNC.items():
                k_up = key.upper()
                if nivel_upper in k_up or k_up in nivel_upper:
                    mnc_levels.update(vals)
                    break

    return mnc_levels if mnc_levels else None


def build_where_clause_matriculados(depto=None, filtros=None, prefix: str = "") -> list:
    """
    Construye condiciones WHERE para snies_matriculados / snies_graduados.

    Estrategia 100% dinámica (sin mapeos hardcodeados):

    1. Columnas con match directo (existen en matriculados):
       NBC, DEPTO_PROGRAMA, MPIO_PROGRAMA, NOMBRE_PROGRAMA

    2. Columnas con diferente nomenclatura (MODALIDAD↔METODOLOGIA, etc.):
       Se resuelven via subquery puente por COD_SNIES_PROGRAMA.
       Esto funciona con cualquier valor nuevo que se agregue a la DB.

    Args:
        depto: Departamento escalar (legacy, se ignora si filtros['deptos'] existe)
        filtros: Dict con filtros del panel
        prefix: Prefijo de tabla (ej: "m.")

    Returns:
        Lista de condiciones SQL (sin AND inicial)
    """
    condiciones = []
    p = f'{prefix}.' if prefix and not prefix.endswith('.') else prefix

    if not filtros:
        filtros = {}

    # ==================================================================
    # 1. MATCH DIRECTO — columnas que existen en matriculados/graduados
    # ==================================================================

    # NBC (UPPER para normalizar case)
    if filtros.get('nbcs'):
        condiciones.append(_in_clause(p, 'NBC', filtros['nbcs'], upper=True))

    # Departamento (lista o escalar legacy)
    if filtros.get('deptos'):
        condiciones.append(_in_clause(p, 'DEPTO_PROGRAMA', filtros['deptos'], upper=True))
    elif depto:
        condiciones.append(f'UPPER({p}"DEPTO_PROGRAMA") = UPPER(\'{_esc(depto)}\')')

    # Municipio
    if filtros.get('municipios'):
        condiciones.append(_in_clause(p, 'MPIO_PROGRAMA', filtros['municipios']))

    # NOTA: 'areas' (ÁREA_DE_CONOCIMIENTO) se resuelve via PUENTE, no directo.
    # AREA_CONOCIMIENTO en matriculados es copia desnormalizada que difiere de
    # ÁREA_DE_CONOCIMIENTO en programas para ~7% de registros → datos incorrectos.

    # Búsqueda por nombre
    if filtros.get('busqueda_nombre'):
        texto = filtros['busqueda_nombre'].strip()
        if texto:
            condiciones.append(
                f'UPPER({p}"NOMBRE_PROGRAMA") LIKE UPPER(\'%{_esc(texto)}%\')'
            )

    # Código SNIES directo (normalizar .0 para 2023-2024 data)
    if filtros.get('cod_snies_programas'):
        escaped_codes = "', '".join([_esc(c) for c in filtros['cod_snies_programas']])
        condiciones.append(
            f'REGEXP_REPLACE(CAST({p}"COD_SNIES_PROGRAMA" AS VARCHAR), \'\\.0$\', \'\') IN (\'{escaped_codes}\')'
        )

    # ==================================================================
    # 2. SUBQUERY PUENTE — para filtros cuya columna difiere entre tablas
    #    Resuelve dinámicamente via: COD_SNIES_PROGRAMA IN
    #      (SELECT CÓDIGO_SNIES_DEL_PROGRAMA FROM snies_programas WHERE …)
    #    No requiere mapeos hardcodeados.
    # ==================================================================

    bridge_conditions = []

    # Áreas de conocimiento → ÁREA_DE_CONOCIMIENTO en programas (autoritativa)
    if filtros.get('areas'):
        bridge_conditions.append(_in_clause('', 'ÁREA_DE_CONOCIMIENTO', filtros['areas'], upper=True))

    # Campos amplios → no existe en matriculados
    if filtros.get('campos_amplios'):
        bridge_conditions.append(_in_clause('', 'CINE_F_2013_AC_CAMPO_AMPLIO', filtros['campos_amplios'], upper=True))

    # Modalidades → MODALIDAD en programas ≠ METODOLOGIA en matriculados
    if filtros.get('modalidades'):
        bridge_conditions.append(_in_clause('', 'MODALIDAD', filtros['modalidades'], upper=True))

    # Sectores → SECTOR en programas ≠ SECTOR_IES en matriculados
    if filtros.get('sectores'):
        bridge_conditions.append(_in_clause('', 'SECTOR', filtros['sectores'], upper=True))

    # Niveles → NIVEL_DE_FORMACIÓN en programas ≠ NIVEL_FORMACION en matriculados
    if filtros.get('niveles'):
        bridge_conditions.append(_in_clause('', 'NIVEL_DE_FORMACIÓN', filtros['niveles'], upper=True))

    # Caracteres → CARÁCTER_ACADÉMICO en programas ≠ CARACTER_IES en matriculados
    if filtros.get('caracteres'):
        bridge_conditions.append(_in_clause('', 'CARÁCTER_ACADÉMICO', filtros['caracteres'], upper=True))

    # Estados → ESTADO_PROGRAMA solo existe en programas
    if filtros.get('estados'):
        bridge_conditions.append(_in_clause('', 'ESTADO_PROGRAMA', filtros['estados'], upper=True))

    # Si hay condiciones que requieren el puente, generar UNA sola subquery
    # CORRECCIÓN CRÍTICA: Normalizar COD_SNIES_PROGRAMA quitando sufijo '.0'
    # En 2023-2024, COD_SNIES_PROGRAMA se almacena como "61.0" (float-as-string)
    # mientras CÓDIGO_SNIES_DEL_PROGRAMA (BIGINT) se castea a "61".
    # Sin normalizar → 0% match para 2023-2024 (datos invisibles).
    if bridge_conditions:
        bridge_where = " AND ".join(bridge_conditions)
        condiciones.append(
            f'REGEXP_REPLACE(CAST({p}"COD_SNIES_PROGRAMA" AS VARCHAR), \'\\.0$\', \'\') IN ('
            f'SELECT CAST("CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) '
            f'FROM snies.snies_programas WHERE {bridge_where})'
        )

    return condiciones
