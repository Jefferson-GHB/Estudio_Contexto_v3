"""
Pipeline ETL — Ejemplo de orquestador de ingestion de fuentes de datos
=============================================================

Ejecuta todos los scripts de ingesta en orden: catalogos → SNIES → SIET →
ICFES → Socrata → APE → Internacional → Territorial. Cada script es
independiente y puede ejecutarse por separado. El orquestador garantiza
el orden de dependencias y registra el progreso.

Dependencias entre scripts:
  ingestar_catalogos.py (sin dependencias)
  ingestar_snies.py (sin dependencias)
  ingestar_socrata.py (sin dependencias)
  ingestar_ape.py (sin dependencias)
  ingestar_internacional.py (sin dependencias)
  ingestar_territorial.py (sin dependencias)

Ejecucion:
  python pipelines/pipeline_etl.py              # todos los scripts
  python pipelines/pipeline_etl.py --solo snies  # solo un script
  python pipelines/pipeline_etl.py --dry-run     # valida sin ejecutar
"""

import sys
import os
import subprocess
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# CONFIGURACION
# ============================================================================

PIPELINE = [
    ("catalogos",       "admin/ingestar_catalogos.py",       "Catalogos NBC, CUOC, CIIU, MNC, Mapeo de Variables"),
    ("snies",           "admin/ingestar_snies.py",           "SNIES: programas, matricula, graduados"),
    ("socrata",         "admin/ingestar_socrata.py",         "datos.gov.co: ~188 tablas Socrata"),
    ("ape",             "admin/ingestar_ape.py",             "APE/SENA: vacantes, inscritos, colocados"),
    ("internacional",   "admin/ingestar_internacional.py",   "Banco Mundial, OECD, UNESCO, ILO"),
    ("territorial",     "admin/ingestar_territorial.py",     "DNP, MinTIC, DIVIPOLA, conectividad"),
]

# ============================================================================
# ORQUESTADOR
# ============================================================================

def ejecutar_etl(solo=None, dry_run=False):
    """
    Ejecuta el pipeline ETL completo o un script especifico.

    Args:
        solo: Nombre del script a ejecutar (None = todos)
        dry_run: Si True, solo muestra que haria sin ejecutar
    """
    inicio = datetime.now()
    print("=" * 70)
    print(f"  PIPELINE ETL — Sistema de Analisis de Contexto")
    print(f"  Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("  MODO: DRY-RUN (validacion sin ejecucion)")
    print("=" * 70)

    if solo:
        pipeline = [(solo, f"admin/ingestar_{solo}.py", solo)]
    else:
        pipeline = PIPELINE

    resultados = {}
    for nombre, script, descripcion in pipeline:
        print(f"\n{'─' * 70}")
        print(f"  [{nombre}] {descripcion}")
        print(f"  Script: {script}")
        print(f"{'─' * 70}")

        if not os.path.exists(script):
            print(f"  ERROR: Script no encontrado — {script}")
            resultados[nombre] = "NO_ENCONTRADO"
            continue

        if dry_run:
            print(f"  [DRY-RUN] Ejecutaria: python {script}")
            resultados[nombre] = "DRY_RUN"
            continue

        try:
            t0 = time.time()
            result = subprocess.run(
                [sys.executable, script],
                capture_output=True, text=True, timeout=3600,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            elapsed = time.time() - t0

            if result.returncode == 0:
                print(f"  OK — {elapsed:.1f}s")
                resultados[nombre] = "OK"
            else:
                print(f"  ERROR (exit {result.returncode}) — {elapsed:.1f}s")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:500]}")
                resultados[nombre] = f"ERROR_{result.returncode}"

        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT — excedio 1 hora")
            resultados[nombre] = "TIMEOUT"
        except Exception as e:
            print(f"  EXCEPCION: {e}")
            resultados[nombre] = "EXCEPCION"

    # ============================================================================
    # RESUMEN
    # ============================================================================
    fin = datetime.now()
    print("\n" + "=" * 70)
    print(f"  RESUMEN — {fin.strftime('%H:%M:%S')} ({(fin - inicio).total_seconds():.0f}s)")
    print("=" * 70)
    for nombre, estado in resultados.items():
        simbolo = "OK" if estado == "OK" else ("--" if estado == "DRY_RUN" else "!!")
        print(f"  [{simbolo}] {nombre}: {estado}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL — Estudio Contexto")
    parser.add_argument("--solo", help="Ejecutar solo un script (snies, socrata, ape, etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Validar sin ejecutar")
    args = parser.parse_args()
    ejecutar_etl(solo=args.solo, dry_run=args.dry_run)
