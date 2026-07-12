# Ingesta de Catálogos y Unificación del Bridge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar dependencia de pandas para carga de CSVs en el bridge SNIES↔SIET, ingerir NBCs corregidos a DuckDB, y auditar divergencias entre catálogos.

**Architecture:** Los catálogos `mapeo_cinef_detallado_siet` y `mapeo_cinef_snies_codigo` ya existen en `catalogo_curado.*` de DuckDB pero el código los ignora y recarga vía pandas. Se elimina la función de carga y se reemplaza con SQL directo. Se ingiere `CATALOGO_NBC_SNIES_CORREGIDO.csv` como tabla prioritaria en la cadena estructural.

**Tech Stack:** Python 3.13, DuckDB, Streamlit, pandas (solo para auditoría y script de ingesta, no en runtime)

## Global Constraints

- 50 tests existentes deben seguir pasando (0 FAIL)
- Conexión a DuckDB siempre read-only excepto en script de ingesta
- No romper `get_siet_areas_from_campos_amplios()` — ya usa SQL correcto
- El bridge ML (`match_nbc_to_siet`, `get_skills_bridge_analysis`) debe seguir funcionando igual

---

### Task 1: Script de auditoría CSV ↔ DB

**Covers:** [S0]

**Files:**
- Create: `scripts/auditar_catalogos.py`

**Interfaces:**
- Consumes: DuckDB (read-only), `_CATALOGO_CURADO/MAPEO_CINEF_DETALLADO_SIET.csv`, `_CATALOGO_CURADO/MAPEO_CINEF_SNIES_CODIGO.csv`, `_CATALOGO_CURADO/CATALOGO_NBC_SNIES_CORREGIDO.csv`
- Produces: `scripts/audit_diff_report.txt`

- [ ] **Step 1: Write the script**

