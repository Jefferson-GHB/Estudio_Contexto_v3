"""
Ingesta Internacional — Banco Mundial, OECD, UNESCO, ILO
==========================================================

Descarga indicadores globales desde las APIs publicas de organismos
internacionales y los carga en DuckDB para analisis comparativo.

Schemas cubiertos (docs/tecnica/05_fuentes_datos.md Grupo C, ~60 tablas):
  indicadores_globales (22 tablas): Banco Mundial — empleo, educacion, PIB
  banco_mundial (22 tablas): Duplicado espejo de indicadores_globales
  oecd_internacional (2 tablas): PISA scores, labour statistics
  unesco_internacional (3 tablas): SDG4 educacion, indicadores
  ilo_internacional (2 tablas): Empleo global, tendencias LATAM
  esco (2 tablas): Habilidades europeas (ver ingestar_esco.py)

APIs utilizadas:
  Banco Mundial: https://api.worldbank.org/v2/ (gratuita, sin key)
  OECD: https://stats.oecd.org/SDMX-JSON/ (gratuita)
  UNESCO: https://api.uis.unesco.org/ (requiere registro)

Nota: Los datos del Banco Mundial estan duplicados en dos schemas
(indicadores_globales y banco_mundial) como resultado de dos rondas
de ingesta independientes. Se mantiene indicadores_globales como
fuente primaria y banco_mundial como respaldo historico.

Requisitos:
  - Conexion a internet
  - DuckDB con permisos de escritura
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import requests
import json
import pandas as pd
import time
from config.database import DUCKDB_PATH

# ============================================================================
# CONFIGURACION DE INDICADORES — Banco Mundial API v2
# ============================================================================

# Indicadores del Banco Mundial con codigos API
INDICADORES_BM = {
    "bm_desempleo_jovenes": {
        "codigo": "SL.UEM.1524.ZS",
        "descripcion": "Desempleo juvenil (% de la poblacion activa 15-24)",
    },
    "bm_tasa_desempleo": {
        "codigo": "SL.UEM.TOTL.ZS",
        "descripcion": "Desempleo total (% de la poblacion activa)",
    },
    "bm_participacion_fuerza_laboral": {
        "codigo": "SL.TLF.CACT.ZS",
        "descripcion": "Participacion en la fuerza laboral (% poblacion 15+)",
    },
    "bm_pib_per_capita": {
        "codigo": "NY.GDP.PCAP.CD",
        "descripcion": "PIB per capita (USD corrientes)",
    },
    "bm_crecimiento_pib": {
        "codigo": "NY.GDP.MKTP.KD.ZG",
        "descripcion": "Crecimiento del PIB (% anual)",
    },
    "bm_gasto_educacion_pib": {
        "codigo": "SE.XPD.TOTL.GD.ZS",
        "descripcion": "Gasto publico en educacion (% del PIB)",
    },
    "bm_tasa_matricula_terciaria": {
        "codigo": "SE.TER.ENRR",
        "descripcion": "Tasa bruta de matricula en educacion terciaria",
    },
    "bm_usuarios_internet_pct": {
        "codigo": "IT.NET.USER.ZS",
        "descripcion": "Usuarios de internet (% de la poblacion)",
    },
    "bm_poblacion_total": {
        "codigo": "SP.POP.TOTL",
        "descripcion": "Poblacion total",
    },
    "bm_empleo_vulnerable": {
        "codigo": "SL.EMP.VULN.ZS",
        "descripcion": "Empleo vulnerable (% del empleo total)",
    },
}

PAISES = ["COL", "BRA", "MEX", "ARG", "CHL", "PER", "ECU", "URY", "PRY", "BOL",
          "CRI", "PAN", "GTM", "HND", "SLV", "NIC", "DOM", "VEN", "CUB"]

# ============================================================================
# DESCARGA BANCO MUNDIAL
# ============================================================================

def descargar_indicador_bm(codigo: str, nombre_tabla: str) -> pd.DataFrame:
    """
    Descarga un indicador del Banco Mundial para todos los paises LATAM.

    La API del BM devuelve JSON paginado. Cada entrada tiene:
      countryiso3code, date (año), value (float o null)

    Returns:
        DataFrame con columnas: pais, ano, valor
    """
    url = f"https://api.worldbank.org/v2/country/{';'.join(PAISES)}/indicator/{codigo}"
    params = {
        'format': 'json',
        'per_page': 1000,
        'date': '2010:2024',
    }

    print(f"  Descargando {nombre_tabla} ({codigo})...")
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if len(data) < 2:
            print(f"    Sin datos")
            return pd.DataFrame()

        registros = data[1]  # el primer elemento es metadata
        if not registros:
            return pd.DataFrame()

        filas = []
        for r in registros:
            if r.get('value') is not None:
                filas.append({
                    'pais': r['country']['id'],
                    'ano': int(r['date']),
                    'valor': float(r['value']),
                })

        df = pd.DataFrame(filas)
        print(f"    {len(df):,} registros descargados")
        return df

    except Exception as e:
        print(f"    ERROR: {e}")
        return pd.DataFrame()


# ============================================================================
# INGESTA PRINCIPAL
# ============================================================================

def ingestar_internacional(force=False, dry_run=False):
    """Descarga indicadores del Banco Mundial y carga en DuckDB."""
    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for nombre_tabla, config in INDICADORES_BM.items():
        nombre_completo = f"indicadores_globales.{nombre_tabla}"
        print(f"\n{'─' * 60}")
        print(f"  {nombre_completo}")
        print(f"  {config['descripcion']}")
        print(f"{'─' * 60}")

        existe = conn.execute(f"""
            SELECT count(*) FROM duckdb_tables()
            WHERE schema_name = 'indicadores_globales' AND table_name = '{nombre_tabla}'
        """).fetchone()[0] > 0

        if existe and not force:
            conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
            print(f"  YA EXISTE ({conteo:,} filas) — omitir")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Descargaria indicador {config['codigo']}")
            continue

        df = descargar_indicador_bm(config['codigo'], nombre_tabla)
        if df.empty:
            continue

        if existe:
            conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

        conn.register('_df_bm', df)
        conn.execute(f"CREATE TABLE {nombre_completo} AS SELECT * FROM _df_bm")
        conn.unregister('_df_bm')

        conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
        print(f"  Cargado: {conteo:,} filas en {nombre_completo}")

        time.sleep(0.3)  # respetar rate limit del BM

    conn.close()
    print("\n  Ingesta Internacional completada.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ingestar_internacional(force=args.force, dry_run=args.dry_run)
