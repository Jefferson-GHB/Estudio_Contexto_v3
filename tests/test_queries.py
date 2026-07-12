"""
Test suite: Validates ALL query functions against the real DuckDB database.
===============================================================================

Scenario-based: each test simulates real sidebar filter combinations and verifies
that every query function returns non-empty, sensible data.

Run:
    cd Estudio_Contexto
    python -m tests.test_queries

Exit code 0 = all pass, 1 = failures found.
"""

import sys
import os
import io
import time

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DUCKDB_PATH", "data/repositorio.duckdb")

import duckdb

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0
SKIP = 0
RESULTS = []   # [(name, status, detail)]


def ok(name, detail=""):
    global PASS
    PASS += 1
    RESULTS.append((name, "OK", detail))
    print(f"  [OK]   {name}  {detail}")


def fail(name, detail=""):
    global FAIL
    FAIL += 1
    RESULTS.append((name, "FAIL", detail))
    print(f"  [FAIL] {name}  {detail}")


def skip(name, detail=""):
    global SKIP
    SKIP += 1
    RESULTS.append((name, "SKIP", detail))
    print(f"  [SKIP] {name}  {detail}")


def check(name, result, *, min_rows=1, min_val=None, is_dict=False, required_keys=None):
    """Validate query result.

    result: DataFrame, dict, or tuple.
    """
    import pandas as pd

    if result is None:
        fail(name, "returned None")
        return False

    if is_dict:
        if not isinstance(result, dict):
            fail(name, f"expected dict, got {type(result).__name__}")
            return False
        if required_keys:
            missing = [k for k in required_keys if k not in result]
            if missing:
                fail(name, f"missing keys: {missing}")
                return False
        if min_val is not None:
            for k, v in result.items():
                if isinstance(v, (int, float)) and v > 0:
                    ok(name, f"{result}")
                    return True
            fail(name, f"all values zero: {result}")
            return False
        ok(name, f"keys={list(result.keys())}")
        return True

    if isinstance(result, tuple):
        # e.g. get_competencias_cuoc returns (df1, df2)
        for i, r in enumerate(result):
            if isinstance(r, pd.DataFrame) and len(r) >= min_rows:
                ok(name, f"tuple[{i}] has {len(r)} rows")
                return True
        fail(name, f"all elements < {min_rows} rows")
        return False

    if isinstance(result, pd.DataFrame):
        if len(result) >= min_rows:
            ok(name, f"{len(result)} rows")
            return True
        else:
            fail(name, f"{len(result)} rows (expected >= {min_rows})")
            return False

    fail(name, f"unexpected type: {type(result).__name__}")
    return False


# ---------------------------------------------------------------------------
# Load real values from DB for all tests
# ---------------------------------------------------------------------------

