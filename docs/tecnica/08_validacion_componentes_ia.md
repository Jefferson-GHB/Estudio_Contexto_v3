# Validacion de Componentes de Inteligencia Artificial

Metricas y metodos de validacion aplicados a los tres componentes de IA del sistema. Dado que la solucion no entrena modelos supervisados desde cero (usa embeddings pre-entrenados, RAG estructurado y un LLM via API), las metricas se centran en la calidad de las correspondencias semanticas, la integridad del pipeline de datos y la consistencia del motor de decision.

---

## 1. Por que no se reportan metricas de clasificacion (ROC, precision, recall)

El sistema **no contiene un clasificador supervisado entrenado**. Opera sobre tres componentes de naturaleza distinta:

| Componente | Tipo | Metrica aplicable |
|:-----------|:-----|:------------------|
| Busqueda semantica (MiniLM) | Modelo pre-entrenado de proposito general | Umbrales adaptativos, cobertura de matches, validacion de puentes |
| RAG estructurado (EducacionRAG) | Recuperacion aumentada desde base de datos | Integridad de contexto, trazabilidad de fuentes |
| Generacion LLM (Gemini) | Modelo generativo via API externa | Verificacion de estructura (7 secciones), citacion de fuentes |

Pretender reportar ROC o F1-Score para un sistema que no entrena un clasificador seria metodologicamente incorrecto. La validacion se enfoca en los puntos donde el sistema toma decisiones algoritmicas: **umbrales de similitud, consistencia de cruces entre fuentes y coherencia de recomendaciones**.

---

## 2. Busqueda Semantica: Threshold Adaptativo

### 2.1 Logica de umbral

El sistema usa un **umbral adaptativo** en lugar de un valor fijo. Esto evita tanto falsos positivos (matches debiles en campos con poca oferta) como falsos negativos (campos donde ninguna ocupacion supera un umbral arbitrario).

