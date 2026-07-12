"""
Benchmark de modelos de embedding para puente SNIES-SIET.

Evalua multiples modelos contra TODOS los NBCs del catalogo.
Metricas: precision (coherencia area), matches encontrados, score_spread,
         top match quality, tiempo de encoding.

Uso:
  python scripts/benchmark_modelos.py [--model MODEL_NAME] [--nbc NBC_NAME]
  python scripts/benchmark_modelos.py --all   # Evalua todos los modelos disponibles
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
import pandas as pd
from config.database import get_conn
from services.ml.snies_etdh import match_nbc_to_siet_v2, validate_bridge, _get_nbc_skills_profile
from data.transform import normalize_nbc_name, build_canonical_siet_mapping, _norm

# Modelos a evaluar (configurable via env EMBEDDING_MODEL)
MODELS = {
    "MiniLM": "paraphrase-multilingual-MiniLM-L12-v2",
    "GTE": "Alibaba-NLP/gte-multilingual-base",
    "MiniLM-E5": "intfloat/multilingual-e5-large",
}

def evaluate_model(model_name: str, model_id: str, nbcs: list, conn) -> dict:
    """Evalua un modelo contra una lista de NBCs."""
    os.environ["EMBEDDING_MODEL"] = model_id
    
    # Forzar recarga del modelo con el nuevo nombre
    import services.ml.matching as ml_matching
    ml_matching._model = None
    ml_matching._model_failed = False
    ml_matching._embeddings_cache = {}
    ml_matching.MODEL_NAME = model_id
    
    # Limpiar cache de corpus SIET (el corpus usa modelo para embeddings)
    import services.ml.snies_etdh as snies_etdh
    snies_etdh._siet_corpus_cache = None
    
    # Invalidar cache en disco de embeddings viejos
    cache_dir = ml_matching.CACHE_DIR
    for f in cache_dir.glob("siet_corpus_*.pkl"):
        f.unlink()
    
    results = []
    start_time = time.time()
    total_matches = 0
    valid_count = 0
    area_coherent = 0
    total_spread = 0.0
    
    for nbc in nbcs:
        t0 = time.time()
        df = match_nbc_to_siet_v2(nbc, conn, top_k=10)
        elapsed = time.time() - t0
        
        v = validate_bridge(nbc, df, conn)
        n = len(df)
        total_matches += n
        if v['is_valid']:
            valid_count += 1
        
        # Check area coherence: top match area in expected areas
        chain = snies_etdh._resolve_structural_chain(nbc, conn)
        expected = set(_norm(a) for a in chain.get('areas_desempeno_siet', []))
        if n > 0 and expected:
            top_area = _norm(str(df.iloc[0].get('area_desempeno', '')))
            if top_area in expected:
                area_coherent += 1
        
        spread = v['metrics'].get('score_spread', 0)
        total_spread += spread
        
        results.append({
            'nbc': nbc[:40],
            'matches': n,
            'score': round(float(df.iloc[0]['score_final']), 3) if n > 0 else 0,
            'area_ok': top_area in expected if (n > 0 and expected) else None,
            'spread': round(spread, 3),
            'time_ms': round(elapsed * 1000, 0),
        })
    
    total_time = time.time() - start_time
    
    df_results = pd.DataFrame(results)
    return {
        'model': model_name,
        'nbcs_tested': len(nbcs),
        'total_matches': total_matches,
        'avg_matches': round(total_matches / len(nbcs), 1),
        'valid_pct': round(100 * valid_count / len(nbcs), 1),
        'area_coherent_pct': round(100 * area_coherent / len(nbcs), 1),
        'avg_spread': round(total_spread / len(nbcs), 3),
        'total_time_s': round(total_time, 1),
        'avg_time_ms': round(1000 * total_time / len(nbcs), 0),
        'details': df_results,
    }


def evaluate_all(conn) -> list:
    """Evalua todos los modelos y genera reporte comparativo."""
    # Cargar TODOS los NBCs del catalogo
    nbcs_raw = conn.execute("""
        SELECT DISTINCT NBC FROM catalogo_curado.catalogo_nbc_snies
        WHERE NBC IS NOT NULL
        ORDER BY NBC
    """).fetchall()
    nbcs = [normalize_nbc_name(r[0], conn) for r in nbcs_raw]
    nbcs = list(dict.fromkeys(nbcs))  # dedup preserving order
    
    print(f"Benchmark: {len(nbcs)} NBCs unicos del catalogo\n")
    
    results = []
    for model_name, model_id in MODELS.items():
        print(f"\n{'='*60}")
        print(f"EVALUANDO: {model_name} ({model_id})")
        print(f"{'='*60}")
        
        try:
            result = evaluate_model(model_name, model_id, nbcs, conn)
            results.append(result)
            print(f"  NBCs: {result['nbcs_tested']}")
            print(f"  Matches/nbc: {result['avg_matches']}")
            print(f"  Area OK: {result['area_coherent_pct']}%")
            print(f"  Valid: {result['valid_pct']}%")
            print(f"  Avg spread: {result['avg_spread']}")
            print(f"  Time: {result['total_time_s']}s ({result['avg_time_ms']}ms/nbc)")
        except Exception as e:
            print(f"  FAILED: {e}")
    
    # Reporte comparativo
    if len(results) >= 2:
        print(f"\n{'='*60}")
        print("COMPARATIVA FINAL")
        print(f"{'='*60}")
        headers = f"{'Model':12s} | {'NBCs':5s} | {'Avg M':6s} | {'Area%':6s} | {'Valid%':6s} | {'Spread':6s} | {'Time':8s}"
        print(headers)
        print("-" * len(headers))
        for r in results:
            print(f"{r['model']:12s} | {r['nbcs_tested']:5d} | {r['avg_matches']:6.1f} | {r['area_coherent_pct']:5.1f}% | {r['valid_pct']:5.1f}% | {r['avg_spread']:6.3f} | {r['total_time_s']:6.1f}s")
    
    return results


if __name__ == "__main__":
    conn = get_conn()
    # Pre-construir mapeo canonico (se usara en todos los modelos)
    print("[Benchmark] Pre-construyendo mapeo canonico SIET...")
    canonical = build_canonical_siet_mapping(conn)
    print(f"[Benchmark] {len(canonical)} mappings, {len(set(canonical.values()))} canonicos\n")
    
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        model_name = sys.argv[idx + 1]
        model_id = MODELS.get(model_name, model_name)
        nbcs_all = conn.execute("SELECT DISTINCT NBC FROM catalogo_curado.catalogo_nbc_snies WHERE NBC IS NOT NULL ORDER BY NBC").fetchall()
        nbcs = [normalize_nbc_name(r[0], conn) for r in nbcs_all]
        nbcs = list(dict.fromkeys(nbcs))
        evaluate_model(model_name, model_id, nbcs, conn)
    else:
        evaluate_all(conn)
    
    conn.close()
