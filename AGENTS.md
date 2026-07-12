# AGENTS.md — Estudio Contexto v3.1.0

## Entrypoints

- **Streamlit (dashboard principal)**: `streamlit run app.py` (puerto 8501). `main()` en L1808, ejecutada al final. **No requiere el backend DSS**.
- **Backend DSS (FastAPI)**: `uvicorn api.main:app --reload --port 8000`. Swagger en `/docs`. Opcional — el dashboard funciona sin él.

## Base de datos: DuckDB

- **Conexión siempre read-only**: `duckdb.connect(DUCKDB_PATH, read_only=True)` en `config/database.py`.
- **Auto-deteccion de ruta** (orden): `DUCKDB_PATH` env → `./data/repositorio.duckdb` → `./repositorio.duckdb` (fallback) → `../DuckDB/repositorio.duckdb`.
- **Case sensitivity en NBCs**: la columna se llama `NUCLEO_BASICO_DEL_CONOCIMIENTO` en unas tablas y `NBC` en otras, con distinta capitalización. `data/filters.py` usa `UPPER()` para matching. Hay `build_nbc_condition()` y `resolver_nbcs_desde_filtros()` para filtros en cascada (Campo Amplio → Área → NBC).
- **Dos sistemas de filtros**: `build_where_clause()` para tablas directas; `build_where_clause_matriculados()` con bridge vía `COD_SNIES_PROGRAMA`.
- **Modos excluyentes**: SNIES (default, educación formal) vs SIET/ETDH (educación para el trabajo).

## Módulos condicionales

Importados con `try/except` en `app.py` (L90-138). No asumir que están disponibles:

| Flag | Módulo | Dependencia pesada |
|---|---|---|
| `ML_ETDH_AVAILABLE` | `services/ml/snies_etdh.py` | torch, sentence-transformers |
| `TERRITORIAL_ROBUST` | `services/territorial/functions.py`, `services/territorial/normalization.py` | scikit-learn |
| `RAG_AVAILABLE` | `services/rag/retrieval.py` (clase `EducacionRAG`) | google-generativeai |
| — | `services/ml/matching.py` | sentence-transformers |

## Testing

- **NO usa pytest ni unittest**. Runner casero en `tests/test_queries.py` (666 L).
- Ejecutar: `python -m tests.test_queries` (exit 0 = todo OK, 1 = fallos).
- Helpers: `ok()`, `fail()`, `skip()`, `check()`. Tests de integración contra DuckDB real — sin mocks.

## Auth y variables de entorno

- **Autenticación**: SHA-256 vía `st.secrets` (producción en HF Spaces Secrets). Fallback a credenciales hardcodeadas en desarrollo local. **No** en `.env`.
- **`.env`** (no commiteado): `GEMINI_API_KEY`, `GITHUB_TOKEN`, `HUGGINGFACE_TOKEN`, `DUCKDB_PATH` (opcional).

## Convenciones no obvias

- Funciones en `snake_case` **en español** (no inglés).
- CSS modular en `config/styles.py` (~130 L). Usar `score_card(score, label)` que devuelve HTML con clase dinámica: `score-green` (>=70), `score-yellow` (40-69), `score-red` (<40).
- `admin/` contiene scripts operativos (análisis, validación, ETL) — **no se ejecutan automáticamente**.
- `catalogo/` tiene ~26 CSV/JSON de catálogos y ontologías (SNIES, CUOC, SIET, MEN, NBC).

## Despliegue

- **Docker**: `python:3.13-slim`, puerto **7860**, CMD: `streamlit run app.py --server.port=7860 --server.address=0.0.0.0`.
- **Git LFS**: configurado en `.gitattributes` para `*.duckdb`, `*.parquet`, `*.pkl`, `*.pt`, `*.safetensors`, `*.zip`. No commitees la BD directamente.
