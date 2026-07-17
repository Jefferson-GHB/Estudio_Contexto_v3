"""
Rastrea referencias a schema.table en el codigo fuente del proyecto.
====================================================================

Escanea archivos Python del dashboard en busca de patrones FROM/JOIN/INTO
y literales de cadena que referencien tablas DuckDB. Util para auditorias
de cobertura: identifica que tablas de la base de datos son efectivamente
consultadas por la aplicacion, y cuales podrian ser candidatas a depuracion.

Recuperado de Repositorio Maestro V1 (v2 pre-refactorizacion). Las rutas originales
apuntaban a archivos del proyecto antiguo (app_streamlit.py, ml_matching.py).
Se actualizaron para reflejar la estructura modular actual de V3.1.0.
"""

import re
import os
import glob

# ============================================================================
# RASTREO DE TABLAS — Busca schema.table en queries SQL y f-strings
# ============================================================================

# Archivos del proyecto actual donde residen las consultas DuckDB
ARCHIVOS_A_ESCANEAR = [
    'data/queries.py',
    'app.py',
    'services/ml/matching.py',
    'services/ml/snies_etdh.py',
    'services/data_loader.py',
    'services/sources.py',
    'views/tab_academico.py',
    'views/tab_laboral.py',
    'views/tab_territorial.py',
    'views/tab_decision.py',
]

tablas_referenciadas = set()

# Patron 1: SQL explicito — FROM/JOIN/INTO schema.table
patron_sql = re.compile(r'(FROM|JOIN|INTO)\s+([a-z_]+)\.([a-z_0-9]+)', re.IGNORECASE)

# Patron 2: Strings literales — "schema"."table" o 'schema'.'table'  
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

print(f"Total tablas referenciadas en codigo: {len(tablas_referenciadas)}")
print()

esquemas = set(t.split('.')[0] for t in tablas_referenciadas)
for esquema in sorted(esquemas):
    tablas_en_esquema = [t for t in tablas_referenciadas if t.startswith(esquema + '.')]
    print(f"  {esquema}: {len(tablas_en_esquema)} tablas")

print("\nTodas las tablas referenciadas:")
for tabla in sorted(tablas_referenciadas):
    print(f"  {tabla}")
