# Arquitectura del Sistema

Diagrama de arquitectura, flujo de datos, integracion de fuentes y stack tecnologico del Sistema de Analisis de Contexto para la Toma de Decisiones Educativas.

---

## 1. Arquitectura en Capas

```
+-----------------------------------------------------------------------------+
|                         CAPA 4: INTELIGENCIA ARTIFICIAL                    |
|  +--------------------------+  +-------------------+  +------------------+ |
|  | Busqueda Semantica       |  | RAG Estructurado  |  | Generacion LLM    | |
|  | MiniLM 384d (sentence-   |  | (EducacionRAG)    |  | Gemini 2.0 Flash  | |
|  | -transformers)           |  | Recuperacion      |  | Informe academico | |
|  | Matching SNIES-CUOC-SIET |  | aumentada desde   |  | APA 7a edicion    | |
|  | Cache 2 niveles (memoria |  | DuckDB + SPADIES  |  |                   | |
|  | + disco)                 |  |                    |  |                   | |
|  +--------------------------+  +-------------------+  +------------------+ |
|                                                                            |
|  +----------------------------------------------------------------------+ |
|  | Motor de Decision (services/decision_engine.py)                      | |
|  | Scores: 30% Academico | 40% Laboral | 20% Territorial | 10% Global  | |
|  | 6 tipos de oferta educativa recomendada                              | |
|  +----------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                         CAPA 3: ANALITICA (DuckDB)                         |
|  +--------------------------+  +-------------------+  +------------------+ |
|  | data/queries.py          |  | data/filters.py    |  | data/search.py   | |
|  | 56 consultas SQL        |  | build_where_clause |  | Busqueda seman-  | |
|  | parametrizadas           |  | Cascada NBC (CINE  |  | tica con embed-  | |
|  | SNIES, SIET, CUOC, APE, |  | -F → Area → NBC)   |  | dings en disco   | |
|  | GEIH, ICFES, DNP, SENA  |  | Bridge programas ↔ |  |                  | |
|  +--------------------------+  +-------------------+  +------------------+ |
|                                                                            |
|  +----------------------------------------------------------------------+ |
|  | services/scoring.py — Indicadores: HHI, CAGR, Ratio Absorcion        | |
|  +----------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                         CAPA 2: PROCESAMIENTO ETL                          |
|  +--------------------------+  +-------------------+  +------------------+ |
|  | admin/ingestar_*.py      |  | data/transform.py  |  | catalogo/        | |
|  | Extraccion de fuentes    |  | Homologacion CINE-F|  | 26 archivos CSV  | |
|  | SNIES XLSX, SIET,        |  | NBC, CUOC, CIIU,  |  | de mapeo SNIES,  | |
|  | Socrata API (datos.gov), |  | MNC, DIVIPOLA     |  | CUOC, SIET, MEN  | |
|  | Banco Mundial API        |  |                    |  |                  | |
|  +--------------------------+  +-------------------+  +------------------+ |
+-----------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------+
|                         CAPA 1: INGESTION DE FUENTES                        |
|                                                                             |
|  Portal datos.gov.co ─── Socrata API ───────────────┐                      |
|  SNIES (snies.mineducacion.gov.co) ── XLSX directo ─┤                      |
|  SIET (siet.mineducacion.gov.co) ──── CSV directo ──┤                      |
|  CUOC (dane.gov.co) ───────────────── XLSX ─────────┤                      |
|  APE / SENA ────── observatorio.sena.edu.co ────────┤──► DuckDB (703 MB)  |
|  ICFES ─────────── icfes.gov.co ──────── CSV ───────┤                      |
|  Banco Mundial ─── API ─────────────────────────────┤                      |
|  OECD / UNESCO ─── API ─────────────────────────────┤                      |
|  ESCO ──────────── download ESCO v1.2.0 ────────────┘                      |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 2. Stack Tecnologico

| Capa | Tecnologia | Version | Rol |
|:-----|:-----------|:--------|:----|
| **Frontend** | Streamlit | 1.42 | Dashboard interactivo con 4 pestanas de sintesis evaluativa |
| **Base de datos** | DuckDB | 1.5 | 703 MB, lectura exclusiva, 54 esquemas, 488 tablas normalizadas |
| **ML / NLP** | sentence-transformers (MiniLM) | 2.2+ | Matching semantico programas academicos ↔ ocupaciones CUOC ↔ competencias |
| **LLM** | Google Gemini 2.0 Flash | via API | Generacion de informe academico con formato APA 7a edicion, citacion de fuentes |
| **RAG** | EducacionRAG (`services/rag/retrieval.py`) | — | Recuperacion aumentada con datos de desercion, Saber PRO y transito desde DuckDB |
| **Visualizacion** | Plotly | 6.0+ | Graficos interactivos (gauges, lineas, distribucion), template global personalizado |
| **Reportes** | python-docx | 1.0+ | Documento Word profesional con portada y marca de agua |
| **Deploy** | Docker + HuggingFace Spaces | Python 3.13-slim | Puerto 7860, Git LFS para archivos > 100 MB |
| **API** | FastAPI | — | Prototipo arquitectonico (`api/`), 81 variables, 5 ejes, 8 dominios, documentacion interactiva |

---

## 3. Flujo de Datos del Usuario

```
+------------------+     +-------------------+     +-------------------+
| SIDEBAR          |     | DATA LAYER        |     | VIEWS             |
| components/      |     | data/queries.py   |     | views/            |
| sidebar.py       |     | data/filters.py   |     | tab_academico.py  |
|                  |     |                   |     | tab_laboral.py    |
| Filtros cascada: |     | Filtros → SQL     |     | tab_territorial.py|
| Campo Amplio ─┐  |     | parametrizado     |     | tab_decision.py   |
| Area ─────────┤  |     | → DuckDB          |     |                   |
| NBC ──────────┘  |     | → DataFrame       |     | 4 sintesis        |
| Departamento ──► | ==> | → Indicadores     | ==> | evaluativas       |
| Municipio        |     | → Scores          |     | con graficos      |
| Modalidad        |     | → Motor Decision  |     | Plotly, tablas    |
| Sector           |     |                   |     | y gauges          |
| Nivel            |     |                   |     |                   |
| Estado           |     |                   |     |                   |
+------------------+     +-------------------+     +-------------------+
        |                                                    |
        |  cargar_opciones_cruzadas()                        |  Reporte final:
        |  (interseccion de todos                            |  generar_reporte_docx()
        |   los filtros activos —                            |  (utils/reporte_docx.py)
        |   cada cambio recalcula                            |  + LLM Gemini:
        |   las opciones de los                              |  analizar_con_llm()
        |   demas filtros)                                   |  (app.py:72-220)
        |                                                    |
        +----------------------------------------------------+
                              |
                              v
                    +-------------------+
                    | DECISION ENGINE   |
                    | services/         |
                    | decision_engine.py|
                    |                   |
                    | Scores ponderados: |
                    | Acad. 30% + Lab.  |
                    | 40% + Terr. 20% + |
                    | Global 10%        |
                    | → 6 tipos oferta  |
                    +-------------------+
