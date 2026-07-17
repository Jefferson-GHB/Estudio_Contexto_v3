"""Compact the DuckDB database by exporting to a fresh file."""
import duckdb
import os

db_path = r'D:\UniSabana_Dev\Estudio_Contexto\repositorio.duckdb'
new_path = db_path + '.compact'

print(f'Before: {os.path.getsize(db_path)/(1024*1024):.1f} MB')

src = duckdb.connect(db_path, read_only=True)
dst = duckdb.connect(new_path)

# Attach source
dst.execute(f"ATTACH '{db_path}' AS src (READ_ONLY)")

# Get all schemas and tables
schemas = src.sql("SELECT DISTINCT schema_name FROM duckdb_tables()").fetchall()

for (schema,) in schemas:
    dst.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    tables = src.sql(f"SELECT table_name FROM duckdb_tables() WHERE schema_name = '{schema}'").fetchall()
    for (table,) in tables:
        print(f'  {schema}.{table}...', end=' ', flush=True)
        try:
            dst.execute(f'CREATE TABLE "{schema}"."{table}" AS SELECT * FROM src."{schema}"."{table}"')
            count = dst.sql(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]
            print(f'{count} rows')
        except Exception as e:
            print(f'ERROR: {e}')

src.close()
dst.close()

new_size = os.path.getsize(new_path) / (1024*1024)
print(f'\nAfter compact: {new_size:.1f} MB')

# Replace original
if new_size < os.path.getsize(db_path) / (1024*1024):
    os.replace(new_path, db_path)
    print(f'Replaced original. Final size: {os.path.getsize(db_path)/(1024*1024):.1f} MB')
else:
    os.remove(new_path)
    print('Compact file is not smaller, keeping original.')
