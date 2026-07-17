"""
Compacta la base de datos DuckDB exportando a un archivo nuevo optimizado.
=====================================================================

Util cuando la DB crece por operaciones de escritura frecuentes (ingestas,
actualizaciones de catalogos) y el almacenamiento interno se fragmenta.
El proceso ATTACH + CREATE TABLE AS SELECT reconstruye cada tabla en un
archivo limpio, eliminando espacio muerto.

ADVERTENCIA: Requiere acceso de escritura a la DB. Ejecutar con la app
detenida. Si el archivo compactado no es mas pequeño, se descarta.

Recuperado de UniSabana_Dev (v2 pre-refactorizacion). Las rutas absolutas
originales apuntaban a D:\UniSabana_Dev\... — se reemplazaron por el
resolvedor automatico de config/database.py.
"""

import os
from config.database import DUCKDB_PATH

# ============================================================================
# COMPACTAR — Reconstruye todas las tablas en una DB nueva optimizada  
# ============================================================================

def compactar_db(original_path=DUCKDB_PATH):
    db_path = original_path
    new_path = db_path + '.compact'

    print(f'Antes: {os.path.getsize(db_path)/(1024*1024):.1f} MB')

    src = duckdb.connect(db_path, read_only=True)
    dst = duckdb.connect(new_path)

    dst.execute(f"ATTACH '{db_path}' AS src (READ_ONLY)")

    schemas = src.sql("SELECT DISTINCT schema_name FROM duckdb_tables()").fetchall()

    for (schema,) in schemas:
        dst.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        tables = src.sql(
            f"SELECT table_name FROM duckdb_tables() WHERE schema_name = '{schema}'"
        ).fetchall()
        for (table,) in tables:
            print(f'  {schema}.{table}...', end=' ', flush=True)
            try:
                dst.execute(
                    f'CREATE TABLE "{schema}"."{table}" AS '
                    f'SELECT * FROM src."{schema}"."{table}"'
                )
                count = dst.sql(
                    f'SELECT count(*) FROM "{schema}"."{table}"'
                ).fetchone()[0]
                print(f'{count} filas')
            except Exception as e:
                print(f'ERROR: {e}')

    src.close()
    dst.close()

    new_size = os.path.getsize(new_path) / (1024 * 1024)
    print(f'\nDespues de compactar: {new_size:.1f} MB')

    if new_size < os.path.getsize(db_path) / (1024 * 1024):
        os.replace(new_path, db_path)
        print(f'Original reemplazada. Tamaño final: {os.path.getsize(db_path)/(1024*1024):.1f} MB')
    else:
        os.remove(new_path)
        print('El archivo compactado no es mas pequeño. Se conserva el original.')


if __name__ == "__main__":
    import duckdb
    compactar_db()