```python
"""Audita divergencias entre CSVs en _CATALOGO_CURADO/ y sus equivalentes en DuckDB."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from config.database import get_conn

REPORT = []

def log(msg):
    print(msg)
    REPORT.append(msg)

conn = get_conn()

# --- Check 1: MAPEO_CINEF_DETALLADO_SIET.csv vs DB ---
log("=" * 60)
log("CHECK 1: MAPEO_CINEF_DETALLADO_SIET.csv vs catalogo_curado.mapeo_cinef_detallado_siet")
log("=" * 60)

csv1 = pd.read_csv("_CATALOGO_CURADO/MAPEO_CINEF_DETALLADO_SIET.csv")
db1 = conn.execute("SELECT * FROM catalogo_curado.mapeo_cinef_detallado_siet ORDER BY ID").fetchdf()

log(f"  CSV rows: {len(csv1)}")
log(f"  DB rows:  {len(db1)}")

csv_ids = set(csv1['ID'].astype(int).tolist())
db_ids = set(db1['ID'].astype(int).tolist())
only_csv = csv_ids - db_ids
only_db = db_ids - csv_ids
if only_csv:
    log(f"  In CSV but NOT in DB: {sorted(only_csv)}")
if only_db:
    log(f"  In DB but NOT in CSV: {sorted(only_db)}")

diff_count = 0
for _, row in csv1.iterrows():
    rid = int(row['ID'])
    db_row = db1[db1['ID'] == rid]
    if db_row.empty:
        continue
    csv_detallado = str(row['CINE_F_Campo_Detallado']).strip()
    csv_siet = str(row['Area_Desempeno_SIET']).strip()
    db_detallado = str(db_row.iloc[0]['CINE_F_Campo_Detallado']).strip()
    db_siet = str(db_row.iloc[0]['Area_Desempeno_SIET']).strip()
    diffs = []
    if csv_detallado != db_detallado:
        diffs.append(f"detallado CSV='{csv_detallado}' DB='{db_detallado}'")
    if csv_siet != db_siet:
        diffs.append(f"siet CSV='{csv_siet}' DB='{db_siet}'")
    if diffs:
        diff_count += 1
        log(f"  DIFF ID={rid}: {'; '.join(diffs)}")

if diff_count == 0:
    log("  Result: IDENTICAL (no differences)")
else:
    log(f"  Result: {diff_count} rows differ")

# --- Check 2: MAPEO_CINEF_SNIES_CODIGO.csv vs DB ---
log("")
log("=" * 60)
log("CHECK 2: MAPEO_CINEF_SNIES_CODIGO.csv vs catalogo_curado.mapeo_cinef_snies_codigo")
log("=" * 60)

csv2 = pd.read_csv("_CATALOGO_CURADO/MAPEO_CINEF_SNIES_CODIGO.csv")
db2 = conn.execute("SELECT * FROM catalogo_curado.mapeo_cinef_snies_codigo ORDER BY CINE_F_SNIES").fetchdf()

log(f"  CSV rows: {len(csv2)}")
log(f"  DB rows:  {len(db2)}")

csv_cinef = set(csv2['CINE_F_SNIES'].str.strip().tolist())
db_cinef = set(db2['CINE_F_SNIES'].str.strip().tolist())
only_csv2 = csv_cinef - db_cinef
only_db2 = db_cinef - csv_cinef
if only_csv2:
    log(f"  In CSV but NOT in DB: {sorted(only_csv2)}")
if only_db2:
    log(f"  In DB but NOT in CSV: {sorted(only_db2)}")

diff_count2 = 0
for _, row in csv2.iterrows():
    cs = str(row['CINE_F_SNIES']).strip()
    db_row = db2[db2['CINE_F_SNIES'].str.strip() == cs]
    if db_row.empty:
        continue
    csv_campo = str(row['CAMPO_AMPLIO']).strip()
    db_campo = str(db_row.iloc[0]['CAMPO_AMPLIO']).strip()
    if csv_campo != db_campo:
        diff_count2 += 1
        log(f"  DIFF CINE_F='{cs}': CSV CAMPO='{csv_campo}' DB CAMPO='{db_campo}'")

if diff_count2 == 0:
    log("  Result: IDENTICAL (no differences)")
else:
    log(f"  Result: {diff_count2} rows differ")

# --- Check 3: CATALOGO_NBC_SNIES_CORREGIDO.csv vs DB ---
log("")
log("=" * 60)
log("CHECK 3: CATALOGO_NBC_SNIES_CORREGIDO.csv vs catalogo_curado.catalogo_nbc_snies")
log("=" * 60)

csv3 = pd.read_csv("_CATALOGO_CURADO/CATALOGO_NBC_SNIES_CORREGIDO.csv")
db3 = conn.execute("SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio FROM catalogo_curado.catalogo_nbc_snies").fetchdf()

log(f"  CSV corregido rows: {len(csv3)}")
log(f"  DB rows: {len(db3)}")

import unicodedata
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).upper().strip()

db3['_norm'] = db3['NBC'].apply(norm)

corrections = 0
not_found = 0
for _, row in csv3.iterrows():
    nbc_name = row['NBC']
    nbc_norm = norm(nbc_name)
    db_match = db3[db3['_norm'] == nbc_norm]
    if db_match.empty:
        not_found += 1
        log(f"  NOT IN DB: '{nbc_name}' -> Area={row['AREA_CONOCIMIENTO']}, CINE={row['CINE_Campo_Amplio']}")
        continue
    db_area = str(db_match.iloc[0]['Area_Conocimiento']).strip()
    db_cine = str(db_match.iloc[0]['CINE_Campo_Amplio']).strip()
    csv_area = str(row['AREA_CONOCIMIENTO']).strip()
    csv_cine = str(row['CINE_Campo_Amplio']).strip()
    area_diff = norm(db_area) != norm(csv_area)
    cine_diff = norm(db_cine) != norm(csv_cine)
    if area_diff or cine_diff:
        corrections += 1
        parts = []
        if area_diff:
            parts.append(f"Area DB='{db_area}' -> CSV='{csv_area}'")
        if cine_diff:
            parts.append(f"CINE DB='{db_cine}' -> CSV='{csv_cine}'")
        log(f"  CORRECTED '{nbc_name}': {'; '.join(parts)}")

log(f"  Corrections needed: {corrections}")
log(f"  NBCs not in DB: {not_found}")

# --- Check 4: hardcoded fallbacks vs DB ---
log("")
log("=" * 60)
log("CHECK 4: Hardcoded fallbacks in ml_matching_snies_etdh.py vs DB tables")
log("=" * 60)

HARDCODED = {
    'ADMINISTRACION DE EMPRESAS Y DERECHO': ['VENTAS Y SERVICIOS', 'FINANZAS Y ADMINISTRACION'],
    'AGROPECUARIO, SILVICULTURA, PESCA Y VETERINARIA': ['EXPLOTACION PRIMARIA Y EXTRACTIVA'],
    'ARTE Y HUMANIDADES': ['ARTE, CULTURA, ESPARCIMIENTO Y DEPORTES'],
    'ARTES Y HUMANIDADES': ['ARTE, CULTURA, ESPARCIMIENTO Y DEPORTES'],
    'CIENCIAS NATURALES, MATEMATICAS Y ESTADISTICA': ['CIENCIAS NATURALES APLICADAS Y RELACIONADAS'],
    'CIENCIAS SOCIALES, PERIODISMO E INFORMACION': ['CIENCIAS SOCIALES, EDUCATIVAS,RELIGIOSAS Y SERVICIOS GUBERNAMENTALES'],
    'EDUCACION': ['CIENCIAS SOCIALES, EDUCATIVAS,RELIGIOSAS Y SERVICIOS GUBERNAMENTALES'],
    'INGENIERIA, INDUSTRIA Y CONSTRUCCION': ['OFICIOS, OPERACION DE EQUIPO Y TRANSPORTE', 'CIENCIAS NATURALES APLICADAS Y RELACIONADAS', 'PROCESAMIENTO, FABRICACION Y ENSAMBLAJE'],
    'SALUD Y BIENESTAR': ['SALUD'],
    'SERVICIOS': ['VENTAS Y SERVICIOS', 'PROCESAMIENTO, FABRICACION Y ENSAMBLAJE', 'EXPLOTACION PRIMARIA Y EXTRACTIVA'],
    'TECNOLOGIAS DE LA INFORMACION Y LA COMUNICACION (TIC)': ['CIENCIAS NATURALES APLICADAS Y RELACIONADAS'],
}

db_siet_areas = conn.execute("""
    SELECT DISTINCT snies.CAMPO_AMPLIO, siet.Area_Desempeno_SIET
    FROM catalogo_curado.mapeo_cinef_snies_codigo snies
    JOIN catalogo_curado.mapeo_cinef_detallado_siet siet
        ON snies.CINE_F_SNIES = siet.CINE_F_Campo_Detallado
    ORDER BY snies.CAMPO_AMPLIO, siet.Area_Desempeno_SIET
""").fetchdf()

idx_mismatch = 0
for campo, expected in HARDCODED.items():
    db_rows = db_siet_areas[db_siet_areas['CAMPO_AMPLIO'].str.strip().str.upper() == campo.upper()]
    db_values = sorted(db_rows['Area_Desempeno_SIET'].str.strip().tolist()) if not db_rows.empty else []
    expected_sorted = sorted(expected)
    if db_values != expected_sorted:
        idx_mismatch += 1
        log(f"  MISMATCH '{campo}': hardcoded={expected_sorted}, DB={db_values}")

if idx_mismatch == 0:
    log("  Result: ALL hardcoded mappings match DB (fallback is redundant)")
else:
    log(f"  Result: {idx_mismatch} hardcoded mappings differ from DB")

conn.close()

# Write report
with open("scripts/audit_diff_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(REPORT))

print(f"\nReport written to scripts/audit_diff_report.txt")
```

