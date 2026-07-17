"""
Verifica la existencia y estructura de tablas complementarias en DuckDB.
========================================================================

Comprueba que las tablas de tendencias tecnologicas, indicadores globales,
microcredenciales, OECD, UNESCO, conectividad y competencias TIC existen
y tienen las columnas esperadas. Complementa a verificar_fuentes.py
cubriendo tablas que no estan en el flujo principal del dashboard pero
que alimentan analisis de contexto global y territorial.

Recuperado de UniSabana_Dev. Ruta absoluta original reemplazada.
"""

import duckdb
from config.database import DUCKDB_PATH

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

TABLAS_A_VERIFICAR = [
    ('tendencias_tecnologicas', 'adopcion_ia_paises'),
    ('tendencias_tecnologicas', 'edtech_adopcion_paises'),
    ('tendencias_tecnologicas', 'industria40_paises'),
    ('tendencias_tecnologicas', 'mercado_ia_global'),
    ('indicadores_globales', 'bm_tasa_desempleo'),
    ('indicadores_globales', 'bm_participacion_fuerza_laboral'),
    ('indicadores_globales', 'bm_gasto_educacion_pib'),
    ('indicadores_globales', 'bm_pib_per_capita'),
    ('indicadores_globales', 'bm_usuarios_internet_pct'),
    ('microcredenciales', 'tendencias'),
    ('microcredenciales', 'mercado_global'),
    ('oecd_internacional', 'labour_statistics'),
    ('unesco_internacional', 'indicadores_educacion'),
    ('conectividad', 'internet_fijo_accesos'),
    ('competencias_tic', 'cobertura_móvil_por_tecnología_departamento_y_muni'),
]

for schema, tabla in TABLAS_A_VERIFICAR:
    try:
        cols = conn.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema = '{schema}' AND table_name = '{tabla}'"
        ).fetchdf()
        print(f'{schema}.{tabla}:')
        for c in cols['column_name'].tolist()[:10]:
            print(f'  - {c}')
        if len(cols) > 10:
            print(f'  ... y {len(cols) - 10} columnas mas')
    except Exception as e:
        print(f'{schema}.{tabla}: NO ENCONTRADA — {str(e)[:60]}')

conn.close()
