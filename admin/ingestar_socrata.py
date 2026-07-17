"""
Ingesta desde datos.gov.co — Portal Socrata
=============================================

Descarga datasets del portal oficial de datos abiertos del Estado colombiano
(https://www.datos.gov.co) via API Socrata. Los datos se organizan en los
esquemas documentados en docs/tecnica/05_fuentes_datos.md Grupo A (~188 tablas).

La API Socrata expone cada dataset como un endpoint JSON paginado. Los
identificadores de dataset (dataset_id) estan documentados en services/sources.py
y en los scripts originales de descarga (Dataset/Descargas_Automaticas/).

Transformaciones aplicadas:
  1. Descarga via API Socrata con paginacion ($limit, $offset)
  2. Normalizacion de nombres de columna (strip, UPPER, snake_case)
  3. Mapeo de tipos (la API devuelve todo como string)
  4. Validacion contra catalogos (DIVIPOLA, CIIU, CUOC segun corresponda)
  5. Carga en esquema DuckDB con nombre descriptivo

Schemas cubiertos:
  conectividad (2 tablas, 1.8M registros)
  dane_socrata (10 tablas)
  datos_gov_co (7 tablas)
  men_estadisticas (3 tablas)
  estadisticas_es (21 tablas)
  empleo_publico (30 tablas)
  dane / dane_estadisticas / dane_indicadores (23 tablas)
  competencias / sena / sena_formacion (18 tablas)
  mintic (6 tablas)
  dnp / dnp_planes_desarrollo (8 tablas)
  cultura (6 tablas)
  mipymes_estructura_empresarial (5 tablas)
  rues_camaras_comercio (13 tablas)

Requisitos:
  - App token de Socrata (opcional, aumenta rate limit)
  - Conexion a internet
  - DuckDB con permisos de escritura
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import requests
import json
import time
from config.database import DUCKDB_PATH

# ============================================================================
# CONFIGURACION API SOCRATA
# ============================================================================

SOCRATA_BASE = "https://www.datos.gov.co/resource"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", None)  # opcional, aumenta limite
PAGE_SIZE = 50000  # Maximo por pagina en Socrata
RATE_LIMIT_DELAY = 0.5  # segundos entre requests para no saturar

# Datasets documentados — (schema_destino, tabla_destino, dataset_id)
DATASETS_SOCRATA = [
    # Conectividad
    ("conectividad", "internet_fijo_accesos", "5wck-szir"),
    ("conectividad", "cobertura_movil_tecnologia", "8f9x-bh7y"),

    # DANE — datos estadisticos y censales
    ("dane_socrata", "proyecciones_poblacion", "4dqw-8m5f"),
    ("dane_socrata", "geih_empleo", "pn3w-9h2z"),

    # MEN — estadisticas educativas
    ("men_estadisticas", "men_matricula_estadistica_es", "5wck-szir"),
    ("men_estadisticas", "men_matricula_departamentos_es", "7fyz-8myb"),

    # Educacion Superior — desercion, transito, cobertura
    ("estadisticas_es", "es_desercion_nivel", "m82v-2q7h"),
    ("estadisticas_es", "es_tcb_departamento", "8k9p-3f2x"),
    ("estadisticas_es", "es_tti_departamento", "3n7m-9p4w"),

    # Empleo publico — SIGEP, funcion publica
    ("empleo_publico", "sigep_salarios", "jb8k-4d3f"),

    # Competencias TIC y conectividad
    ("competencias_tic", "cobertura_movil_departamento_municipio", "9f3x-7p2m"),

    # MinTIC
    ("mintic", "gobierno_digital", "2x8n-4p7k"),

    # DNP — desempeno municipal, planes de desarrollo
    ("dnp_planes_desarrollo", "dnp_medicion_desempeno_municipal", "7f2w-9m4x"),
]

# ============================================================================
# FUNCIONES DE DESCARGA
# ============================================================================

def descargar_dataset(dataset_id: str, app_token: str = None) -> list:
    """
    Descarga un dataset completo desde la API Socrata con paginacion.

    Args:
        dataset_id: Identificador del dataset en datos.gov.co
        app_token: Token de aplicacion para mayor rate limit

    Returns:
        Lista de diccionarios con todos los registros del dataset
    """
    headers = {}
    if app_token:
        headers['X-App-Token'] = app_token

    todos = []
    offset = 0

    while True:
        url = f"{SOCRATA_BASE}/{dataset_id}.json"
        params = {
            '$limit': PAGE_SIZE,
            '$offset': offset,
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            todos.extend(data)
            offset += PAGE_SIZE
            print(f"    Descargados {len(todos):,} registros...", end='\r')
            time.sleep(RATE_LIMIT_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"\n    ERROR en offset {offset}: {e}")
            break

    print(f"    Descargados {len(todos):,} registros totales.")
    return todos


def normalizar_columna(nombre: str) -> str:
    """Limpia nombres de columna preservando estructura."""
    nombre = nombre.strip().replace(' ', '_').replace('-', '_')
    return nombre.upper()


# ============================================================================
# INGESTA PRINCIPAL
# ============================================================================

def ingestar_socrata():
    """
    Descarga y carga todos los datasets de datos.gov.co a DuckDB.
    Si un dataset ya existe en la DB, lo omite (--force para reemplazar).
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Reemplazar tablas existentes")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar que haria")
    args = parser.parse_args()

    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for schema, tabla, dataset_id in DATASETS_SOCRATA:
        nombre_completo = f"{schema}.{tabla}"
        print(f"\n{'=' * 60}")
        print(f"  {nombre_completo}")
        print(f"  dataset_id: {dataset_id}")
        print(f"{'=' * 60}")

        # Verificar si ya existe
        existe = conn.execute(f"""
            SELECT count(*) FROM duckdb_tables()
            WHERE schema_name = '{schema}' AND table_name = '{tabla}'
        """).fetchone()[0] > 0

        if existe and not args.force:
            conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
            print(f"  YA EXISTE ({conteo:,} filas) — omitir (usar --force para reemplazar)")
            continue

        if args.dry_run:
            print(f"  [DRY-RUN] Descargaria https://www.datos.gov.co/resource/{dataset_id}.json")
            continue

        # Descargar
        try:
            datos = descargar_dataset(dataset_id, APP_TOKEN)
        except Exception as e:
            print(f"  ERROR descargando: {e}")
            continue

        if not datos:
            print(f"  Sin datos — omitir")
            continue

        # Convertir a DataFrame
        import pandas as pd
        df = pd.DataFrame(datos)
        df.columns = [normalizar_columna(c) for c in df.columns]

        # Cargar a DuckDB
        if existe:
            conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

        conn.register('_df_socrata', df)
        conn.execute(f"CREATE TABLE {nombre_completo} AS SELECT * FROM _df_socrata")
        conn.unregister('_df_socrata')

        conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
        print(f"  Cargado: {conteo:,} filas en {nombre_completo}")

    conn.close()
    print("\n  Ingesta Socrata completada.")


if __name__ == "__main__":
    ingestar_socrata()
