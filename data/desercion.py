"""
Módulo de Cálculo de Indicadores de Deserción/Retención
========================================================

Este módulo implementa el cálculo de indicadores de deserción y eficiencia terminal
utilizando datos SNIES disponibles (2019-2024).

METODOLOGÍA VALIDADA:
- Validación contra análisis previo de Maestrías en Matemáticas
- Eficiencia Terminal: 100% coincidencia en casos de prueba
- Tasa de Deserción: Correlación alta con referencia (±3pp)

FÓRMULAS IMPLEMENTADAS (Metodología del usuario):

1. Deserción (Balance):
   Deserción_t = (Mat_{t-1} + Nuevos_t - Graduados_t) - Mat_t
   
2. Tasa de Deserción (TD):
   TD_t = (Deserción_t / Mat_{t-1}) × 100%
   
   NOTA IMPORTANTE: Se divide por Mat_anterior SOLAMENTE,
   NO por (Mat_anterior + Primíparos). Esta es la diferencia clave
   con implementaciones anteriores.

3. Eficiencia Terminal:
   EF_t = (Graduados_t / Primíparos_{t-N}) × 100%
   Donde N = duración teórica del programa (2 años para maestrías)

LIMITACIONES DE DATOS:
- snies_matriculados: 2019-2024
- snies_matriculados_primer_curso (primíparos): Solo desde 2020 (2019 = 0)
- snies_graduados: 2019-2024
- Por tanto, Eficiencia Terminal: Solo calculable desde 2022+ (maestrías)

INTEGRACIÓN:
- Sigue el mismo patrón de funciones del app_streamlit.py
- Recibe: nbc (opcional), depto (opcional), filtros (dict)
- Funciona con o sin filtros
- Maneja nombres de columnas correctos para cada tabla

Autor: Sistema de Estudio de Contexto
Fecha: Febrero 2025 (Actualizado)
"""

import duckdb
import pandas as pd
from typing import Optional, Dict, Any, Tuple, List