def load_real_values():
    """Get actual values from DB to use as filter inputs."""
    conn = duckdb.connect("data/repositorio.duckdb", read_only=True)

    vals = {}
    vals["nbc"] = conn.execute(
        """SELECT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" FROM snies.snies_programas
           WHERE "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL LIMIT 1"""
    ).fetchone()[0]

    vals["nbc_sistemas"] = conn.execute(
        """SELECT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" FROM snies.snies_programas
           WHERE UPPER("NÚCLEO_BÁSICO_DEL_CONOCIMIENTO") LIKE '%SISTEMA%'
           ORDER BY 1 LIMIT 1"""
    ).fetchone()[0]

    vals["depto"] = conn.execute(
        """SELECT "DEPARTAMENTO_OFERTA_PROGRAMA" FROM snies.snies_programas
           WHERE "DEPARTAMENTO_OFERTA_PROGRAMA" LIKE '%BOGOT%' LIMIT 1"""
    ).fetchone()[0]

    vals["modalidad"] = conn.execute(
        """SELECT "MODALIDAD" FROM snies.snies_programas
           WHERE "MODALIDAD" = 'PRESENCIAL' LIMIT 1"""
    ).fetchone()[0]

    vals["sector"] = conn.execute(
        """SELECT DISTINCT "SECTOR" FROM snies.snies_programas ORDER BY 1 LIMIT 1"""
    ).fetchone()[0]

    vals["nivel"] = conn.execute(
        """SELECT DISTINCT "NIVEL_DE_FORMACIÓN" FROM snies.snies_programas ORDER BY 1 LIMIT 1"""
    ).fetchone()[0]

    vals["caracter"] = conn.execute(
        """SELECT DISTINCT "CARÁCTER_ACADÉMICO" FROM snies.snies_programas ORDER BY 1 LIMIT 1"""
    ).fetchone()[0]

    vals["campo_amplio"] = conn.execute(
        """SELECT DISTINCT "CINE_F_2013_AC_CAMPO_AMPLIO" FROM snies.snies_programas
           WHERE "CINE_F_2013_AC_CAMPO_AMPLIO" LIKE '%Ingenier%' LIMIT 1"""
    ).fetchone()[0]

    vals["area"] = conn.execute(
        """SELECT DISTINCT "ÁREA_DE_CONOCIMIENTO" FROM snies.snies_programas ORDER BY 1 LIMIT 1"""
    ).fetchone()[0]

    vals["estado"] = conn.execute(
        """SELECT DISTINCT "ESTADO_PROGRAMA" FROM snies.snies_programas
           WHERE "ESTADO_PROGRAMA" = 'ACTIVO' LIMIT 1"""
    ).fetchone()
    vals["estado"] = vals["estado"][0] if vals["estado"] else "Activo"

    vals["cod_snies"] = conn.execute(
        """SELECT CAST("CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) FROM snies.snies_programas LIMIT 1"""
    ).fetchone()[0]

    # NBC value in matriculados (for comparison)
    vals["nbc_matriculados"] = conn.execute(
        """SELECT DISTINCT "NBC" FROM snies.snies_matriculados
           WHERE UPPER("NBC") LIKE '%SISTEMA%' LIMIT 1"""
    ).fetchone()[0]

    # Check case match between tables
    vals["nbc_case_match"] = (vals["nbc_sistemas"].upper() == vals["nbc_matriculados"].upper())

    conn.close()
    return vals


# ---------------------------------------------------------------------------
# Filter Builders
# ---------------------------------------------------------------------------

