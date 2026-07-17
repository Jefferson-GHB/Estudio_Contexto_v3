---
title: Sistema de Análisis de Contexto para la Toma de Decisiones Educativas
emoji: "\U0001F4CA"
colorFrom: red
colorTo: gray
sdk: docker
app_file: app.py
pinned: false
---

<h1 align="center">
  Sistema de Análisis de Contexto<br>para la Toma de Decisiones Educativas
</h1>

<h4 align="center">Estudios de contexto para decisiones curriculares con evidencia de pertinencia y permanencia</h4>

<p align="center">
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/streamlit-1.42-red?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/duckdb-1.5-yellow?logo=duckdb&logoColor=white" alt="DuckDB"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/gemini-2.0__flash-4285F4?logo=google&logoColor=white" alt="Gemini"></a>
  <a href="https://github.com/Jefferson-GHB/Estudio_Contexto_v3/actions"><img src="https://img.shields.io/badge/tests-50/50-brightgreen" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

---

## El problema

En Colombia, segun el Sistema para la Prevencion de la Desercion de la Educacion Superior (SPADIES), la deserción universitaria constituye una señal estructural de riesgo. Cuando una institución diseña, abre o modifica un programa sin leer contexto integrado —mercado laboral, territorio, competencias, trayectorias— genera condiciones que afectan la permanencia: programas en mercados saturados, perfiles de egreso desconectados de ocupaciones reales, o modalidades inviables para la poblacion objetivo.

---

## Justificacion — Valor Publico

Estudio Contexto democratiza el acceso a análisis de contexto educativo basados en **datos abiertos del Estado colombiano**. Es una herramienta gratuita, trazable y auditables para que directivos, comites curriculares y equipos de aseguramiento de la calidad de IES publicas y privadas tomen decisiones de oferta académica con evidencia verificable, fortaleciendo condiciones de permanencia estudiantil.

---

## Datasets utilizados (7 fuentes)

| # | Dataset | Portal | Periodo | Registros |
|---|---------|--------|---------|-----------|
| 1 | **Conectividad Internet Fijo** | **datos.gov.co** | 2016-2023 | 1,678,363 |
| 2 | Cobertura Movil 4G | **datos.gov.co** | 2015-2023 | 1,457,892 |
| 3 | **APE Vacantes** | **datos.gov.co** | 2023-2024 | 23,447 |
| 4 | SNIES Programas | snies.mineducacion.gov.co | 2024 | 12,865 |
| 5 | SIET Programas | siet.mineducacion.gov.co | 2023 | 25,010 |
| 6 | Saber PRO | icfes.gov.co | 2018-2022 | 999,891 |
| 7 | CUOC Ocupaciones | **datos.gov.co** | 2025 | 680 perfiles |

**Dataset externo complementario**: Cualificaciones MEN (MNC, 2024, 396 registros), indicadores Banco Mundial, OECD, UNESCO, OIT.

---

## Variables seleccionadas (14 variables clave)

| # | Variable | Descripcion | Fuente |
|---|----------|-------------|--------|
| 1 | NBC | Nucleo Basico del Conocimiento | SNIES |
| 2 | Matriculados | Total matriculados 2019-2024 | SNIES |
| 3 | Graduados | Total graduados anuales | SNIES |
| 4 | Nivel de formación | Pregrado / Posgrado | SNIES |
| 5 | Modalidad | Presencial / Virtual / Distancia | SNIES |
| 6 | Departamento oferta | Departamento del programa | SNIES |
| 7 | Vacantes APE | Vacantes reportadas 2023-2024 | APE (datos.gov.co) |
| 8 | Ocupacion CUOC | Denominacion ocupacional oficial | CUOC (datos.gov.co) |
| 9 | Conocimientos CUOC | Competencias de conocimiento requeridas | CUOC |
| 10 | Destrezas CUOC | Competencias de destreza requeridas | CUOC |
| 11 | Salario promedio | Salario por departamento y NBC | GEIH |
| 12 | Conectividad 4G | Cobertura movil por municipio | MinTIC (datos.gov.co) |
| 13 | Internet fijo | Accesos de internet fijo por municipio | MinTIC (datos.gov.co) |
| 14 | Saber PRO | Puntaje promedio lectura critica + razonamiento | ICFES |

---

## Tipo de análisis y modelo

**Tipo**: Analisis descriptivo multidimensional con scoring compuesto e IA generativa.