- [ ] **Step 2: Run audit script**

```bash
python scripts/auditar_catalogos.py
```

Expected: script runs, generates `scripts/audit_diff_report.txt`. Review the report for actual divergences.

- [ ] **Step 3: Commit**

```bash
git add scripts/auditar_catalogos.py scripts/audit_diff_report.txt
git commit -m "audit: add CSVvsDB catalog divergence checker"
```

---

### Task 2: Eliminar `_load_cinef_to_siet_mapping()` — migrar a SQL

**Covers:** [S1a]

**Files:**
- Modify: `ml_matching_snies_etdh.py:54-55,59-132,249-260`

**Interfaces:**
- Consumes: `catalogo_curado.mapeo_cinef_snies_codigo`, `catalogo_curado.mapeo_cinef_detallado_siet` (tablas DuckDB), `get_siet_areas_from_campos_amplios()` pattern (L352-362)
- Produces: `_query_siet_areas_from_campo_amplio(campo_amplio, conn) -> List[str]`
- Deletes: `_load_cinef_to_siet_mapping()`, `_cinef_to_siet_cache`, `CATALOGO_DIR`, `MODULE_DIR` (si no usado en otro lado)

- [ ] **Step 1: Identify all imports and globals to remove**

Check `ml_matching_snies_etdh.py` for what depends on deleted code:

