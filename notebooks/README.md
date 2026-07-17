# Notebooks de experimentacion y análisis

El flujo analitico del proyecto se implemento como código Python modular en lugar de notebooks interactivos. La documentación técnica describe el proceso completo equivalente:

| Fase | Documentacion | Codigo |
|---|---|---|
| Exploracion de datos | `docs/tecnica/04_marco_metodologico.md` (Fase 2) | `data/queries.py` (56 funciones de consulta) |
| Limpieza y transformacion | `docs/tecnica/04_marco_metodologico.md` (Fase 3) | `data/queries.py`, `data/transform.py`, `data/filters.py`, `admin/ingestar_*.py` |
| Analisis descriptivo | `docs/tecnica/01_arquitectura.md` (Capa 3) | `services/scoring.py` (HHI, CAGR, ratio absorcion) |
| Modelo predictivo | `docs/tecnica/08_validacion_componentes_ia.md` | `services/ml/matching.py`, `services/ml/snies_etdh.py` |
| Reportes automáticos | `docs/tecnica/07_guia_validacion.md` | `utils/reporte_docx.py`, `app.py` (funcion `analizar_con_llm`) |

## Ejecucion del dashboard

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

Credenciales por defecto: `admin` / `EstudioContexto2026!`

## Ejecucion de pruebas

```bash
python -m tests.test_queries
```

50 pruebas de integracion contra la base de datos real.

## Reproducibilidad

El pipeline completo se puede ejecutar desde `pipelines/pipeline_ml.py`:

```bash
python pipelines/pipeline_ml.py
```

Todos los datos residen en el repositorio DuckDB (`data/repositorio.duckdb`, 703 MB, Git LFS).