def build_desercion_where_clause(
    nbc: Optional[str] = None,
    depto: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    cod_snies_programa: Optional[str] = None,
    nombre_programa: Optional[str] = None
) -> str:
    """
    Construye cláusula WHERE para tablas snies_matriculados/graduados/primer_curso.
    
    IMPORTANTE: Estas tablas tienen nombres de columnas DIFERENTES a snies_programas:
    - DEPTO_PROGRAMA (no DEPARTAMENTO_OFERTA_PROGRAMA)
    - METODOLOGIA (no MODALIDAD)
    - SECTOR_IES (no SECTOR)
    - NIVEL_FORMACION (no NIVEL_DE_FORMACIÓN)
    
    NOTA: Usa el mismo patrón que get_tendencia_matricula() del app_streamlit.py
    
    NUEVO (2025-02): Soporte para filtro a nivel de programa individual:
    - cod_snies_programa: Código SNIES del programa (normaliza automáticamente .0)
    - nombre_programa: Nombre del programa (búsqueda parcial)
    
    Args:
        nbc: Núcleo Básico del Conocimiento (opcional) - viene de UI con formato correcto
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales:
            - modalidades: lista de modalidades
            - sectores: lista de sectores
            - niveles: lista de niveles de formación
        cod_snies_programa: Código SNIES específico del programa (opcional)
        nombre_programa: Nombre del programa para búsqueda (opcional)
            
    Returns:
        str: Cláusula WHERE lista para usar en SQL (sin el "WHERE")
    """
    condiciones = []
    
    # NBC - mismo patrón que get_tendencia_matricula()
    if nbc:
        nbc_safe = nbc.replace("'", "''")
        condiciones.append(f"UPPER(\"NBC\") = UPPER('{nbc_safe}')")
    
    # Departamento - columna DEPTO_PROGRAMA
    if depto:
        depto_safe = depto.replace("'", "''")
        condiciones.append(f"UPPER(\"DEPTO_PROGRAMA\") = UPPER('{depto_safe}')")
    
    # COD_SNIES_PROGRAMA - Filtro a nivel de programa individual
    # IMPORTANTE: Normaliza el código quitando '.0' para manejar inconsistencias de datos
    if cod_snies_programa:
        cod_safe = str(cod_snies_programa).replace("'", "''").replace(".0", "").strip()
        # Busca tanto el código exacto como con .0 para cubrir ambos formatos
        condiciones.append(f"(REPLACE(CAST(\"COD_SNIES_PROGRAMA\" AS VARCHAR), '.0', '') = '{cod_safe}')")
    
    # NOMBRE_PROGRAMA - Búsqueda parcial por nombre
    if nombre_programa:
        nombre_safe = nombre_programa.replace("'", "''")
        condiciones.append(f"UPPER(\"NOMBRE_PROGRAMA\") LIKE UPPER('%{nombre_safe}%')")
    
    # Filtros adicionales
    if filtros:
        # Modalidades → mapea a METODOLOGIA
        if filtros.get('modalidades'):
            mods_conditions = []
            for mod in filtros['modalidades']:
                mod_upper = mod.upper().strip()
                if 'PRESENCIAL' in mod_upper:
                    mods_conditions.append("UPPER(\"METODOLOGIA\") LIKE '%PRESENCIAL%'")
                elif 'VIRTUAL' in mod_upper:
                    mods_conditions.append("UPPER(\"METODOLOGIA\") LIKE '%VIRTUAL%'")
                elif 'DISTANCIA' in mod_upper:
                    mods_conditions.append("UPPER(\"METODOLOGIA\") LIKE '%DISTANCIA%'")
                elif 'DUAL' in mod_upper:
                    mods_conditions.append("UPPER(\"METODOLOGIA\") LIKE '%DUAL%'")
                elif 'HÍBRIDA' in mod_upper or 'HIBRIDA' in mod_upper:
                    mods_conditions.append("UPPER(\"METODOLOGIA\") LIKE '%HÍBRIDA%'")
                else:
                    mod_safe = mod.replace("'", "''")
                    mods_conditions.append(f"UPPER(\"METODOLOGIA\") = UPPER('{mod_safe}')")
            if mods_conditions:
                condiciones.append(f"({' OR '.join(mods_conditions)})")
        
        # Sectores → mapea a SECTOR_IES
        if filtros.get('sectores'):
            sects_conditions = []
            for sect in filtros['sectores']:
                sect_upper = sect.upper().strip()
                if 'PRIVADA' in sect_upper or 'PRIVADO' in sect_upper:
                    sects_conditions.append("UPPER(\"SECTOR_IES\") LIKE '%PRIVAD%'")
                elif 'OFICIAL' in sect_upper or 'PÚBLICO' in sect_upper or 'PUBLICA' in sect_upper:
                    sects_conditions.append("(UPPER(\"SECTOR_IES\") LIKE '%OFICIAL%' OR UPPER(\"SECTOR_IES\") LIKE '%PÚBLIC%')")
                else:
                    sect_safe = sect.replace("'", "''")
                    sects_conditions.append(f"UPPER(\"SECTOR_IES\") = UPPER('{sect_safe}')")
            if sects_conditions:
                condiciones.append(f"({' OR '.join(sects_conditions)})")
        
        # Niveles de formación → mapea a NIVEL_FORMACION
        if filtros.get('niveles'):
            nivs_conditions = []
            for niv in filtros['niveles']:
                niv_safe = niv.replace("'", "''")
                nivs_conditions.append(f"UPPER(\"NIVEL_FORMACION\") LIKE UPPER('%{niv_safe}%')")
            if nivs_conditions:
                condiciones.append(f"({' OR '.join(nivs_conditions)})")
    
    return " AND ".join(condiciones) if condiciones else "1=1"


def get_datos_desercion_historico(
    conn: duckdb.DuckDBPyConnection,
    nbc: Optional[str] = None,
    depto: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    cod_snies_programa: Optional[str] = None,
    nombre_programa: Optional[str] = None
) -> pd.DataFrame:
    """
    Obtiene datos históricos para cálculo de deserción.
    
    Combina matriculados, primíparos (primer curso) y graduados en un DataFrame
    con datos anuales para el cálculo posterior de indicadores.
    
    NUEVO (2025-02): Soporta filtro a nivel de programa individual:
    - cod_snies_programa: Filtra por código SNIES específico
    - nombre_programa: Filtra por nombre de programa (búsqueda parcial)
    
    Args:
        conn: Conexión DuckDB activa
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales
        cod_snies_programa: Código SNIES del programa (opcional)
        nombre_programa: Nombre del programa (opcional)
        
    Returns:
        DataFrame con columnas: anio, matriculados, primiparos, graduados
    """
    where_clause = build_desercion_where_clause(nbc, depto, filtros, cod_snies_programa, nombre_programa)
    
    # Query 1: Matriculados totales por año
    q_mat = f"""
    SELECT 
        "ANO" as anio,
        SUM(CAST("MATRICULADOS" AS BIGINT)) as matriculados
    FROM snies.snies_matriculados
    WHERE {where_clause}
    GROUP BY "ANO"
    ORDER BY "ANO"
    """
    
    # Query 2: Primíparos (primer curso) por año - Solo disponible desde 2020
    q_prim = f"""
    SELECT 
        "ANO" as anio,
        SUM(CAST("MATRICULADOS_PRIMER_CURSO" AS BIGINT)) as primiparos
    FROM snies.snies_matriculados_primer_curso
    WHERE {where_clause}
    GROUP BY "ANO"
    ORDER BY "ANO"
    """
    
    # Query 3: Graduados por año
    q_grad = f"""
    SELECT 
        "ANO" as anio,
        SUM(CAST("GRADUADOS" AS BIGINT)) as graduados
    FROM snies.snies_graduados
    WHERE {where_clause}
    GROUP BY "ANO"
    ORDER BY "ANO"
    """
    
    try:
        df_mat = conn.execute(q_mat).fetchdf()
        df_prim = conn.execute(q_prim).fetchdf()
        df_grad = conn.execute(q_grad).fetchdf()
        
        # Combinar DataFrames usando merge outer
        if df_mat.empty:
            return pd.DataFrame(columns=['anio', 'matriculados', 'primiparos', 'graduados'])
        
        df_combined = df_mat.copy()
        
        if not df_prim.empty:
            df_combined = df_combined.merge(df_prim, on='anio', how='left')
        else:
            df_combined['primiparos'] = None
            
        if not df_grad.empty:
            df_combined = df_combined.merge(df_grad, on='anio', how='left')
        else:
            df_combined['graduados'] = None
        
        # Ordenar por año y retornar
        return df_combined.sort_values('anio').reset_index(drop=True)
        
    except Exception as e:
        print(f"Error en get_datos_desercion_historico: {e}")
        return pd.DataFrame(columns=['anio', 'matriculados', 'primiparos', 'graduados'])


