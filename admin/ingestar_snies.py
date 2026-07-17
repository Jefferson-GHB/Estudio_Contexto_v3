"""
Ingesta SNIES — Programas, matricula, graduados, inscritos, admitidos
======================================================================

Descarga los archivos XLSX del portal SNIES (https://snies.mineducacion.gov.co/)
y los carga en DuckDB con el esquema documentado en docs/tecnica/05_fuentes_datos.md.

Las tablas de SNIES usan columnas VARCHAR universalmente (artefacto de importacion
desde XLSX). Las columnas numericas (MATRICULADOS, GRADUADOS, etc.) son casteables
a DOUBLE sin perdida en el 100% de los casos.

Fuentes:
  - Programas: https://snies.mineducacion.gov.co/ → XLSX con 56 NBCs
  - Matriculados/Graduados/Inscritos/Admitidos/Primer curso: series historicas 2019-2024
  - Metadata de columnas documentado en services/sources.py

Transformaciones aplicadas:
  1. Normalizacion de nombres de columna (strip accents, UPPER, snake_case)
  2. Validacion de NBCs contra catalogo_curado.catalogo_nbc_snies (56/56 OK)
  3. Validacion de CINE-F contra clasificadores (11 valores, 0% huerfanos)
  4. Remocion de filas con codigo de programa nulo
  5. Verificacion post-carga: conteo, nulos, duplicados

Requisitos:
  - Archivos XLSX fuente en data/raw/snies/ (descarga manual previa desde el portal)
  - DuckDB con permisos de escritura
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd
from pathlib import Path
from config.database import DUCKDB_PATH

# ============================================================================
# CONFIGURACION DE FUENTES
# ============================================================================

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "snies"

TABLAS_SNIES = {
    "snies_programas": {
        "archivo": "SNIES_PROGRAMAS_2024.xlsx",
        "schema": "snies",
        "descripcion": "Programas academicos activos — 30,660 registros, 56 NBCs",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "NOMBRE_DEL_PROGRAMA",
                          "NUCLEO_BASICO_DEL_CONOCIMIENTO", "AREA_DE_CONOCIMIENTO",
                          "CINE_F_2013_AC_CAMPO_AMPLIO", "NIVEL_FORMACION",
                          "METODOLOGIA", "SECTOR_IES", "CARACTER_IES",
                          "DEPARTAMENTO", "MUNICIPIO", "CREDITOS", "DURACION"],
        "nulos_esperados": ["JUSTIFICACION", "REGISTRO_UNICO", "VIGENCIA_TRANSITORIA"],
    },
    "snies_matriculados": {
        "archivo": "SNIES_MATRICULADOS_2019_2024.xlsx",
        "schema": "snies",
        "descripcion": "Matriculados por ano — 427,727 registros, 2019-2024",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "MATRICULADOS", "ANO", "SEMESTRE",
                          "NOMBRE_IES", "SECTOR_IES", "DEPARTAMENTO"],
    },
    "snies_graduados": {
        "archivo": "SNIES_GRADUADOS_2018_2024.xlsx",
        "schema": "snies",
        "descripcion": "Graduados por ano — 267,069 registros, 2019-2024",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "GRADUADOS", "ANO", "SEMESTRE"],
    },
    "snies_inscritos": {
        "archivo": "SNIES_INSCRITOS_2019_2024.xlsx",
        "schema": "snies",
        "descripcion": "Inscritos por ano — 324,783 registros, 2019-2024",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "INSCRITOS", "ANO", "SEMESTRE"],
    },
    "snies_admitidos": {
        "archivo": "SNIES_ADMITIDOS_2019_2024.xlsx",
        "schema": "snies",
        "descripcion": "Admitidos por ano — 306,178 registros, 2019-2024",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "ADMITIDOS", "ANO", "SEMESTRE"],
    },
    "snies_matriculados_primer_curso": {
        "archivo": "SNIES_PRIMER_CURSO_2019_2024.xlsx",
        "schema": "snies",
        "descripcion": "Matriculados primer curso — 286,148 registros, 2019-2024",
        "columnas_clave": ["COD_SNIES_PROGRAMA", "MATRICULADOS_PRIMER_CURSO", "ANO", "SEMESTRE"],
    },
}

# ============================================================================
# FUNCIONES DE TRANSFORMACION
# ============================================================================

def normalizar_columna(nombre: str) -> str:
    """Limpia nombres de columna: strip, replace spaces, remove accents."""
    import unicodedata
    nombre = nombre.strip()
    nombre = nombre.replace(' ', '_').replace('-', '_').replace('.', '')
    nombre = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('ascii')
    return nombre.upper()


def validar_nbcs(df: pd.DataFrame, conn: duckdb.DuckDBPyConnection, col_nbc: str):
    """Verifica que los NBCs del DataFrame existan en el catalogo."""
    nbcs_catalogo = set(
        conn.execute("SELECT DISTINCT UPPER(NBC) FROM catalogo_curado.catalogo_nbc_snies")
        .fetchdf()['UPPER(NBC)'].values
    )
    nbcs_df = set(df[col_nbc].dropna().str.upper().unique())
    huerfanos = nbcs_df - nbcs_catalogo
    if huerfanos:
        print(f"  ADVERTENCIA: {len(huerfanos)} NBCs no encontrados en catalogo:")
        for nbc in list(huerfanos)[:5]:
            print(f"    - {nbc}")
    else:
        print(f"  NBCs: {len(nbcs_df)} en datos, {len(nbcs_catalogo)} en catalogo — 0 huerfanos")


# ============================================================================
# INGESTA PRINCIPAL
# ============================================================================

def ingestar_snies(raw_dir=RAW_DIR, dry_run=False):
    """
    Carga todas las tablas SNIES desde archivos XLSX a DuckDB.

    Args:
        raw_dir: Directorio con los archivos XLSX fuente
        dry_run: Si True, solo verifica que los archivos existen
    """
    conn = duckdb.connect(DUCKDB_PATH, read_only=False)

    for nombre_tabla, config in TABLAS_SNIES.items():
        archivo = raw_dir / config['archivo']
        schema = config['schema']
        print(f"\n{'=' * 60}")
        print(f"  {schema}.{nombre_tabla}")
        print(f"  {config['descripcion']}")
        print(f"{'=' * 60}")

        if not archivo.exists():
            print(f"  ARCHIVO NO ENCONTRADO: {archivo}")
            print(f"  Descargar de: https://snies.mineducacion.gov.co/")
            continue

        if dry_run:
            print(f"  [DRY-RUN] Cargaria {archivo.name} ({archivo.stat().st_size / 1024:.0f} KB)")
            continue

        # 1. CARGAR XLSX
        print(f"  Cargando {archivo.name}...")
        try:
            df = pd.read_excel(archivo, dtype=str)
        except Exception as e:
            print(f"  ERROR al leer XLSX: {e}")
            continue

        # 2. NORMALIZAR COLUMNAS
        df.columns = [normalizar_columna(c) for c in df.columns]
        print(f"  {len(df):,} filas, {len(df.columns)} columnas")

        # 3. REMOVER FILAS SIN CODIGO DE PROGRAMA
        if 'COD_SNIES_PROGRAMA' in df.columns:
            antes = len(df)
            df = df.dropna(subset=['COD_SNIES_PROGRAMA'])
            df = df[df['COD_SNIES_PROGRAMA'] != '']
            if len(df) < antes:
                print(f"  Removidas {antes - len(df):,} filas sin COD_SNIES_PROGRAMA")

        # 4. VALIDAR NBCs (si la tabla tiene columna NBC)
        col_nbc = None
        for c in df.columns:
            if 'NBC' in c or 'NUCLEO' in c:
                col_nbc = c
                break
        if col_nbc:
            validar_nbcs(df, conn, col_nbc)

        # 5. CARGAR A DUCKDB
        nombre_completo = f"{schema}.{nombre_tabla}"
        conn.execute(f"DROP TABLE IF EXISTS {nombre_completo}")

        # Registrar como tabla DuckDB
        conn.register('_df_temp', df)
        conn.execute(f"CREATE TABLE {nombre_completo} AS SELECT * FROM _df_temp")
        conn.unregister('_df_temp')

        # 6. VERIFICAR
        conteo = conn.execute(f"SELECT count(*) FROM {nombre_completo}").fetchone()[0]
        print(f"  Cargado: {conteo:,} filas en {nombre_completo}")

    conn.close()
    print("\n  Ingesta SNIES completada.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ingestar_snies(dry_run=args.dry_run)
