"""Diagnostico completo de calidad de datos en DuckDB """
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
from config.database import DUCKDB_PATH
from collections import defaultdict

conn = duckdb.connect(DUCKDB_PATH, read_only=True)

# ============================================================================
# 1. INVENTARIO GLOBAL
# ============================================================================
print("=" * 80)
print("  1. INVENTARIO GLOBAL — 53 esquemas, ~488 tablas")
print("=" * 80)

inventory = conn.execute("""
    SELECT schema_name, count(*) as n_tablas, 
           sum(estimated_size) as size_bytes
    FROM duckdb_tables() 
    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'main')
    GROUP BY schema_name
    ORDER BY size_bytes DESC
""").fetchdf()

total_tables = inventory['n_tablas'].sum()
total_size_mb = inventory['size_bytes'].sum() / (1024 * 1024)
print(f"Total: {total_tables} tablas, {total_size_mb:.0f} MB")
print(f"\n{'Schema':<35} {'Tablas':>7} {'Size MB':>10}")
print("-" * 55)
for _, row in inventory.iterrows():
    size_mb = row['size_bytes'] / (1024 * 1024)
    print(f"{row['schema_name']:<35} {row['n_tablas']:>7} {size_mb:>10.1f}")

# ============================================================================
# 2. NULOS — Tasa por columna en tablas principales
# ============================================================================
print("\n" + "=" * 80)
print("  2. TASA DE NULOS — Tablas criticas del dashboard")
print("=" * 80)

TABLAS_CRITICAS = [
    ('snies', 'snies_programas'),
    ('snies', 'snies_matriculados'),
    ('snies', 'snies_graduados'),
    ('snies', 'snies_inscritos'),
    ('snies', 'snies_admitidos'),
    ('snies', 'snies_matriculados_primer_curso'),
    ('siet', 'siet_programas'),
    ('tendencias_laborales', 'vacantes_ape_clean'),
    ('competencias', 'cuoc_conocimientos'),
    ('competencias', 'cuoc_destrezas'),
    ('conectividad', 'internet_fijo_accesos'),
    ('icfes_saber', 'icfes_saber_pro_resultados'),
    ('catalogo_curado', 'cualificaciones_men'),
    ('datos_complementarios', 'tendencia_vacantes_anual'),
]

for schema, tabla in TABLAS_CRITICAS:
    try:
        cols = conn.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='{tabla}'").fetchdf()
        total = conn.execute(f"SELECT count(*) FROM {schema}.{tabla}").fetchone()[0]
        if total == 0:
            print(f"\n  {schema}.{tabla}: VACIA")
            continue
        
        nulos_altos = []
        for col in cols['column_name']:
            n_null = conn.execute(f"SELECT count(*) FROM {schema}.{tabla} WHERE \"{col}\" IS NULL").fetchone()[0]
            pct = n_null / total * 100
            if pct > 5:
                nulos_altos.append((col, pct, n_null))
        
        if nulos_altos:
            print(f"\n  {schema}.{tabla} ({total:,} filas):")
            for col, pct, n_null in sorted(nulos_altos, key=lambda x: -x[1])[:5]:
                print(f"    {col:<40} {pct:>5.0f}% nulos ({n_null:,})")
        else:
            print(f"\n  {schema}.{tabla} ({total:,} filas): OK — <5% nulos en todas las columnas")
    except Exception as e:
        print(f"\n  {schema}.{tabla}: ERROR — {str(e)[:80]}")

# ============================================================================
# 3. DUPLICADOS — Filas repetidas en tablas principales
# ============================================================================
print("\n" + "=" * 80)
print("  3. DUPLICADOS — Filas repetidas (todas las columnas iguales)")
print("=" * 80)