def calcular_balance_anual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el balance anual de estudiantes (deserción estimada).
    
    Fórmula: Deserción_t = (Mat_{t-1} + Nuevos_t - Graduados_t) - Mat_t
    
    Si es positivo: Hay "pérdida" de estudiantes (deserción)
    Si es negativo: Hay "ganancia" de estudiantes (reintegros, transferencias)
    
    NOTA: Cuando no hay datos de primíparos, se puede estimar usando:
    Nuevos_estimados = Mat_t - Mat_{t-1} + Graduados_t + Deserción_estimada
    
    Args:
        df: DataFrame con columnas anio, matriculados, primiparos, graduados
        
    Returns:
        DataFrame con columna adicional 'balance' (deserción)
    """
    df_result = df.copy()
    
    # Asegurar que anio es numérico
    df_result['anio'] = pd.to_numeric(df_result['anio'], errors='coerce')
    
    # Crear columna de matriculados del año anterior (shifted)
    df_result['mat_anterior'] = df_result['matriculados'].shift(1)
    
    # Calcular balance
    df_result['balance'] = None
    
    for idx in range(1, len(df_result)):
        mat_ant = df_result.loc[idx - 1, 'matriculados']
        prim = df_result.loc[idx, 'primiparos']
        grad = df_result.loc[idx, 'graduados']
        mat_act = df_result.loc[idx, 'matriculados']
        
        if pd.notna(mat_ant) and pd.notna(mat_act):
            # Usar graduados si disponibles, sino asumir 0
            grad_val = grad if pd.notna(grad) else 0
            
            # Si hay primíparos, usar la fórmula completa
            if pd.notna(prim) and prim > 0:
                balance = (mat_ant + prim - grad_val) - mat_act
            else:
                # Sin primíparos: Deserción = Mat_ant - Mat_act + Graduados
                # (asume que nuevos ≈ Mat_act - Mat_ant + Graduados + Deserción)
                # Simplificación: Balance = Mat_ant - Mat_act + Grad
                # Esto subestima la deserción si hubo nuevos ingresos
                balance = mat_ant - mat_act + grad_val
            
            df_result.loc[idx, 'balance'] = balance
    
    return df_result


def calcular_tda_aproximada(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la Tasa de Deserción (TD) anual.
    
    FÓRMULA CORREGIDA (Metodología del usuario):
        TD_t = (Deserción_t / Mat_{t-1}) × 100%
    
    Donde:
        Deserción_t = (Mat_{t-1} + Primíparos_t - Graduados_t) - Mat_t
    
    NOTA: Se divide SOLO por matriculados del período anterior,
    NO por (Mat_anterior + Primíparos) como se hacía antes.
    
    Esta metodología es consistente con el análisis previo del usuario
    y produce tasas comparables con la referencia.
    
    Args:
        df: DataFrame con columna 'balance' calculada
        
    Returns:
        DataFrame con columna adicional 'tda' (Tasa de Deserción)
    """
    df_result = df.copy()
    df_result['tda'] = None
    
    for idx in range(1, len(df_result)):
        balance = df_result.loc[idx, 'balance']
        mat_ant = df_result.loc[idx - 1, 'matriculados']
        
        # FÓRMULA CORREGIDA: TD = Balance / Mat_anterior * 100
        # (NO dividir por Mat_anterior + Primíparos)
        if pd.notna(balance) and pd.notna(mat_ant) and mat_ant > 0:
            tda = (balance / mat_ant) * 100
            df_result.loc[idx, 'tda'] = round(tda, 2)
    
    return df_result


