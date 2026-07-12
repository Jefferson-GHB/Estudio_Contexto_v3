# [S1] Sub-fase 0: Auditoría CSV ↔ DB

**Objetivo**: Detectar divergencias entre catálogos en `_CATALOGO_CURADO/*.csv` y sus equivalentes en DuckDB antes de migrar.

**Script**: `scripts/auditar_catalogos.py` (solo lectura, no modifica nada)

**Chequeos**:
1. `mapeo_cinef_detallado_siet` (CSV 106 filas) vs `catalogo_curado.mapeo_cinef_detallado_siet` (tabla DB) — comparar IDs, CINE_F_Campo_Detallado, Area_Desempeno_SIET. Reportar filas faltantes o con valores distintos.
2. `mapeo_cinef_snies_codigo` (CSV 106 filas) vs `catalogo_curado.mapeo_cinef_snies_codigo` — comparar CINE_F_SNIES, CODIGO_CINE_F, CAMPO_AMPLIO.
3. `CATALOGO_NBC_SNIES_CORREGIDO.csv` (57 filas) vs `catalogo_curado.catalogo_nbc_snies` — para cada NBC del CSV corregido, mostrar el valor actual en DB y el valor corregido (AREA_CONOCIMIENTO, CINE_Campo_Amplio). Esto identifica exactamente qué NBCs tienen errores.
4. Los 11 mapeos hardcodeados en `ml_matching_snies_etdh.py:112-125` — verificar contra `catalogo_curado.mapeo_cinef_detallado_siet` + `mapeo_cinef_snies_codigo` vía JOIN. ¿Hay Campos Amplios sin cobertura en las tablas DB?

**Output**: `scripts/audit_diff_report.txt` con hallazgos concretos. Sin opiniones, solo datos.

**Riesgo**: Cero. Solo lectura, no modifica código ni datos.

---

# [S2] Fase 1a: Eliminar pandas del bridge

**Problema**: `_load_cinef_to_siet_mapping()` (L59-132 de `ml_matching_snies_etdh.py`) carga 2 CSVs con `pd.read_csv()`, hace JOIN en Python, cachea en variable global `_cinef_to_siet_cache`, y tiene 11 mapeos hardcodeados como fallback. Pero `get_siet_areas_from_campos_amplios()` (L276-377) ya hace exactamente lo mismo vía SQL puro contra las tablas DB.

**Cambios en `ml_matching_snies_etdh.py`**:

1. **Eliminar**: función `_load_cinef_to_siet_mapping()` completa (~75 líneas), variable global `_cinef_to_siet_cache`, imports de `os`, `Path` (si no se usan en otro lado).
2. **Reemplazar** único call site en `_resolve_structural_chain()` L249-260:
   ```python
   # ANTES:
   cinef_siet = _load_cinef_to_siet_mapping()
   siet_areas = cinef_siet.get(cine, [])
   if not siet_areas:
       for k, v in cinef_siet.items():
           if _normalize_text(k) == cine_norm_val:
               siet_areas = v
               break

   # DESPUÉS:
   siet_areas = _query_siet_areas_from_campo_amplio(cine, conn)
   ```
3. **Nueva helper `_query_siet_areas_from_campo_amplio(campo_amplio, conn)`**: JOIN SQL directo entre `mapeo_cinef_snies_codigo` y `mapeo_cinef_detallado_siet`, mismo patrón que `get_siet_areas_from_campos_amplios()` pero para un solo campo amplio. Reutiliza `_normalize_text()` para matching fuzzy.

**Archivos tocados**:
- `ml_matching_snies_etdh.py` — solo este archivo
- `_CATALOGO_CURADO/MAPEO_CINEF_DETALLADO_SIET.csv` y `MAPEO_CINEF_SNIES_CODIGO.csv` — ya no son necesarios para el runtime (se mantienen como referencia histórica)

**Riesgo**: Bajo. La consulta SQL usa las mismas tablas que `get_siet_areas_from_campos_amplios()`, que ya funciona en producción.

---

# [S3] Fase 1b: Cargar NBCs corregidos a DuckDB

**Problema**: `CATALOGO_NBC_SNIES_CORREGIDO.csv` (57 filas) contiene correcciones a mapeos NBC→Área→CINE-F que `catalogo_curado.catalogo_nbc_snies` tiene erróneos. El CSV nunca fue ingerido.

**Script de ingesta**: `scripts/ingestar_nbc_corregido.py`
1. Crea tabla `catalogo_curado.catalogo_nbc_snies_corregido`:
   ```sql
   CREATE TABLE catalogo_curado.catalogo_nbc_snies_corregido (
       ID_NBC INTEGER,
       NBC VARCHAR,
       AREA_CONOCIMIENTO VARCHAR,
       CINE_Campo_Amplio VARCHAR,
       Programas_Count INTEGER
   )
   ```
2. Inserta las 57 filas del CSV.

**Cambios en `ml_matching_snies_etdh.py`** (`_resolve_structural_chain`, PASO 1, ~L176-201):

```python
# ANTES: solo busca en catalogo_nbc_snies
df_nbc = conn.execute("""
    SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio
    FROM catalogo_curado.catalogo_nbc_snies
""").fetchdf()

# DESPUÉS: prioriza corregido, fallback a original
df_nbc = conn.execute("""
    SELECT NBC, AREA_CONOCIMIENTO as Area_Conocimiento, CINE_Campo_Amplio
    FROM catalogo_curado.catalogo_nbc_snies_corregido
    WHERE NBC = ?
""", [nbc_nombre]).fetchdf()

if df_nbc.empty:
    df_nbc = conn.execute("""
        SELECT NBC, Area_Conocimiento, CINE_Campo_Amplio
        FROM catalogo_curado.catalogo_nbc_snies
    """).fetchdf()
    # ... matching fuzzy existente
    used_corrected = False
else:
    used_corrected = True

print(f"[Structural] NBC '{nbc_nombre}' -> corrected={used_corrected}, CINE={cine}")
```

**Archivos tocados**:
- `scripts/ingestar_nbc_corregido.py` (nuevo)
- `ml_matching_snies_etdh.py` (PASO 1 de `_resolve_structural_chain`)

**Riesgo**: Bajo. La tabla corregida es un subconjunto (57 de 350+ NBCs). Si un NBC no está en ella, se usa la tabla original como fallback.

---

# [S4] Verificación

Después de implementar S1-S3:

1. `python scripts/auditar_catalogos.py` — confirmar que los diffs detectados en S0 se resolvieron
2. `python -m tests.test_queries` — 50 tests deben pasar (0 FAIL)
3. Smoke test manual: abrir Streamlit, seleccionar "Ingeniería de sistemas, telemática y afines", verificar que:
   - El puente estructural deriva áreas SIET
   - El bridge ML (si disponible) encuentra programas SIET
   - La sección "Puente de Competencias" muestra datos coherentes
