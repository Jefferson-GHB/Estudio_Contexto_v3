import duckdb
import pandas as pd

conn = duckdb.connect('D:/UniSabana_Dev/Dataset/DuckDB/repositorio.duckdb', read_only=True)

# ===========================================
# COMPETENCIAS DETALLADO - Para Skills Gap
# ===========================================
print('='*70)
print('COMPETENCIAS - CUOC CONOCIMIENTOS Y DESTREZAS')
print('='*70)

# cuoc_conocimientos
try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'cuoc_conocimientos'
    """).fetchall()
    print(f"\ncuoc_conocimientos Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM clasificadores.cuoc_conocimientos LIMIT 10").fetchdf()
    print(sample.to_string())
    
    count = conn.execute("SELECT COUNT(*) FROM clasificadores.cuoc_conocimientos").fetchone()[0]
    print(f"Total registros: {count}")
except Exception as e:
    print(f"Error: {e}")

# cuoc_destrezas
try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'cuoc_destrezas'
    """).fetchall()
    print(f"\ncuoc_destrezas Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM clasificadores.cuoc_destrezas LIMIT 10").fetchdf()
    print(sample.to_string())
    
    count = conn.execute("SELECT COUNT(*) FROM clasificadores.cuoc_destrezas").fetchone()[0]
    print(f"Total registros: {count}")
except Exception as e:
    print(f"Error: {e}")

# ===========================================
# MAPEO NBC -> CUOC
# ===========================================
print('\n' + '='*70)
print('MAPEO NBC -> CUOC')
print('='*70)

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

# ===========================================
# CONECTIVIDAD 4G DETALLADO
# ===========================================
print('\n' + '='*70)
print('COBERTURA 4G POR DEPARTAMENTO Y MUNICIPIO')
print('='*70)

try:
    # Estructura de cobertura móvil
    sample = conn.execute("""
        SELECT DISTINCT departamento, municipio, cobertuta_4g, cobertura_lte
        FROM competencias_tic."cobertura_móvil_por_tecnología_departamento_y_muni"
        WHERE a_o = 2023 OR a_o = 2022
        LIMIT 20
    """).fetchdf()
    print(sample.to_string())
    
    # Contar municipios con cobertura 4G
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
    print("\n--- Estadísticas por departamento ---")
    print(stats.to_string())
except Exception as e:
    print(f"Error: {e}")

# Internet Fijo
print('\n' + '='*70)
print('INTERNET FIJO')
print('='*70)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'conectividad' AND table_name = 'internet_fijo_accesos'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("""
        SELECT * FROM conectividad.internet_fijo_accesos 
        LIMIT 10
    """).fetchdf()
    print(sample.to_string())
except Exception as e:
    print(f"Error: {e}")

# ===========================================
# VACANTES APE DETALLADO - Ver relación con NBC
# ===========================================
print('\n' + '='*70)
print('VACANTES APE - Estructura completa')
print('='*70)

try:
    sample = conn.execute("""
        SELECT v.*, c.OCUPACION, c.GRAN_GRUPO, c.NIVEL
        FROM tendencias_laborales.vacantes_ape_clean v
        LEFT JOIN clasificadores.cuoc c ON CAST(v.codigo_cuoc AS VARCHAR) = CAST(c.COD_OCUPACION AS VARCHAR)
        LIMIT 20
    """).fetchdf()
    print(sample.to_string())
    
    total = conn.execute("""
        SELECT SUM(vacantes_2024) as total_vacantes_2024,
               SUM(vacantes_2023) as total_vacantes_2023,
               COUNT(DISTINCT codigo_cuoc) as n_ocupaciones
        FROM tendencias_laborales.vacantes_ape_clean
    """).fetchdf()
    print("\n--- Totales ---")
    print(total.to_string())
except Exception as e:
    print(f"Error: {e}")

# ===========================================
# BANCO MUNDIAL - Desempleo Jóvenes
# ===========================================
print('\n' + '='*70)
print('INDICADORES BANCO MUNDIAL')
print('='*70)

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