for schema, tabla in TABLAS_CRITICAS[:8]:  # solo las mas importantes
    try:
        total = conn.execute(f"SELECT count(*) FROM {schema}.{tabla}").fetchone()[0]
        if total == 0:
            continue
        # Count distinct rows vs total
        cols = conn.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='{tabla}'").fetchdf()
        col_list = ', '.join(f'"{c}"' for c in cols['column_name'])
        distinct = conn.execute(f"SELECT count(*) FROM (SELECT DISTINCT {col_list} FROM {schema}.{tabla})").fetchone()[0]
        dupes = total - distinct
        if dupes > 0:
            print(f"  {schema}.{tabla}: {dupes:,} duplicados ({dupes/total*100:.1f}%) de {total:,}")
        else:
            print(f"  {schema}.{tabla}: OK — sin duplicados ({total:,} filas)")
    except Exception as e:
        print(f"  {schema}.{tabla}: ERROR — {str(e)[:60]}")

# ============================================================================
# 4. FRESCURA DE DATOS — Rangos de fechas/años
# ============================================================================
print("\n" + "=" * 80)
print("  4. FRESCURA — Año mas reciente en cada tabla temporal")
print("=" * 80)

# Tables known to have temporal columns
tablas_temporales = [
    ('snies.snies_matriculados', 'ANO'),
    ('snies.snies_graduados', 'ANO'),
    ('snies.snies_inscritos', 'ANO'),
    ('snies.snies_admitidos', 'ANO'),
    ('snies.snies_matriculados_primer_curso', 'ANO'),
    ('estadisticas_es.es_desercion_nivel', 'periodo'),
    ('tendencias_laborales.vacantes_ape_clean', None),  # no year col — check vacantes_2023/2024
    ('datos_complementarios.tendencia_vacantes_anual', 'ano'),
    ('datos_complementarios.tendencia_inscritos_anual', 'ano'),
    ('datos_complementarios.tendencia_colocados_anual', 'ano'),
    ('icfes_saber.icfes_saber_pro_resultados', 'periodo'),
    ('datos_complementarios.graduados_nbc_ano', 'anio'),
]

for full_name, col in tablas_temporales:
    schema, tabla = full_name.split('.')
    try:
        if col:
            minmax = conn.execute(f'SELECT MIN("{col}") as min_val, MAX("{col}") as max_val FROM {full_name}').fetchone()
            print(f"  {full_name:<50} {col}: {minmax[0]} → {minmax[1]}")
        elif tabla == 'vacantes_ape_clean':
            # Special case: has vacantes_2023 and vacantes_2024 columns
            has_23 = conn.execute(f"SELECT count(*) FROM {full_name} WHERE CAST(vacantes_2023 AS DOUBLE) > 0").fetchone()[0]
            has_24 = conn.execute(f"SELECT count(*) FROM {full_name} WHERE CAST(vacantes_2024 AS DOUBLE) > 0").fetchone()[0]
            print(f"  {full_name:<50} años: 2023 ({has_23} ocupaciones), 2024 ({has_24} ocupaciones)")
    except Exception as e:
        print(f"  {full_name}: ERROR — {str(e)[:60]}")

# ============================================================================
# 5. NORMALIZACION — Consistencia de clasificadores
# ============================================================================
print("\n" + "=" * 80)
print("  5. NORMALIZACION — Consistencia de clasificadores (CINE-F, NBC, CUOC)")
print("=" * 80)

# Check NBC consistency: do all program NBCs exist in the NBC catalog?
try:
    nbcs_prog = conn.execute("""
        SELECT COUNT(DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO") 
        FROM snies.snies_programas 
        WHERE "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL
    """).fetchone()[0]
    
    nbcs_cat = conn.execute("""
        SELECT COUNT(DISTINCT NBC) FROM catalogo_curado.catalogo_nbc_snies
    """).fetchone()[0]
    
    print(f"  NBCs en programas SNIES: {nbcs_prog}")
    print(f"  NBCs en catalogo:        {nbcs_cat}")
    
    # Find NBCs in programs not in catalog
    huerfanos = conn.execute("""
        SELECT DISTINCT p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" as nbc
        FROM snies.snies_programas p
        WHERE p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM catalogo_curado.catalogo_nbc_snies c
            WHERE UPPER(c.NBC) = UPPER(p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO")
        )
        LIMIT 10
    """).fetchdf()
    if not huerfanos.empty:
        print(f"  NBCs huerfanos (en programas pero no en catalogo): {len(huerfanos)}")
        for nbc in huerfanos['nbc'].values[:5]:
            print(f"    - {nbc}")
    else:
        print(f"  NBCs huerfanos: 0 — todos los NBCs tienen entrada en catalogo")