```

---

## 4. Componentes de Inteligencia Artificial

### 4.1 Busqueda Semantica con Embeddings Multilingues

| Aspecto | Detalle |
|:--------|:--------|
| Modelo | MiniLM (384 dimensiones, multilingue) |
| Framework | `sentence-transformers` 2.2+ |
| Corpus indexado | Ocupaciones CUOC (680 perfiles), conocimientos (3,599), destrezas (4,422), programas SIET (25,010) |
| Cache | Dos niveles: memoria (dict) + disco (`services/cache_data/ml_embeddings/`, 180+ archivos .pkl) |
| Umbrales | Adaptativos: intenta emparejamiento exigente primero, relaja si resultados escasos |
| Fallback | Si `sentence-transformers` no esta disponible, recurre a busqueda por palabras clave |
| Ubicacion | `services/ml/matching.py`, `services/ml/snies_etdh.py` |

**Puente SNIES ↔ SIET:**

El modelo de lenguaje identifica correspondencias entre educacion superior formal (SNIES) y educacion para el trabajo (SIET) a partir del significado de los textos, no de coincidencias literales. Esto permite que el analisis de pertinencia de un programa universitario se enriquezca con senales del ecosistema de formacion para el trabajo, revelando complementariedades que los datos estructurados no harian visibles.

**Matching SNIES → CUOC:**

El sistema asocia un NBC con ocupaciones CUOC y sus competencias (conocimientos, destrezas) usando similitud semantica, aun cuando las denominaciones no compartan una sola palabra. La funcion `get_competencias_cuoc()` (`data/queries.py`) retorna tuplas de DataFrames con conocimientos y destrezas asociados al NBC consultado.

### 4.2 RAG — Recuperacion Aumentada con Datos Estructurados

| Aspecto | Detalle |
|:--------|:--------|
| Clase | `EducacionRAG` (`services/rag/retrieval.py`) |
| Fuente de contexto | DuckDB (datos de desercion SPADIES, Saber PRO, transito inmediato, cobertura) |
| Metodo | `augment_context(nbc_codigo, departamento, contexto, filtros_activos)` |
| Integracion | `app.py:84-90` — enriquece el contexto antes de enviarlo al LLM |
| Disponibilidad | Condicional: `RAG_AVAILABLE` (requiere `google-generativeai`) |

### 4.3 Generacion LLM — Informe Academico

| Aspecto | Detalle |
|:--------|:--------|
| Modelo | Google Gemini 2.0 Flash (fallback: 2.5 Flash, flash-latest, flash-lite) |
| API Key | `GEMINIAPIKEY` o `GOOGLEAPIKEY` (variables de entorno) |
| Prompt | System prompt de 58 lineas en `app.py:103-160` con perfil de investigador senior, reglas de citacion LaTeX, estructura de 7 secciones |
| Output | Informe en Markdown con LaTeX para formulas, tablas profesionales, veredicto y hoja de ruta |
| Citacion | Catalogo de 15 fuentes oficiales con formato `(FUENTE - Periodo)` |
| Ubicacion | `app.py:72-220` (funcion `analizar_con_llm`) y `services/llm.py` (429 lineas, 1 funcion) |

---

## 5. Sistema de Filtros

### 5.1 Filtros en Cascada

El sidebar carga opciones mediante `cargar_opciones_cruzadas()` que aplica interseccion de todos los filtros activos. Cada vez que se cambia un filtro, las opciones de los demas se recalculan.

Jerarquia: **Campo Amplio CINE-F → Area de Conocimiento → NBC**

### 5.2 Dos Sistemas de Filtros SQL

| Sistema | Funcion | Uso |
|:--------|:--------|:----|
| `build_where_clause(filtros, alias)` | `data/filters.py` | Tablas directas: `snies_programas`, `snies_instituciones` |
| `build_where_clause_matriculados(filtros)` | `data/filters.py`  | Tablas con bridge via `COD_SNIES_PROGRAMA`: `snies_matriculados`, `snies_graduados`, `snies_inscritos`, `snies_admitidos` |

### 5.3 Puente Programas ↔ Matriculados

Las tablas de matriculados, graduados, inscritos y admitidos no contienen todas las dimensiones de `snies_programas`. Para filtros cuyas columnas no existen en la tabla destino, el sistema:
1. Construye una subconsulta que usa `COD_SNIES_PROGRAMA` como puente hacia `snies_programas`
2. Normaliza `COD_SNIES_PROGRAMA` con `REGEXP_REPLACE(CAST(... AS VARCHAR), '\\.0$', '')` (sufijo `.0` de float-as-string)
3. Consolida multiples filtros en una sola subconsulta para optimizar rendimiento

### 5.4 Case Sensitivity en NBCs

`NUCLEO_BASICO_DEL_CONOCIMIENTO` en `snies_programas` usa mayusculas y tildes. `NBC` en `snies_matriculados` usa un formato diferente. `data/filters.py` normaliza via `UPPER()` para garantizar coincidencia.

---

## 6. Infraestructura de Despliegue

### 6.1 Docker

| Aspecto | Valor |
|:--------|:------|
| Imagen base | `python:3.13-slim` |
| Puerto | 7860 |
| Comando | `streamlit run app.py --server.port=7860 --server.address=0.0.0.0` |
| Estrategia BD | Clona el repo desde GitHub LFS durante el build para obtener `data/repositorio.duckdb` (703 MB) |
| Archivo | `Dockerfile` (30 lineas) |

### 6.2 Git LFS

| Extensiones | Archivos |
|:------------|:---------|
| `*.duckdb`, `*.parquet`, `*.pkl`, `*.pt`, `*.safetensors`, `*.npy`, `*.zip`, `*.gz` | Base de datos + embeddings cacheados |
| Exclusion | `.env`, `*.duckdb.wal`, `__pycache__/`, `.streamlit/secrets.toml` |
| Archivo | `.gitattributes` (36 lineas), `.gitignore` (48 lineas) |

### 6.3 HuggingFace Spaces

- URL: `https://jeffersonca-estudio-contexto.hf.space/`
- Repositorio: `https://github.com/Jefferson-GHB/Estudio_Contexto_v3`
- Autenticacion: SHA-256 via `st.secrets` (produccion) con fallback `admin` / `EstudioContexto2026!` (desarrollo)
- Variables de entorno: `GEMINIAPIKEY`, `GITHUB_TOKEN`, `HUGGINGFACE_TOKEN`, `DUCKDB_PATH`