def test_filter_builders(vals):
    """Test build_where_clause and build_where_clause_matriculados."""
    from data.filters import build_where_clause, build_where_clause_matriculados, build_nbc_condition

    conn = duckdb.connect("data/repositorio.duckdb", read_only=True)

    print("\n" + "=" * 70)
    print("FILTER BUILDERS")
    print("=" * 70)

    # 1. build_where_clause — programas
    f1 = {"nbcs": [vals["nbc_sistemas"]]}
    wc1 = build_where_clause(f1, "p")
    cnt = conn.execute(f'SELECT COUNT(*) FROM snies.snies_programas p WHERE {wc1}').fetchone()[0]
    ok("BWC: single NBC", f"{cnt} rows") if cnt > 0 else fail("BWC: single NBC", f"0 rows — SQL: {wc1[:120]}")

    # 2. build_where_clause — multi filter
    f2 = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]], "modalidades": [vals["modalidad"]]}
    wc2 = build_where_clause(f2, "")
    cnt2 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_programas WHERE {wc2}').fetchone()[0]
    ok("BWC: NBC+Depto+Mod", f"{cnt2} rows") if cnt2 > 0 else fail("BWC: NBC+Depto+Mod", f"0 rows — SQL: {wc2[:150]}")

    # 3. build_where_clause — all filters
    f3 = {
        "nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]],
        "modalidades": [vals["modalidad"]], "sectores": [vals["sector"]],
        "niveles": [vals["nivel"]], "caracteres": [vals["caracter"]],
        "campos_amplios": [vals["campo_amplio"]], "areas": [vals["area"]],
        "estados": [vals["estado"]], "busqueda_nombre": "sistemas",
        "cod_snies_programas": [vals["cod_snies"]]
    }
    wc3 = build_where_clause(f3, "")
    cnt3 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_programas WHERE {wc3}').fetchone()[0]
    # May be 0 due to extreme specificity - just verify no SQL error
    ok("BWC: all filters (no SQL error)", f"{cnt3} rows")

    # 4. build_where_clause — empty filters
    wc4 = build_where_clause({}, "p")
    assert wc4 == "1=1", f"Empty should be 1=1, got: {wc4}"
    ok("BWC: empty -> 1=1")

    # 5. build_where_clause_matriculados — NBC direct
    f5 = {"nbcs": [vals["nbc_sistemas"]]}
    conds5 = build_where_clause_matriculados(filtros=f5)
    wc5 = " AND ".join(conds5)
    cnt5 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_matriculados WHERE {wc5}').fetchone()[0]
    ok("BWC_M: NBC UPPER match", f"{cnt5} rows") if cnt5 > 0 else fail("BWC_M: NBC UPPER match", f"0 rows — SQL: {wc5}")

    # 6. build_where_clause_matriculados — bridge subquery
    f6 = {"modalidades": [vals["modalidad"]]}
    conds6 = build_where_clause_matriculados(filtros=f6)
    wc6 = " AND ".join(conds6)
    cnt6 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_matriculados WHERE {wc6}').fetchone()[0]
    ok("BWC_M: modalidad bridge", f"{cnt6} rows") if cnt6 > 0 else fail("BWC_M: modalidad bridge", f"0 rows")

    # 7. build_where_clause_matriculados — full combo
    f7 = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]], "modalidades": [vals["modalidad"]]}
    conds7 = build_where_clause_matriculados(filtros=f7)
    wc7 = " AND ".join(conds7)
    cnt7 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_matriculados WHERE {wc7}').fetchone()[0]
    ok("BWC_M: NBC+Depto+Mod combo", f"{cnt7} rows") if cnt7 > 0 else fail("BWC_M: NBC+Depto+Mod combo", f"0 rows")

    # 8. build_nbc_condition
    nbc_cond = build_nbc_condition(vals["nbc_sistemas"], "p.")
    cnt8 = conn.execute(f'SELECT COUNT(*) FROM snies.snies_programas p WHERE {nbc_cond}').fetchone()[0]
    ok("build_nbc_condition", f"{cnt8} rows") if cnt8 > 0 else fail("build_nbc_condition", f"0 rows — SQL: {nbc_cond[:100]}")

    conn.close()


# ---------------------------------------------------------------------------
# Query Functions — Programas (build_where_clause)
# ---------------------------------------------------------------------------

def test_programas_queries(vals):
    """Test query functions that hit snies_programas."""
    from data.queries import (
        get_estadisticas_basicas,
        get_benchmarking_data,
        get_programas_detalle,
        get_desglose_academico,
    )

    print("\n" + "=" * 70)
    print("PROGRAMAS QUERIES (build_where_clause)")
    print("=" * 70)

    # Scenario A: single NBC
    fA = {"nbcs": [vals["nbc_sistemas"]]}

    result = get_estadisticas_basicas(filtros=fA)
    if isinstance(result, dict) and result.get("total_programas", 0) > 0:
        ok("get_estadisticas_basicas(NBC)", f"programas={result['total_programas']}")
    else:
        fail("get_estadisticas_basicas(NBC)", f"{result}")

    result = get_benchmarking_data(filtros=fA)
    check("get_benchmarking_data(NBC)", result, min_rows=1)

    result = get_programas_detalle(filtros=fA)
    check("get_programas_detalle(NBC)", result, min_rows=1)

    result = get_desglose_academico(filtros=fA)
    if isinstance(result, dict) and any(
        len(v) > 0 for v in result.values() if hasattr(v, "__len__") and not isinstance(v, str)
    ):
        ok("get_desglose_academico(NBC)", f"keys={list(result.keys())[:5]}")
    else:
        fail("get_desglose_academico(NBC)", f"all empty: {type(result)}")

    # Scenario B: NBC + Depto + Modalidad
    fB = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]], "modalidades": [vals["modalidad"]]}

    result = get_estadisticas_basicas(filtros=fB)
    if isinstance(result, dict) and result.get("total_programas", 0) > 0:
        ok("get_estadisticas_basicas(NBC+Depto+Mod)", f"programas={result['total_programas']}")
    else:
        fail("get_estadisticas_basicas(NBC+Depto+Mod)", f"{result}")

    # Scenario C: no filters (all data)
    fC = {}
    result = get_estadisticas_basicas(filtros=fC)
    if isinstance(result, dict) and result.get("total_programas", 0) > 1000:
        ok("get_estadisticas_basicas(empty)", f"programas={result['total_programas']}")
    else:
        fail("get_estadisticas_basicas(empty)", f"{result}")


