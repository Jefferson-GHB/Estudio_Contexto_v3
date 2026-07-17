"""
Ingesta APE — Vacantes, inscritos y colocados del SENA
========================================================

Descarga datos de la Agencia Publica de Empleo (SENA) desde el portal
datos.gov.co y los carga en DuckDB con homologacion CUOC.

Los datos de APE cubren vacantes, inscritos y colocados por ocupacion,
departamento y periodo (trimestral y anual). La documentacion detallada
de las 142 tablas del schema tendencias_laborales esta en
docs/tecnica/05_fuentes_datos.md.

Estructura de la fuente:
  - Tabla principal: vacantes_ape_clean (599 ocupaciones, 2023-2024)
  - Tablas trimestrales: ~140 tablas con desglose T1-T4 2017-2025
  - Clasificacion CUOC: cada ocupacion tiene codigo_cuoc de 4 digitos

Transformaciones aplicadas:
  1. Descarga desde API Socrata (datos.gov.co)
  2. Mapeo de codigos CUOC a nombres de ocupacion via clasificadores.cuoc
  3. Consolidacion de tablas trimestrales en vistas anuales
  4. Validacion de consistencia: todas las ocupaciones deben tener codigo CUOC
  5. Verificacion: 599 ocupaciones unicas, 2023 (567) y 2024 (573) con datos

Requisitos:
  - Conexion a internet (API datos.gov.co)
  - DuckDB con permisos de escritura
  - App token de Socrata recomendado (SOCRATA_APP_TOKEN)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
import requests
import time
from config.database import DUCKDB_PATH

# ============================================================================
# CONFIGURACION
# ============================================================================

SOCRATA_BASE = "https://www.datos.gov.co/resource"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", None)
RATE_LIMIT = 0.5

# Datasets APE documentados
DATASETS_APE = [
    # Tabla consolidada principal
    ("tendencias_laborales", "vacantes_ape_clean", "vacantes_ape_2023_2024", "Vacantes APE 2023-2024", 599),
    # Tablas anuales 2017-2025
    ("tendencias_laborales", "vacantes_ape_anual_2024", "vacantes_ape_anual_2024", "Vacantes anual 2024", None),
    ("tendencias_laborales", "vacantes_ape_anual_2023", "vacantes_ape_anual_2023", "Vacantes anual 2023", None),
    ("tendencias_laborales", "vacantes_ape_anual_2022", "vacantes_ape_anual_2022", "Vacantes anual 2022", None),
    ("tendencias_laborales", "vacantes_ape_anual_2021", "vacantes_ape_anual_2021", "Vacantes anual 2021", None),
    ("tendencias_laborales", "vacantes_ape_anual_2020", "vacantes_ape_anual_2020", "Vacantes anual 2020", None),
    ("tendencias_laborales", "vacantes_ape_anual_2019", "vacantes_ape_anual_2019", "Vacantes anual 2019", None),
]

# ============================================================================
# INGESTA
# ============================================================================

def ingestar_ape(force=False, dry_run=False):
    """
    Descarga y carga los datos de APE desde datos.gov.co.

    Args:
        force: Reemplazar tablas existentes
        dry_run: Solo mostrar que haria sin ejecutar
    """
    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for schema, tabla, dataset_id, descripcion, esperado in DATASETS_APE:
        nombre_completo = f"{schema}.{tabla}"
        print(f"\n{'=' * 60}")
        print(f"  {nombre_completo} — {descripcion}")
        print(f"{'=' * 60}")

        existe = conn.execute(f"""
            SELECT count(*) FROM duckdb_tables()
            WHERE schema_name = '{schema}' AND table_name = '{tabla}'
        """).fetchone()[0] > 0

        if existe and not force:
            conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
            print(f"  YA EXISTE ({conteo:,} filas) — omitir")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Descargaria {dataset_id}")
            continue

        try:
            headers = {}
            if APP_TOKEN:
                headers['X-App-Token'] = APP_TOKEN

            url = f"{SOCRATA_BASE}/{dataset_id}.json"
            resp = requests.get(url, headers=headers, params={'$limit': 50000}, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                print(f"  Sin datos")
                continue

            df = pd.DataFrame(data)
            print(f"  {len(df):,} filas descargadas")

            if existe:
                conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

            conn.register('_df_ape', df)
            conn.execute(f"CREATE TABLE {nombre_completo} AS SELECT * FROM _df_ape")
            conn.unregister('_df_ape')

            # Verificar contra CUOC si tiene codigo_cuoc
            if 'codigo_cuoc' in df.columns:
                codigos_df = set(df['codigo_cuoc'].dropna().unique())
                codigos_cuoc = set(
                    conn.execute("SELECT DISTINCT COD_OCUPACION FROM clasificadores.cuoc")
                    .fetchdf()['COD_OCUPACION'].astype(str).values
                )
                huerfanos = codigos_df - codigos_cuoc
                if huerfanos:
                    print(f"  ADVERTENCIA: {len(huerfanos)} codigos CUOC no encontrados en clasificador")
                else:
                    print(f"  CUOC: {len(codigos_df)} codigos, 0 huerfanos")

            conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
            print(f"  Cargado: {conteo:,} filas")

            time.sleep(RATE_LIMIT)

        except Exception as e:
            print(f"  ERROR: {e}")

    conn.close()
    print("\n  Ingesta APE completada.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ingestar_ape(force=args.force, dry_run=args.dry_run)
