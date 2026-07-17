"""
Suite de Evaluacion Profesional del Modelo ML — Puente SNIES-SIET.

Metricas:
  - Precision@K (K=1,3,5,10): % de top-K que son correctos
  - Recall@K: % de programas correctos recuperados en top-K
  - F1@K: media armonica de Precision y Recall
  - MRR (Mean Reciprocal Rank): posicion del primer acierto
  - MAP (Mean Average Precision): precision promedio en todos los ranks
  - NDCG@K: Normalized Discounted Cumulative Gain
  - Coverage: % de NBCs con al menos 1 match

Reportes:
  - Tabla por NBC (top match, area, score, correcto)
  - Desglose por area SIET (precision por area)
  - Graficos: distribucion de scores, precision vs recall
  - JSON exportable para auditoria

Uso: python scripts/evaluar_modelo.py [--model MODEL_NAME] [--report REPORT_PATH]
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict

from config.database import get_conn
from data.transform import normalize_nbc_name, _norm, build_canonical_siet_mapping
from services.ml.snies_etdh import (match_nbc_to_siet_v2, validate_bridge,
                                     _get_nbc_skills_profile, _resolve_structural_chain,
                                     _strip_siet_prefix)

# ======================================================================
# METRICAS
# ======================================================================

def precision_at_k(relevant, retrieved, k):
    """Precision@K: cuantos de los top-K son relevantes."""
    if not retrieved: return 0.0
    top_k = retrieved[:k]
    return sum(1 for item in top_k if item in relevant) / k


def recall_at_k(relevant, retrieved, k):
    """Recall@K: cuantos de los relevantes estan en top-K."""
    if not relevant: return 1.0
    top_k = retrieved[:k]
    return sum(1 for item in top_k if item in relevant) / len(relevant)


def f1_at_k(precision, recall):
    """F1 score."""
    if precision + recall == 0: return 0.0
    return 2 * precision * recall / (precision + recall)


def mrr(relevant, retrieved, max_k=10):
    """Mean Reciprocal Rank: 1 / posicion del primer acierto."""
    for i, item in enumerate(retrieved[:max_k]):
        if item in relevant:
            return 1.0 / (i + 1)
    return 0.0


def average_precision(relevant, retrieved, max_k=10):
    """Average Precision@K: media de P@k en posiciones de acierto."""
    score = 0.0
    num_hits = 0
    for i, item in enumerate(retrieved[:max_k]):
        if item in relevant:
            num_hits += 1
            score += num_hits / (i + 1)
    if num_hits == 0: return 0.0
    return score / num_hits


def dcg_at_k(scores, k):
    """Discounted Cumulative Gain."""
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(scores[:k]))


def ndcg_at_k(relevance_list, k):
    """Normalized DCG: DCG / IDCG. relevance_list: lista binaria ordenada por rank."""
    if not any(relevance_list): return 0.0
    dcg_val = dcg_at_k(relevance_list, k)
    ideal = sorted(relevance_list, reverse=True)[:k]
    idcg_val = dcg_at_k(ideal, k)
    if idcg_val == 0: return 0.0
    return dcg_val / idcg_val


# ======================================================================
# DATOS
# ======================================================================

def load_data(conn):
    """Carga NBCs, corpus SIET y areas esperadas."""
    nbcs_raw = conn.execute(
        "SELECT DISTINCT NBC FROM catalogo_curado.catalogo_nbc_snies WHERE NBC IS NOT NULL ORDER BY NBC"
    ).fetchall()
    all_nbcs = [normalize_nbc_name(r[0], conn) for r in nbcs_raw]
    all_nbcs = list(dict.fromkeys(all_nbcs))

    canonical = build_canonical_siet_mapping(conn)
    df = conn.execute("""
        SELECT DISTINCT "Nombre Programa" as nombre, "Area de Desempeño" as area
        FROM siet.siet_programas WHERE "Nombre Programa" IS NOT NULL AND LENGTH("Nombre Programa") > 5
    """).fetchdf()
    df['canonical'] = df['nombre'].map(canonical).fillna(df['nombre'])
    df = df.drop_duplicates(subset=['canonical'])
    corpus_names = df['canonical'].tolist()
    corpus_areas = df['area'].apply(_norm).tolist()

    expected_areas = []
    for nbc in all_nbcs:
        chain = _resolve_structural_chain(nbc, conn)
        areas = set(_norm(a) for a in chain.get('areas_desempeno_siet', []))
        expected_areas.append(areas)

    return all_nbcs, corpus_names, corpus_areas, expected_areas


# ======================================================================
# EVALUACION PRINCIPAL
# ======================================================================

def evaluate(conn, model_name="MiniLM"):
    """Ejecuta evaluacion completa del modelo."""
    print(f"{'='*70}")
    print(f"EVALUACION DEL MODELO ML — Puente SNIES <-> SIET/ETDH")
    print(f"Modelo: {model_name}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}\n")

    t0 = time.time()
    all_nbcs, corpus_names, corpus_areas, expected_areas = load_data(conn)

    # Resultados
    results = []
    per_area = defaultdict(lambda: {'ok': 0, 'total': 0, 'precision': [], 'recall': [], 'f1': []})
    metrics_per_k = defaultdict(list)

    for i, (nbc, expected) in enumerate(zip(all_nbcs, expected_areas)):
        canon = normalize_nbc_name(nbc, conn)

        # Ejecutar pipeline
        df_results = match_nbc_to_siet_v2(canon, conn, top_k=10)

        if df_results.empty:
            results.append({
                'nbc': nbc, 'top_match': '', 'top_area': '', 'top_score': 0,
                'matches_found': 0, 'correct_in_top5': False, 'mrr': 0,
                'areas_relevant': sorted(expected),
                'retrieved_areas': [],
                'retrieved_scores': [],
            })
            continue

        # Obtener areas de los resultados
        retrieved_areas = []
        retrieved_scores = []
        for _, row in df_results.iterrows():
            retrieved_areas.append(_norm(str(row.get('area_desempeno', ''))))
            retrieved_scores.append(float(row.get('score_final', 0)))

        # Determinar relevancia per-documento (area correcta = 1, incorrecta = 0)
        relevant_areas = expected if expected else set()
        relevance_list = [1 if a in relevant_areas else 0 for a in retrieved_areas]

        # Metricas por K
        for k in [1, 3, 5, 10]:
            p = precision_at_k(relevant_areas, retrieved_areas, k)
            r = recall_at_k(relevant_areas, retrieved_areas, k)
            f = f1_at_k(p, r)
            metrics_per_k[f'P@{k}'].append(p)
            metrics_per_k[f'R@{k}'].append(r)
            metrics_per_k[f'F1@{k}'].append(f)

        # MRR
        m = mrr(relevant_areas, retrieved_areas)

        # MAP (usa areas como tokens de relevancia binaria)
        ap = average_precision(relevant_areas, retrieved_areas)

        # NDCG con relevancia per-documento
        ndcg = ndcg_at_k(relevance_list, 10)

        metrics_per_k['MRR'].append(m)
        metrics_per_k['MAP'].append(ap)
        metrics_per_k['NDCG@10'].append(ndcg)

        # Correcto en top-5?
        top5_correct = any(a in relevant_areas for a in retrieved_areas[:5]) if relevant_areas else False

        # Per-area stats
        for area in relevant_areas:
            per_area[area]['total'] += 1
            if top5_correct:
                per_area[area]['ok'] += 1
            per_area[area]['precision'].append(precision_at_k(relevant_areas, retrieved_areas, 5))
            per_area[area]['recall'].append(recall_at_k(relevant_areas, retrieved_areas, 5))

        results.append({
            'nbc': nbc,
            'top_match': df_results.iloc[0]['nombre_programa'] if len(df_results) > 0 else '',
            'top_area': retrieved_areas[0] if retrieved_areas else '',
            'top_score': retrieved_scores[0] if retrieved_scores else 0,
            'matches_found': len(df_results),
            'correct_in_top5': top5_correct,
            'mrr': m,
            'map': ap,
            'ndcg': ndcg,
            'areas_relevant': sorted(relevant_areas) if relevant_areas else [],
            'retrieved_areas': retrieved_areas[:5],
            'retrieved_scores': retrieved_scores[:5],
        })

    elapsed = time.time() - t0

    # ==================================================================
    # REPORTE
    # ==================================================================
    n_total = len(results)
    n_with_areas = sum(1 for r in results if r['areas_relevant'])
    n_correct_top5 = sum(1 for r in results if r['correct_in_top5'])

    report = {
        'model': model_name,
        'date': datetime.now().isoformat(),
        'total_nbcs': n_total,
        'nbcs_with_areas': n_with_areas,
        'correct_top5': n_correct_top5,
        'precision_top5_pct': round(100 * n_correct_top5 / max(n_with_areas, 1), 1),
        'elapsed_seconds': round(elapsed, 1),
        'metrics_avg': {k: round(np.mean(v), 4) for k, v in metrics_per_k.items() if v},
        'metrics_std': {k: round(np.std(v), 4) for k, v in metrics_per_k.items() if v},
        'per_area': {
            area: {
                'nbc_count': stats['total'],
                'correct': stats['ok'],
                'precision_pct': round(100 * stats['ok'] / max(stats['total'], 1), 1),
                'avg_precision@5': round(np.mean(stats['precision']), 3) if stats['precision'] else 0,
            }
            for area, stats in sorted(per_area.items())
        },
        'per_nbc': results,
    }

    # ==================================================================
    # IMPRIMIR REPORTE
    # ==================================================================
    print(f"RESUMEN DE METRICAS")
    print(f"{'='*50}")
    print(f"  NBCs evaluados:              {n_total}")
    print(f"  NBCs con areas SIET:         {n_with_areas}")
    print(f"  Correctos en Top-5:          {n_correct_top5}/{n_with_areas} ({report['precision_top5_pct']}%)")
    print()

    print(f"METRICAS AGREGADAS (promedio sobre {n_with_areas} NBCs)")
    print(f"{'='*55}")
    headers = f"{'Metrica':15s} {'Promedio':10s} {'StdDev':10s}"
    print(headers)
    print("-" * 35)
    for k in ['P@1', 'P@3', 'P@5', 'P@10', 'R@1', 'R@3', 'R@5', 'F1@5', 'MRR', 'MAP', 'NDCG@10']:
        if k in report['metrics_avg']:
            print(f"  {k:13s} {report['metrics_avg'][k]:10.4f} {report['metrics_std'][k]:10.4f}")

    print(f"\nDESGLOSE POR AREA SIET")
    print(f"{'='*60}")
    print(f"{'Area SIET':45s} {'NBCs':6s} {'OK':5s} {'Prec%':7s}")
    print("-" * 65)
    for area, stats in sorted(report['per_area'].items(), key=lambda x: x[1]['precision_pct'], reverse=True):
        bar = "#" * int(stats['precision_pct'] / 5)
        print(f"  {area[:45]:45s} {stats['nbc_count']:5d}  {stats['correct']:4d}  {stats['precision_pct']:5.1f}% {bar}")

    print(f"\nTOP 5 MEJORES NBCs (por MRR)")
    best = sorted(results, key=lambda r: r['mrr'], reverse=True)[:5]
    for r in best:
        print(f"  {r['nbc'][:40]:40s} MRR={r['mrr']:.3f} MAP={r['map']:.3f} Top='{r['top_match'][:40]}'")

    print(f"\nTOP 5 PEORES NBCs (por MRR)")
    worst = sorted(results, key=lambda r: r['mrr'])[:5]
    for r in worst:
        print(f"  {r['nbc'][:40]:40s} MRR={r['mrr']:.3f} Top='{r['top_match'][:40]}'")

    print(f"\n  Tiempo total: {elapsed:.1f}s ({elapsed/60:.1f}min)")

    return report


# ======================================================================
# GRAFICOS
# ======================================================================

def generar_graficos(report, output_dir="scripts/evaluacion_output"):
    """Genera graficos de la evaluacion usando matplotlib."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("\n[Graficos] matplotlib no disponible — saltando graficos")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Figura 1: Metricas agregadas (bar chart)
    fig, ax = plt.subplots(figsize=(10, 5))
    metric_names = [k for k in ['P@1', 'P@3', 'P@5', 'P@10', 'R@5', 'F1@5', 'MRR', 'MAP', 'NDCG@10']
                    if k in report['metrics_avg']]
    values = [report['metrics_avg'][k] for k in metric_names]
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(values)))
    bars = ax.bar(metric_names, values, color=colors, edgecolor='white', linewidth=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.3f}', ha='center', va='bottom', fontsize=8)
    ax.set_ylabel('Score')
    ax.set_title(f'Metricas del Modelo ML — Puente SNIES-SIET\n{report["model"]} — {report["date"][:10]}')
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'metricas_agregadas.png'), dpi=150)
    plt.close()
    print(f"[Graficos] metricas_agregadas.png guardado")

    # Figura 2: Precision por area SIET (horizontal bar)
    areas = sorted(report['per_area'].items(), key=lambda x: x[1]['precision_pct'], reverse=True)
    if areas:
        fig, ax = plt.subplots(figsize=(10, max(5, len(areas) * 0.4)))
        names = [a[:45] for a, _ in areas]
        precs = [s['precision_pct'] for _, s in areas]
        bars = ax.barh(range(len(names)), precs, color=plt.cm.RdYlGn(np.array(precs)/100))
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7)
        ax.set_xlabel('Precision Top-5 (%)')
        ax.set_title(f'Precision por Area SIET\nTotal: {report["correct_top5"]}/{report["nbcs_with_areas"]} ({report["precision_top5_pct"]}%)')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'precision_por_area.png'), dpi=150)
        plt.close()
        print(f"[Graficos] precision_por_area.png guardado")

    # Figura 3: Distribucion de scores Top-5 (histogram)
    correct_scores = []
    incorrect_scores = []
    for r in report['per_nbc']:
        if not r['retrieved_scores']: continue
        if r['correct_in_top5']:
            correct_scores.append(r['retrieved_scores'][0])
        else:
            incorrect_scores.append(r['retrieved_scores'][0])

    fig, ax = plt.subplots(figsize=(8, 4))
    if correct_scores:
        ax.hist(correct_scores, bins=15, alpha=0.7, label=f'Correctas (n={len(correct_scores)})', color='#2ecc71')
    if incorrect_scores:
        ax.hist(incorrect_scores, bins=15, alpha=0.7, label=f'Incorrectas (n={len(incorrect_scores)})', color='#e74c3c')
    ax.set_xlabel('Score del Top Match')
    ax.set_ylabel('Frecuencia')
    ax.set_title('Distribucion de Scores: Correctas vs Incorrectas')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'score_distribution.png'), dpi=150)
    plt.close()
    print(f"[Graficos] score_distribution.png guardado")

    print(f"\n[Graficos] {len(os.listdir(output_dir))} archivos en {output_dir}")


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    model_name = "MiniLM"
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        model_name = sys.argv[idx + 1]

    conn = get_conn()
    try:
        report = evaluate(conn, model_name=model_name)

        # Guardar JSON
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir,
            f"evaluacion_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nReporte JSON: {json_path}")

        # Generar graficos
        generar_graficos(report, output_dir)

    finally:
        conn.close()