**Modelo**: Sistema multi-componente que integra:
- **Indicadores estadísticos**: HHI (concentracion de mercado), CAGR (tasa de crecimiento compuesta), Ratio de Absorcion Laboral
- **Matching semantico**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers, 384 dim) para cruzar programas académicos con ocupaciones CUOC y programas SIET — ~30K embeddings cacheados en disco
- **RAG**: Recuperacion aumentada con datos de deserción SPADIES que enriquecen el contexto del LLM
- **LLM**: Google Gemini 2.0 Flash con prompt estructurado de ~500 lineas generando informe en formato APA 7a edicion con citación de fuentes verificables
- **Motor de decisión heuristica**: Scoring ponderado (30% académico + 40% laboral + 20% territorial + 10% global) que produce recomendacion trazable: OFERTAR / NO OFERTAR / MICROCREDENCIAL

---

## Resultados clave

| Metrica | Valor |
|---------|-------|
| Pruebas de integracion automatizadas | 50/50 contra repositorio DuckDB real |
| Sintesis evaluativas | 4 (Academica, Laboral, Territorial, Decision Final) |
| Schemas integrados | 54 (488 tablas, 703 MB) |
| Embeddings semanticos indexados | ~30,000 programas SNIES + SIET |
| Fallback del LLM | 4 modelos Gemini con degradacion progresiva |
| Validacion del puente SNIES-SIET | Umbral adaptativo de similitud por NBC (0.639-0.650) |
| **Metricas IR (56 NBCs)** | **P@1=0.786, MRR=0.810, MAP=0.794, NDCG@10=0.813** |

**Pipeline de ejecucion**: `pip install -r requirements.txt` → `python -m streamlit run app.py` → seleccionar NBC → 4 tabs con resultados en tiempo real.

---

## Interpretacion

- **Score ≥ 80 (OFERTAR)**: Condiciones favorables de mercado, empleabilidad y territorio. Baja concentracion, crecimiento positivo, vacantes activas, salarios competitivos y conectividad suficiente.
- **Score 50-79 (OFERTAR CON AJUSTES)**: Señales mixtas. Se recomienda revisar modalidad, departamento o nivel de formación antes de comprometer recursos.
- **Score < 50 (REVALUAR)**: Mercado saturado o sin demanda laboral detectable. Explorar formación complementaria de corta duracion alineada con competencias CUOC especificas.

La recomendacion es **trazable**: cada componente del score se desglosa con su valor numerico y fuente de datos, permitiendo auditoria completa del resultado.

---

## Impacto potencial

- **Instituciones de educación superior**: Decisiones de oferta académica basadas en evidencia integrada de mercado laboral, territorio y calidad, reduciendo el riesgo de abrir programas en mercados saturados o sin demanda laboral.
- **Entidades gubernamentales**: Modelo de referencia para estudios de pertinencia educativa con datos abiertos del Estado, reproducible y escalable a cualquier departamento o NBC.
- **Ciudadania**: Transparencia sobre la relación entre formación y empleabilidad, fortaleciendo expectativas de retorno de la inversion educativa.

---

## Demo en vivo

