"""Ingesta del mapeo de variables (catalogo/MAPEO_DSS_OFICIAL.csv) a catalogo_curado.mapeo_variables."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import duckdb
from config.database import DUCKDB_PATH

csv_path = os.path.join(os.path.dirname(__file__), "..", "catalogo", "MAPEO_DSS_OFICIAL.csv")
df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

conn = duckdb.connect(DUCKDB_PATH, read_only=False)

conn.execute("DROP TABLE IF EXISTS catalogo_curado.mapeo_dss_variables")
conn.execute("""
    CREATE TABLE catalogo_curado.mapeo_dss_variables (
        Eje VARCHAR,
        Dominio VARCHAR,
        ID_Variable VARCHAR,
        Nombre_Variable VARCHAR,
        Schema VARCHAR,
        Tabla VARCHAR,
        Columna_Principal VARCHAR,
        Tipo_Cruce VARCHAR,
        Cruce_Via VARCHAR,
        Nota VARCHAR,
        Verificado BOOLEAN
    )
""")

for _, row in df.iterrows():
    conn.execute("""
        INSERT INTO catalogo_curado.mapeo_dss_variables
        (Eje, Dominio, ID_Variable, Nombre_Variable, Schema, Tabla, Columna_Principal, Tipo_Cruce, Cruce_Via, Nota, Verificado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        str(row['Eje']),
        str(row['Dominio']),
        str(row['ID_Variable']),
        str(row['Nombre_Variable']),
        str(row['Schema']),
        str(row['Tabla']),
        str(row['Columna_Principal']),
        str(row['Tipo_Cruce']),
        str(row.get('Cruce_Via', '')) if pd.notna(row.get('Cruce_Via')) else '',
        str(row.get('Nota', '')) if pd.notna(row.get('Nota')) else '',
        bool(row.get('Verificado', False))
    ])

count = conn.execute("SELECT COUNT(*) FROM catalogo_curado.mapeo_dss_variables").fetchone()[0]
print(f"Ingested {count} rows")

sample = conn.execute("SELECT Eje, Dominio, ID_Variable, Verificado FROM catalogo_curado.mapeo_dss_variables LIMIT 5").fetchdf()
print(sample.to_string())

conn.close()
print("Done.")