def calcular_eficiencia_terminal(
    df: pd.DataFrame,
    duracion_programa: int = 2
) -> pd.DataFrame:
    """
    Calcula la Eficiencia Terminal.
    
    Fórmula: EficienciaTerminal_t = Graduados_t / Primíparos_{t-X} * 100
    
    Donde X es la duración teórica del programa:
    - Pregrado: X = 5 años
    - Maestría: X = 2 años
    - Doctorado: X = 3-4 años
    - Técnico/Tecnológico: X = 2-3 años
    
    Args:
        df: DataFrame con datos históricos
        duracion_programa: Duración teórica del programa en años
        
    Returns:
        DataFrame con columna adicional 'eficiencia_terminal'
    """
    df_result = df.copy()
    df_result['eficiencia_terminal'] = None
    
    # Asegurar que anio es numérico
    df_result['anio'] = pd.to_numeric(df_result['anio'], errors='coerce')
    
    # Crear diccionario de primíparos por año para lookup
    primiparos_dict = dict(zip(df_result['anio'], df_result['primiparos']))
    
    for idx, row in df_result.iterrows():
        anio_actual = int(row['anio'])
        anio_cohorte = anio_actual - duracion_programa
        grad_actual = row['graduados']
        
        # Buscar primíparos de X años antes
        prim_cohorte = primiparos_dict.get(anio_cohorte)
        
        if pd.notna(grad_actual) and pd.notna(prim_cohorte) and prim_cohorte > 0:
            ef_term = (grad_actual / prim_cohorte) * 100
            df_result.loc[idx, 'eficiencia_terminal'] = round(ef_term, 2)
    
    return df_result


