# Validación de Componentes de Inteligencia Artificial

Métricas y métodos de validación aplicados a los tres componentes de IA del sistema. 
La validación del matching semántico sigue el estándar de recuperación de información
(Information Retrieval) con ground truth taxonómico real. Los resultados se generan
mediante `admin/evaluacion/evaluar_modelo.py` y los gráficos via `admin/evaluacion/generar_graficos.py`.

---

## 1. Evaluación del Matching Semántico (MiniLM) — Métricas IR

### 1.1 Ground truth

Cada NBC (Núcleo Básico del Conocimiento) se mapea a áreas de desempeño SIET
específicas mediante la cadena estructural CINE-F → CUOC → SIET
(`services/ml/snies_etdh.py:_resolve_structural_chain`). Este mapeo es determinístico
y verificable contra los catálogos oficiales (`catalogo_curado.*`). Se usa como
ground truth para evaluar si los programas SIET recuperados pertenecen al área correcta.

### 1.2 Métricas agregadas — 56 NBCs evaluados

| Métrica | Valor | Interpretación |
|:--------|:------|:---------------|
| **P@1** (Precision@1) | **0.786** | El 78.6% de los mejores matches están en el área correcta |
| **P@3** (Precision@3) | 0.661 | El 66.1% de los 3 mejores están en área correcta |
| **P@5** (Precision@5) | 0.471 | El 47.1% de los 5 mejores están en área correcta |
| **P@10** (Precision@10) | 0.252 | El 25.2% de los 10 mejores están en área correcta |
| **R@5** (Recall@5) | 1.557 | Se recupera en promedio 1.5 áreas correctas por NBC en el top-5 |
| **F1@5** | 0.651 | Media armónica de P@5 y R@5 |
| **MRR** (Mean Reciprocal Rank) | **0.810** | El primer match correcto aparece en posición ~1.24 en promedio |
| **MAP** (Mean Average Precision) | **0.794** | Precisión promedio en todos los ranks de acierto |
| **NDCG@10** | **0.813** | Calidad del ranking al 81.3% del ideal |
| **Top-5 correcto** | **100%** (47/47) | Todos los NBCs con áreas mapeadas tienen al menos 1 match correcto |
| **Cobertura** | 47/56 (83.9%) | NBCs con áreas SIET vía cadena CINE-F |

### 1.3 Precisión por área SIET

| Área SIET | NBCs | Precisión Top-5 |
|:----------|:-----|:----------------|
| Arte, Cultura, Esparcimiento y Deportes | 9 | 100% |
| Ciencias Naturales Aplicadas y Relacionadas | 19 | 100% |
| Ciencias Sociales, Educativas y Religiosas | 14 | 100% |
| Explotación Primaria y Extractiva | 18 | 100% |
| Finanzas y Administración | 11 | 100% |
| Oficios, Operación Equipo y Transporte | 13 | 100% |
| Procesamiento, Fabricación y Ensamblaje | 13 | 100% |
| Salud | 11 | 100% |
| Ventas y Servicios | 6 | 100% |
| **Total** | **114 NBC-área** | **100%** |

### 1.4 Gráficos de evaluación

Los siguientes gráficos se generan automáticamente desde `admin/evaluacion/generar_graficos.py`
a partir del JSON de resultados:

| Gráfico | Descripción |
|:--------|:------------|
| `reports/figures/metricas_agregadas.png` | Barras con P@1-10, R@5, F1@5, MRR, MAP, NDCG |
| `reports/figures/precision_por_area.png` | Precisión Top-5 por área SIET (barras horizontales) |
| `reports/figures/score_distribution.png` | Distribución de scores: match correcto vs incorrecto |

### 1.5 Ejecución y reproducibilidad

```bash
# Evaluar el modelo (genera JSON con todas las métricas)
python admin/evaluacion/evaluar_modelo.py

# Generar gráficos a partir del JSON
python admin/evaluacion/generar_graficos.py
```

Los resultados crudos se guardan en `admin/evaluacion/resultados/` y se copian a `reports/`
para consulta durante la presentación. El JSON incluye métricas por NBC individual,
permitiendo auditoría completa del proceso de evaluación.

---

## 2. Búsqueda Semántica: Threshold Adaptativo

### 2.1 Lógica de umbral

El sistema usa un **umbral adaptativo** en lugar de un valor fijo. Esto evita tanto
falsos positivos (matches débiles en campos con poca oferta) como falsos negativos
(campos donde ninguna ocupación supera un umbral arbitrario).