| Parametro | Valor | Ubicacion |
|:----------|:------|:----------|
| Modelo | `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones) | `services/ml/matching.py:9` |
| Corpus | Ocupaciones CUOC (680), conocimientos (3,599), destrezas (4,422), programas SIET (11,233) | `services/cache_data/ml_embeddings/` |
| Cache | Dos niveles: memoria (dict) + disco (180+ archivos .pkl) | `services/ml/matching.py`, `data/search.py` |

**Formula del threshold adaptativo** (`services/ml/snies_etdh.py:782-783`):

```
threshold = max(0.25, mediana(scores) + 1.5 × desviacion_estandar(scores))
threshold = min(threshold, 0.70)
```

Esto significa que el umbral se ajusta automaticamente segun la distribucion de similitudes de cada consulta: en campos con matches muy claros, el umbral sube (mayor exigencia); en campos con vocabulario mas disperso, baja hasta un minimo de 0.25.

### 2.2 Umbrales por componente

| Componente | Threshold | Razon |
|:-----------|:----------|:------|
| Matching SNIES → CUOC (semantico) | Adaptativo (min 0.25, max 0.70) | Distribucion variable de similitudes entre campos |
| Puente SNIES → SIET (estructural + semantico) | Adaptativo (min 0.25) | Two-stage: primero area CUOC, luego similitud semantica |
| Matching competencias CUOC | 0.25 fijo | Vocabulario mas tecnico y consistente |
| Skills bridge SNIES ↔ SIET | 0.35 fijo | Mayor exigencia por ser analisis transversal |
| Busqueda de programas (sidebar) | 0.30 fijo | Balance precision/cobertura para UI interactiva |

### 2.3 Validacion del puente SNIES ↔ SIET

La funcion `validate_bridge()` (`services/ml/snies_etdh.py:851-907`) ejecuta 4 verificaciones automaticas:

| Check | Criterio | Proposito |
|:------|:---------|:----------|
| 1. Resultados no vacios | `n_results > 0` | El puente encontro correspondencias |
| 2. Dispersion de scores | `score_spread > 0.1` | Los scores no son todos identicos (evita overfitting) |
| 3. Ratio top/resto | `top_score / rest_mean < 3.0` | El primer resultado no domina desproporcionadamente |
| 4. Consistencia de areas | Al menos 1 area SIET identificada | El mapeo estructural encontro areas de desempeno |

**Metricas producidas:** `score_spread` (dispersion), `score_median`, `score_mean`, `n_results`, `total_matricula`

---

## 3. Integridad del Pipeline de Datos

### 3.1 Suite de 50 pruebas de integracion

El archivo `tests/test_queries.py` (666 lineas) ejecuta 50 pruebas automatizadas contra la base de datos real, cubriendo:

| Categoria | Pruebas | Que valida |
|:----------|:--------|:-----------|
| Construccion de filtros | 8 | `build_where_clause`, `build_where_clause_matriculados`, `build_nbc_condition` |
| Consultas SNIES programas | 6 | `get_estadisticas_basicas`, `get_benchmarking_data`, `get_desglose_academico` |
| Consultas matriculados/graduados | 11 | `get_market_share`, `get_tendencia_matricula`, `get_graduados_historico` |
| Explorador interactivo | 6 | `get_datos_explorador_interactivo` con multiples combinaciones |
| Comparativas SNIES/SIET | 2 | `get_comparativa_snies_siet_por_depto` |
| SIET | 3 | `get_estadisticas_siet`, `get_desglose_siet` |
| Laboral (ML matching) | 6 | `get_vacantes_reales`, `get_competencias_cuoc`, `get_salarios_reales` |
| Territorial | 2 | `get_conectividad_territorial`, `get_municipios_pdet` |
| Consistencia de datos | 3 | NBC case match, bridge match rate, data integrity |
| Rendimiento | 3 | Benchmarks de funciones criticas |

**Resultado actual:** 50 OK / 0 FAIL / 0 SKIP (exit code 0)

### 3.2 Metricas de consistencia

| Metrica | Valor | Significado |
|:--------|:------|:------------|
| Bridge match rate (programas ↔ matriculados) | 51% | ~15,279 de 29,755 COD_SNIES_PROGRAMA tienen correspondencia directa entre tablas. El 49% restante requiere resolucion via subquery puente |
| NBC case match (programas vs matriculados) | UPPER matches | La normalizacion via `UPPER()` resuelve diferencias de capitalizacion entre `NUCLEO_BASICO_DEL_CONOCIMIENTO` y `NBC` |
| Tiempo promedio `get_estadisticas_basicas` | ~131ms | Respuesta sub-500ms para consultas complejas con filtros |
| Tiempo promedio `get_market_share` | ~127ms | Consulta con subquery anidada para ultimo ano |
| Tiempo promedio `get_tendencia_matricula` | ~129ms | Serie temporal con agregacion sobre ~300K registros |

---

## 4. Motor de Decision: Validacion de Coherencia

### 4.1 Pesos del scoring

El motor de decision (`services/decision_engine.py`) pondera 4 sintesis evaluativas:

| Sintesis | Peso | Justificacion |
|:---------|:-----|:--------------|
| Academica | 30% | Concentracion de mercado (HHI) y crecimiento (CAGR) |
| Laboral | 40% | Mayor peso porque refleja empleabilidad real: volumen de vacantes, ratio de absorcion (x3 ajustado por subreporte APE), senal salarial, densidad de competencias, y bonus por alineacion SNIES-SIET |
| Territorial | 20% | Conectividad digital, desempeno municipal DNP, contexto PDET |
| Global | 10% | Desempleo juvenil (Banco Mundial) como indicador macro |

### 4.2 Validacion del scoring

Cada sintesis se descompone en subindicadores con formulas documentadas:

**Score laboral (40%) — desglose multi-componente** (`services/scoring.py` + `views/tab_decision.py:88-124`):

| Subcomponente | Peso en score laboral | Formula |
|:--------------|:----------------------|:--------|
| Volumen de vacantes | 30% | Escalonado: >50K=100, >20K=80, >5K=60, >1K=40, >100=20, <100=5 |
| Ratio de absorcion (x3 ajust.) | 20% | `min(100, ratio_ajustado × 50)` |
| Senal salarial (SIGEP/OLE) | 25% | `min(100, (salario_mediana / SMLV / 3) × 100)` |
| Densidad de competencias CUOC | 25% | `min(100, n_competencias × 5)` |

**Bonus por puente SNIES-SIET:** `+max(0, (alignment - 0.15) × 15) + max(0, (complementarity - 0.1) × 8)`

La coherencia del scoring se valida indirectamente mediante las 50 pruebas de integracion: si los filtros producen datos correctos y las metricas (HHI, CAGR) se calculan sobre esos datos, el scoring es trazable y auditable.

---

## 5. Generacion LLM: Verificacion Estructural

La funcion `analizar_con_llm()` (`app.py:72-220`) envia un prompt estructurado de ~58 lineas a Gemini 2.0 Flash. La validacion del componente LLM es:

| Aspecto | Metodo de validacion |
|:--------|:---------------------|
| Estructura del informe | Verificacion de 7 secciones obligatorias presentes en el prompt |
| Citacion de fuentes | Catalogo de 15 fuentes oficiales con formato `(FUENTE - Periodo)` |
| Notacion LaTeX | Reglas explicitas en el prompt: `\frac`, `\sum`, `\left`, `\right`, `\%` |
| Fallback | Prueba secuencial de 4 modelos: `gemini-2.0-flash` → `2.5-flash` → `flash-latest` → `flash-lite` |
| Enriquecimiento RAG | Si `RAG_AVAILABLE`, recupera datos de desercion SPADIES, Saber PRO y transito desde DuckDB antes de enviar al LLM |

---

## 6. Resumen de Metricas Reportables

| Metrica | Valor | Tipo |
|:--------|:------|:-----|
| Tests de integracion | 50/50 OK | Validacion de pipeline |
| Bridge match rate | 51% | Cobertura de cruce entre tablas |
| NBC case match | UPPER normalizado | Consistencia de datos |
| Threshold semantico | Adaptativo (0.25-0.70) | Calidad de matching |
| Score spread (bridge) | Variable por consulta | Dispersion de scores |
| Tiempo queries criticas | <500ms | Rendimiento |
| Modelos LLM con fallback | 4 | Robustez de generacion |

---

## 7. Lectura Metodologica

El hecho de que este sistema no entrene un modelo supervisado desde cero **no es una debilidad** — es una decision arquitectonica. En el contexto del reto de educacion del concurso, el valor esta en la **integracion de multiples fuentes de datos abiertos** y en la **generacion de evidencia trazable para decisiones institucionales**. Entrenar un clasificador de desercion requeriria datos etiquetados a nivel de estudiante que este sistema deliberadamente no utiliza, por razones tanto tecnicas (los datos abiertos disponibles son agregados, no individuales) como eticas (no se infiere riesgo individual).

La ruta de evolucion hacia modelado predictivo supervisado esta documentada en `06_conclusiones.md` (seccion 3.2) como objetivo de mediano plazo.

---

*Documento generado a partir del codigo fuente (`services/ml/snies_etdh.py:782-783, 851-907`, `services/ml/matching.py`, `tests/test_queries.py`, `app.py:72-220`, `services/decision_engine.py`) y ejecucion real de la suite de pruebas.*