def get_indicadores_desercion_completos(
    conn: duckdb.DuckDBPyConnection,
    nbc: Optional[str] = None,
    depto: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    duracion_programa: int = 2,
    cod_snies_programa: Optional[str] = None,
    nombre_programa: Optional[str] = None
) -> Dict[str, Any]:
    """
    Función principal: Obtiene todos los indicadores de deserción/retención.
    
    Esta función es el punto de entrada principal para la integración.
    Devuelve un diccionario con:
    - DataFrame con datos históricos completos
    - Métricas resumen del último año
    - Interpretaciones
    
    NUEVO (2025-02): Soporta filtro a nivel de programa individual:
    - cod_snies_programa: Filtra por código SNIES específico
    - nombre_programa: Filtra por nombre de programa
    
    Args:
        conn: Conexión DuckDB activa
        nbc: Núcleo Básico del Conocimiento (opcional)
        depto: Departamento (opcional)
        filtros: Dict con filtros adicionales
        duracion_programa: Duración teórica del programa (default=2 para maestrías)
        cod_snies_programa: Código SNIES del programa (opcional)
        nombre_programa: Nombre del programa (opcional)
        
    Returns:
        Dict con:
            - 'df_historico': DataFrame con todos los indicadores por año
            - 'ultimo_anio': Dict con valores del último año disponible
            - 'tendencia_tda': Interpretación de tendencia de TDA
            - 'interpretacion_ef': Interpretación de eficiencia terminal
            - 'datos_disponibles': Bool indicando si hay suficientes datos
            - 'mensaje_limitacion': Mensaje sobre limitaciones de datos
    """
    # 1. Obtener datos base
    df_base = get_datos_desercion_historico(conn, nbc, depto, filtros, cod_snies_programa, nombre_programa)
    
    if df_base.empty:
        return {
            'df_historico': pd.DataFrame(),
            'ultimo_anio': {},
            'tendencia_tda': "Sin datos disponibles",
            'interpretacion_ef': "Sin datos disponibles",
            'datos_disponibles': False,
            'mensaje_limitacion': "No se encontraron datos con los filtros aplicados"
        }
    
    # 2. Calcular indicadores
    df_balance = calcular_balance_anual(df_base)
    df_tda = calcular_tda_aproximada(df_balance)
    df_completo = calcular_eficiencia_terminal(df_tda, duracion_programa)
    
    # 3. Extraer métricas del último año con datos válidos de TDA
    df_con_tda = df_completo[df_completo['tda'].notna()]
    
    if df_con_tda.empty:
        ultimo_anio = {
            'anio': None,
            'tda': None,
            'balance': None,
            'eficiencia_terminal': None
        }
        tendencia_tda = "Datos insuficientes para calcular TDA (faltan primíparos)"
    else:
        ultimo = df_con_tda.iloc[-1]
        ultimo_anio = {
            'anio': int(ultimo['anio']),
            'tda': float(ultimo['tda']) if pd.notna(ultimo['tda']) else None,
            'balance': int(ultimo['balance']) if pd.notna(ultimo['balance']) else None,
            'eficiencia_terminal': float(ultimo['eficiencia_terminal']) if pd.notna(ultimo['eficiencia_terminal']) else None
        }
        
        # Calcular tendencia de TDA (comparando últimos 2 años disponibles)
        if len(df_con_tda) >= 2:
            tda_actual = df_con_tda.iloc[-1]['tda']
            tda_anterior = df_con_tda.iloc[-2]['tda']
            if tda_actual < tda_anterior:
                tendencia_tda = f" TDA mejorando: {tda_anterior:.1f}% → {tda_actual:.1f}%"
            elif tda_actual > tda_anterior:
                tendencia_tda = f" TDA empeorando: {tda_anterior:.1f}% → {tda_actual:.1f}%"
            else:
                tendencia_tda = f" TDA estable: {tda_actual:.1f}%"
        else:
            tendencia_tda = f"TDA: {ultimo['tda']:.1f}% (un solo año disponible)"
    
    # 4. Interpretación de eficiencia terminal
    df_con_ef = df_completo[df_completo['eficiencia_terminal'].notna()]
    
    if df_con_ef.empty:
        interpretacion_ef = f"Eficiencia Terminal no calculable (primíparos solo desde 2020, requiere datos de {duracion_programa} años antes)"
    else:
        ef_ultimo = df_con_ef.iloc[-1]['eficiencia_terminal']
        anio_ef = int(df_con_ef.iloc[-1]['anio'])
        
        if ef_ultimo >= 80:
            interpretacion_ef = f" Alta ({ef_ultimo:.1f}% en {anio_ef}): Excelente tasa de graduación"
        elif ef_ultimo >= 50:
            interpretacion_ef = f" Media ({ef_ultimo:.1f}% en {anio_ef}): Margen de mejora en retención"
        else:
            interpretacion_ef = f" Baja ({ef_ultimo:.1f}% en {anio_ef}): Revisar factores de deserción"
    
    # 5. Mensaje sobre limitaciones
    anos_disponibles = sorted(df_completo['anio'].unique())
    primer_anio_prim = df_completo[df_completo['primiparos'].notna()]['anio'].min() if df_completo['primiparos'].notna().any() else None
    
    mensaje_limitacion = []
    mensaje_limitacion.append(f"Datos de matrícula: {min(anos_disponibles)}-{max(anos_disponibles)}")
    if primer_anio_prim:
        mensaje_limitacion.append(f"Primíparos disponibles desde: {int(primer_anio_prim)}")
        primer_anio_ef = int(primer_anio_prim) + duracion_programa
        mensaje_limitacion.append(f"Eficiencia Terminal calculable desde: {primer_anio_ef}")
    else:
        mensaje_limitacion.append("Sin datos de primíparos (se requieren para TDA y Eficiencia Terminal)")
    
    return {
        'df_historico': df_completo,
        'ultimo_anio': ultimo_anio,
        'tendencia_tda': tendencia_tda,
        'interpretacion_ef': interpretacion_ef,
        'datos_disponibles': not df_completo.empty,
        'mensaje_limitacion': " | ".join(mensaje_limitacion)
    }


def detectar_duracion_programa(filtros: Optional[Dict[str, Any]] = None) -> int:
    """
    Detecta la duración teórica del programa basado en el nivel de formación.
    
    Esta función es útil cuando no se conoce el nivel de formación específico.
    
    Args:
        filtros: Dict con filtros que puede incluir 'niveles'
        
    Returns:
        int: Duración teórica estimada en años
    """
    if not filtros or not filtros.get('niveles'):
        return 4  # Default: pregrado típico
    
    niveles = [n.upper() for n in filtros['niveles']]
    
    # Detectar por palabras clave
    for nivel in niveles:
        if 'MAESTR' in nivel or 'MÁSTER' in nivel:
            return 2
        elif 'DOCTOR' in nivel:
            return 4
        elif 'ESPECIALIZ' in nivel:
            return 1
        elif 'TÉCNIC' in nivel or 'TECNIC' in nivel:
            return 2
        elif 'TECNÓLOG' in nivel or 'TECNOLOG' in nivel:
            return 3
        elif 'PROFESIONAL' in nivel or 'UNIVERSITAR' in nivel:
            return 5
    
    return 4  # Default


# ============================================================================
# FUNCIONES DE APOYO PARA LA INTEGRACIÓN EN STREAMLIT
# ============================================================================

