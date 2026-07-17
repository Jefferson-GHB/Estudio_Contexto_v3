"""
Verifica la integridad del puente competencias CUOC ↔ ocupaciones.
==================================================================

Explora:
- Conocimientos y destrezas por ocupacion en la DB
- Ocupaciones con mayor cobertura de competencias
- Ejemplo concreto (codigo 2151) para validar el mapeo
- Relacion NBC → ocupaciones CUOC via catalogo_curado.mapeo_nbc_cuoc

Recuperado de Repositorio Maestro V1. Ruta absoluta original reemplazada.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
from config.database import DUCKDB_PATH

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

# ============================================================================
# 1. INVENTARIO DE CONOCIMIENTOS Y DESTREZAS
# ============================================================================
print('=== CUOC CONOCIMIENTOS ===')
sample = conn.execute('SELECT * FROM competencias.cuoc_conocimientos LIMIT 10').fetchdf()
print(sample.to_string())
count = conn.execute("SELECT COUNT(*) FROM competencias.cuoc_conocimientos").fetchone()[0]
print(f'Total conocimientos: {count:,}')

print('\n=== CUOC DESTREZAS ===')
sample = conn.execute('SELECT * FROM competencias.cuoc_destrezas LIMIT 10').fetchdf()
print(sample.to_string())
count = conn.execute("SELECT COUNT(*) FROM competencias.cuoc_destrezas").fetchone()[0]
print(f'Total destrezas: {count:,}')

# ============================================================================
# 2. OCUPACIONES CON COMPETENCIAS REGISTRADAS
# ============================================================================
print('\n=== OCUPACIONES CON COMPETENCIAS ===')
ocupaciones = conn.execute("""
    SELECT DISTINCT c.codigo_ocupacion, c.nombre_ocupacion
    FROM competencias.cuoc_conocimientos c
    ORDER BY c.codigo_ocupacion
    LIMIT 30
""").fetchdf()
print(ocupaciones.to_string())

# ============================================================================
# 3. EJEMPLO CONCRETO — Codigo 2151 (Ingenieros Electricos)
# ============================================================================
print('\n=== EJEMPLO: Competencias para codigo 2151 ===')
conocimientos = conn.execute("""
    SELECT codigo_ocupacion, conocimiento
    FROM competencias.cuoc_conocimientos
    WHERE codigo_ocupacion = 2151
""").fetchdf()
if not conocimientos.empty:
    print('Conocimientos:', conocimientos['conocimiento'].tolist())
else:
    print('Sin conocimientos registrados para 2151')

destrezas = conn.execute("""
    SELECT codigo_ocupacion, destreza
    FROM competencias.cuoc_destrezas
    WHERE codigo_ocupacion = 2151
""").fetchdf()
if not destrezas.empty:
    print('Destrezas:', destrezas['destreza'].tolist())
else:
    print('Sin destrezas registradas para 2151')

# ============================================================================
# 4. MAPEO NBC → OCUPACIONES CUOC
# ============================================================================
print('\n=== MAPEO NBC → OCUPACIONES CUOC ===')
mapeo = conn.execute("""
    SELECT NBC, Areas_Cualificacion_CUOC, N_Ocupaciones_CUOC
    FROM catalogo_curado.mapeo_nbc_cuoc
    WHERE N_Ocupaciones_CUOC > 0
    LIMIT 10
""").fetchdf()
print(mapeo.to_string())

conn.close()
