"""
Auditoria de fuentes de datos — Verifica integridad de tablas clave.
====================================================================

Recorre 9 categorias de datos (competencias, vacantes, conectividad,
PDET, tendencias tecnologicas, salarios, estructura empresarial, DNP,
Banco Mundial) y para cada una reporta: columnas disponibles, muestra
de datos, y conteo total de registros.

Util para validar que la DB contiene los datos esperados por cada
componente del dashboard ANTES de ejecutar la aplicacion.

Recuperado de UniSabana_Dev. Ruta absoluta original reemplazada por
el resolvedor automatico de config/database.py.
"""

import duckdb
from config.database import DUCKDB_PATH

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

def _columnas(schema, tabla):
    """Lee los nombres de columna de una tabla."""
    return conn.execute(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{tabla}'
    """).fetchall()

def _muestra(schema, tabla, limite=3):
    """Obtiene las primeras N filas de una tabla."""
    return conn.execute(f"SELECT * FROM {schema}.{tabla} LIMIT {limite}").fetchdf()

def _conteo(schema, tabla):
    """Cuenta registros en una tabla."""
    return conn.execute(f"SELECT COUNT(*) FROM {schema}.{tabla}").fetchone()[0]


# ============================================================================
# 1. COMPETENCIAS CUOC
# ============================================================================
print('=' * 60)
print('1. COMPETENCIAS — CUOC (Skills Gap)')
print('=' * 60)

try:
    result = conn.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name LIKE '%cuoc%' OR table_name LIKE '%competenc%'
           OR table_name LIKE '%destrez%' OR table_name LIKE '%conocim%'
    """).fetchall()
    print(f"Tablas encontradas: {[r[0] for r in result]}")
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 2. VACANTES APE
# ============================================================================
print('\n' + '=' * 60)
print('2. VACANTES APE CLEAN — Demanda Laboral')
print('=' * 60)

try:
    cols = _columnas('tendencias_laborales', 'vacantes_ape_clean')
    print(f"Columnas: {[r[0] for r in cols]}")
    sample = _muestra('tendencias_laborales', 'vacantes_ape_clean', 5)
    print(sample)
    print(f"Total registros: {_conteo('tendencias_laborales', 'vacantes_ape_clean'):,}")
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 3. CONECTIVIDAD
# ============================================================================
print('\n' + '=' * 60)
print('3. CONECTIVIDAD — Internet / 4G')
print('=' * 60)

try:
    result = conn.execute("""
        SELECT table_schema, table_name FROM information_schema.tables
        WHERE table_name LIKE '%internet%' OR table_name LIKE '%conectiv%'
           OR table_name LIKE '%4g%' OR table_name LIKE '%cobertura%'
    """).fetchall()
    print(f"Tablas de conectividad: {result}")
    for schema, table in result[:5]:
        cols = _columnas(schema, table)
        print(f"\n[{schema}.{table}] Columnas: {[r[0] for r in cols]}")
        try:
            print(_muestra(schema, table, 3))
        except Exception:
            pass
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 4. MUNICIPIOS PDET
# ============================================================================
print('\n' + '=' * 60)
print('4. MUNICIPIOS PDET')
print('=' * 60)

try:
    cols = _columnas('territorial', 'municipios_pdet')
    print(f"Columnas: {[r[0] for r in cols]}")
    print(_muestra('territorial', 'municipios_pdet', 5))
    print(f"Total municipios PDET: {_conteo('territorial', 'municipios_pdet'):,}")
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 5. TENDENCIAS TECNOLOGICAS
# ============================================================================
print('\n' + '=' * 60)
print('5. TENDENCIAS TECNOLOGICAS')
print('=' * 60)

try:
    cols = _columnas('tendencias_tecnologicas', 'habilidades_futuro')
    print(f"Columnas: {[r[0] for r in cols]}")
    print(_muestra('tendencias_tecnologicas', 'habilidades_futuro', 10))
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 6. SALARIOS POR CARGO
# ============================================================================
print('\n' + '=' * 60)
print('6. SALARIOS POR CARGO')
print('=' * 60)

try:
    cols = _columnas('datos_complementarios', 'salarios_por_cargo')
    print(f"Columnas: {[r[0] for r in cols]}")
    print(_muestra('datos_complementarios', 'salarios_por_cargo', 5))
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 7. ESTRUCTURA EMPRESARIAL CIIU
# ============================================================================
print('\n' + '=' * 60)
print('7. ESTRUCTURA EMPRESARIAL — CIIU')
print('=' * 60)

try:
    cols = _columnas('rues_camaras_comercio', 'estructura_empresarial_actividad_economica')
    print(f"Columnas: {[r[0] for r in cols]}")
    print(_muestra('rues_camaras_comercio', 'estructura_empresarial_actividad_economica', 5))
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 8. DNP DESEMPENO MUNICIPAL
# ============================================================================
print('\n' + '=' * 60)
print('8. DNP DESEMPENO MUNICIPAL')
print('=' * 60)

try:
    cols = _columnas('dnp_planes_desarrollo', 'dnp_medicion_desempeno_municipal')
    print(f"Columnas: {[r[0] for r in cols]}")
    print(_muestra('dnp_planes_desarrollo', 'dnp_medicion_desempeno_municipal', 5))
except Exception as e:
    print(f"Error: {e}")

# ============================================================================
# 9. INDICADORES GLOBALES — Banco Mundial
# ============================================================================
print('\n' + '=' * 60)
print('9. INDICADORES GLOBALES — Banco Mundial')
print('=' * 60)

try:
    cols = _columnas('indicadores_globales', 'bm_desempleo_jovenes')
    print(f"Columnas: {[r[0] for r in cols]}")
    muestra = conn.execute("""
        SELECT * FROM indicadores_globales.bm_desempleo_jovenes
        WHERE pais = 'Colombia' ORDER BY ano DESC LIMIT 5
    """).fetchdf()
    print(muestra)
except Exception as e:
    print(f"Error: {e}")

conn.close()
