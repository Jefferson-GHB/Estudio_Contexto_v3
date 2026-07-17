"""Audita veracidad del mapeo de variables: schema/tabla/columna existen, cruces coherentes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import duckdb
from config.database import DUCKDB_PATH

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

mapeo = conn.execute("SELECT * FROM catalogo_curado.mapeo_dss_variables ORDER BY Eje, Dominio, ID_Variable").fetchdf()
tables_df = conn.execute("""
    SELECT table_schema, table_name, column_name
    FROM information_schema.columns
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY 1, 2, 3
""").fetchdf()

real_tables = set(zip(tables_df['table_schema'], tables_df['table_name']))
real_columns = set(zip(tables_df['table_schema'], tables_df['table_name'], tables_df['column_name']))

# Build lookup: (schema, tabla) -> list of columns
schema_tables = {}
for (s, t, c) in real_columns:
    schema_tables.setdefault((s, t), []).append(c)

errors = []
warnings = []
stats = {}

for _, r in mapeo.iterrows():
    eje = r['Eje']
    vid = r['ID_Variable']
    nombre = r['Nombre_Variable']
    schema = str(r['Schema']).strip() if pd.notna(r['Schema']) else None
    tabla = str(r['Tabla']).strip() if pd.notna(r['Tabla']) else None
    col = str(r['Columna_Principal']).strip() if pd.notna(r['Columna_Principal']) else None
    cruce = str(r['Cruce_Via']).strip() if pd.notna(r['Cruce_Via']) else None
    tipo = str(r['Tipo_Cruce']).strip() if pd.notna(r['Tipo_Cruce']) else None

    stats.setdefault(eje, {"total": 0, "con_tabla": 0, "sin_tabla": 0, "ok": 0, "err": 0})
    stats[eje]["total"] += 1

    # Variables without schema+tabla = LLM/CALC generated (not in DB)
    if not schema or not tabla or schema == 'nan' or tabla == 'nan' or schema == '' or tabla == '':
        stats[eje]["sin_tabla"] += 1
        continue

    stats[eje]["con_tabla"] += 1

    # Check table exists
    if (schema, tabla) not in real_tables:
        errors.append(f"[{vid}] TABLE MISSING: {schema}.{tabla} ({nombre})")
        stats[eje]["err"] += 1
        continue

    avail_cols = schema_tables.get((schema, tabla), [])

    # Check column
    if col and col != 'nan' and (schema, tabla, col) not in real_columns:
        avail_casefold = {c.upper(): c for c in avail_cols}
        col_upper = col.upper()
        if col_upper in avail_casefold:
            real_name = avail_casefold[col_upper]
            warnings.append(f"[{vid}] COLUMN CASE: {schema}.{tabla}.{col} -> real: '{real_name}' ({nombre})")
        else:
            errors.append(f"[{vid}] COLUMN MISSING: {schema}.{tabla}.{col} ({nombre}). Available: {avail_cols[:5]}...")
            stats[eje]["err"] += 1
            continue

    # Check cruce consistency
    if cruce and cruce != 'nan':
        if cruce == 'NBC':
            snies_tbls = {'snies_programas', 'snies_matriculados', 'snies_graduados',
                        'snies_inscritos', 'snies_admitidos', 'snies_matriculados_primer_curso',
                        'catalogo_nbc_snies'}
            if tabla not in snies_tbls:
                warnings.append(f"[{vid}] CRUCE_VIA=NBC but tabla='{tabla}' ({nombre})")

    # Check tipo_cruce
    if tipo:
        if tipo == 'LLAVE_PRINCIPAL' and col:
            if not any(kw in col.upper() for kw in ['CODIGO', 'SNIES', 'ID_', 'NBC']):
                warnings.append(f"[{vid}] LLAVE_PRINCIPAL with unusual col: {col} ({nombre})")
        if tipo == 'DATO' and cruce and cruce != 'nan':
            warnings.append(f"[{vid}] DATO type has Cruce_Via={cruce} ({nombre})")

    stats[eje]["ok"] += 1

# Report
print("=" * 70)
print("AUDITORIA MAPEO DE VARIABLES — Veracidad de esquemas y cruces")
print("=" * 70)
for eje, s in sorted(stats.items()):
    bar = "OK" if s["err"] == 0 and s["sin_tabla"] == 0 else f"{s['err']} ERR" if s['err'] else f"{s['sin_tabla']} SIN_TABLA"
    print(f"  {eje}: {s['total']} vars | {s['ok']} OK | {s['con_tabla']} c/tabla | {bar}")

print(f"\n--- ERRORES ({len(errors)}) ---")
for e in errors:
    print(f"  {e}")

print(f"\n--- ADVERTENCIAS ({len(warnings)}) ---")
for w in warnings:
    print(f"  {w}")

print(f"\n--- SIN TABLA/SCHEMA (generadas por LLM o CALC) ---")
sin = mapeo[mapeo['Schema'].isna() | (mapeo['Schema'] == 'nan') | (mapeo['Schema'] == '')]
if not sin.empty:
    for _, r in sin.iterrows():
        nota = str(r['Nota'])[:100] if pd.notna(r['Nota']) else '(sin nota)'
        print(f"  [{r['ID_Variable']}] {r['Nombre_Variable']} — {nota}")
else:
    print("  (ninguna)")

conn.close()
