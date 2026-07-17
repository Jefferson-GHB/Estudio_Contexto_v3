# Changelog

## v3.2.0 — Refactor, limpieza de prototipo, docs concurso, ingesta ETL, evaluacion ML

- refactor: atomizar app.py (4053 → 387 L) en servicios y vistas por dominio
- chore: eliminar api/ (prototipo de backend no integrado) y todas sus referencias
- docs: purgar referencias del prototipo en documentacion, AGENTS.md, scripts y catalogos
- docs: crear estado_ingesta.md (clasificacion A/B/C por metodo de regeneracion)
- feat: 6 scripts ETL representativos (SNIES, Socrata, APE, Internacional, Territorial, Catalogos)
- chore: renombrar scripts mapeo_dss → mapeo_variables y cruces_verificados.json
- docs: eliminar 6 MDs de investigacion del prototipo de catalogo/
- feat(ml): suite de evaluacion IR sobre 56 NBCs (P@1=0.786, MRR=0.810, MAP=0.794, NDCG=0.813)
- docs: reescribir README para formato concurso Datos al Ecosistema 2026
- docs: agregar estructura completa del repositorio al README
- docs: corregir ñ y acentos en 18 archivos de documentacion
- docs: actualizar 08_validacion_componentes_ia con metricas IR reales
- docs: actualizar DOCX maestro (eliminar FastAPI, corregir esquemas, agregar metricas)
- build: CI (50 tests), environment.yml, Changelog, pipeline_etl.py

## v3.1.0 — Dashboard de pertinencia educativa

- 21f6a72 Fix spelling of 'Munoz' in README.md
- 8c9e6e7 Correct typo in README.md
- acc19c9 Dockerfile: download DuckDB from GitHub LFS on HF build
- 75901a5 fix: HF Spaces YAML frontmatter
- 19439f5 Se requiere pydocx
- 0098534 fix: use_container_width deprecado, SQL columna con acentos
- fbe3eae UI: alinear labels y README con narrativa de deserción/permanencia
- c4ce00e docs: README profesional con badges, arquitectura y guia
- ec054fc Agregar base de datos DuckDB (671 MB, LFS)
- aefe27c v3.1.0 — Dashboard de pertinencia educativa