| Parámetro | Valor | Ubicación |
|:----------|:------|:----------|
| Modelo | `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones) | `services/ml/matching.py:9` |
| Corpus | Ocupaciones CUOC (680), conocimientos (3,599), destrezas (4,422), programas SIET (11,233) | `services/cache_data/ml_embeddings/` |
| Cache | Dos niveles: memoria (dict) + disco (180+ archivos .pkl) | `services/ml/matching.py`, `data/search.py` |

**Fórmula del threshold adaptativo** (`services/ml/snies_etdh.py:782-783`):

```
threshold = max(0.25, mediana(scores) + 1.5 × desviación_estándar(scores))
threshold = min(threshold, 0.70)
```

### 2.2 Umbrales por componente

| Componente | Threshold | Razón |
|:-----------|:----------|:------|
| Matching SNIES → CUOC (semántico) | Adaptativo (min 0.25, max 0.70) | Distribución variable de similitudes entre campos |
| Puente SNIES → SIET (estructural + semántico) | Adaptativo (min 0.25) | Two-stage: primero área CUOC, luego similitud semántica |
| Matching competencias CUOC | 0.25 fijo | Vocabulario más técnico y consistente |
| Skills bridge SNIES ↔ SIET | 0.35 fijo | Mayor exigencia por ser análisis transversal |
| Búsqueda de programas (sidebar) | 0.30 fijo | Balance precisión/cobertura para UI interactiva |

### 2.3 Validación del puente SNIES ↔ SIET

La función `validate_bridge()` (`services/ml/snies_etdh.py:851-907`) ejecuta 4
verificaciones automáticas:

| Check | Criterio | Propósito |
|:------|:---------|:----------|
| 1. Resultados no vacíos | `n_results > 0` | El puente encontró correspondencias |
| 2. Dispersión de scores | `score_spread > 0.1` | Los scores no son todos idénticos (evita overfitting) |
| 3. Ratio top/resto | `top_score / rest_mean < 3.0` | El primer resultado no domina desproporcionadamente |
| 4. Consistencia de áreas | Al menos 1 área SIET identificada | El mapeo estructural encontró áreas de desempeño |

**Métricas producidas:** `score_spread` (dispersión), `score_median`, `score_mean`, `n_results`, `total_matricula`

---

## 3. Integridad del Pipeline de Datos

### 3.1 Suite de 50 pruebas de integración

El archivo `tests/test_queries.py` (666 líneas) ejecuta 50 pruebas automatizadas
contra la base de datos real, cubriendo:

| Categoría | Pruebas | Qué valida |
|:----------|:--------|:-----------|
| Construcción de filtros | 8 | `build_where_clause`, `build_where_clause_matriculados`, `build_nbc_condition` |
| Consultas SNIES programas | 6 | `get_estadisticas_basicas`, `get_benchmarking_data`, `get_desglose_academico` |
| Consultas matriculados/graduados | 11 | `get_market_share`, `get_tendencia_matricula`, `get_graduados_historico` |
| Explorador interactivo | 6 | `get_datos_explorador_interactivo` con múltiples combinaciones |
| Comparativas SNIES/SIET | 2 | `get_comparativa_snies_siet_por_depto` |
| SIET | 3 | `get_estadisticas_siet`, `get_desglose_siet` |
| Laboral (ML matching) | 6 | `get_vacantes_reales`, `get_competencias_cuoc`, `get_salarios_reales` |
| Territorial | 2 | `get_conectividad_territorial`, `get_municipios_pdet` |
| Consistencia de datos | 3 | NBC case match, bridge match rate, data integrity |
| Rendimiento | 3 | Benchmarks de funciones críticas |

**Resultado actual:** 50 OK / 0 FAIL / 0 SKIP (exit code 0)

### 3.2 Métricas de consistencia

| Métrica | Valor | Significado |
|:--------|:------|:------------|
| Bridge match rate (programas ↔ matriculados) | 51% | ~15,279 de 29,755 COD_SNIES_PROGRAMA tienen correspondencia directa entre tablas |
| NBC case match (programas vs matriculados) | UPPER matches | La normalización via `UPPER()` resuelve diferencias de capitalización |
| Tiempo promedio `get_estadisticas_basicas` | ~131ms | Respuesta sub-500ms para consultas complejas con filtros |
| Tiempo promedio `get_market_share` | ~127ms | Consulta con subquery anidada para último año |
| Tiempo promedio `get_tendencia_matricula` | ~129ms | Serie temporal con agregación sobre ~300K registros |

---

## 4. Motor de Decisión: Validación de Coherencia

### 4.1 Pesos del scoring

El motor de decisión (`services/decision_engine.py`) pondera 4 síntesis evaluativas:

| Síntesis | Peso | Justificación |
|:---------|:-----|:--------------|
| Académica | 30% | Concentración de mercado (HHI) y crecimiento (CAGR) |
| Laboral | 40% | Mayor peso porque refleja empleabilidad real |
| Territorial | 20% | Conectividad digital, desempeño municipal DNP, contexto PDET |
| Global | 10% | Desempleo juvenil (Banco Mundial) como indicador macro |

### 4.2 Validación del scoring

**Score laboral (40%) — desglose multi-componente** (`services/scoring.py` + `views/tab_decision.py:88-124`):

| Subcomponente | Peso en score laboral | Fórmula |
|:--------------|:----------------------|:--------|
| Volumen de vacantes | 30% | Escalonado: >50K=100, >20K=80, >5K=60, >1K=40, >100=20, <100=5 |
| Ratio de absorción (x3 ajust.) | 20% | `min(100, ratio_ajustado × 50)` |
| Señal salarial (SIGEP/OLE) | 25% | `min(100, (salario_mediana / SMLV / 3) × 100)` |
| Densidad de competencias CUOC | 25% | `min(100, n_competencias × 5)` |

**Bonus por puente SNIES-SIET:** `+max(0, (alignment - 0.15) × 15) + max(0, (complementarity - 0.1) × 8)`

---

## 5. Generación LLM: Verificación Estructural

La función `analizar_con_llm()` (`app.py`) envía un prompt estructurado de ~500 líneas
a Gemini 2.0 Flash:

| Aspecto | Método de validación |
|:--------|:---------------------|
| Estructura del informe | Verificación de 7 secciones obligatorias presentes en el prompt |
| Citación de fuentes | Catálogo de 15 fuentes oficiales con formato `(FUENTE - Periodo)` |
| Notación LaTeX | Reglas explícitas en el prompt: `\frac`, `\sum`, `\left`, `\right`, `\%` |
| Fallback | Prueba secuencial de 4 modelos: `gemini-2.0-flash` → `2.5-flash` → `flash-latest` → `flash-lite` |
| Enriquecimiento RAG | Si `RAG_AVAILABLE`, recupera datos de deserción SPADIES, Saber PRO y tránsito desde DuckDB |

---

## 6. Resumen de Métricas Reportables

| Métrica | Valor | Tipo |
|:--------|:------|:-----|
| P@1 (Precision@1) | 0.786 | IR — matching semántico |
| MRR (Mean Reciprocal Rank) | 0.810 | IR — calidad de ranking |
| MAP (Mean Average Precision) | 0.794 | IR — precisión multi-nivel |
| NDCG@10 | 0.813 | IR — calidad del ranking normalizada |
| Top-5 correcto | 100% (47/47) | IR — cobertura por NBC |
| Tests de integración | 50/50 OK | Validación de pipeline |
| Bridge match rate | 51% | Cobertura de cruce entre tablas |
| Threshold semántico | Adaptativo (0.25-0.70) | Calidad de matching |
| Tiempo queries críticas | <500ms | Rendimiento |
| Modelos LLM con fallback | 4 | Robustez de generación |

---

## 7. Lectura Metodológica

El componente de matching semántico del sistema se evalúa con métricas de recuperación de
información (Precision@K, Recall@K, MRR, MAP, NDCG), que son el estándar para sistemas
basados en embeddings. El ground truth es la cadena taxonómica CINE-F → SIET, verificable
contra los catálogos oficiales. No se reportan métricas de clasificación supervisada (ROC,
Accuracy) porque el sistema no entrena un clasificador desde cero — opera sobre un modelo
pre-entrenado de propósito general (MiniLM) evaluado con métricas de ranking.

Los resultados completos, incluyendo el desglose por NBC individual, están disponibles en
formato JSON auditable en `reports/evaluacion_MiniLM_*.json`.

La ruta de evolución hacia modelado predictivo supervisado está documentada en
`06_conclusiones.md` (sección 3.2) como objetivo de mediano plazo.

---

*Documento generado a partir de la ejecución real de `admin/evaluacion/evaluar_modelo.py`
(2026-07-17, 56 NBCs, 437s), `admin/evaluacion/generar_graficos.py`, `tests/test_queries.py`
(50 pruebas), `services/ml/snies_etdh.py`, `services/ml/matching.py`, `services/decision_engine.py`,
y `app.py`.*