---

## 7. Modulos Condicionales

El unico modulo condicional en `app.py:37-41` es el sistema RAG:

| Flag | Modulo | Dependencia | Funcion |
|:-----|:-------|:------------|:--------|
| `RAG_AVAILABLE` | `services/rag/retrieval.py` (`EducacionRAG`) | `google-generativeai` | Recuperacion aumentada de contexto |

Los modulos de matching semantico (`services/ml/matching.py`, `services/ml/snies_etdh.py`) y territorial (`services/territorial/`) son cargados bajo demanda por `services/data_loader.py` (259 lineas, funcion `cargar_datos_base()`), que centraliza toda la carga de datos de las 4 sintesis evaluativas.

---

## 8. API Backend (Prototipo)

| Aspecto | Detalle |
|:--------|:--------|
| Framework | FastAPI (`api/main.py`) |
| Estado | Prototipo arquitectonico — no integrado al dashboard, no desplegable |
| Valor | Modelado conceptual de 81 variables en 5 ejes y 8 dominios |
| Endpoints | `api/routes.py`: 5 grupos funcionales (estado del sistema, exploracion de variables, recuperacion de datos, generacion de contexto, tendencias) |
| Esquemas | `api/schemas.py` — validacion de datos con Pydantic |
| Motor | `api/engine.py` — construccion dinamica de consultas (no predefinidas) |
| Fuente de verdad | `catalogo/MAPEO_DSS_OFICIAL.csv` (114 variables mapeadas) |