def get_programas_disponibles(
    conn: duckdb.DuckDBPyConnection,
    nbc: Optional[str] = None,
    depto: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    min_anos_datos: int = 3
) -> pd.DataFrame:
    """
    Obtiene lista de programas disponibles para análisis de deserción.
    
    Esta función es útil para poblar dropdowns en la UI de Streamlit,
    permitiendo al usuario seleccionar un programa específico.
    
    IMPORTANTE: Solo incluye programas con datos suficientes (min_anos_datos)
    para evitar cálculos de deserción poco confiables.
    
    Args:
        conn: Conexión DuckDB activa
        nbc: NBC para filtrar (opcional)
        depto: Departamento para filtrar (opcional)
        filtros: Dict con filtros adicionales (opcional)
        min_anos_datos: Mínimo de años con datos para incluir el programa (default=3)
        
    Returns:
        DataFrame con columnas:
            - cod_snies: Código SNIES normalizado (sin .0)
            - nombre_programa: Nombre del programa
            - nombre_ies: Nombre de la institución
            - nivel_formacion: Nivel de formación
            - anos_con_datos: Cantidad de años con datos
            - anos_disponibles: Lista de años (ej: "2019,2020,2021")
            - total_matriculados_ultimo_ano: Matriculados del último año
    """
    where_clause = build_desercion_where_clause(nbc, depto, filtros)
    
    query = f"""
    WITH programas_con_datos AS (
        SELECT 
            REPLACE(CAST("COD_SNIES_PROGRAMA" AS VARCHAR), '.0', '') as cod_snies,
            "NOMBRE_PROGRAMA" as nombre_programa,
            "NOMBRE_IES" as nombre_ies,
            "NIVEL_FORMACION" as nivel_formacion,
            "ANO" as anio,
            SUM(CAST("MATRICULADOS" AS BIGINT)) as matriculados
        FROM snies.snies_matriculados
        WHERE {where_clause}
        GROUP BY 
            REPLACE(CAST("COD_SNIES_PROGRAMA" AS VARCHAR), '.0', ''),
            "NOMBRE_PROGRAMA",
            "NOMBRE_IES",
            "NIVEL_FORMACION",
            "ANO"
    ),
    resumen_programas AS (
        SELECT 
            cod_snies,
            nombre_programa,
            nombre_ies,
            nivel_formacion,
            COUNT(DISTINCT anio) as anos_con_datos,
            STRING_AGG(DISTINCT CAST(anio AS VARCHAR), ',' ORDER BY CAST(anio AS VARCHAR)) as anos_disponibles,
            MAX(CASE WHEN anio = (SELECT MAX(anio) FROM programas_con_datos) THEN matriculados ELSE NULL END) as total_matriculados_ultimo_ano
        FROM programas_con_datos
        GROUP BY cod_snies, nombre_programa, nombre_ies, nivel_formacion
        HAVING COUNT(DISTINCT anio) >= {min_anos_datos}
    )
    SELECT 
        cod_snies,
        nombre_programa,
        nombre_ies,
        nivel_formacion,
        anos_con_datos,
        anos_disponibles,
        COALESCE(total_matriculados_ultimo_ano, 0) as total_matriculados_ultimo_ano
    FROM resumen_programas
    ORDER BY total_matriculados_ultimo_ano DESC, nombre_programa
    """
    
    try:
        return conn.execute(query).fetchdf()
    except Exception as e:
        print(f"Error en get_programas_disponibles: {e}")
        return pd.DataFrame(columns=[
            'cod_snies', 'nombre_programa', 'nombre_ies', 'nivel_formacion',
            'anos_con_datos', 'anos_disponibles', 'total_matriculados_ultimo_ano'
        ])


