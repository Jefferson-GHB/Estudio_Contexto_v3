"""
Genera gráficos de evaluación del modelo ML a partir del JSON de resultados.

Uso: python generar_graficos.py [ruta_json]

Si no se especifica ruta_json, usa el archivo más reciente en resultados/.
"""
import sys, os, json, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTADOS_DIR = os.path.join(SCRIPT_DIR, "resultados")


def encontrar_json() -> str:
    """Encuentra el archivo JSON de evaluación más reciente."""
    patron = os.path.join(RESULTADOS_DIR, "evaluacion_*.json")
    archivos = sorted(glob.glob(patron), key=os.path.getmtime, reverse=True)
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos JSON en {RESULTADOS_DIR}")
    return archivos[0]


def generar_graficos(json_path: str, output_dir: str = None):
    """Genera los 3 gráficos de evaluación a partir del JSON."""
    if output_dir is None:
        output_dir = RESULTADOS_DIR

    with open(json_path, encoding='utf-8') as f:
        report = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    # ── Figura 1: Métricas agregadas ──
    metric_order = ['P@1', 'P@3', 'P@5', 'P@10', 'R@5', 'F1@5', 'MRR', 'MAP', 'NDCG@10']
    metric_names = [k for k in metric_order if k in report['metrics_avg']]
    values = [report['metrics_avg'][k] for k in metric_names]
    errors = [report['metrics_std'].get(k, 0) for k in metric_names]

    fig, ax = plt.subplots(figsize=(11, 5))
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(values)))
    bars = ax.bar(metric_names, values, yerr=errors, color=colors, edgecolor='white', linewidth=0.8, capsize=4)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                f'{val:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylabel('Score')
    ax.set_title(f'Métricas del Modelo ML — Puente Semántico SNIES↔SIET\n'
                 f'Modelo: {report["model"]} | {report["date"][:10]} | '
                 f'{report["nbcs_with_areas"]} NBCs evaluados', fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.grid(axis='y', alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    plt.tight_layout()
    graph_path = os.path.join(output_dir, 'metricas_agregadas.png')
    plt.savefig(graph_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] {graph_path}")

    # ── Figura 2: Precisión por área SIET ──
    areas = sorted(report['per_area'].items(), key=lambda x: x[1]['precision_pct'], reverse=True)
    if areas:
        fig, ax = plt.subplots(figsize=(11, max(4.5, len(areas) * 0.35)))
        names = [a[:60] for a, _ in areas]
        precs = [s['precision_pct'] for _, s in areas]
        colors_area = plt.cm.RdYlGn(np.array(precs) / 100.0)

        bars = ax.barh(range(len(names)), precs, color=colors_area, edgecolor='white', linewidth=0.5)

        for i, (name, prec) in enumerate(zip(names, precs)):
            ax.text(prec + 1, i, f'{prec:.0f}%', va='center', fontsize=8, fontweight='bold')

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7)
        ax.set_xlabel('Precisión Top-5 (%)')
        ax.set_title(f'Precisión por Área SIET\n'
                     f'Total: {report["correct_top5"]}/{report["nbcs_with_areas"]} '
                     f'({report["precision_top5_pct"]}%)', fontsize=11)
        ax.set_xlim(0, 115)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        graph_path = os.path.join(output_dir, 'precision_por_area.png')
        plt.savefig(graph_path, dpi=200, bbox_inches='tight')
        plt.close()
        print(f"[OK] {graph_path}")

    # ── Figura 3: Distribución de scores ──
    correct_scores = []
    incorrect_scores = []
    for r in report['per_nbc']:
        if not r['retrieved_scores']:
            continue
        if r['correct_in_top5']:
            correct_scores.append(float(r['retrieved_scores'][0]))
        else:
            incorrect_scores.append(float(r['retrieved_scores'][0]))

    fig, ax = plt.subplots(figsize=(9, 5))
    bins = np.linspace(0, 1, 21)
    if correct_scores:
        ax.hist(correct_scores, bins=bins, alpha=0.7,
                label=f'Correctas (Top-5) — n={len(correct_scores)}',
                color='#2ecc71', edgecolor='white', linewidth=0.5)
    if incorrect_scores:
        ax.hist(incorrect_scores, bins=bins, alpha=0.8,
                label=f'Incorrectas (Top-5) — n={len(incorrect_scores)}',
                color='#e74c3c', edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Score del Top Match', fontsize=11)
    ax.set_ylabel('Frecuencia (NBCs)', fontsize=11)
    ax.set_title(f'Distribución de Scores: Match Correcto vs Incorrecto\n'
                 f'Modelo: {report["model"]}', fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    graph_path = os.path.join(output_dir, 'score_distribution.png')
    plt.savefig(graph_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] {graph_path}")

    print(f"\nGráficos generados en: {output_dir}")
    print(f"  {len(os.listdir(output_dir))} archivos totales")


if __name__ == "__main__":
    try:
        json_path = sys.argv[1] if len(sys.argv) > 1 else encontrar_json()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    generar_graficos(json_path)