```bash
python -c "
# Verify no other usage of _load_cinef_to_siet_mapping
import ast
tree = ast.parse(open('ml_matching_snies_etdh.py', encoding='utf-8').read())
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == '_load_cinef_to_siet_mapping':
        print(f'Call at line {node.lineno}')
# Check _cinef_to_siet_cache usage
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id == '_cinef_to_siet_cache':
        print(f'_cinef_to_siet_cache at line {node.lineno}, ctx={type(node.ctx).__name__}')
"
```

- [ ] **Step 2: Delete function and global variable**

Remove lines 54-55 (globals), 59-132 (entire `_load_cinef_to_siet_mapping()` function).

Remove line 43-44 (if `MODULE_DIR` and `CATALOGO_DIR` are unused after deletion — check: `MODULE_DIR` is also used in `_load_cinef_to_siet_mapping` only, so safe to delete both lines 36-37 in imports).

```python
# Lines 36-37 to remove:
# MODULE_DIR = Path(__file__).parent
# CATALOGO_DIR = MODULE_DIR / "_CATALOGO_CURADO"
```

```python
# Lines 54-55 to remove:
# _cinef_to_siet_cache: Optional[Dict[str, List[str]]] = None
```

```python
# Lines 59-132: delete entire function _load_cinef_to_siet_mapping()
```

- [ ] **Step 3: Add `_query_siet_areas_from_campo_amplio()` helper**

Insert after line 55 (after remaining global caches) or near `get_siet_areas_from_campos_amplios()` (L276). Place it right before `_resolve_structural_chain()` for locality:

```python
def _query_siet_areas_from_campo_amplio(campo_amplio: str, conn) -> List[str]:
    """Obtiene areas SIET para un Campo Amplio via JOIN SQL directo."""
    if not campo_amplio:
        return []
    try:
        campo_norm = _normalize_text(campo_amplio)
        # Load all mappings and match in Python (same pattern as existing code)
        df = conn.execute("""
            SELECT DISTINCT snies.CAMPO_AMPLIO, siet.Area_Desempeno_SIET
            FROM catalogo_curado.mapeo_cinef_snies_codigo snies
            JOIN catalogo_curado.mapeo_cinef_detallado_siet siet
                ON snies.CINE_F_SNIES = siet.CINE_F_Campo_Detallado
            ORDER BY siet.Area_Desempeno_SIET
        """).fetchdf()
        if df.empty:
            return []
        # Normalize CAMPO_AMPLIO for matching
        df['_norm'] = df['CAMPO_AMPLIO'].apply(_normalize_text)
        matched = df[df['_norm'] == campo_norm]
        if matched.empty:
            # Fuzzy fallback
            for _, row in df.iterrows():
                if campo_norm in row['_norm'] or row['_norm'] in campo_norm:
                    matched = df[df['_norm'] == row['_norm']]
                    break
        return matched['Area_Desempeno_SIET'].unique().tolist() if not matched.empty else []
    except Exception as e:
        print(f"[Structural] Error querying SIET areas for '{campo_amplio}': {e}")
        return []
```

