"""
Exploracion rapida de la estructura de tablas SNIES en DuckDB.
===============================================================

Lista columnas, rango de años y ejemplos de NBC para las 5 tablas
principales del ciclo estudiantil (inscritos, admitidos, primer curso,
matriculados, graduados). Util para verificar que la DB contiene los
datos esperados antes de ejecutar el dashboard.

Recuperado de UniSabana_Dev. La ruta original apuntaba a repositorio_hf.duckdb
(version legacy de HuggingFace). Se actualizo al resolvedor automatico.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import DUCKDB_PATH
import duckdb

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

TABLAS_CICLO = [
    'snies.snies_inscritos',
    'snies.snies_admitidos',
    'snies.snies_matriculados_primer_curso',
    'snies.snies_graduados',
    'snies.snies_matriculados',
]

for tabla in TABLAS_CICLO:
    print(f"\n{'=' * 60}")
    print(f"  {tabla}")
    print('=' * 60)

    # Columnas
    cols = conn.execute(f"DESCRIBE {tabla}").fetchdf()
    print("\n  Columnas:")
    print(cols[['column_name', 'column_type']].to_string(index=False))

    # Rango de años
    print("\n  Rango de años:")
    try:
        anos = conn.execute(
            f'SELECT MIN("ANO") as min_ano, MAX("ANO") as max_ano, COUNT(*) as registros '
            f'FROM {tabla}'
        ).fetchdf()
        print(anos.to_string(index=False))
    except Exception:
        print("  Error al consultar años")

    # Muestra de NBCs
    print("\n  Ejemplos de NBC:")
    try:
        nbcs = conn.execute(
            f'SELECT DISTINCT "NBC" FROM {tabla} WHERE "NBC" IS NOT NULL LIMIT 5'
        ).fetchdf()
        for nbc in nbcs['NBC'].values:
            print(f"    - {nbc}")
    except Exception:
        print("  Error al consultar NBCs")

conn.close()