---

## 9. Estructura de Directorios del Proyecto

```
Estudio_Contexto_v3/
├── app.py                        # Dashboard principal (387 lineas). Delega carga de datos a services/data_loader.py y renderizado a views/tab_*.py
├── Dockerfile                    # Contenedor Python 3.13-slim, puerto 7860
├── requirements.txt              # 13 dependencias
├── AGENTS.md                     # Guia para agentes de desarrollo
├── .gitignore                    # 48 lineas (exclusion de temporales, credenciales, artefactos)
├── .gitattributes                # 36 lineas (Git LFS para archivos binarios)
│
├── config/
│   ├── database.py               # Conexion DuckDB read-only + auto-deteccion de ruta
│   ├── styles.py                 # CSS, score cards, welcome banner
│   └── constants.py              # Constantes del sistema
│
├── data/
│   ├── repositorio.duckdb        # Base de datos (703 MB, Git LFS)
│   ├── queries.py                # 56 consultas SQL parametrizadas (3,138 lineas)
│   ├── filters.py                # Constructor de clausulas WHERE + cascada NBC
│   ├── search.py                 # Busqueda semantica con embeddings en disco
│   ├── transform.py              # Transformacion de datos
│   ├── desercion.py              # Modulo especializado SPADIES
│   └── constants.py              # Constantes de datos
│
├── components/
│   ├── sidebar.py                # Sidebar con busqueda inteligente y filtros cascada
│   └── display.py                # Utilidades de visualizacion (section headers)
│
├── services/
│   ├── ml/
│   │   ├── matching.py           # Matching semantico (MiniLM)
│   │   └── snies_etdh.py         # Puente SNIES ↔ SIET (pipeline v2)
│   ├── rag/
│   │   └── retrieval.py          # EducacionRAG (recuperacion aumentada)
│   ├── llm.py                    # Integracion Google Gemini
│   ├── scoring.py                # Indicadores: HHI, CAGR, Ratio Absorcion
│   ├── decision_engine.py        # Motor de recomendacion (6 tipos de oferta)
│   ├── context.py + context_builder.py  # Construccion de contexto para LLM
│   ├── sources.py                # Diccionario de fuentes con URLs (376 lineas)
│   ├── data_loader.py            # Carga de datos
│   └── territorial/
│       ├── functions.py          # Desempeno DNP, cluster empresarial
│       └── normalization.py      # Normalizacion regional
│
├── views/
│   ├── tab_academico.py          # Sintesis Academica
│   ├── tab_laboral.py            # Sintesis Laboral
│   ├── tab_territorial.py        # Sintesis Territorial
│   ├── tab_decision.py           # Decision Final
│   ├── etdh.py                   # Dashboard ETDH
│   └── methodology.py            # Vista de metodologia
│
├── visualizations/
│   └── charts.py                 # Gauges Plotly (HHI, Saber PRO, Score)
│
├── utils/
│   ├── auth.py                   # Autenticacion SHA-256
│   ├── helpers.py                # Utilidades (descarga de datos de graficos)
│   └── reporte_docx.py           # Generador de informe Word profesional
│
├── api/                          # Prototipo FastAPI (no integrado)
│   ├── main.py, routes.py, schemas.py, engine.py, config.py
│
├── catalogo/                     # 26 archivos CSV/JSON de mapeo (SNIES, CUOC, SIET, MEN)
│
├── services/cache_data/           # Embeddings cacheados en disco (180+ archivos .pkl)
│
├── admin/                        # Scripts de auditoria, evaluacion e ingestion
│   ├── ingestar_mapeo_dss.py, auditar_mapeo_dss.py, benchmark_modelos.py, ...
│
├── tests/
│   └── test_queries.py           # 50 tests de integracion contra DuckDB real (666 lineas)
│
├── docs/
│   ├── compose/                  # Documentacion interna de desarrollo
│   └── tecnica/                  # Documentacion tecnica para evaluacion
```

---

*Documento generado a partir de `app.py` (387 lineas, imports L1-35, main L227), `services/data_loader.py` (259 lineas), `data/queries.py` (3,138 lineas, 56 funciones), `AGENTS.md` (56 lineas), `Dockerfile` (30 lineas), `services/sources.py` (376 lineas), y el arbol de directorios del repositorio.*
