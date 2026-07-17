# Reports — Resultados y Evaluación

## Qué hay aquí

| Archivo | Contenido |
|---------|-----------|
| `evaluacion_MiniLM_*.json` | Métricas completas del matching semántico (56 NBCs, auditable) |
| `figures/metricas_agregadas.png` | Barras: P@K, MRR, MAP, NDCG@10 |
| `figures/precision_por_area.png` | Precisión Top-5 por área de desempeño SIET |
| `figures/score_distribution.png` | Distribución de scores: match correcto vs incorrecto |
| `figures/dashboard_overview.png` | Captura del dashboard en ejecución |

## Métricas del modelo (MiniLM, 384 dim, 56 NBCs)

| Sigla | Qué mide | Cómo se interpreta | Valor |
|-------|----------|-------------------|-------|
| **P@K** | De los K mejores matches, ¿cuántos son correctos? | Más alto = menos ruido en el top | P@1=78.6%, P@5=47.1% |
| **R@K** | ¿Cuántas áreas correctas encontré en el top-K? | Más alto = mejor cobertura | R@5=1.56 áreas por NBC |
| **F1@5** | Balance entre precisión y cobertura | >0.5 es aceptable, >0.7 es fuerte | 0.651 |
| **MRR** | ¿En qué posición aparece el primer acierto? | 1.0 = siempre primero. >0.8 = muy bueno | **0.810** |
| **MAP** | Precisión promedio en todos los ranks | >0.7 = ranking de calidad | **0.794** |
| **NDCG@10** | ¿Qué tan cerca está el ranking del ideal? | >0.8 = buen ordenamiento | **0.813** |

## Veredicto

El modelo alcanza **78.6% de acierto en el primer match** y **81% en calidad de ranking**,
con cobertura completa: todos los NBCs con áreas mapeadas (47/56) tienen al menos un
match correcto en el top-5. Las áreas con vocabulario solapado (finanzas/administración,
arte/humanidades) introducen ruido en los matches secundarios, que es esperable en un
sistema no supervisado de propósito general.

## Ground truth

La evaluación usa como verdad de referencia la cadena taxonómica oficial:
**NBC → CINE-F → Área de desempeño SIET**. Si el modelo recupera un programa SIET
cuya área coincide con la esperada, el match se considera correcto. Este criterio es
determinístico y verificable contra los catálogos en `catalogo/`.

## Regenerar resultados

```bash
python admin/evaluacion/evaluar_modelo.py      # Evalúa los 56 NBCs (~7 min)
python admin/evaluacion/generar_graficos.py    # Genera gráficos desde el JSON
```
