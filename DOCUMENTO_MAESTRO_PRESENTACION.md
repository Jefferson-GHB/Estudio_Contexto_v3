# Documento Maestro — Estudio Contexto v3.1.0

Guia tecnica completa para la sustentacion del proyecto ante el jurado del **Concurso Datos al Ecosistema 2026: IA para Colombia**. Todo el contenido esta basado en el codigo fuente real, la base de datos DuckDB y la documentacion tecnica del repositorio.

**Equipo:** Grupo 195 | **Nivel:** Intermedio | **Reto:** Educacion | **Categoria:** Innovacion social

---

## Indice

1. [Que es Estudio Contexto](#1-que-es-estudio-contexto)
2. [El problema que resuelve](#2-el-problema-que-resuelve)
3. [Arquitectura del sistema](#3-arquitectura-del-sistema)
4. [Base de datos DuckDB](#4-base-de-datos-duckdb)
5. [Componentes de Inteligencia Artificial](#5-componentes-de-inteligencia-artificial)
6. [Modulos clave del codigo](#6-modulos-clave-del-codigo)
7. [Metodologia CRISP-ML](#7-metodologia-crisp-ml)
8. [Sistema de filtros](#8-sistema-de-filtros)
9. [Motor de decision y scoring](#9-motor-de-decision-y-scoring)
10. [Validacion y metricas](#10-validacion-y-metricas)
11. [Glosario de terminos tecnicos](#11-glosario-de-terminos-tecnicos)
12. [Que NO hace el sistema (y por que)](#12-que-no-hace-el-sistema-y-por-que)
13. [Alineacion con los criterios del concurso](#13-alineacion-con-los-criterios-del-concurso)
14. [Demostracion en vivo](#14-demostracion-en-vivo)

---

## 1. Que es Estudio Contexto

**Estudio Contexto** es una aplicacion web de analitica institucional que integra datos abiertos del ecosistema educativo colombiano —SNIES, SIET, CUOC, APE, GEIH, ICFES, DNP, SENA, MinTIC, DANE— en un solo motor analitico para producir **estudios de contexto** que orientan decisiones curriculares con evidencia de pertinencia y permanencia.

En terminos practicos: un directivo o comite curricular selecciona un area de conocimiento (ej. "Ingenieria de sistemas"), un departamento (ej. "Bogota"), y la aplicacion responde en tiempo real con indicadores de saturacion de mercado (HHI), tendencia de matricula (CAGR), demanda laboral real (vacantes APE), competencias requeridas (CUOC), condiciones territoriales y un **veredicto final** con recomendacion de oferta educativa.

**URL publica:** https://jeffersonca-estudio-contexto.hf.space/
**Repositorio:** https://github.com/Jefferson-GHB/Estudio_Contexto_v3

### Lo que NO es

- **No es un predictor de desercion individual.** Opera con datos agregados, no infiere riesgo a nivel de estudiante.
- **No es un modelo de machine learning entrenado desde cero.** Usa modelos pre-entrenados (embeddings multilingues) y heuristica cuantitativa documentada.
- **No es un generador automatico de registros calificados.** Es un sistema de apoyo a la decision, no un sustituto del criterio experto.

---

## 2. El problema que resuelve

### Contexto: desercion universitaria en Colombia

La desercion en educacion superior es una senal estructural de riesgo para la calidad, la equidad y la sostenibilidad del sistema. Sus causas se relacionan con:

- **Factores academicos:** saturacion de mercados, baja diferenciacion curricular, calidad insuficiente
- **Factores laborales:** desconexion entre formacion y demanda real de ocupaciones
- **Factores territoriales:** barreras de acceso, conectividad limitada, debil tejido empresarial
- **Factores de decision:** apertura de programas sin evidencia integrada de contexto

### La brecha actual

Las instituciones de educacion superior disponen de fuentes de informacion (SNIES, SIET, SPADIES, APE, CUOC) pero estas operan como **silos de datos**: consultarlos requiere esfuerzo manual, los cruces entre fuentes no estan automatizados, y la evidencia no se integra en un solo punto de decision.

### El enfoque del sistema

La desercion se aborda como una **variable critica de contexto, sostenibilidad y pertinencia.** La herramienta identifica condiciones que pueden afectar la permanencia **antes** de que se consoliden en la operacion academica: un programa con baja pertinencia laboral, abierto en un territorio sin conectividad o en un mercado ya saturado tiene mayor probabilidad de generar condiciones de abandono.

**Pregunta central que responde el sistema:**

> "Dado un area de conocimiento y un territorio, ¿existe evidencia suficiente para ofertar, ajustar o revaluar un programa academico?"

---

## 3. Arquitectura del sistema

El sistema opera en **4 capas**, todas contenidas en un contenedor Docker desplegable:

```
+------------------------------------------------------------------+
| CAPA 4: INTELIGENCIA ARTIFICIAL                                   |
| +------------------+ +-----------------+ +--------------------+  |
| | Busqueda Semantica| | RAG Estructurado| | Generacion LLM     |  |
| | MiniLM (384 dims) | | (EducacionRAG) | | Gemini 2.0 Flash   |  |
| | Matching:         | | Recupera datos  | | Informe academico  |  |
| | SNIES->CUOC->SIET | | DuckDB+SPADIES  | | APA 7a edicion     |  |
| +------------------+ +-----------------+ +--------------------+  |
| +-------------------------------------------------------------+  |
| | Motor de Decision: 30% Academico, 40% Laboral,              |  |
| | 20% Territorial, 10% Global -> OFERTAR / NO OFERTAR / ...   |  |
| +-------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
+------------------------------------------------------------------+
| CAPA 3: ANALITICA (DuckDB 703 MB, read-only, 56 esquemas)       |
| data/queries.py (50+ SQL parametrizadas)                         |
| data/filters.py (WHERE + bridge COD_SNIES_PROGRAMA)              |
| data/search.py (busqueda semantica con cache en disco)           |
| services/scoring.py (HHI, CAGR, Ratio Absorcion)                 |
+------------------------------------------------------------------+
                              |
+------------------------------------------------------------------+
| CAPA 2: PROCESAMIENTO ETL                                        |
| admin/ingestar_*.py - Extraccion fuentes, homologacion           |
| CINE-F, NBC, CUOC, CIIU, MNC, DIVIPOLA                           |
| catalogo/ (26 archivos CSV de mapeo)                             |
+------------------------------------------------------------------+
                              |
+------------------------------------------------------------------+
| CAPA 1: INGESTION DE FUENTES                                     |
| SNIES, SIET, CUOC, APE/SENA, ICFES, Banco Mundial, OECD,        |
| UNESCO, ESCO, GEIH/DANE, MinTIC, DNP, RUES, MIPYMES             |
+------------------------------------------------------------------+
```

### Stack tecnologico

| Capa | Tecnologia | Rol |
|:-----|:-----------|:----|
| Frontend | Streamlit 1.59 | Dashboard con 4 tabs, sidebar con filtros cascada |
| Base de datos | DuckDB 1.5 | 703 MB, lectura exclusiva, ~316 tablas en 56 esquemas |
| ML/NLP | sentence-transformers (MiniLM) | Matching semantico entre nombres de programas, ocupaciones y competencias |
| LLM | Google Gemini 2.0 Flash | Generacion de informe academico con LaTeX y citacion APA |
| RAG | EducacionRAG (custom) | Recuperacion aumentada desde DuckDB con datos de desercion |
| Visualizacion | Plotly 6 | Graficos interactivos (gauges, lineas, radar, sunburst, heatmap) |
| Reportes | python-docx | Documento Word profesional con portada institucional |
| Despliegue | Docker + HuggingFace Spaces | Python 3.13-slim, puerto 7860 |
| API (prototipo) | FastAPI | 81 variables, 5 ejes, 8 dominios, documentacion Swagger |

---

## 4. Base de datos DuckDB

### ¿Por que DuckDB y no PostgreSQL o MySQL?

DuckDB es un motor **analitico embebido** (no requiere servidor). Es ideal para analitica de datos porque:

1. **Embebido:** Un solo archivo de 703 MB contiene toda la base de datos. No requiere instalacion, configuracion ni servidor.
2. **Read-only:** La conexion se abre en modo lectura (`read_only=True`). Es inmutable para el usuario.
3. **SQL completo:** Soporta CTEs, window functions, subconsultas anidadas, expresiones regulares.
4. **Velocidad:** Optimizado para consultas analiticas (agregaciones, joins, filtros) sobre datos tabulares.

### Estructura del repositorio

| Metrica | Valor |
|:--------|:------|
| Tamano total | 703 MB |
| Esquemas | 56 |
| Tablas | ~316 |
| Variables mapeadas (DSS) | 114 |
| Ejes de pertinencia | 5 |
| Dominios funcionales | 8 |

**Principales familias de tablas:**

| Esquema | Contenido | Ejemplos |
|:--------|:----------|:---------|
| `snies.*` | Educacion superior | `snies_programas` (12,865), `snies_matriculados` (297K), `snies_graduados`, `snies_instituciones` |
| `siet.*` | Educacion para el trabajo | `siet_programas` (25,010), `siet_matricula_programa_`, `siet_instituciones` |
| `cuoc.*` | Ocupaciones Colombia | `cuoc_limpio_2025` (14,462 ocupaciones) |
| `competencias.*` | Conocimientos y destrezas | `cuoc_conocimientos` (3,599), `cuoc_destrezas` (4,422) |
| `tendencias_laborales.*` | Mercado laboral | `vacantes_ape_clean` |
| `conectividad.*` | Internet y cobertura | `internet_fijo_accesos`, `cobertura_movil_*` |
| `catalogo_curado.*` | Mapeos y catalogos | NBC-CUOC, CUOC-CIIU, cualificaciones MEN |
| `indicadores_globales.*` | Banco Mundial | `bm_desempleo_jovenes`, `bm_pib_per_capita` |
| `divipola.*` | Division politica DANE | Departamentos, municipios |
| `territorial.*` | Contexto territorial | `municipios_pdet` (170 municipios priorizados) |
| `rues_camaras_comercio.*` | Tejido empresarial | Empresas activas, top 10,000 |
| `dnp_planes_desarrollo.*` | Politica publica | Medicion desempeno municipal |
| `oecd_internacional.*` | Datos internacionales | OECD, UNESCO, ILO |

### Acceso y seguridad

```python
# config/database.py - Conexion siempre en modo lectura
def get_conn():
    return duckdb.connect(DUCKDB_PATH, read_only=True)
```

La ruta de la BD se auto-detecta: variable de entorno `DUCKDB_PATH` -> `data/repositorio.duckdb` -> fallback. Esto permite que la misma aplicacion funcione en desarrollo local, en Docker y en HuggingFace Spaces sin cambiar codigo.

---

## 5. Componentes de Inteligencia Artificial

### 5.1 Busqueda Semantica con Embeddings Multilingues

#### ¿Que es un embedding?

Un embedding es una **representacion numerica de texto** en un espacio vectorial de alta dimension (384 en nuestro caso). Palabras o frases con significado similar quedan cercanas en ese espacio, aunque no compartan ninguna palabra literal.

**Ejemplo concreto:** "Ingenieria de sistemas" y "Desarrollo de software" no comparten palabras pero sus embeddings estan cercanos porque semanticamente se refieren a lo mismo.

#### ¿Por que MiniLM y no otro modelo?

| Criterio | MiniLM (384d) | Alternativas consideradas |
|:---------|:--------------|:--------------------------|
| **Dimension** | 384 | BERT-base (768), GPT embeddings (1536) |
| **Idioma** | Multilingue (50+ lenguajes) | Modelos solo-ingles no funcionan con nombres de programas en espanol |
| **Tamano** | ~470 MB en disco | Modelos mas grandes (1-2 GB) son inviables en HuggingFace Spaces |
| **Velocidad** | Sub-segundo | Modelos mas grandes requieren GPU |
| **Precision** | Suficiente para matching de programas y ocupaciones | Mejor precision con modelos grandes, pero trade-off de recursos |

**Modelo:** `paraphrase-multilingual-MiniLM-L12-v2` (via `sentence-transformers`)

#### ¿Como funciona el matching?

1. **Indexacion:** Los nombres de todos los programas SNIES (12,865), SIET (25,010) y Saber PRO (~10,000) se convierten a embeddings y se almacenan en cache en disco (`services/cache_data/ml_embeddings/`).
2. **Consulta:** Cuando el usuario selecciona un NBC, el sistema genera el embedding de la consulta.
3. **Similitud:** Calcula la similitud coseno entre el embedding de la consulta y todos los embeddings del corpus.
4. **Umbral adaptativo:** En lugar de un umbral fijo, se usa: `threshold = max(0.25, mediana(scores) + 1.5 * std(scores))` limitado a 0.70. Esto se ajusta automaticamente a la distribucion de similitudes de cada consulta.
5. **Resultados:** Los matches por encima del umbral se retornan ordenados por score.

**Ubicacion en el codigo:** `services/ml/matching.py`, `services/ml/snies_etdh.py`, `data/search.py`

#### Puente SNIES ↔ SIET

Este es el componente mas innovador. Tradicionalmente, la educacion superior (SNIES) y la educacion para el trabajo (SIET) se analizan por separado. El sistema usa un **puente en dos etapas:**

1. **Etapa estructural:** El NBC se mapea a areas de cualificacion CUOC usando catalogos oficiales. Esas areas se traducen a areas de desempeno SIET.
2. **Etapa semantica:** Los programas SIET en esas areas se comparan semanticamente con el nombre del NBC via embeddings.

Esto revela complementariedades entre ambos sistemas que los datos estructurados no harian visibles. Por ejemplo, un NBC en "Ingenieria de sistemas" puede identificar programas SIET en "Desarrollo de software" como ruta complementaria de formacion.

**Validacion:** La funcion `validate_bridge()` ejecuta 4 verificaciones automaticas: resultados no vacios, dispersion de scores (>0.1), ratio top/resto (<3x), y consistencia de areas.

### 5.2 RAG — Recuperacion Aumentada con Datos Estructurados

#### ¿Que es RAG?

RAG (Retrieval-Augmented Generation) es una tecnica que **enriquece el contexto** que se envia a un LLM con datos recuperados de una fuente de conocimiento externa. En lugar de depender solo de lo que el LLM "sabe" de su entrenamiento, se le proporcionan datos especificos y actualizados.

#### Implementacion

Nuestro RAG (`services/rag/retrieval.py`, clase `EducacionRAG`) es **estructurado**, no vectorial:

- **Fuente:** DuckDB (tablas de SPADIES, Saber PRO, transito inmediato, cobertura)
- **Metodo:** Consulta SQL directa, no busqueda por similitud
- **Funcion:** `augment_context(nbc_codigo, departamento, contexto, filtros_activos)`

Cuando el usuario solicita un informe con IA, antes de enviar el prompt a Gemini, el sistema:
1. Recupera datos de desercion del NBC desde DuckDB
2. Recupera resultados Saber PRO
3. Recupera tasas de transito inmediato y cobertura
4. Agrega estos datos al contexto del prompt

Esto garantiza que el LLM tenga acceso a datos actualizados que NO estan en su entrenamiento original.

**Disponibilidad:** Condicional (`RAG_AVAILABLE` en `app.py:116`). Requiere `google-generativeai`. Si no esta disponible, el LLM opera con el contexto base del dashboard.

### 5.3 Generacion LLM — Informe Academico

#### Modelo y configuracion

| Parametro | Valor |
|:----------|:------|
| Modelo principal | `gemini-2.0-flash` |
| Fallbacks | `gemini-2.5-flash`, `gemini-flash-latest`, `gemini-2.0-flash-lite` |
| API Key | `GEMINIAPIKEY` o `GOOGLEAPIKEY` (variables de entorno) |
| Temperatura | 0.7 |
| Max tokens | 16,384 |

#### Estructura del prompt

El prompt del sistema tiene **~480 lineas** y define:

1. **Perfil academico** del asistente (investigador senior, doctor en politicas educativas, 25 anos de experiencia)
2. **Reglas de citacion** (catalogo de 15 fuentes oficiales con formato `FUENTE - Periodo`)
3. **Estructura del informe** (7 secciones obligatorias con formato paper academico)
4. **Reglas de LaTeX** (`\frac`, `\sum`, `\left`, `\right`, `\%`)
5. **Prohibicion de emojis**

El prompt de tarea incluye el contexto completo (datos del dashboard, RAG, puente de competencias) y las instrucciones adicionales del usuario.

#### ¿Por que Gemini y no otro LLM?

- **Acceso gratuito** via API (no requiere infraestructura propia)
- **Soporte nativo de LaTeX** en la salida
- **Ventana de contexto** suficiente para el prompt completo (~480 lineas de sistema + contexto variable)
- **Disponible en Colombia** (no requiere VPN)
- **4 modelos en fallback** para robustez

---

## 6. Modulos clave del codigo

### Estructura del repositorio (post-refactor)

```
Estudio_Contexto_v3/              # 380 lineas (era 4053 antes del refactor)
├── app.py                        # Entrypoint principal (387 L): auth, sidebar, carga datos, tabs
├── views/                        # Vistas por sintesis evaluativa
│   ├── tab_academico.py          # Tab 1: Concentracion (HHI), crecimiento (CAGR), Saber PRO, desglose (907 L)
│   ├── tab_laboral.py            # Tab 2: Demanda laboral, competencias, salarios, puente SNIES-SIET (674 L)
│   ├── tab_territorial.py        # Tab 3: Territorio, conectividad, cluster empresarial, scoring (560 L)
│   └── tab_decision.py           # Tab 4: Score ponderado, veredicto, LLM, ESCO (592 L)
├── services/
│   ├── context.py                # Dataclass Context: 52 campos compartidos entre tabs (83 L)
│   ├── data_loader.py            # Carga centralizada: NBCs, stats, ML matching (259 L)
│   ├── scoring.py                # HHI, CAGR, Ratio Absorcion, Score Final (111 L)
│   ├── decision_engine.py        # 6 tipos de oferta educativa (72 L)
│   ├── context_builder.py        # Construye contexto markdown para LLM (493 L)
│   ├── sources.py                # Diccionario de 28 fuentes con URLs y citaciones (376 L)
│   ├── ml/
│   │   ├── matching.py           # Matching semantico: embeddings, cosine similarity
│   │   └── snies_etdh.py         # Puente SNIES ↔ SIET (pipeline v2 unificado)
│   ├── rag/
│   │   └── retrieval.py          # EducacionRAG: recuperacion aumentada desde DuckDB
│   └── territorial/
│       ├── functions.py          # Desempeno DNP, cluster empresarial (RUES)
│       └── normalization.py      # Normalizacion regional
├── data/
│   ├── queries.py                # 50+ consultas SQL parametrizadas (~2000 L)
│   ├── filters.py                # Constructor clausulas WHERE + bridge COD_SNIES_PROGRAMA (387 L)
│   ├── search.py                 # Busqueda semantica con embeddings en disco (183 L)
│   ├── constants.py              # Stopwords para NLP
│   └── repositorio.duckdb        # BD principal (703 MB, Git LFS)
├── config/
│   ├── database.py               # Conexion DuckDB read-only (27 L)
│   ├── styles.py                 # CSS + componentes UI (score cards, glass cards, etc.) (680 L)
│   └── constants.py              # TEMPLATE_COLORS, SEXO_NORMALIZE_SQL
├── components/
│   ├── sidebar.py                # Sidebar con filtros cascada y busqueda inteligente
│   └── display.py                # section_header y utilidades de UI
├── visualizations/
│   └── charts.py                 # Gauges Plotly: HHI, Saber PRO, Score
├── utils/
│   ├── auth.py                   # Autenticacion SHA-256 (176 L)
│   ├── helpers.py                # descargar_datos_grafico, utilidades
│   └── reporte_docx.py           # Generador informe Word profesional
├── api/                          # Prototipo FastAPI (no integrado, 2070 L engine)
├── admin/                        # Scripts ETL: auditoria, ingesta, validacion
├── catalogo/                     # 26 archivos CSV/JSON de mapeo
├── docs/tecnica/                 # Documentacion para evaluacion (8 archivos)
├── tests/
│   └── test_queries.py           # 50 tests de integracion contra DuckDB real (666 L)
├── Dockerfile                    # Contenedor Python 3.13-slim, puerto 7860
├── .github/workflows/ci.yml      # CI: ejecuta los 50 tests en cada push
└── requirements.txt              # 13 dependencias
```

### Funciones criticas que debes conocer

| Funcion | Ubicacion | Que hace |
|:--------|:----------|:---------|
| `main()` | `app.py:227` | Entrypoint: auth, sidebar, carga datos, 4 tabs |
| `cargar_datos_base()` | `services/data_loader.py:36` | Carga TODOS los datos antes de los tabs |
| `analizar_con_llm()` | `app.py:72-220` | Envia contexto a Gemini, retorna informe |
| `build_where_clause()` | `data/filters.py:138` | Construye WHERE para snies_programas |
| `build_where_clause_matriculados()` | `data/filters.py:273` | Bridge para matriculados/graduados |
| `calcular_hhi()` | `services/scoring.py:7` | Indice Herfindahl-Hirschman de concentracion |
| `calcular_cagr()` | `services/scoring.py:36` | Tasa de crecimiento anual compuesta |
| `calcular_score_final()` | `services/scoring.py:97` | Score ponderado (30/40/20/10) |
| `determinar_tipo_oferta()` | `services/decision_engine.py:4` | 6 tipos de oferta educativa |
| `match_nbc_to_siet_v2()` | `services/ml/snies_etdh.py:702` | Puente semantico SNIES → SIET |
| `get_skills_bridge_analysis_v2()` | `services/ml/snies_etdh.py` | Puente de competencias via CUOC |
| `EducacionRAG.augment_context()` | `services/rag/retrieval.py` | Enriquecimiento RAG para LLM |

---

## 7. Metodologia CRISP-ML

El desarrollo sigue el marco **CRISP-ML** (Cross-Industry Standard Process for Machine Learning), adaptado al dominio educativo:

### Fase 1: Comprension del problema

- Definicion del marco de pertinencia educativa como dispositivo de decision institucional
- Cuatro sintesis evaluativas: academica, laboral, territorial, global
- Identificacion de la desercion como variable transversal de contexto

### Fase 2: Comprension de los datos

- Inventario exhaustivo de fuentes oficiales colombianas
- Construccion de repositorio unificado DuckDB con 56 esquemas tematicos
- Homologacion con clasificadores: CINE-F, NBC, CUOC, CIIU, MNC, DIVIPOLA

### Fase 3: Preparacion de los datos (ETL)

- Extraccion desde portales oficiales (Socrata API, descarga directa XLSX/CSV)
- Limpieza: estandarizacion de nombres, formatos, periodos, codigos
- Transformacion: homologacion con clasificadores oficiales
- Carga en DuckDB con esquemas normalizados
- `admin/ingestar_*.py` documenta el proceso reproducible

### Fase 4: Modelado

- **Indicadores cuantitativos:** HHI, CAGR, ratio de absorcion, indice de conectividad
- **Busqueda semantica:** Modelo MiniLM pre-entrenado, embeddings cacheados en disco
- **Puente SNIES-SIET:** Matching en dos etapas (estructural + semantico)
- **RAG estructurado:** Recuperacion desde DuckDB para enriquecer contexto LLM
- **Motor de decision:** Scoring ponderado con 6 tipos de recomendacion

### Fase 5: Evaluacion

- 50 pruebas automatizadas contra datos reales
- Validacion de filtros, consultas, consistencia entre tablas y rendimiento
- Bridge match rate: 51% de correspondencia directa entre programas y matriculados

### Fase 6: Despliegue

- Contenedor Docker (Python 3.13-slim, puerto 7860)
- HuggingFace Spaces para demo publica
- Git LFS para archivos binarios (>100 MB)
- CI via GitHub Actions

---

## 8. Sistema de filtros

### Filtros en cascada

El sidebar ofrece filtros jerarquicos que se recalculan dinamicamente:

```
Campo Amplio CINE-F → Area de Conocimiento → NBC
Departamento → Municipio
```

Cuando se selecciona un filtro, las opciones de los demas se actualizan mediante interseccion de todos los filtros activos (funcion `cargar_opciones_cruzadas()` en `components/sidebar.py`).

### Dos sistemas de consulta SQL

El repositorio DuckDB tiene diferencias de esquema entre tablas. Para resolverlas, el sistema usa:

| Sistema | Funcion | Para |
|:--------|:--------|:-----|
| Directo | `build_where_clause(filtros, alias)` | Tablas con columnas identicas a los filtros (`snies_programas`) |
| Bridge | `build_where_clause_matriculados(filtros)` | Tablas con columnas diferentes (`snies_matriculados`, `snies_graduados`) |

**El problema del bridge:** Las tablas de matriculados usan `MODALIDAD` como `METODOLOGIA`, `SECTOR` como `SECTOR_IES`, etc. Ademas, `COD_SNIES_PROGRAMA` puede tener sufijo `.0` (float-as-string). El bridge:

1. Construye una subconsulta que usa `COD_SNIES_PROGRAMA` como puente hacia `snies_programas`
2. Normaliza con `REGEXP_REPLACE(CAST(... AS VARCHAR), '\\.0$', '')`
3. Consolida multiples filtros en una sola subconsulta

### Case sensitivity en NBCs

`NUCLEO_BASICO_DEL_CONOCIMIENTO` en programas usa mayusculas y tildes. `NBC` en matriculados usa un formato diferente. `data/filters.py` normaliza via `UPPER()`.

---

## 9. Motor de decision y scoring

### Pesos del scoring

| Sintesis | Peso | Indicadores principales |
|:---------|:-----|:------------------------|
| Academica | 30% | HHI (concentracion), CAGR (crecimiento), Saber PRO (calidad) |
| Laboral | 40% | Volumen de vacantes APE, ratio de absorcion (x3 ajustado), senal salarial SIGEP/OLE, densidad de competencias CUOC, bonus por puente SNIES-SIET |
| Territorial | 20% | Conectividad digital, desempeno municipal DNP, municipios PDET, cluster empresarial |
| Global | 10% | Desempleo juvenil Colombia (Banco Mundial) |

**¿Por que 40% laboral?** Porque la empleabilidad es el indicador mas directo de pertinencia: un programa puede tener baja saturacion academica, pero si no hay mercado laboral que absorba a sus graduados, la probabilidad de abandono por perdida de valor del titulo es alta.

### Score laboral desglosado

El score laboral no es un numero simple. Se descompone en 4 subcomponentes:

| Subcomponente | Peso | Como se calcula |
|:--------------|:-----|:----------------|
| Volumen de vacantes | 30% | Escalonado: >50K=100, >20K=80, >5K=60, >1K=40, >100=20 |
| Ratio de absorcion | 20% | `min(100, ratio × 3 × 50)` — el factor x3 corrige el subreporte de la APE |
| Senal salarial | 25% | `min(100, (salario / SMLV / 3) × 100)` |
| Competencias CUOC | 25% | `min(100, n_competencias × 5)` — 20 competencias = 100 |

**Bonus:** Si el puente SNIES-SIET muestra alineacion de competencias (>15%), se suman hasta 20 puntos adicionales.

### Veredictos

| Score | Veredicto | Color |
|:------|:----------|:------|
| >= 80 | OFERTAR | Verde |
| 50-79 | OFERTAR CON AJUSTES | Amarillo |
| < 50 | REVALUAR | Rojo |

### Tipos de oferta educativa

El motor (`services/decision_engine.py`) recomienda entre 6 tipos segun la combinacion de scores:

| Tipo | Condiciones |
|:-----|:------------|
| PROGRAMA_COMPLETO | Academica >= 70, Laboral >= 70, Territorial >= 60 |
| RUTA_FORMATIVA | Demanda existe pero restricciones territoriales |
| MICROCREDENCIAL | Alta demanda laboral, baja demanda academica |
| EDUCACION_CONTINUA | Multiples competencias identificadas (>8) |
| EVALUAR_VIABILIDAD | Scores mixtos, requiere estudio adicional |
| NO_RECOMENDADO | Baja demanda en todas las sintesis |

---

## 10. Validacion y metricas

### Suite de pruebas automatizadas

`tests/test_queries.py` (666 lineas) ejecuta **50 pruebas de integracion** contra la base de datos real (no mocks, no datos sinteticos):

| Categoria | Pruebas | Ejemplos |
|:----------|:--------|:---------|
| Construccion de filtros | 8 | Single NBC, NBC+Depto+Mod, all filters, empty |
| Consultas programas | 6 | `get_estadisticas_basicas`, `get_benchmarking_data`, `get_desglose_academico` |
| Matriculados y graduados | 11 | `get_market_share`, `get_tendencia_matricula`, `get_graduados_historico` |
| Explorador interactivo | 6 | Multiples combinaciones de dimensiones y filtros |
| SIET | 3 | `get_estadisticas_siet`, `get_desglose_siet` |
| Laboral (ML matching) | 6 | `get_vacantes_reales`, `get_competencias_cuoc`, `get_salarios_reales` |
| Territorial | 2 | `get_conectividad_territorial`, `get_municipios_pdet` |
| Consistencia de datos | 3 | NBC case match, bridge match rate |
| Rendimiento | 3 | Benchmarks: <500ms todas las funciones |

**Resultado actual:** 50 OK / 0 FAIL / 0 SKIP

**Ejecucion:** `python -m tests.test_queries` (exit code 0 = todo OK, 1 = fallos)

### Metricas de consistencia

| Metrica | Valor | Interpretacion |
|:--------|:------|:---------------|
| Bridge match rate | 51% | 15,279 de 29,755 programas tienen correspondencia directa entre tablas |
| NBC case match | UPPER matches | Normalizacion resuelve diferencias de capitalizacion |
| Tiempo `get_estadisticas_basicas` | ~131ms | Sub-500ms para consultas con filtros complejos |
| Tiempo `get_market_share` | ~127ms | Consulta con subquery anidada |
| Tiempo `get_tendencia_matricula` | ~129ms | Serie temporal sobre ~300K registros |

### Validacion del matching semantico

| Metrica | Valor |
|:--------|:------|
| Threshold matching SNIES-CUOC | Adaptativo: `max(0.25, mediana + 1.5*std)`, cap 0.70 |
| Threshold skills bridge | 0.35 fijo |
| Validacion del puente (validate_bridge) | 4 checks: n_results > 0, score_spread > 0.1, ratio top/resto < 3x, areas identificadas |

---

## 11. Glosario de terminos tecnicos

### Terminos generales

| Termino | Definicion |
|:--------|:-----------|
| **SNIES** | Sistema Nacional de Informacion de la Educacion Superior. Base de datos oficial del MEN con todos los programas de educacion superior en Colombia. |
| **SIET** | Sistema de Informacion de Educacion para el Trabajo. Equivalente al SNIES pero para formacion tecnica laboral (cursos cortos, certificaciones). |
| **NBC** | Nucleo Basico del Conocimiento. Clasificacion del MEN que agrupa programas academicos afines (ej. "Ingenieria de sistemas, telematica y afines"). Hay 54 NBCs. |
| **CINE-F** | Clasificacion Internacional Normalizada de la Educacion - Campos de formacion (UNESCO 2013). Estructura jerarquica: Campo Amplio → Campo Especifico → Campo Detallado. |
| **CUOC** | Clasificacion Unica de Ocupaciones para Colombia (DANE). Define 680 ocupaciones estandarizadas con sus competencias, conocimientos y destrezas. |
| **CIIU** | Clasificacion Industrial Internacional Uniforme. Categoriza actividades economicas (700 codigos). Usada para mapear sectores productivos. |
| **MNC** | Marco Nacional de Cualificaciones. Define 8 niveles de cualificacion desde operativo (1) hasta doctorado (8). |
| **DIVIPOLA** | Division Politico-Administrativa de Colombia (DANE). Codigos oficiales de departamentos y municipios. |
| **APE** | Agencia Publica de Empleo (SENA). Registra vacantes, inscritos y colocados del mercado laboral colombiano. |
| **PDET** | Programas de Desarrollo con Enfoque Territorial. 170 municipios priorizados para el postconflicto. |
| **GEIH** | Gran Encuesta Integrada de Hogares (DANE). Fuente de datos salariales. |
| **OLE** | Observatorio Laboral para la Educacion (MinEducacion). Datos de ingreso base de cotizacion de graduados. |
| **SIGEP** | Sistema de Informacion y Gestion del Empleo Publico. Datos salariales del sector publico. |
| **MDM** | Medicion de Desempeno Municipal (DNP). Indicador de capacidad institucional de cada municipio (0-100). |
| **ESCO** | European Skills, Competences, Qualifications and Occupations. Taxonomia europea de 13,939 habilidades. |
| **SPADIES** | Sistema para la Prevencion de la Desercion de la Educacion Superior. Datos historicos de desercion por programa. |

### Terminos de IA/ML

| Termino | Definicion |
|:--------|:-----------|
| **Embedding** | Representacion numerica (vector) de un texto en un espacio de alta dimension. Palabras con significado similar tienen vectores cercanos. En nuestro caso, 384 numeros por cada texto. |
| **MiniLM** | Modelo de lenguaje pre-entrenado por Microsoft. Version "multilingual" entiende 50+ idiomas incluyendo espanol. 384 dimensiones, ~470 MB. |
| **sentence-transformers** | Libreria Python que facilita usar modelos como MiniLM para generar embeddings y calcular similitud semantica. |
| **Similitud coseno** | Medida matematica de que tan cercanos estan dos vectores en el espacio. Va de -1 (opuestos) a 1 (identicos). Usamos >0.25 como umbral minimo. |
| **RAG** | Retrieval-Augmented Generation. Tecnica que recupera datos de una fuente externa y los agrega al prompt de un LLM para mejorar la precision de sus respuestas. |
| **LLM** | Large Language Model. Modelo de inteligencia artificial entrenado con cantidades masivas de texto. En nuestro caso, Google Gemini. |
| **Prompt engineering** | Diseno cuidadoso de las instrucciones que se envian al LLM para obtener respuestas de calidad. Nuestro prompt tiene ~480 lineas. |
| **Threshold adaptativo** | Umbral de similitud que se ajusta automaticamente segun la distribucion de scores de cada consulta, en lugar de usar un valor fijo. |
| **Bridge / Puente** | Mecanismo que conecta dos sistemas de datos que usan diferentes esquemas o nomenclaturas. |

### Terminos de metricas y scoring

| Termino | Definicion |
|:--------|:-----------|
| **HHI** | Indice Herfindahl-Hirschman. Mide concentracion de mercado: suma de los cuadrados de las cuotas de mercado. <1000: competitivo, 1000-1800: moderado, >1800: concentrado. |
| **CAGR** | Compound Annual Growth Rate. Tasa de crecimiento anual compuesta: `(Vf/Vi)^(1/n) - 1`. Mide la tendencia de matricula en el tiempo. |
| **Ratio de absorcion** | `Vacantes APE / Graduados`. Mide la capacidad del mercado laboral de absorber los graduados de un NBC. Se ajusta x3 por subreporte de la APE (solo captura ~30-40% del mercado). |
| **Score de pertinencia** | Ponderacion de las 4 sintesis evaluativas (30% academica, 40% laboral, 20% territorial, 10% global). Escala 0-100. |
| **Bridge match rate** | Porcentaje de programas en `snies_matriculados` cuyo `COD_SNIES_PROGRAMA` tiene correspondencia directa en `snies_programas`. |

---

## 12. Que NO hace el sistema (y por que)

### No predice desercion individual

**Por que:** Los datos abiertos disponibles son agregados (por programa, departamento, ano). Predecir desercion a nivel de estudiante requeriria datos individuales (notas, asistencia, condicion socioeconomica) que no son publicos por razones de privacidad.

**Que hace en su lugar:** Analiza condiciones estructurales de contexto (saturacion de mercado, demanda laboral, conectividad territorial) asociadas a la permanencia. La ruta hacia prediccion supervisada esta documentada como objetivo de mediano plazo.

### No entrena un modelo supervisado desde cero

**Por que:** El valor del sistema esta en la integracion de fuentes y en la generacion de evidencia trazable. Entrenar un clasificador (ej. Random Forest para desercion) requeriria datos etiquetados que no estan disponibles como datos abiertos. Ademas, un modelo "caja negra" seria menos interpretable para directivos que indicadores cuantitativos transparentes como HHI y CAGR.

**Que usa en su lugar:** Modelos pre-entrenados (MiniLM para embeddings), heuristica cuantitativa documentada (scoring con formulas explicitas), y APIs externas (Gemini para generacion de texto). Todo es trazable y auditable.

### No automatiza la actualizacion de fuentes

**Por que:** Las fuentes oficiales (SNIES, SIET, APE) publican nuevos cortes en calendarios irregulares. Automatizar la deteccion y descarga requeriria monitoreo continuo de portales gubernamentales.

**Que tiene en su lugar:** Scripts documentados de ingestion (`admin/ingestar_*.py`) que registran fuente, fecha de corte, transformaciones aplicadas y responsable de validacion. La actualizacion es manual pero reproducible.

### No funciona sin el archivo DuckDB

**Por que:** La base de datos de 703 MB contiene todos los datos pre-procesados y normalizados. Sin ella, el dashboard no tiene datos que consultar.

**Como se distribuye:** Via Git LFS. El `Dockerfile` clona el repositorio completo (incluyendo LFS) durante el build. En desarrollo local, el archivo debe estar en `data/repositorio.duckdb`.

---

## 13. Alineacion con los criterios del concurso

### Nivel Intermedio — Requisitos y como los cumple el sistema

| Requisito del concurso | Evidencia en el sistema |
|:-----------------------|:------------------------|
| Integrar 3-10 conjuntos de datos del portal | 7 fuentes oficiales integradas: SNIES, SIET, CUOC, APE, ICFES, GEIH, DNP. Mas fuentes internacionales (Banco Mundial, OECD, UNESCO) y catalogos. |
| Al menos 1 dataset de datos.gov.co | Multiples datasets via Socrata API documentados en `services/sources.py` y `docs/tecnica/05_fuentes_datos.md` |
| 10-20 variables en el modelo | 114 variables en el modelo DSS, 50+ consultas SQL, 56 esquemas de datos |
| Procesos de limpieza y transformacion | Pipeline ETL documentado: extraccion, estandarizacion, homologacion con CINE-F/NBC/CUOC/CIIU/MNC/DIVIPOLA, validacion de consistencia entre tablas |
| Modelos de ML mas avanzados | Matching semantico con embeddings multilingues, RAG estructurado, generacion LLM, motor de decision multi-componente |
| Procesamiento de lenguaje natural | Busqueda semantica de programas, matching NBC-CUOC via embeddings, puente competencias SNIES-SIET, generacion de informes con Gemini |
| Sistema de recomendacion | Motor de decision con 6 tipos de oferta educativa basado en scoring ponderado |
| Pruebas automatizadas | 50 tests de integracion contra datos reales, benchmark de rendimiento |
| Documentacion del repositorio | 7+ documentos tecnicos en `docs/tecnica/`, `AGENTS.md`, `README.md`, `Changelog.md` |
| Evidencia de fuentes | `services/sources.py` (376 lineas) con 28 fuentes documentadas: nombre, entidad, URL, periodo, actualizacion |
| Despliegue funcional | Docker + HuggingFace Spaces. URL publica activa. |
| API documentada | Prototipo FastAPI con Swagger (`api/`): 81 variables, 5 ejes, 8 dominios |
| Arquitectura de datos | DuckDB con 56 esquemas, ~316 tablas, 114 variables mapeadas |

---

## 14. Demostracion en vivo

### Flujo recomendado para la sustentacion

1. **Login** (credenciales: admin / EstudioContexto2026!)
2. **Seleccionar un NBC** en el sidebar → Ej: "Ingenieria de sistemas, telematica y afines"
3. **Tab 1 - Academico:** Mostrar el gauge HHI (concentracion de mercado), CAGR (crecimiento), graficos de evolucion estudiantil
4. **Tab 2 - Laboral:** Mostrar ratio de absorcion, salarios OLE/SIGEP, radar de competencias, puente SNIES-SIET
5. **Tab 3 - Territorial:** Mostrar indicadores educativos, conectividad, cluster empresarial, score territorial
6. **Tab 4 - Decision:** Mostrar los 4 gauges de scoring, el veredicto, el tipo de oferta recomendada
7. **(Opcional) Generar informe con IA:** Click en "Analizar con IA" para mostrar el informe generado por Gemini

### Puntos fuertes para destacar ante el jurado

1. **Integracion real de 7+ fuentes oficiales** en un solo motor analitico
2. **50 tests automatizados** que validan consistencia de datos y correccion de filtros
3. **Matching semantico con umbral adaptativo** que resuelve el problema de vocabularios diferentes entre sistemas
4. **Puente SNIES-SIET** que revela complementariedades entre educacion formal y formacion para el trabajo
5. **Motor de decision transparente** con formulas documentadas y pesos justificados
6. **RAG estructurado** que enriquece el contexto del LLM con datos actualizados de DuckDB
7. **Despliegue productivo** en Docker + HuggingFace Spaces con CI via GitHub Actions
8. **Codigo modularizado** (refactor reciente de monolitico 4053L a 387L + 7 modulos)

### Lo que NO debes decir

- No digas que es un "modelo predictivo de desercion" — es un sistema de analitica contextual
- No digas que "entrenamos un modelo de ML" — usamos modelos pre-entrenados y heuristica
- No digas que "reemplaza el criterio experto" — es un sistema de apoyo a la decision
- No digas "inteligencia artificial" a secas — especifica los 3 componentes: embeddings, RAG, LLM

### Lo que SI debes decir

- "Integramos 7 fuentes oficiales en un repositorio analitico unificado"
- "Usamos embeddings multilingues para encontrar correspondencias semanticas entre programas y ocupaciones"
- "El motor de decision pondera 4 dimensiones con pesos documentados y justificados"
- "50 pruebas automatizadas validan la integridad del pipeline de datos"
- "El sistema produce evidencia trazable: cada dato tiene fuente, periodo y metodo de calculo"
