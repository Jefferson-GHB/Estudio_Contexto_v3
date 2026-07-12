"""Ingesta CATALOGO_NBC_SNIES_CORREGIDO.csv → catalogo_curado.catalogo_nbc_snies_corregido."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import duckdb
from config.database import DUCKDB_PATH

csv_path = os.path.join(os.path.dirname(__file__), "..", "catalogo", "CATALOGO_NBC_SNIES_CORREGIDO.csv")
df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} rows from {csv_path}")
print(f"Columns: {list(df.columns)}")

# Connect with WRITE access
conn = duckdb.connect(DUCKDB_PATH, read_only=False)

# Drop existing table if any
conn.execute("DROP TABLE IF EXISTS catalogo_curado.catalogo_nbc_snies_corregido")

# Create table
conn.execute("""
    CREATE TABLE catalogo_curado.catalogo_nbc_snies_corregido (
        ID_NBC INTEGER,
        NBC VARCHAR,
        AREA_CONOCIMIENTO VARCHAR,
        CINE_Campo_Amplio VARCHAR,
        Programas_Count INTEGER
    )
""")

# Insert rows
for _, row in df.iterrows():
    conn.execute("""
        INSERT INTO catalogo_curado.catalogo_nbc_snies_corregido
        (ID_NBC, NBC, AREA_CONOCIMIENTO, CINE_Campo_Amplio, Programas_Count)
        VALUES (?, ?, ?, ?, ?)
    """, [
        int(row['ID_NBC']),
        str(row['NBC']),
        str(row['AREA_CONOCIMIENTO']),
        str(row['CINE_Campo_Amplio']),
        int(row['Programas_Count'])
    ])

# Verify
count = conn.execute("SELECT COUNT(*) FROM catalogo_curado.catalogo_nbc_snies_corregido").fetchone()[0]
print(f"Ingested {count} rows into catalogo_curado.catalogo_nbc_snies_corregido")

# Show sample
sample = conn.execute("SELECT * FROM catalogo_curado.catalogo_nbc_snies_corregido LIMIT 5").fetchdf()
print(sample.to_string())

conn.close()
print("Done.")