- [ ] **Step 4: Replace call site in `_resolve_structural_chain()` PASO 4**

Replace lines 249-260:

```python
# BEFORE (lines 249-260):
        # --- PASO 4: CINE -> Areas_Desempeno_SIET (via CSV mapping) ---
        cinef_siet = _load_cinef_to_siet_mapping()
        # Try exact match first
        siet_areas = cinef_siet.get(cine, [])
        if not siet_areas:
            # Try normalized match
            cine_norm_val = _normalize_text(cine)
            for k, v in cinef_siet.items():
                if _normalize_text(k) == cine_norm_val:
                    siet_areas = v
                    break
        result['areas_desempeno_siet'] = siet_areas
```

```python
# AFTER:
        # --- PASO 4: CINE -> Areas_Desempeno_SIET (via SQL) ---
        siet_areas = _query_siet_areas_from_campo_amplio(cine, conn)
        result['areas_desempeno_siet'] = siet_areas
```

- [ ] **Step 5: Verify tests still pass**

```bash
python -m tests.test_queries
```

Expected: 50 OK, 0 FAIL.

- [ ] **Step 6: Commit**

```bash
git add ml_matching_snies_etdh.py
git commit -m "refactor: replace pandas CSV load with SQL for SIET area mapping"
```

---

### Task 3: Ingerir `CATALOGO_NBC_SNIES_CORREGIDO.csv` a DuckDB

**Covers:** [S1b]

**Files:**
- Create: `scripts/ingestar_nbc_corregido.py`
- Modify: `ml_matching_snies_etdh.py:176-201` (PASO 1 of `_resolve_structural_chain`)

**Interfaces:**
- Consumes: `_CATALOGO_CURADO/CATALOGO_NBC_SNIES_CORREGIDO.csv`, DuckDB (write-enabled for ingestion, read-only for query)
- Produces: `catalogo_curado.catalogo_nbc_snies_corregido` (tabla DuckDB), modified `_resolve_structural_chain()` PASO 1

- [ ] **Step 1: Create ingestion script**

```python
"""Ingesta CATALOGO_NBC_SNIES_CORREGIDO.csv → catalogo_curado.catalogo_nbc_snies_corregido."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

csv_path = "_CATALOGO_CURADO/CATALOGO_NBC_SNIES_CORREGIDO.csv"
df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} rows from {csv_path}")
print(f"Columns: {list(df.columns)}")

# Connect to DuckDB
from config.database import get_conn
conn = get_conn()

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
```

- [ ] **Step 2: Run ingestion**

```bash
python scripts/ingestar_nbc_corregido.py
```

Expected: "Ingested 57 rows into catalogo_curado.catalogo_nbc_snies_corregido"

- [ ] **Step 3: Modify `_resolve_structural_chain()` PASO 1 to use corrected table first**

Replace lines 176-201:

```python
# BEFORE (lines 176-201):
        # --- PASO 1: NBC -> CINE_Campo_Amplio (tabla catalogo_nbc_snies) ---
        # Use Python-side accent-insensitive matching
        df_all_nbcs = conn.execute("""
            SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio
            FROM catalogo_curado.catalogo_nbc_snies
        """).fetchdf()

        df_nbc = pd.DataFrame()
        if not df_all_nbcs.empty:
            df_all_nbcs['_norm'] = df_all_nbcs['NBC'].apply(_normalize_text)
            # Exact normalized match
            mask = df_all_nbcs['_norm'] == nbc_norm
            if mask.any():
                df_nbc = df_all_nbcs[mask].drop(columns=['_norm']).head(1)
            else:
                # Partial match on first part before comma
                first_part = nbc_norm.split(',')[0].strip()
                if first_part:
                    mask2 = df_all_nbcs['_norm'].str.contains(first_part, na=False)
                    if mask2.any():
                        df_nbc = df_all_nbcs[mask2].drop(columns=['_norm']).head(1)

        if df_nbc.empty:
            print(f"[Structural] NBC '{nbc_nombre}' no encontrado en catalogo_nbc_snies")
            _structural_chain_cache[cache_key] = result
            return result

        result['cine_campo_amplio'] = df_nbc['CINE_Campo_Amplio'].iloc[0]
        result['area_conocimiento'] = df_nbc['Area_Conocimiento'].iloc[0]
```

