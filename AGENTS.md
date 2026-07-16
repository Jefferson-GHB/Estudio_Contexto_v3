# AGENTS.md — Estudio Contexto v3.1.0

## Entrypoints

- **Streamlit dashboard**: `python -m streamlit run app.py`. `main()` en L560. No requiere el backend DSS.
- **Backend DSS (FastAPI)**: Prototipo arquitectónico (`api/`). No está en producción ni integrado al dashboard.

## api/ — Prototipo de Arquitectura Orientada a API

`api/` es un prototipo FastAPI que modela el dominio en **81 variables** organizadas en 5 ejes y 8 dominios. Apunta a una arquitectura desacoplada y consultable vía REST, donde `catalogo/MAPEO_DSS_OFICIAL.csv` es la fuente de verdad del modelo de datos. No está integrado al dashboard ni desplegable — su valor está en el **modelado conceptual** (variables, dominios, mapeos NBC-CUOC-CIIU) y los catálogos curados en `catalogo_curado.*`.

## Base de datos: DuckDB

- **Conexión read-only**: `duckdb.connect(DUCKDB_PATH, read_only=True)` en `config/database.py`.
- **Auto-detección de ruta**: `DUCKDB_PATH` env → `./data/repositorio.duckdb` → `./repositorio.duckdb` → `../DuckDB/repositorio.duckdb`.
- **Case sensitivity en NBCs**: `NÚCLEO_BÁSICO_DEL_CONOCIMIENTO` en programas vs `NBC` en matriculados. `data/filters.py` usa `UPPER()`.
- **Dos sistemas de filtros**: `build_where_clause()` para tablas directas; `build_where_clause_matriculados()` con bridge vía `COD_SNIES_PROGRAMA`. COD_SNIES_PROGRAMA puede tener sufijo `.0` (float-as-string) — el bridge lo normaliza con `REGEXP_REPLACE(CAST(... AS VARCHAR), '\.0$', '')`.
- **Modos excluyentes**: SNIES (default, educación formal) vs SIET/ETDH (educación para el trabajo). No se mezclan.
- **53 tablas fuentes** (snies, siet, cuoc, ape, geih, icfes, dnp, dane, etc.) en esquemas separados.

## Módulos condicionales

Importados con `try/except` en `app.py:93-118`. No asumir que están disponibles:

| Flag | Módulo | Dependencia |
|---|---|---|
| `ML_ETDH_AVAILABLE` | `services/ml/snies_etdh.py` | sentence-transformers |
| `TERRITORIAL_ROBUST` | `services/territorial/functions.py`, `services/territorial/normalization.py` | scikit-learn |
| `RAG_AVAILABLE` | `services/rag/retrieval.py` (clase `EducacionRAG`) | google-generativeai (ya en requirements) |

## Testing

- **NO usa pytest**. Runner casero en `tests/test_queries.py` (666 L).
- Ejecutar: `python -m tests.test_queries` (exit 0 = todo OK, 1 = fallos).
- Helpers: `ok()`, `fail()`, `skip()`, `check()`. Tests de integración contra DuckDB real — sin mocks.

## Auth y variables de entorno

- **Auth**: SHA-256 vía `st.secrets` (producción en HF Spaces Secrets). Fallback: admin/EstudioContexto2026! en desarrollo.
- **LLM API Key**: `GEMINIAPIKEY` o `GOOGLEAPIKEY` (NO `GEMINI_API_KEY`). El código prueba 4 modelos: `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-flash-latest`, `gemini-2.0-flash-lite`.
- **`.env`** (no commiteado): `GEMINIAPIKEY`, `GITHUB_TOKEN`, `HUGGINGFACE_TOKEN`, `DUCKDB_PATH`.

## Convenciones no obvias

- Funciones en `snake_case` **en español** (no inglés).
- CSS en `config/styles.py` con `score_card(score, label)`: `score-green` (>=70), `score-yellow` (40-69), `score-red` (<40).
- `admin/` contiene scripts operativos (auditoría, ETL, ML grid search) — no se ejecutan automáticamente.
- `catalogo/` tiene ~26 CSV/JSON de catálogos SNIES, CUOC, SIET, MEN, NBC.
- **Plotly template**: template global con paleta personalizada en `app.py:129-147`. Usar `px` o `go.Figure` automáticamente usan el template.
- **Data layer**: `data/__init__.py` re-exporta ~50 funciones de consulta. Las queries de SNIES reciben `filtros=(dict)` (no escalares) para respetar multiselect. NO pasar sel_nbc o arg_depto como escalares — causa doble-filtrado.
- **Cascada de filtros**: sidebar carga opciones vía `caragar_opciones_cruzadas()` que aplica intersección de todos los filtros activos. Cada vez que se cambia un filtro, las opciones de los demás se recalculan.

## Despliegue

- **Docker**: `python:3.13-slim`, puerto **7860**, CMD: `streamlit run app.py --server.port=7860 --server.address=0.0.0.0`.
- **Git LFS**: activo para `*.duckdb`, `*.parquet`, `*.pkl`, `*.pt`, `*.safetensors`, `*.zip`. No commitear la BD directamente.
