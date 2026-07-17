"""
Compara las tablas de la DB contra las referenciadas en el codigo fuente.
=====================================================================

Cruce entre el inventario real de DuckDB y el rastreo de analizar_uso_tablas.py.
Identifica tablas huerfanas (existen en la DB pero ninguna consulta del
dashboard las referencia) y estima el espacio recuperable si se eliminan.

Util como paso previo a compactar_db.py: eliminar tablas sin uso reduce
el tamaño de la DB antes de compactar.

Recuperado de Repositorio Maestro V1 (v2). La lista hardcodeada de tablas usadas
se reemplazo por una lectura dinamica desde el codigo fuente actual.
"""

import duckdb
from collections import defaultdict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import DUCKDB_PATH

# ============================================================================
# CARGA DE REFERENCIAS — Desde el codigo fuente actual (mismo patron de analizar_uso_tablas.py)
# ============================================================================

import re

ARCHIVOS_A_ESCANEAR = [
    'data/queries.py', 'app.py',
    'services/ml/matching.py', 'services/ml/snies_etdh.py', 'services/data_loader.py',
    'services/sources.py',
    'views/tab_academico.py', 'views/tab_laboral.py',
    'views/tab_territorial.py', 'views/tab_decision.py',
]
import re, os

tablas_referenciadas = set()
patron_sql = re.compile(r'(FROM|JOIN|INTO)\s+([a-z_]+)\.([a-z_0-9]+)', re.IGNORECASE)
patron_string = re.compile(r'["\']([a-z_]+)\.([a-z_0-9]+)["\']', re.IGNORECASE)

for archivo in ARCHIVOS_A_ESCANEAR:
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        for match in patron_sql.findall(contenido):
            _, schema, tabla = match
            tablas_referenciadas.add(f"{schema.lower()}.{tabla.lower()}")
        for schema, tabla in patron_string.findall(contenido):
            if schema.lower() not in ['main', 'temp', 'information_schema']:
                tablas_referenciadas.add(f"{schema.lower()}.{tabla.lower()}")

# ============================================================================
# CRUCE DB vs CODIGO — Identifica tablas sin uso
# ============================================================================

db = duckdb.connect(DUCKDB_PATH, read_only=True)

resultado = db.sql("""
    SELECT schema_name, table_name, estimated_size
    FROM duckdb_tables()
    ORDER BY estimated_size DESC
""").fetchall()

tablas_sin_uso = []
espacio_total = 0

print("TABLAS SIN USO (candidatas a eliminacion):\n")
print(f"{'Schema.Table':<60} {'Size MB':>10} {'Filas':>12}")
print("-" * 85)

for schema, tabla, size in resultado:
    nombre_completo = f"{schema}.{tabla}".lower()
    if schema.lower() in ['information_schema', 'pg_catalog', 'main']:
        continue

    if nombre_completo not in tablas_referenciadas:
        size_mb = (size or 0) / (1024 * 1024)
        espacio_total += size_mb
        try:
            filas = db.execute(f'SELECT count(*) FROM "{schema}"."{tabla}"').fetchone()[0]
        except Exception:
            filas = 0
        tablas_sin_uso.append((nombre_completo, size_mb, filas))
        print(f"{nombre_completo:<60} {size_mb:>10.2f} {filas:>12,}")

print("-" * 85)
print(f"{'TOTAL SIN USO':<60} {espacio_total:>10.2f} MB")
print(f"\nTotal tablas sin uso: {len(tablas_sin_uso)}")

# Desglose por esquema
print("\nEspacio sin uso por esquema:")
por_esquema = defaultdict(lambda: {'size': 0, 'count': 0})
for tabla, size, _ in tablas_sin_uso:
    esquema = tabla.split('.')[0]
    por_esquema[esquema]['size'] += size
    por_esquema[esquema]['count'] += 1

for esquema in sorted(por_esquema, key=lambda s: por_esquema[s]['size'], reverse=True):
    info = por_esquema[esquema]
    print(f"  {esquema}: {info['count']} tablas, {info['size']:.2f} MB")

db.close()
