"""
Ingesta Territorial — DNP, MinTIC, DIVIPOLA, Conectividad
===========================================================

Descarga datos territoriales desde el portal datos.gov.co y otras fuentes
oficiales para alimentar los indicadores de pertinencia territorial
(conectividad, desempeno municipal, PDET, DIVIPOLA).

Schemas cubiertos (docs/tecnica/05_fuentes_datos.md Grupos A y D):
  dnp_planes_desarrollo (7 tablas): Medicion desempeno municipal, PDET, red vial
  mintic (6 tablas): Gobierno digital, centros digitales, capacitaciones TIC
  divipola (7 tablas): Codificacion DIVIPOLA — departamentos y municipios
  conectividad (2 tablas): Internet fijo (1.6M registros) y cobertura movil 4G
  territorial (1 tabla): Municipios PDET priorizados
  dnp (1 tabla): Planes de desarrollo

Fuentes:
  Desempeno Municipal (MDM): https://www.datos.gov.co/ (DNP)
  Conectividad: https://www.datos.gov.co/ (MinTIC-CRC)
  DIVIPOLA: https://www.dane.gov.co/ (DANE, codificacion oficial)
  PDET: https://www.renovacionterritorio.gov.co/ (ART)

Estructura actual de la DB:
  internet_fijo_accesos: 1,678,363 registros — la tabla mas grande
  dnp_medicion_desempeno_municipal: 22,020 municipios evaluados
  municipios_pdet: 170 municipios priorizados en 16 regiones

Requisitos:
  - Conexion a internet (datos.gov.co)
  - App token de Socrata recomendado
  - DuckDB con permisos de escritura
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import requests
import pandas as pd
import time
from config.database import DUCKDB_PATH

# ============================================================================
# CONFIGURACION DE FUENTES TERRITORIALES
# ============================================================================

SOCRATA_BASE = "https://www.datos.gov.co/resource"
APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", None)

DATASETS_TERRITORIALES = [
    # Conectividad — MinTIC/CRC
    ("conectividad", "internet_fijo_accesos",
     "https://www.datos.gov.co/resource/5wck-szir.json",
     "Accesos a internet fijo por municipio y tecnologia", 1678363),

    # DNP — Medicion de Desempeno Municipal
    ("dnp_planes_desarrollo", "dnp_medicion_desempeno_municipal",
     "https://www.datos.gov.co/resource/7f2w-9m4x.json",
     "Medicion de desempeno municipal MDM — DNP", 22020),

    # DIVIPOLA — Codificacion territorial oficial DANE
    ("divipola", "divipola_municipios",
     "https://www.datos.gov.co/resource/8k9p-3f2x.json",
     "Codificacion DIVIPOLA — municipios de Colombia", 1122),
]


def descargar_json(url: str, max_intentos=3) -> list:
    """Descarga un endpoint JSON con reintentos."""
    for intento in range(max_intentos):
        try:
            headers = {}
            if APP_TOKEN:
                headers['X-App-Token'] = APP_TOKEN
            resp = requests.get(url, headers=headers, params={'$limit': 50000}, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"    Intento {intento+1}/{max_intentos}: {e}")
            time.sleep(2)
    return []


# ============================================================================
# INGESTA PRINCIPAL
# ============================================================================

def ingestar_territorial(force=False, dry_run=False):
    """Descarga y carga datos territoriales en DuckDB."""
    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for schema, tabla, url, descripcion, esperado in DATASETS_TERRITORIALES:
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
            print(f"  [DRY-RUN] Descargaria {url}")
            continue

        datos = descargar_json(url)
        if not datos:
            print(f"  Sin datos — omitir")
            continue

        df = pd.DataFrame(datos)
        print(f"  {len(df):,} filas descargadas")

        if esperado and len(df) != esperado:
            print(f"  ADVERTENCIA: Esperadas {esperado:,}, recibidas {len(df):,}")

        if existe:
            conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

        conn.register('_df_terr', df)
        conn.execute(f"CREATE TABLE {nombre_completo} AS SELECT * FROM _df_terr")
        conn.unregister('_df_terr')

        conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
        print(f"  Cargado: {conteo:,} filas")
        time.sleep(0.5)

    conn.close()
    print("\n  Ingesta Territorial completada.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ingestar_territorial(force=args.force, dry_run=args.dry_run)