# ---------------------------------------------------------------------------
# Query Functions — Matriculados (build_where_clause_matriculados)
# ---------------------------------------------------------------------------

def test_matriculados_queries(vals):
    """Test query functions that hit snies_matriculados / snies_graduados."""
    from data.queries import (
        get_market_share,
        get_tendencia_matricula,
        get_tendencia_inscritos,
        get_tendencia_admitidos,
        get_tendencia_primer_curso,
        get_graduados_historico,
    )

    print("\n" + "=" * 70)
    print("MATRICULADOS QUERIES (build_where_clause_matriculados)")
    print("=" * 70)

    # Scenario A: single NBC
    fA = {"nbcs": [vals["nbc_sistemas"]]}

    check("get_market_share(NBC)", get_market_share(filtros=fA), min_rows=1)
    check("get_tendencia_matricula(NBC)", get_tendencia_matricula(filtros=fA), min_rows=1)
    check("get_graduados_historico(NBC)", get_graduados_historico(filtros=fA), min_rows=1)
    check("get_tendencia_inscritos(NBC)", get_tendencia_inscritos(filtros=fA), min_rows=1)
    check("get_tendencia_admitidos(NBC)", get_tendencia_admitidos(filtros=fA), min_rows=1)
    check("get_tendencia_primer_curso(NBC)", get_tendencia_primer_curso(filtros=fA), min_rows=1)

    # Scenario B: NBC + Depto
    fB = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]]}

    check("get_market_share(NBC+Depto)", get_market_share(filtros=fB), min_rows=1)
    check("get_tendencia_matricula(NBC+Depto)", get_tendencia_matricula(filtros=fB), min_rows=1)

    # Scenario C: NBC + Depto + Modalidad (via bridge)
    fC = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]], "modalidades": [vals["modalidad"]]}

    check("get_market_share(NBC+Depto+Mod)", get_market_share(filtros=fC), min_rows=1)
    check("get_tendencia_matricula(NBC+Depto+Mod)", get_tendencia_matricula(filtros=fC), min_rows=1)

    # Scenario D: empty filters (all data)
    fD = {}
    check("get_tendencia_matricula(empty)", get_tendencia_matricula(filtros=fD), min_rows=5)


# ---------------------------------------------------------------------------
# Query Functions — Explorador Interactivo
# ---------------------------------------------------------------------------