```python
# AFTER:
        # --- PASO 1: NBC -> CINE_Campo_Amplio ---
        # Prioridad: tabla corregida (57 NBCs auditados), luego tabla original (fallback)
        df_nbc = pd.DataFrame()
        used_corrected = False

        # Intentar primero con tabla corregida
        try:
            df_corrected = conn.execute("""
                SELECT NBC, AREA_CONOCIMIENTO as Area_Conocimiento, CINE_Campo_Amplio
                FROM catalogo_curado.catalogo_nbc_snies_corregido
            """).fetchdf()
            if not df_corrected.empty:
                df_corrected['_norm'] = df_corrected['NBC'].apply(_normalize_text)
                mask = df_corrected['_norm'] == nbc_norm
                if mask.any():
                    df_nbc = df_corrected[mask].drop(columns=['_norm']).head(1)
                    used_corrected = True
        except Exception:
            pass  # Tabla corregida no existe aún, usar original

        # Fallback a tabla original
        if df_nbc.empty:
            df_all_nbcs = conn.execute("""
                SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio
                FROM catalogo_curado.catalogo_nbc_snies
            """).fetchdf()
            if not df_all_nbcs.empty:
                df_all_nbcs['_norm'] = df_all_nbcs['NBC'].apply(_normalize_text)
                mask = df_all_nbcs['_norm'] == nbc_norm
                if mask.any():
                    df_nbc = df_all_nbcs[mask].drop(columns=['_norm']).head(1)
                else:
                    first_part = nbc_norm.split(',')[0].strip()
                    if first_part:
                        mask2 = df_all_nbcs['_norm'].str.contains(first_part, na=False)
                        if mask2.any():
                            df_nbc = df_all_nbcs[mask2].drop(columns=['_norm']).head(1)

        if df_nbc.empty:
            print(f"[Structural] NBC '{nbc_nombre}' no encontrado en catalogo")
            _structural_chain_cache[cache_key] = result
            return result

        result['cine_campo_amplio'] = df_nbc['CINE_Campo_Amplio'].iloc[0]
        result['area_conocimiento'] = df_nbc['Area_Conocimiento'].iloc[0]
        print(f"[Structural] NBC '{nbc_nombre}' -> corrected={used_corrected}, "
              f"CINE={result['cine_campo_amplio']}")
```

- [ ] **Step 4: Verify tests still pass**

```bash
python -m tests.test_queries
```

Expected: 50 OK, 0 FAIL.

- [ ] **Step 5: Run audit script again to confirm fixes**

```bash
python scripts/auditar_catalogos.py
```

Expected: Check 3 now shows "NOT IN DB: 0" for all 57 NBCs (they now exist in `catalogo_nbc_snies_corregido`). Check 4 may still show mismatches if hardcoded fallbacks differ from DB (this is expected and will be addressed in Fase 3).

- [ ] **Step 6: Commit**

```bash
git add scripts/ingestar_nbc_corregido.py ml_matching_snies_etdh.py
git commit -m "feat: ingest corrected NBC catalog and prioritize in structural chain"
```

---

### Task 4: Verificación final

**Covers:** [S4]

**Files:**
- (none — verification only)

- [ ] **Step 1: Run full test suite**

```bash
python -m tests.test_queries
```

Expected: 50 OK, 0 FAIL.

- [ ] **Step 2: Run audit script**

```bash
python scripts/auditar_catalogos.py
```

Review output. All checks should show no critical divergences. Save final report.

- [ ] **Step 3: Verify syntax of modified files**

```bash
python -c "import ast; ast.parse(open('ml_matching_snies_etdh.py', encoding='utf-8').read()); print('ml_matching_snies_etdh.py: OK')"
```

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "verify: all tests pass, catalog audit clean after ingestion"
```