except Exception as e:
    print(f"  Error NBC: {e}")

# Check CINE-F coverage in programs
try:
    cinef = conn.execute("""
        SELECT COUNT(DISTINCT "CINE_F_2013_AC_CAMPO_AMPLIO") as con_cinef,
               COUNT(*) as total,
               SUM(CASE WHEN "CINE_F_2013_AC_CAMPO_AMPLIO" IS NULL THEN 1 ELSE 0 END) as sin_cinef
        FROM snies.snies_programas
    """).fetchone()
    print(f"\n  CINE-F Campo Amplio en programas: {cinef[0]} valores distintos")
    print(f"  Programas sin CINE-F: {cinef[2]:,} de {cinef[1]:,} ({cinef[2]/cinef[1]*100:.1f}%)")
except Exception as e:
    print(f"  Error CINE-F: {e}")

# ============================================================================
# 6. TIPOS DE DATO — Columnas VARCHAR que deberian ser numericas
# ============================================================================
print("\n" + "=" * 80)
print("  6. TIPOS DE DATO — Columnas VARCHAR en tablas numericas")
print("=" * 80)

# The DB has all VARCHAR columns — this is a DuckDB import artifact.
# Check if numeric columns can actually be cast.
tablas_numericas = [
    ('snies.snies_matriculados', 'MATRICULADOS'),
    ('snies.snies_graduados', 'GRADUADOS'),
    ('snies.snies_inscritos', 'INSCRITOS'),
    ('snies.snies_admitidos', 'ADMITIDOS'),
    ('icfes_saber.icfes_saber_pro_resultados', 'total_17'),
]

for full_name, col in tablas_numericas:
    schema, tabla = full_name.split('.')
    try:
        total = conn.execute(f"SELECT count(*) FROM {full_name}").fetchone()[0]
        ok = conn.execute(f"""
            SELECT count(*) FROM {full_name} 
            WHERE "{col}" IS NOT NULL 
            AND "{col}" != '' 
            AND "{col}" != '0'
            AND TRY_CAST("{col}" AS DOUBLE) IS NOT NULL
        """).fetchone()[0]
        bad = conn.execute(f"""
            SELECT count(*) FROM {full_name}
            WHERE "{col}" IS NOT NULL 
            AND "{col}" != ''
            AND TRY_CAST("{col}" AS DOUBLE) IS NULL
        """).fetchone()[0]
        non_null = total - conn.execute(f"SELECT count(*) FROM {full_name} WHERE \"{col}\" IS NULL OR \"{col}\" = ''").fetchone()[0]
        if bad > 0:
            print(f"  {full_name}.{col}: {bad:,}/{non_null:,} valores NO casteables a DOUBLE ({bad/non_null*100:.2f}%)")
        else:
            print(f"  {full_name}.{col}: OK — {ok:,} valores numericos validos de {non_null:,} no nulos")
    except Exception as e:
        print(f"  {full_name}: ERROR — {str(e)[:60]}")

# ============================================================================
# 7. VOLUMEN — Tablas mas grandes y mas pequeñas
# ============================================================================
print("\n" + "=" * 80)
print("  7. VOLUMEN — Top 10 tablas mas pesadas")
print("=" * 80)

top_heavy = conn.execute("""
    SELECT schema_name || '.' || table_name as full_name, 
           estimated_size / (1024*1024) as size_mb
    FROM duckdb_tables()
    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'main')
    ORDER BY estimated_size DESC
    LIMIT 10
""").fetchdf()

for _, row in top_heavy.iterrows():
    print(f"  {row['full_name']:<60} {row['size_mb']:>8.1f} MB")

# ============================================================================
# 8. RESUMEN
# ============================================================================
print("\n" + "=" * 80)
print("  8. RESUMEN DE CALIDAD")
print("=" * 80)

conn.close()