def test_explorador(vals):
    """Test get_datos_explorador_interactivo."""
    from data.queries import get_datos_explorador_interactivo

    print("\n" + "=" * 70)
    print("EXPLORADOR INTERACTIVO")
    print("=" * 70)

    fA = {"nbcs": [vals["nbc_sistemas"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano"], 2018, 2023, filtros_base=fA)
    check("explorador: NBC Matriculados por Ano", result, min_rows=1)

    fB = {"nbcs": [vals["nbc_sistemas"]], "deptos": [vals["depto"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano", "Sexo"], 2018, 2023, filtros_base=fB)
    check("explorador: NBC+Depto Matriculados Ano+Sexo", result, min_rows=1)

    # With modalidad filter (uses METODOLOGIA mapping — potential problem!)
    fC = {"modalidades": [vals["modalidad"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano"], 2018, 2023, filtros_base=fC)
    check("explorador: Modalidad filter", result, min_rows=1)

    # With sector filter
    fD = {"sectores": [vals["sector"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano"], 2018, 2023, filtros_base=fD)
    check("explorador: Sector filter", result, min_rows=1)

    # With nivel filter
    fE = {"niveles": [vals["nivel"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano"], 2018, 2023, filtros_base=fE)
    check("explorador: Nivel filter", result, min_rows=1)

    # With campo amplio filter (might be unhandled!)
    fF = {"campos_amplios": [vals["campo_amplio"]]}
    result = get_datos_explorador_interactivo("Matriculados", ["Ano"], 2018, 2023, filtros_base=fF)
    check("explorador: Campo amplio filter", result, min_rows=1)


# ---------------------------------------------------------------------------
# Query Functions — Comparativas
# ---------------------------------------------------------------------------

def test_comparativas(vals):
    """Test comparativa functions."""
    from data.queries import get_comparativa_snies_siet_por_depto, get_comparativa_tipo_formacion

    print("\n" + "=" * 70)
    print("COMPARATIVAS")
    print("=" * 70)

    fA = {"nbcs": [vals["nbc_sistemas"]]}

    check("comparativa_depto(NBC)", get_comparativa_snies_siet_por_depto(filtros=fA), min_rows=1)
    check("comparativa_tipo(NBC)", get_comparativa_tipo_formacion(filtros=fA), min_rows=1)


# ---------------------------------------------------------------------------
# Query Functions — SIET
# ---------------------------------------------------------------------------

def test_siet(vals):
    """Test SIET query functions (use own inline WHERE, not build_where_clause)."""
    from data.queries import get_estadisticas_siet, get_desglose_siet, get_programas_detalle_siet

    print("\n" + "=" * 70)
    print("SIET QUERIES")
    print("=" * 70)

    # No filters (all SIET data)
    result = get_estadisticas_siet()
    if isinstance(result, dict) and result.get("total_programas", 0) > 0:
        ok("get_estadisticas_siet(empty)", f"programas={result.get('total_programas')}")
    else:
        fail("get_estadisticas_siet(empty)", f"{result}")

    result = get_desglose_siet(None, None, None)
    if isinstance(result, dict) and len(result) > 0:
        ok("get_desglose_siet(empty)", f"keys={list(result.keys())[:3]}")
    else:
        fail("get_desglose_siet(empty)", f"empty or None")

    result = get_programas_detalle_siet()
    check("get_programas_detalle_siet(empty)", result, min_rows=1)


# ---------------------------------------------------------------------------
# Query Functions — Laboral (NBC-scalar, ML-based)
# ---------------------------------------------------------------------------

def test_laboral(vals):
    """Test laboral query functions (use scalar NBC, ML matching)."""
    from data.queries import (
        get_vacantes_reales,
        get_competencias_cuoc,
        get_salarios_reales,
        get_graduados_nacionales,
        get_tendencia_laboral_nbc,
        get_graduados_nbc_historico,
    )

    print("\n" + "=" * 70)
    print("LABORAL QUERIES (NBC scalar, ML matching)")
    print("=" * 70)

    nbc = vals["nbc_sistemas"]

    result = get_vacantes_reales(nbc=nbc)
    check("get_vacantes_reales(NBC)", result, min_rows=0)  # May be 0 if no vacancies data

    result = get_competencias_cuoc(nbc=nbc)
    if isinstance(result, tuple) and len(result) == 2:
        ok("get_competencias_cuoc(NBC)", f"({len(result[0])} conocim, {len(result[1])} destrezas)")
    else:
        check("get_competencias_cuoc(NBC)", result, min_rows=0)

    result = get_salarios_reales(nbc=nbc)
    check("get_salarios_reales(NBC)", result, is_dict=True, 
          required_keys=['ole_ibc', 'sigep_nivel_educativo', 'tiene_datos'])

    result = get_graduados_nacionales([nbc])
    if isinstance(result, int) and result > 0:
        ok("get_graduados_nacionales(NBC)", f"{result} graduados")
    elif isinstance(result, int):
        fail("get_graduados_nacionales(NBC)", f"returned 0")
    else:
        check("get_graduados_nacionales(NBC)", result, min_rows=1)

    # Tendencia laboral APE (vacantes/inscritos/colocados)
    result = get_tendencia_laboral_nbc(nbc)
    if isinstance(result, tuple) and len(result) == 3:
        vac, ins, col = result
        total = len(vac) + len(ins) + len(col)
        if total > 0:
            ok("get_tendencia_laboral_nbc(NBC)", f"({len(vac)} vac, {len(ins)} ins, {len(col)} col)")
        else:
            fail("get_tendencia_laboral_nbc(NBC)", "all DataFrames empty")
    else:
        fail("get_tendencia_laboral_nbc(NBC)", f"expected tuple(3), got {type(result).__name__}")

    # Graduados NBC historico (datos complementarios)
    result = get_graduados_nbc_historico(nbc)
    check("get_graduados_nbc_historico(NBC)", result, min_rows=1)


# ---------------------------------------------------------------------------
# Query Functions — Territorial
# ---------------------------------------------------------------------------

def test_territorial(vals):
    """Test territorial query functions."""
    from data.queries import get_conectividad_territorial, get_municipios_pdet

    print("\n" + "=" * 70)
    print("TERRITORIAL QUERIES")
    print("=" * 70)

    depto = vals["depto"]

    result = get_conectividad_territorial(depto)
    check("get_conectividad_territorial(depto)", result, min_rows=0)

    result = get_municipios_pdet(depto)
    check("get_municipios_pdet(depto)", result, min_rows=0)


# ---------------------------------------------------------------------------
# Cross-Validation: Data Consistency
# ---------------------------------------------------------------------------

def test_data_consistency(vals):
    """Cross-validate that filter results are consistent between tables."""
    from data.filters import build_where_clause, build_where_clause_matriculados

    print("\n" + "=" * 70)
    print("DATA CONSISTENCY CHECKS")
    print("=" * 70)

    conn = duckdb.connect("data/repositorio.duckdb", read_only=True)

    nbc = vals["nbc_sistemas"]

    # Check: programas count for NBC should be > 0
    f = {"nbcs": [nbc]}
    wc = build_where_clause(f, "")
    cnt_prog = conn.execute(f'SELECT COUNT(*) FROM snies.snies_programas WHERE {wc}').fetchone()[0]

    # Check: matriculados count for same NBC should be > 0
    conds = build_where_clause_matriculados(filtros=f)
    wc_m = " AND ".join(conds)
    cnt_mat = conn.execute(f'SELECT COUNT(*) FROM snies.snies_matriculados WHERE {wc_m}').fetchone()[0]

    ok(f"NBC programas={cnt_prog}, matriculados={cnt_mat}") if cnt_prog > 0 and cnt_mat > 0 \
        else fail(f"NBC data mismatch", f"programas={cnt_prog}, matriculados={cnt_mat}")

    # Check: NBC value case between tables
    nbc_prog = conn.execute(
        'SELECT DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" FROM snies.snies_programas '
        'WHERE UPPER("NÚCLEO_BÁSICO_DEL_CONOCIMIENTO") LIKE \'%SISTEMA%\' LIMIT 1'
    ).fetchone()[0]
    nbc_mat = conn.execute(
        'SELECT DISTINCT "NBC" FROM snies.snies_matriculados WHERE UPPER("NBC") LIKE \'%SISTEMA%\' LIMIT 1'
    ).fetchone()[0]
    if nbc_prog.upper() == nbc_mat.upper():
        ok(f"NBC case: prog=[{nbc_prog[:30]}] mat=[{nbc_mat[:30]}] — UPPER matches")
    else:
        fail(f"NBC case mismatch", f"prog=[{nbc_prog}] mat=[{nbc_mat}]")

    # Check: bridge match rate
    cnt_bridge = conn.execute(
        """SELECT COUNT(DISTINCT CAST("COD_SNIES_PROGRAMA" AS VARCHAR))
           FROM snies.snies_matriculados
           WHERE CAST("COD_SNIES_PROGRAMA" AS VARCHAR) IN
             (SELECT CAST("CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) FROM snies.snies_programas)"""
    ).fetchone()[0]
    cnt_total = conn.execute(
        "SELECT COUNT(DISTINCT CAST(\"COD_SNIES_PROGRAMA\" AS VARCHAR)) FROM snies.snies_matriculados"
    ).fetchone()[0]
    pct = cnt_bridge / cnt_total * 100 if cnt_total > 0 else 0
    ok(f"Bridge match: {cnt_bridge}/{cnt_total} ({pct:.0f}%)") if pct > 30 \
        else fail(f"Bridge match low", f"{pct:.0f}%")

    conn.close()


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

def test_performance(vals):
    """Performance benchmarks."""
    from data.queries import get_estadisticas_basicas, get_market_share, get_tendencia_matricula

    print("\n" + "=" * 70)
    print("PERFORMANCE")
    print("=" * 70)

    fA = {"nbcs": [vals["nbc_sistemas"]]}

    t0 = time.time()
    for _ in range(5):
        get_estadisticas_basicas(filtros=fA)
    t_stats = (time.time() - t0) / 5 * 1000
    ok(f"get_estadisticas_basicas avg={t_stats:.0f}ms") if t_stats < 500 else fail(f"slow", f"{t_stats:.0f}ms")

    t0 = time.time()
    for _ in range(5):
        get_market_share(filtros=fA)
    t_market = (time.time() - t0) / 5 * 1000
    ok(f"get_market_share avg={t_market:.0f}ms") if t_market < 1000 else fail(f"slow", f"{t_market:.0f}ms")

    t0 = time.time()
    for _ in range(5):
        get_tendencia_matricula(filtros=fA)
    t_tend = (time.time() - t0) / 5 * 1000
    ok(f"get_tendencia_matricula avg={t_tend:.0f}ms") if t_tend < 500 else fail(f"slow", f"{t_tend:.0f}ms")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("=" * 70)
    print("   ESTUDIO DE CONTEXTO — Query Test Suite")
    print("=" * 70)

    vals = load_real_values()
    print(f"\nTest values loaded:")
    print(f"  NBC: {vals['nbc_sistemas']}")
    print(f"  Depto: {vals['depto']}")
    print(f"  Modalidad: {vals['modalidad']}")
    print(f"  Sector: {vals['sector']}")
    print(f"  Nivel: {vals['nivel']}")
    print(f"  Carácter: {vals['caracter']}")
    print(f"  Campo Amplio: {vals['campo_amplio']}")
    print(f"  NBC case match: {vals['nbc_case_match']}")

    test_filter_builders(vals)
    test_programas_queries(vals)
    test_matriculados_queries(vals)
    test_explorador(vals)
    test_comparativas(vals)
    test_siet(vals)
    test_laboral(vals)
    test_territorial(vals)
    test_data_consistency(vals)
    test_performance(vals)

    print("\n" + "=" * 70)
    print(f"  TOTAL: {PASS} OK  |  {FAIL} FAIL  |  {SKIP} SKIP")
    if FAIL > 0:
        print("\n  FAILURES:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"    - {name}: {detail}")
    print("=" * 70)

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
