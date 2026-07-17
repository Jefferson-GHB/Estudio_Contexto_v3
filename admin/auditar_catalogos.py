"""Audita consistencia entre tablas de catalogo_curado en DuckDB (post-ingesta)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import unicodedata
from config.database import get_conn

REPORT = []

def log(msg):
    print(msg)
    REPORT.append(msg)

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).upper().strip()

conn = get_conn()

# --- Check 1: mapeo_cinef_detallado_siet ---
log("=" * 60)
log("CHECK 1: catalogo_curado.mapeo_cinef_detallado_siet")
log("=" * 60)
db1 = conn.execute("SELECT COUNT(*) as n FROM catalogo_curado.mapeo_cinef_detallado_siet").fetchone()[0]
log(f"  Rows: {db1}")
log(f"  Status: {'OK' if db1 == 106 else 'WARN (' + str(db1) + ' != 106)'}")

# --- Check 2: mapeo_cinef_snies_codigo ---
log("")
log("=" * 60)
log("CHECK 2: catalogo_curado.mapeo_cinef_snies_codigo")
log("=" * 60)
db2 = conn.execute("SELECT COUNT(*) as n FROM catalogo_curado.mapeo_cinef_snies_codigo").fetchone()[0]
log(f"  Rows: {db2}")
log(f"  Status: {'OK' if db2 == 106 else 'WARN (' + str(db2) + ' != 106)'}")

# --- Check 3: NBC corregido vs original ---
log("")
log("=" * 60)
log("CHECK 3: catalogo_nbc_snies_corregido vs catalogo_nbc_snies")
log("=" * 60)
try:
    db3c = conn.execute("SELECT * FROM catalogo_curado.catalogo_nbc_snies_corregido").fetchdf()
    log(f"  Corregido: {len(db3c)} rows")
except Exception:
    log("  Corregido: NOT FOUND (run ingest script)")
    db3c = pd.DataFrame()

db3o = conn.execute("SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio FROM catalogo_curado.catalogo_nbc_snies").fetchdf()
log(f"  Original: {len(db3o)} rows")

if not db3c.empty:
    db3o['_n'] = db3o['NBC'].apply(norm)
    corrections = 0
    for _, r in db3c.iterrows():
        m = db3o[db3o['_n'] == norm(r['NBC'])]
        if m.empty:
            log(f"  ONLY CORRECTED: '{r['NBC']}'")
            corrections += 1
            continue
        if norm(m.iloc[0]['Area_Conocimiento']) != norm(r['AREA_CONOCIMIENTO']):
            corrections += 1
            log(f"  AREA '{r['NBC']}': orig='{m.iloc[0]['Area_Conocimiento']}' -> corr='{r['AREA_CONOCIMIENTO']}'")
        if norm(m.iloc[0]['CINE_Campo_Amplio']) != norm(r['CINE_Campo_Amplio']):
            corrections += 1
            log(f"  CINE '{r['NBC']}': orig='{m.iloc[0]['CINE_Campo_Amplio']}' -> corr='{r['CINE_Campo_Amplio']}'")
    log(f"  Corrections in effect: {corrections}")

# --- Check 4: mapeo_variables ---
log("")
log("=" * 60)
log("CHECK 4: catalogo_curado.mapeo_variables")
log("=" * 60)
db4 = conn.execute("""
    SELECT Eje, Dominio, COUNT(*) as n_vars, SUM(CASE WHEN Verificado THEN 1 ELSE 0 END) as verified
    FROM catalogo_curado.mapeo_dss_variables
    GROUP BY Eje, Dominio ORDER BY Eje, Dominio
""").fetchdf()
log(f"  Total variables: {db4['n_vars'].sum()}")
log(f"  Verified: {db4['verified'].sum()}")
for _, r in db4.iterrows():
    log(f"  {r['Eje']} / {r['Dominio']}: {r['n_vars']} vars ({r['verified']} verified)")

conn.close()

os.makedirs("scripts", exist_ok=True)
with open("scripts/audit_db_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(REPORT))
print(f"\nReport written to scripts/audit_db_report.txt")
