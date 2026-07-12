"""Corrige los 7 errores detectados en el mapeo DSS (audit Aug 2026)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
from config.database import DUCKDB_PATH

FIXES = [
    # 1-2. colocados/inscritos: usar tablas consolidadas con nombres de columna reales
    ("colocados_historico", "datos_complementarios", "tendencia_colocados_anual", "colocados"),
    ("inscritos_historico", "datos_complementarios", "tendencia_inscritos_anual", "inscritos"),
    # 3-4. vacantes: mismas tablas consolidadas
    ("vacantes_departamento", "datos_complementarios", "tendencia_vacantes_anual", "ocupacion"),
    ("vacantes_historico", "datos_complementarios", "tendencia_vacantes_anual", "vacantes"),
    # 5-7. cobertura: schema competencias_tic no existe, real es conectividad
    ("cobertura_4g", "conectividad", "cobertura_movil_tecnologia", "cobertuta_4g"),
    ("cobertura_4g_detalle", "conectividad", "cobertura_movil_tecnologia", "cobertura_lte"),
    ("proveedor_movil", "conectividad", "cobertura_movil_tecnologia", "cobertura_5g"),
]

conn = duckdb.connect(DUCKDB_PATH, read_only=False)

for var_id, new_schema, new_tabla, new_col in FIXES:
    old = conn.execute(f"SELECT Schema, Tabla, Columna_Principal FROM catalogo_curado.mapeo_dss_variables WHERE ID_Variable='{var_id}'").fetchone()
    old_s = old[0]
    old_t = old[1]
    old_c = old[2]
    conn.execute(f"""
        UPDATE catalogo_curado.mapeo_dss_variables
        SET Schema='{new_schema}', Tabla='{new_tabla}', Columna_Principal='{new_col}',
            Nota=COALESCE(Nota,'') || ' | Corregido 2026-07: schema/tabla original era errónea ({old_s}.{old_t}.{old_c})'
        WHERE ID_Variable='{var_id}'
    """)
    print(f"  FIXED [{var_id}]: {old_s}.{old_t}.{old_c} -> {new_schema}.{new_tabla}.{new_col}")

# Verify
print(f"\nVerifying {len(FIXES)} fixes...")
for var_id, s, t, c in FIXES:
    r = conn.execute(f"SELECT Schema, Tabla, Columna_Principal FROM catalogo_curado.mapeo_dss_variables WHERE ID_Variable='{var_id}'").fetchone()
    s2, t2, c2 = r[0], r[1], r[2]
    ok = "OK" if (s2, t2, c2) == (s, t, c) else "FAIL"
    print(f"  [{var_id}] {ok}: {s2}.{t2}.{c2}")

conn.close()
print("Done.")