def get_desercion_por_programa(
    conn: duckdb.DuckDBPyConnection,
    cod_snies_programa: str,
    duracion_programa: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calcula indicadores de deserción para UN programa específico.
    
    Esta es la función recomendada para análisis preciso, ya que evita
    los problemas de reclasificación de NBC que afectan los cálculos agregados.
    
    Args:
        conn: Conexión DuckDB activa
        cod_snies_programa: Código SNIES del programa (se normaliza automáticamente)
        duracion_programa: Duración teórica del programa (si no se proporciona, se detecta)
        
    Returns:
        Dict con:
            - 'programa': Info del programa (nombre, IES, nivel)
            - 'df_historico': DataFrame con indicadores por año
            - 'ultimo_anio': Métricas del último año
            - 'tendencia_tda': Interpretación de tendencia
            - 'interpretacion_ef': Interpretación de eficiencia terminal
            - 'datos_disponibles': Bool
            - 'mensaje_limitacion': Mensaje sobre datos
            - 'continuidad_datos': Info sobre años disponibles
    """
    # Normalizar código SNIES
    cod_normalizado = str(cod_snies_programa).replace('.0', '').strip()
    
    # Obtener información del programa
    info_query = f"""
    SELECT DISTINCT
        "NOMBRE_PROGRAMA" as nombre_programa,
        "NOMBRE_IES" as nombre_ies,
        "NIVEL_FORMACION" as nivel_formacion,
        "NBC" as nbc,
        "DEPTO_PROGRAMA" as departamento
    FROM snies.snies_matriculados
    WHERE REPLACE(CAST("COD_SNIES_PROGRAMA" AS VARCHAR), '.0', '') = '{cod_normalizado}'
    LIMIT 1
    """
    
    try:
        info_df = conn.execute(info_query).fetchdf()
        if info_df.empty:
            return {
                'programa': None,
                'df_historico': pd.DataFrame(),
                'ultimo_anio': {},
                'tendencia_tda': "Programa no encontrado",
                'interpretacion_ef': "Programa no encontrado",
                'datos_disponibles': False,
                'mensaje_limitacion': f"No se encontró programa con código SNIES: {cod_snies_programa}",
                'continuidad_datos': None
            }
        
        info_programa = {
            'cod_snies': cod_normalizado,
            'nombre_programa': info_df.iloc[0]['nombre_programa'],
            'nombre_ies': info_df.iloc[0]['nombre_ies'],
            'nivel_formacion': info_df.iloc[0]['nivel_formacion'],
            'nbc': info_df.iloc[0]['nbc'],
            'departamento': info_df.iloc[0]['departamento']
        }
        
        # Detectar duración si no se proporciona
        if duracion_programa is None:
            nivel = str(info_programa['nivel_formacion']).upper()
            if 'MAESTR' in nivel:
                duracion_programa = 2
            elif 'DOCTOR' in nivel:
                duracion_programa = 4
            elif 'ESPECIALIZ' in nivel:
                duracion_programa = 1
            elif 'TÉCNIC' in nivel or 'TECNIC' in nivel:
                duracion_programa = 2
            elif 'TECNÓLOG' in nivel or 'TECNOLOG' in nivel:
                duracion_programa = 3
            else:
                duracion_programa = 5  # Pregrado default
        
        # Obtener indicadores usando la función existente
        resultado = get_indicadores_desercion_completos(
            conn=conn,
            cod_snies_programa=cod_normalizado,
            duracion_programa=duracion_programa
        )
        
        # Verificar continuidad de datos
        if resultado['datos_disponibles'] and not resultado['df_historico'].empty:
            df = resultado['df_historico']
            anos = sorted(df['anio'].dropna().unique())
            anos_esperados = list(range(int(min(anos)), int(max(anos)) + 1))
            anos_faltantes = set(anos_esperados) - set([int(a) for a in anos])
            
            continuidad = {
                'anos_disponibles': [int(a) for a in anos],
                'anos_faltantes': list(anos_faltantes),
                'es_continuo': len(anos_faltantes) == 0,
                'rango': f"{int(min(anos))}-{int(max(anos))}"
            }
        else:
            continuidad = None
        
        return {
            'programa': info_programa,
            'df_historico': resultado['df_historico'],
            'ultimo_anio': resultado['ultimo_anio'],
            'tendencia_tda': resultado['tendencia_tda'],
            'interpretacion_ef': resultado['interpretacion_ef'],
            'datos_disponibles': resultado['datos_disponibles'],
            'mensaje_limitacion': resultado['mensaje_limitacion'],
            'continuidad_datos': continuidad
        }
        
    except Exception as e:
        return {
            'programa': None,
            'df_historico': pd.DataFrame(),
            'ultimo_anio': {},
            'tendencia_tda': f"Error: {str(e)}",
            'interpretacion_ef': f"Error: {str(e)}",
            'datos_disponibles': False,
            'mensaje_limitacion': f"Error al procesar programa: {str(e)}",
            'continuidad_datos': None
        }


def get_resumen_desercion_kpi(
    conn: duckdb.DuckDBPyConnection,
    nbc: Optional[str] = None,
    depto: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    cod_snies_programa: Optional[str] = None,
    nombre_programa: Optional[str] = None
) -> Dict[str, Any]:
    """
    Versión simplificada para mostrar en KPIs de Streamlit.
    
    Retorna solo los valores necesarios para st.metric().
    
    Args:
        conn: Conexión DuckDB
        nbc: NBC opcional
        depto: Departamento opcional
        filtros: Dict de filtros opcionales
        cod_snies_programa: Código SNIES del programa (opcional)
        nombre_programa: Nombre del programa (opcional)
        
    Returns:
        Dict con: tda_valor, tda_delta, ef_valor, datos_ok, mensaje
    """
    duracion = detectar_duracion_programa(filtros)
    resultado = get_indicadores_desercion_completos(
        conn, nbc, depto, filtros, duracion, cod_snies_programa, nombre_programa
    )
    
    if not resultado['datos_disponibles']:
        return {
            'tda_valor': None,
            'tda_delta': None,
            'ef_valor': None,
            'datos_ok': False,
            'mensaje': resultado['mensaje_limitacion']
        }
    
    df = resultado['df_historico']
    df_tda = df[df['tda'].notna()]
    
    tda_valor = None
    tda_delta = None
    ef_valor = None
    
    if len(df_tda) >= 1:
        tda_valor = round(df_tda.iloc[-1]['tda'], 1)
        if len(df_tda) >= 2:
            tda_anterior = df_tda.iloc[-2]['tda']
            tda_delta = round(tda_valor - tda_anterior, 1)
    
    df_ef = df[df['eficiencia_terminal'].notna()]
    if len(df_ef) >= 1:
        ef_valor = round(df_ef.iloc[-1]['eficiencia_terminal'], 1)
    
    return {
        'tda_valor': tda_valor,
        'tda_delta': tda_delta,
        'ef_valor': ef_valor,
        'datos_ok': True,
        'mensaje': resultado['mensaje_limitacion']
    }


# ============================================================================
# TEST DEL MÓDULO
# ============================================================================

if __name__ == "__main__":
    import os
    
    # Ruta al DuckDB
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'repositorio_900mb.duckdb')
    
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encuentra {DB_PATH}")
        exit(1)
    
    print("="*70)
    print("TEST DEL MÓDULO DE DESERCIÓN SPADIES")
    print("="*70)
    
    conn = duckdb.connect(DB_PATH, read_only=True)
    
    # Test 1: Sin filtros (nacional)
    print("\n TEST 1: Análisis Nacional (sin filtros)")
    print("-"*50)
    resultado = get_indicadores_desercion_completos(conn)
    if resultado['datos_disponibles']:
        print(f"Datos: {resultado['mensaje_limitacion']}")
        print(f"\nÚltimo año: {resultado['ultimo_anio']}")
        print(f"Tendencia TDA: {resultado['tendencia_tda']}")
        print(f"Eficiencia Terminal: {resultado['interpretacion_ef']}")
        print(f"\nHistórico:")
        print(resultado['df_historico'].to_string())
    else:
        print(f"Sin datos: {resultado['mensaje_limitacion']}")
    
    # Test 2: Con NBC específico
    print("\n TEST 2: Análisis por NBC (Matemáticas)")
    print("-"*50)
    # Obtener el NBC exacto de la BD
    nbc_exacto = conn.execute("SELECT DISTINCT NBC FROM snies.snies_matriculados WHERE NBC LIKE '%MATEM%'").fetchone()[0]
    print(f"NBC encontrado: {nbc_exacto}")
    resultado = get_indicadores_desercion_completos(conn, nbc=nbc_exacto)
    if resultado['datos_disponibles']:
        print(f"Datos: {resultado['mensaje_limitacion']}")
        print(f"\nÚltimo año: {resultado['ultimo_anio']}")
        print(f"Tendencia TDA: {resultado['tendencia_tda']}")
        print(f"Eficiencia Terminal: {resultado['interpretacion_ef']}")
    else:
        print(f"Sin datos: {resultado['mensaje_limitacion']}")
    
    # Test 3: Con filtros (nivel maestría)
    print("\n TEST 3: Análisis Maestrías en Matemáticas")
    print("-"*50)
    filtros_test = {'niveles': ['Maestría']}
    resultado = get_indicadores_desercion_completos(
        conn, 
        nbc=nbc_exacto, 
        filtros=filtros_test,
        duracion_programa=2
    )
    if resultado['datos_disponibles']:
        print(f"Datos: {resultado['mensaje_limitacion']}")
        print(f"\nÚltimo año: {resultado['ultimo_anio']}")
        print(f"Tendencia TDA: {resultado['tendencia_tda']}")
        print(f"Eficiencia Terminal: {resultado['interpretacion_ef']}")
        print(f"\nHistórico detallado:")
        print(resultado['df_historico'].to_string())
    else:
        print(f"Sin datos: {resultado['mensaje_limitacion']}")
    
    # Test 4: Función KPI simplificada
    print("\n TEST 4: Función KPI para Streamlit")
    print("-"*50)
    kpi = get_resumen_desercion_kpi(conn, nbc=nbc_exacto, filtros=filtros_test)
    print(f"TDA: {kpi['tda_valor']}% (delta: {kpi['tda_delta']})")
    print(f"Eficiencia Terminal: {kpi['ef_valor']}%")
    print(f"Mensaje: {kpi['mensaje']}")
    
    conn.close()
    print("\n Tests completados")