**Aplicacion Web**: [https://jeffersonca-estudio-contexto.hf.space/](https://jeffersonca-estudio-contexto.hf.space/)

- Usuario: `admin`
- Contrasena: `EstudioContexto2026!`
- Seleccione un NBC (ej: "Ingenieria de sistemas, telematica y afines") y explore las 4 sintesis.

**Contenedor Docker**:
```bash
docker build -t estudio-contexto .
docker run -p 7860:7860 estudio-contexto
```

---

## Documentacion y enlaces

| Recurso | Acceso |
|---------|--------|
| Presentacion (PDF) | [RECURSOS/presentacion.pdf](RECURSOS/presentacion.pdf) |
| Documentacion técnica | [docs/tecnica/](docs/tecnica/) — Arquitectura, Datos, Metodologia, Validacion |
| Repositorio GitHub | [github.com/Jefferson-GHB/Estudio_Contexto_v3](https://github.com/Jefferson-GHB/Estudio_Contexto_v3) |
| Changelog | [Changelog.md](Changelog.md) |

---

## Estructura del repositorio

```
Estudio_Contexto_v3/
│
├── app.py                        # Dashboard principal (387 lineas). Delegacion a services/ y views/
├── AGENTS.md                     # Guia para agentes de desarrollo con convenciones del proyecto
├── Changelog.md                  # Registro cronologico de versiones y cambios
├── LICENSE                       # MIT
├── environment.yml               # Entorno conda con todas las dependencias
├── requirements.txt              # Dependencias pip
├── Dockerfile                     # Contenedor de despliegue (Python 3.13-slim, puerto 7860)
├── .gitignore / .gitattributes   # Git LFS y exclusiones
│
├── views/                        # Vistas de cada sintesis evaluativa
│   ├── tab_academico.py          # Concentracion (HHI), crecimiento (CAGR), calidad (Saber PRO)
│   ├── tab_laboral.py            # Demanda laboral, vacantes, competencias, salarios
│   ├── tab_territorial.py        # Conectividad, PDET, desempeno municipal
│   ├── tab_decision.py           # Score ponderado, veredicto, informe LLM + DOCX
│   ├── etdh.py                   # Dashboard SIET/ETDH (educación para el trabajo)
│   └── methodology.py            # Documentacion de la metodología de scoring
│
├── services/                     # Logica de negocio y procesamiento
│   ├── context.py                # Dataclass Context (52 campos compartidos entre tabs)
│   ├── data_loader.py            # Carga centralizada pre-tab + ML matching + metricas
│   ├── scoring.py                # HHI, CAGR, Ratio de Absorcion, Score Final
│   ├── decision_engine.py        # Motor de recomendacion (OFERTAR / OFERTAR CON AJUSTES / REVALUAR)
│   ├── context_builder.py        # Construccion de contexto markdown para el LLM (~500 lineas APA 7)
│   ├── llm.py                    # Integracion Gemini 2.0 Flash con fallback de 4 modelos
│   ├── sources.py                # Diccionario de 28 fuentes con URLs y citación APA
│   ├── ml/                       # Matching semantico (MiniLM) + puente SNIES↔SIET via CUOC
│   ├── rag/                      # RAG con datos de deserción SPADIES
│   └── territorial/              # Normalizacion territorial, DNP, cluster empresarial
│
├── data/                         # Capa de acceso a datos
│   ├── queries.py                # 56 consultas SQL parametrizadas (3,138 lineas)
│   ├── filters.py                # 2 subsistemas WHERE + cascada NBC (bridge COD_SNIES_PROGRAMA)
│   ├── search.py                 # Busqueda semantica con embeddings en disco
│   ├── transform.py              # Normalizacion de nombres SIET y canonicalizacion
│   ├── desercion.py              # Script de apoyo — cálculo exploratorio de indicadores de permanencia desde SNIES
│   ├── constants.py              # Constantes de datos
│   ├── repositorio.duckdb        # Base de datos (703 MB, 54 esquemas, 488 tablas, Git LFS)
│   ├── raw/                      # Archivos fuente originales sin procesar
│   ├── external/                 # Datos auxiliares externos
│   └── processed/                # Datos procesados intermedios
│
├── components/                   # Componentes reutilizables de UI
│   ├── sidebar.py                # Panel de filtros con busqueda inteligente y cascada
│   └── display.py                # Componentes de visualización (section_header, etc.)
│
├── config/                       # Configuracion del sistema
│   ├── database.py               # Conexion DuckDB read-only + auto-deteccion de ruta
│   ├── styles.py                 # CSS personalizado, loading overlay, insight cards
│   └── constants.py              # Constantes compartidas (TEMPLATE_COLORS, etc.)
│
├── visualizations/               # Graficos Plotly reutilizables
│   └── charts.py                 # Gauges (HHI, Saber PRO, Score), distribuciones, heatmaps
│
├── utils/                        # Utilidades transversales
│   ├── auth.py                   # Autenticacion SHA-256 (st.secrets en prod)
│   ├── helpers.py                # Descarga de datos de gráficos, utilidades
│   └── reporte_docx.py           # Generador de informe Word con portada y marca de agua
│
├── admin/                        # ~25 scripts de ETL, auditoria, evaluación y diagnostico
│   ├── ingestar_snies.py         # Ingesta XLSX del portal SNIES
│   ├── ingestar_socrata.py       # Ingesta via API Socrata (datos.gov.co)
│   ├── ingestar_ape.py           # Ingesta APE/SENA (vacantes)
│   ├── ingestar_internacional.py # Ingesta Banco Mundial, OECD, UNESCO, ILO
│   ├── ingestar_territorial.py   # Ingesta DNP, MinTIC, DIVIPOLA, conectividad
│   ├── ingestar_catalogos.py     # Ingesta de 7 catalogos de mapeo (CSV → DuckDB)
│   ├── ingestar_mapeo_variables.py # Ingesta del mapeo de 114 variables
│   ├── auditar_catalogos.py      # Auditoria de consistencia entre catalogos y fuentes
│   ├── auditar_mapeo_variables.py # Verificacion de esquemas, tablas y columnas
│   ├── evaluacion/               # Suite de evaluacion del modelo ML
│   │   ├── evaluar_modelo.py     # Metricas IR (P@K, MRR, MAP, NDCG) sobre 56 NBCs
│   │   ├── benchmark_modelos.py  # Comparativa de modelos de embedding
│   │   ├── generar_graficos.py   # Generacion de graficos desde JSON de resultados
│   │   └── resultados/           # JSON + graficos de evaluacion automatica
│   └── ...                       # ~12 scripts adicionales (diagnostico, grid search)
│
├── catalogo/                     # ~20 archivos CSV/JSON de catalogos y mapeos normalizados
│   ├── MAPEO_DSS_OFICIAL.csv     # Mapeo de 114 variables a esquemas/tablas/columnas
│   ├── CATALOGO_NBC_SNIES.csv    # NBCs con campos CINE-F y áreas de conocimiento
│   ├── MAPEO_CUOC_CIIU.csv       # Mapeo ocupaciones ↔ sectores economicos
│   ├── cruces_verificados.json   # 63 cruces SQL validados entre tablas
│   └── ... (+15 CSVs de mapeo entre clasificadores)
│
├── pipelines/                    # Orquestadores de flujos de datos
│   ├── pipeline_etl.py           # Orquestador de ingestion (--solo, --dry-run)
│   └── pipeline_ml.py            # Pipeline de matching semantico y entrenamiento
│
├── tests/                        # Pruebas automatizadas
│   └── test_queries.py           # 50 tests de integracion contra DuckDB real (666 lineas)
│
├── docs/                         # Documentacion del proyecto
│   ├── técnica/                  # 9 documentos técnicos (evaluación concurso)
│   │   ├── 01_arquitectura.md    # Diagrama de 4 capas + stack
│   │   ├── 02_diccionario_datos.md # 114 variables en 4 ejes y 9 dominios
│   │   ├── 03_planteamiento_problema.md
│   │   ├── 04_marco_metodologico.md # CRISP-ML fase por fase
│   │   ├── 05_fuentes_datos.md   # Trazabilidad de 54 esquemas
│   │   ├── 06_conclusiones.md    # Hallazgos, limitaciones, próximos pasos
│   │   ├── 07_guia_validacion.md # Como ejecutar tests y validar resultados
│   │   ├── 08_validacion_componentes_ia.md # Metricas reales de IA
│   │   └── estado_ingesta.md     # Clasificacion A/B/C por método de regeneracion
│   └── compose/                  # Documentacion interna de desarrollo
│
├── RECURSOS/                     # Material visual del proyecto
│   └── ...                       # Presentacion (PDF/PPTX), portada
│
├── reports/                      # Resultados visibles
│   └── figures/                  # Capturas del dashboard + graficos de evaluacion ML
│
├── models/                       # Artefactos de modelos (referencia)
├── notebooks/                    # Documentacion del flujo analitico equivalente
└── src/                          # Re-exportaciones del paquete services
```



```bash
git clone https://github.com/Jefferson-GHB/Estudio_Contexto_v3.git
cd Estudio_Contexto_v3
pip install -r requirements.txt
python -m streamlit run app.py
```

> Credenciales por defecto: `admin` / `EstudioContexto2026!`. Variable `GEMINIAPIKEY` requerida para el componente LLM.

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| **Jefferson Cuastusa** | Lider técnico BI, modelado de datos, ETL, visualización. Ingeniero de Sistemas. |
| **Ximena Molano** | Especialista en educación superior, calidad, evaluación curricular. Economista. |
| **Claudia Milena Muñoz** | Lider académica y de aseguramiento de la calidad. Ingeniera Industrial, Mg. y candidata a Dra. en Educacion. |

---

## Metodologia

CRISP-ML (Cross-Industry Standard Process for Machine Learning) adaptado al dominio educativo: comprension del problema → comprension de datos → preparacion ETL → modelado de indicadores → evaluación (50 tests automatizados) → despliegue (Docker + HuggingFace Spaces).

---

<p align="center">
  <sub>Desarrollado por Equipo 195 — Concurso Datos al Ecosistema 2026</sub>
</p>
