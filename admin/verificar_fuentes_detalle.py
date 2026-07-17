"""
Verificacion detallada de fuentes — Competencias, mapeos y conectividad.
========================================================================

Profundiza el analisis de verificar_fuentes.py enfocandose en:
- Estructura completa de conocimientos y destrezas CUOC
- Mapeo NBC → CUOC (llave del puente educacion-trabajo)
- Cobertura 4G por departamento y municipio
- Internet fijo (accesos, tecnologias, velocidades)
- Vacantes APE con JOIN a clasificacion CUOC
- Indicadores Banco Mundial filtrados por Colombia

Recuperado de UniSabana_Dev. Ruta absoluta original reemplazada.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
from config.database import DUCKDB_PATH

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

# ============================================================================
# 1. CONOCIMIENTOS Y DESTREZAS CUOC
# ============================================================================
print('=' * 70)
print('COMPETENCIAS — CUOC CONOCIMIENTOS Y DESTREZAS')
print('=' * 70)

for tabla_nombre in ['cuoc_conocimientos', 'cuoc_destrezas']:
    try:
        result = conn.execute(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{tabla_nombre}'
        """).fetchall()
        print(f"\n{tabla_nombre} — Columnas: {[r[0] for r in result]}")
        sample = conn.execute(f"SELECT * FROM clasificadores.{tabla_nombre} LIMIT 10").fetchdf()
        print(sample.to_string())
        count = conn.execute(f"SELECT COUNT(*) FROM clasificadores.{tabla_nombre}").fetchone()[0]
        print(f"Total registros: {count:,}")
    except Exception as e:
        print(f"Error {tabla_nombre}: {e}")

# ============================================================================
# 2. MAPEO NBC → CUOC
# ============================================================================
print('\n' + '=' * 70)
print('MAPEO NBC → CUOC')
print('=' * 70)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mapeo_nbc_cuoc'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    sample = conn.execute("SELECT * FROM catalogo_curado.mapeo_nbc_cuoc LIMIT 10").fetchdf()
    print(sample.to_string())
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 3. COBERTURA 4G POR DEPARTAMENTO
# ============================================================================
print('\n' + '=' * 70)
print('COBERTURA 4G POR DEPARTAMENTO Y MUNICIPIO')
print('=' * 70)

try:
    sample = conn.execute("""
        SELECT DISTINCT departamento, municipio, cobertuta_4g, cobertura_lte
        FROM competencias_tic."cobertura_móvil_por_tecnología_departamento_y_muni"
        WHERE a_o = 2023
        LIMIT 20
    """).fetchdf()
    print(sample.to_string())

    stats = conn.execute("""
        SELECT departamento,
               COUNT(DISTINCT municipio) as n_municipios,
               SUM(CASE WHEN cobertuta_4g = 'S' THEN 1 ELSE 0 END) as con_4g
        FROM competencias_tic."cobertura_móvil_por_tecnología_departamento_y_muni"
        WHERE a_o = 2023
        GROUP BY departamento
        ORDER BY con_4g DESC
        LIMIT 15
    """).fetchdf()
    print("\n--- Estadisticas por departamento ---")
    print(stats.to_string())
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 4. INTERNET FIJO
# ============================================================================
print('\n' + '=' * 70)
print('INTERNET FIJO')
print('=' * 70)

try:
    cols = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'conectividad' AND table_name = 'internet_fijo_accesos'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in cols]}")
    sample = conn.execute("SELECT * FROM conectividad.internet_fijo_accesos LIMIT 10").fetchdf()
    print(sample.to_string())
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 5. VACANTES APE — JOIN con CUOC
# ============================================================================
print('\n' + '=' * 70)
print('VACANTES APE — Estructura completa con JOIN CUOC')
print('=' * 70)

try:
    sample = conn.execute("""
        SELECT v.*, c.OCUPACION, c.GRAN_GRUPO, c.NIVEL
        FROM tendencias_laborales.vacantes_ape_clean v
        LEFT JOIN clasificadores.cuoc c
            ON CAST(v.codigo_cuoc AS VARCHAR) = CAST(c.COD_OCUPACION AS VARCHAR)
        LIMIT 20
    """).fetchdf()
    print(sample.to_string())

    total = conn.execute("""
        SELECT SUM(vacantes_2024) as total_2024,
               SUM(vacantes_2023) as total_2023,
               COUNT(DISTINCT codigo_cuoc) as n_ocupaciones
        FROM tendencias_laborales.vacantes_ape_clean
    """).fetchdf()
    print("\n--- Totales ---")
    print(total.to_string())
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 6. BANCO MUNDIAL — Desempleo juvenil Colombia
# ============================================================================
print('\n' + '=' * 70)
print('INDICADORES BANCO MUNDIAL — Colombia')
print('=' * 70)

try:
    sample = conn.execute("""
        SELECT * FROM indicadores_globales.bm_desempleo_jovenes
        WHERE pais = 'Colombia'
        ORDER BY a_o DESC
        LIMIT 10
    """).fetchdf()
    print(sample.to_string())
except Exception as e:
    print(f"Error: {e}")

conn.close()
