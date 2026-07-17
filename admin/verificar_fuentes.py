import duckdb
import pandas as pd

conn = duckdb.connect('D:/UniSabana_Dev/Dataset/DuckDB/repositorio.duckdb', read_only=True)

# ===========================================
# 1. COMPETENCIAS - Para Skills Gap Radar Chart
# ===========================================
print('='*60)
print('1. COMPETENCIAS - CUOC (Skills Gap)')
print('='*60)

# Buscar tablas de competencias en clasificadores
try:
    result = conn.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name LIKE '%cuoc%' OR table_name LIKE '%competenc%' OR table_name LIKE '%destrez%' OR table_name LIKE '%conocim%'
    """).fetchall()
    print(f"Tablas encontradas: {[r[0] for r in result]}")
except Exception as e:
    print(f"Error: {e}")

# Ver columnas de CUOC si existe
try:
    for schema in ['clasificadores', 'cuoc']:
        result = conn.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = '{schema}' AND table_name = 'cuoc'
        """).fetchall()
        if result:
            print(f"\n[{schema}.cuoc] Columnas: {[r[0] for r in result]}")
            sample = conn.execute(f"SELECT * FROM {schema}.cuoc LIMIT 3").fetchdf()
            print(sample)
except Exception as e:
    print(f"Error: {e}")

# ===========================================
# 2. VACANTES APE CLEAN - Para Demanda Real
# ===========================================
print('\n' + '='*60)
print('2. VACANTES APE CLEAN - Demanda Laboral')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'tendencias_laborales' AND table_name = 'vacantes_ape_clean'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM tendencias_laborales.vacantes_ape_clean LIMIT 5").fetchdf()
    print(sample)
    
    count = conn.execute("SELECT COUNT(*) FROM tendencias_laborales.vacantes_ape_clean").fetchone()[0]
    print(f"Total registros: {count}")
except Exception as e:
    print(f"Error vacantes_ape_clean: {e}")

# ===========================================
# 3. CONECTIVIDAD - Internet y 4G
# ===========================================
print('\n' + '='*60)
print('3. CONECTIVIDAD - Internet / 4G')
print('='*60)

# Buscar tablas de conectividad
try:
    result = conn.execute("""
        SELECT table_schema, table_name FROM information_schema.tables 
        WHERE table_name LIKE '%internet%' OR table_name LIKE '%conectiv%' OR table_name LIKE '%4g%' OR table_name LIKE '%movil%' OR table_name LIKE '%cobertura%'
    """).fetchall()
    print(f"Tablas conectividad: {result}")
    
    for schema, table in result[:5]:
        cols = conn.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = '{schema}' AND table_name = '{table}'
        """).fetchall()
        print(f"\n[{schema}.{table}] Columnas: {[r[0] for r in cols]}")
        try:
            sample = conn.execute(f"SELECT * FROM {schema}.{table} LIMIT 3").fetchdf()
            print(sample)
        except:
            pass
except Exception as e:
    print(f"Error conectividad: {e}")

# ===========================================
# 4. MUNICIPIOS PDET
# ===========================================
print('\n' + '='*60)
print('4. MUNICIPIOS PDET')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'territorial' AND table_name = 'municipios_pdet'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM territorial.municipios_pdet LIMIT 5").fetchdf()
    print(sample)
    
    count = conn.execute("SELECT COUNT(*) FROM territorial.municipios_pdet").fetchone()[0]
    print(f"Total municipios PDET: {count}")
except Exception as e:
    print(f"Error PDET: {e}")

# ===========================================
# 5. TENDENCIAS TECNOLÓGICAS (Eje Global)
# ===========================================
print('\n' + '='*60)
print('5. TENDENCIAS TECNOLÓGICAS')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'tendencias_tecnologicas' AND table_name = 'habilidades_futuro'
    """).fetchall()
    print(f"Columnas habilidades_futuro: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM tendencias_tecnologicas.habilidades_futuro LIMIT 10").fetchdf()
    print(sample)
except Exception as e:
    print(f"Error habilidades_futuro: {e}")

# ===========================================
# 6. SALARIOS POR CARGO
# ===========================================
print('\n' + '='*60)
print('6. SALARIOS POR CARGO')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'datos_complementarios' AND table_name = 'salarios_por_cargo'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM datos_complementarios.salarios_por_cargo LIMIT 5").fetchdf()
    print(sample)
except Exception as e:
    print(f"Error salarios: {e}")

# ===========================================
# 7. ESTRUCTURA EMPRESARIAL (CIIU)
# ===========================================
print('\n' + '='*60)
print('7. ESTRUCTURA EMPRESARIAL - CIIU')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'rues_camaras_comercio' AND table_name = 'estructura_empresarial_actividad_economica'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM rues_camaras_comercio.estructura_empresarial_actividad_economica LIMIT 5").fetchdf()
    print(sample)
except Exception as e:
    print(f"Error estructura_empresarial: {e}")

# ===========================================
# 8. DNP DESEMPEÑO MUNICIPAL
# ===========================================
print('\n' + '='*60)
print('8. DNP DESEMPEÑO MUNICIPAL')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'dnp_planes_desarrollo' AND table_name = 'dnp_medicion_desempeno_municipal'
    """).fetchall()
    print(f"Columnas: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM dnp_planes_desarrollo.dnp_medicion_desempeno_municipal LIMIT 5").fetchdf()
    print(sample)
except Exception as e:
    print(f"Error DNP: {e}")

# ===========================================
# 9. INDICADORES GLOBALES - Banco Mundial
# ===========================================
print('\n' + '='*60)
print('9. INDICADORES GLOBALES - Banco Mundial')
print('='*60)

try:
    result = conn.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'indicadores_globales' AND table_name = 'bm_desempleo_jovenes'
    """).fetchall()
    print(f"Columnas bm_desempleo_jovenes: {[r[0] for r in result]}")
    
    sample = conn.execute("SELECT * FROM indicadores_globales.bm_desempleo_jovenes WHERE pais = 'Colombia' ORDER BY ano DESC LIMIT 5").fetchdf()
    print(sample)
except Exception as e:
    print(f"Error BM: {e}")

conn.close()
