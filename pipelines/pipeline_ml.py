"""
Pipeline ML — Flujo completo de analisis de pertinencia educativa.

Ejecuta el ciclo completo: carga de filtros → consulta DuckDB → indicadores → scoring.
Disenado como wrapper de referencia para el codigo productivo en services/ y data/.

Ejecucion:
    python pipelines/pipeline_ml.py

Requisitos:
    - data/repositorio.duckdb (703 MB, via Git LFS)
    - Dependencias en requirements.txt
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DUCKDB_PATH", "data/repositorio.duckdb")

from services.data_loader import cargar_datos_base


def ejecutar_pipeline(nbc: str = "Ingenieria de Sistemas", departamento: str = "BOGOTA D.C."):
    """
    Ejecuta el pipeline completo para un NBC y departamento especificos.

    Args:
        nbc: Nucleo Basico del Conocimiento (ej. "Ingenieria de Sistemas")
        departamento: Departamento (ej. "BOGOTA D.C.")

    Returns:
        Context con todos los datos, indicadores y scores calculados.
    """
    filtros = {
        "campos_amplios": [],
        "areas": [],
        "nbcs": [nbc],
        "deptos": [departamento],
        "municipios": [],
        "modalidades": [],
        "sectores": [],
        "niveles": [],
        "caracteres": [],
        "estados": [],
        "busqueda_nombre": "",
        "cod_snies_programas": [],
    }
    filtros_siet = {
        "areas_desempeno": [],
        "deptos_siet": [],
        "estados_siet": [],
        "modalidades_siet": [],
        "mostrar": False,
    }

    ctx = cargar_datos_base(filtros, filtros_siet)

    print("=" * 60)
    print(f"  PIPELINE — {nbc} | {departamento}")
    print("=" * 60)
    print(f"  Programas activos: {ctx.stats.get('total_programas', 0):,}")
    print(f"  IES ofertantes:    {ctx.stats.get('total_ies', 0):,}")
    print(f"  HHI:               {ctx.hhi}")
    print(f"  CAGR:              {ctx.cagr}%")
    print(f"  Ratio absorcion:   {ctx.ratio_abs}")
    print(f"  Conectividad:      {len(ctx.df_conectividad)} registros")
    print("=" * 60)

    return ctx


if __name__ == "__main__":
    ejecutar_pipeline()
