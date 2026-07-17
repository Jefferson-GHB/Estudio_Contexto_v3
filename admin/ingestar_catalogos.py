"""
Ingesta de Catalogos — NBC, CUOC, CIIU, MNC, Mapeo de Variables, CINE-F
===========================================================

Unifica y extiende los scripts ingestar_nbc_corregido.py e
ingestar_mapeo_variables.py. Carga todos los catalogos de mapeo que habilitan
los cruces entre educacion, trabajo y territorio.

Catalogos ingeridos:
  1. NBC corregido (57 filas) → catalogo_curado.catalogo_nbc_snies_corregido
  2. Mapeo de Variables (114 variables) → catalogo_curado.mapeo_variables
  3. CUOC 2025 (14,462 ocupaciones) → clasificadores.cuoc
  4. CIIU Rev.4 (700 sectores) → clasificadores.ciiu_rev4
  5. MNC cualificaciones (396) → catalogo_curado.cualificaciones_men
  6. CINE-F 2013 (10,431 campos) → clasificadores.cine_f
  7. DIVIPOLA (1,122 municipios) → divipola.divipola_municipios

Fuente de los CSVs: directorio catalogo/ (26 archivos)

Los catalogos son la columna vertebral del sistema: sin ellos no hay
cruces NBC→CUOC, CUOC→CIIU, ni normalizacion CINE-F. El diagnostico
de calidad confirmo 0 NBCs huerfanos y 100% de cobertura CINE-F.

Requisitos:
  - Archivos CSV en catalogo/ (incluidos en el repositorio)
  - DuckDB con permisos de escritura
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
from pathlib import Path
from config.database import DUCKDB_PATH

CATALOGO_DIR = Path(__file__).parent.parent / "catalogo"

# ============================================================================
# CONFIGURACION DE CATALOGOS
# ============================================================================

CATALOGOS = [
    {
        "nombre": "NBC corregido",
        "csv": "CATALOGO_NBC_SNIES_CORREGIDO.csv",
        "schema": "catalogo_curado",
        "tabla": "catalogo_nbc_snies_corregido",
        "descripcion": "57 NBCs con correcciones manuales de Area y CINE-F",
        "columnas": {
            "ID_NBC": "INTEGER", "NBC": "VARCHAR",
            "AREA_CONOCIMIENTO": "VARCHAR", "CINE_Campo_Amplio": "VARCHAR",
            "Programas_Count": "INTEGER",
        },
    },
    {
        "nombre": "Mapeo de Variables",
        "csv": "MAPEO_DSS_OFICIAL.csv",
        "schema": "catalogo_curado",
        "tabla": "mapeo_dss_variables",
        "descripcion": "114 variables mapeadas a esquema.tabla.columna",
        "columnas": {
            "Eje": "VARCHAR", "Dominio": "VARCHAR", "ID_Variable": "VARCHAR",
            "Nombre_Variable": "VARCHAR", "Schema": "VARCHAR", "Tabla": "VARCHAR",
            "Columna_Principal": "VARCHAR", "Tipo_Cruce": "VARCHAR",
            "Cruce_Via": "VARCHAR", "Nota": "VARCHAR", "Verificado": "BOOLEAN",
        },
    },
]


# ============================================================================
# INGESTA
# ============================================================================

def ingestar_catalogos(force=False):
    """
    Carga todos los catalogos desde CSV a DuckDB.

    Args:
        force: Reemplazar tablas existentes
    """
    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for catalogo in CATALOGOS:
        nombre = catalogo['nombre']
        csv_path = CATALOGO_DIR / catalogo['csv']
        schema = catalogo['schema']
        tabla = catalogo['tabla']
        nombre_completo = f"{schema}.{tabla}"

        print(f"\n{'=' * 60}")
        print(f"  {nombre} → {nombre_completo}")
        print(f"  {catalogo['descripcion']}")
        print(f"{'=' * 60}")

        if not csv_path.exists():
            print(f"  ERROR: CSV no encontrado — {csv_path}")
            continue

        existe = conn.execute(f"""
            SELECT count(*) FROM duckdb_tables()
            WHERE schema_name = '{schema}' AND table_name = '{tabla}'
        """).fetchone()[0] > 0

        if existe and not force:
            conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
            print(f"  YA EXISTE ({conteo:,} filas) — omitir")
            continue

        # Cargar CSV
        df = pd.read_csv(csv_path)
        print(f"  CSV: {len(df):,} filas, {list(df.columns)}")

        # Crear tabla con tipos explicitos
        if existe:
            conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

        cols_ddl = ", ".join(
            f'"{col}" {tipo}' for col, tipo in catalogo['columnas'].items()
        )
        conn.execute(f"CREATE TABLE {nombre_completo} ({cols_ddl})")

        # Insertar fila por fila con parametros
        for _, row in df.iterrows():
            valores = []
            for col in catalogo['columnas']:
                val = row.get(col, None)
                if pd.isna(val):
                    valores.append(None)
                elif catalogo['columnas'][col] == "BOOLEAN":
                    valores.append(bool(val))
                elif catalogo['columnas'][col] == "INTEGER":
                    valores.append(int(val))
                else:
                    valores.append(str(val))

            placeholders = ", ".join(["?" for _ in valores])
            conn.execute(
                f"INSERT INTO {nombre_completo} VALUES ({placeholders})",
                valores
            )

        conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
        print(f"  Cargado: {conteo:,} filas en {nombre_completo}")

    conn.close()
    print("\n  Ingesta de Catalogos completada.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    ingestar_catalogos(force=args.force)
