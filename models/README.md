# Modelos — Artefactos de machine learning

Los modelos y artefactos del sistema se almacenan en las siguientes ubicaciones:

## Embeddings pre-calculados

Los embeddings semanticos (MiniLM 384d) se cachean en disco:
- `services/cache_data/ml_embeddings/` — 180+ archivos .pkl con embeddings de ocupaciones CUOC, conocimientos, destrezas y programas SIET
- `catalogo/cache/ml_embeddings/` — Cache secundario de embeddings

## Modelo de lenguaje

- **Busqueda semantica**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones) via `sentence-transformers`
- **Generacion LLM**: Google Gemini 2.0 Flash via API (modelo externo, no local)

## Motor de decisión

`services/decision_engine.py` — Scoring ponderado (30% académica, 40% laboral, 20% territorial, 10% global) con 6 tipos de oferta educativa.

## Nota

El sistema no entrena modelos supervisados desde cero. Utiliza modelos pre-entrenados para busqueda semantica y un LLM externo para generación de informes. La ruta de evolucion hacia modelado predictivo supervisado de deserción esta documentada en `docs/tecnica/06_conclusiones.md` (seccion 3.2).
