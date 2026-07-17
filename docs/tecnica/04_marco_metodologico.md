# Marco Metodologico — CRISP-ML

Aplicacion del marco CRISP-ML (Cross-Industry Standard Process for Machine Learning) adaptado al dominio de la analitica educativa para el Sistema de Analisis de Contexto para la Toma de Decisiones Educativas.

---

## Fase 1: Comprension del Problema

### Definicion del Marco de Pertinencia Educativa

El problema central es la deserción universitaria como señal estructural de riesgo para la calidad, la equidad y la sostenibilidad de la educación superior en Colombia. Las instituciones diseñan, renuevan o modifican programas académicos sin una lectura integrada del contexto (mercado educativo, demanda laboral, territorio, competencias, trayectorias), lo que puede generar condiciones que afectan la permanencia estudiantil.

### Objetivo del Proyecto

Implementar una aplicación web que integre datos abiertos educativos, laborales y territoriales para producir estudios de contexto, indicadores de pertinencia y recomendaciones accionables sobre oferta académica, incorporando la deserción como variable de comprension de condiciones de permanencia.

### Estructura de Decision

El problema se descompone en **cuatro sintesis evaluativas**:

| Sintesis | Pregunta que responde | Peso en decisión |
|:---------|:----------------------|:-----------------|
| Academica | La oferta actual responde a necesidades de la poblacion o genera condiciones de riesgo para la permanencia? | 30% |
| Laboral | Existen ocupaciones, vacantes y competencias que respalden la empleabilidad? | 40% |
| Territorial | El departamento tiene conectividad, demanda y condiciones de acceso? | 20% |
| Global | Como se comparan las tendencias locales con el contexto internacional? | 10% |

---

## Fase 2: Comprension de los Datos

### Inventario de Fuentes

Se realizo un inventario exhaustivo de fuentes oficiales y abiertas del ecosistema educativo colombiano, que derivo en la construccion de un repositorio unificado DuckDB con 54 esquemas tematicos organizados en cuatro grupos:

| Grupo | Fuentes | Esquemas | Descripcion |
|:------|:--------|:---------|:------------|
| A | Portal datos.gov.co (Socrata API) | 19 esquemas | Datos del portal oficial de datos abiertos del Estado colombiano |
| B | Portales MEN/ICFES (descarga directa) | 4 esquemas | SNIES, SIET, ICFES Saber PRO/TyT |
| C | Organismos internacionales | 7 esquemas | Banco Mundial, OECD, UNESCO, ILO, ESCO |
| D | Catalogos curados (elaboración propia) | 26 esquemas | Mapeos NBC-CUOC, CINE-F, CIIU, MNC, DIVIPOLA, tendencias |

### Volumen y Cobertura

| Metrica | Valor |
|:--------|:------|
| Tamano total del repositorio | 703 MB |
| Numero de esquemas | 56 |
| Numero de tablas | 488 |
| Registros totales | > 8 millones |
| Periodo de cobertura | 2014-2025 |
| Cobertura geografica | 33 departamentos, 1,122 municipios |
| NBCs cubiertos | 55 (todos los definidos por el MEN) |

### Documentacion de Fuentes

Todas las fuentes estan documentadas con trazabilidad en:
- `services/sources.py` (376 lineas): URLs, entidades, períodos, citaciones
- `docs/tecnica/05_fuentes_datos.md`: Clasificacion detallada con evidencia de origen

---

## Fase 3: Preparacion de los Datos (ETL)

### Procesos de Extraccion

| Fuente | Metodo de extraccion | Formato | Scripts |
|:-------|:---------------------|:--------|:--------|
| SNIES | Descarga directa de archivos XLSX desde `snies.mineducacion.gov.co` | XLSX | `admin/ingestar_*.py` |
| SIET | Descarga directa desde `siet.mineducacion.gov.co` | CSV | `admin/ingestar_*.py` |
| datos.gov.co | API Socrata | JSON/CSV | `admin/ingestar_*.py` |
| Banco Mundial | API `datos.bancomundial.org` | JSON | Scripts en `admin/` |
| CUOC 2025 | Archivos XLSX desde `dane.gov.co` | XLSX | Scripts en `admin/` |
| ICFES | Archivos de resultados Saber PRO/TyT | CSV | Scripts en `admin/` |

### Procesos de Limpieza y Homologacion

1. **Estandarizacion de nombres, formatos, períodos, codigos y unidades de análisis**
2. **Homologacion con clasificadores oficiales:**

| Clasificador | Proposito | Tablas afectadas |
|:-------------|:----------|:-----------------|
| CINE-F 2013 (UNESCO) | Clasificacion internacional de campos de educación | `snies_programas`, `catalogo_nbc_snies` |
| NBC (MEN Colombia) | Nucleos Basicos de Conocimiento — 55 NBCs | `snies_programas`, `snies_matriculados`, `mapeo_nbc_cuoc` |
| CUOC 2025 (DANE) | Clasificacion Unica de Ocupaciones — 14,462 codigos | `cuoc_limpio_2025`, `competencias` |
| CIIU Rev.4 (DANE) | Clasificacion Industrial Internacional Uniforme — 700 codigos | `ciiu_rev4`, `mapeo_cuoc_ciiu` |
| MNC (MEN) | Marco Nacional de Cualificaciones — 396 cualificaciones | `cualificaciones_men` |
| DIVIPOLA (DANE) | Division Politico-Administrativa — 33 dptos, 1,122 mpios | `divipola_departamentos`, `divipola_municipios` |

3. **Depuracion de duplicados, control de campos nulos y validación de consistencia entre tablas**

4. **Carga en estructuras DuckDB** para consultas SQL, visualización y recuperación aumentada

5. **Registro de trazabilidad:** Cada tabla del repositorio puede rastrearse hasta su fuente original, fecha de corte y transformaciones aplicadas. Scripts de auditoria en `admin/auditar_*.py` verifican la consistencia entre catalogos y fuentes.

### Transformaciones Especificas

- **Normalizacion de `COD_SNIES_PROGRAMA`:** En `snies_matriculados`, el código puede tener sufijo `.0` (float-as-string). El puente programas↔matriculados en `data/filters.py` lo normaliza con `REGEXP_REPLACE(CAST(... AS VARCHAR), '\\.0$', '')`.
- **Case sensitivity en NBCs:** `NUCLEO_BASICO_DEL_CONOCIMIENTO` (programas) usa formato diferente a `NBC` (matriculados). El sistema aplica `UPPER()` para garantizar coincidencia.
- **Cascada CINE-F → Area → NBC:** `data/filters.py:build_nbc_condition()` y `resolver_nbcs_desde_filtros()` implementan la jerarquia de filtros.

---

## Fase 4: Modelado

### 4.1 Indicadores Cuantitativos Derivados

| Indicador | Formula | Implementacion | Interpretacion |
|:----------|:--------|:---------------|:---------------|
| HHI (Herfindahl-Hirschman) | `HHI = sum(s_i^2)` donde s_i es la cuota de mercado de la IES i | `services/scoring.py:calcular_hhi()` | Concentracion del mercado educativo. <1500: competitivo, 1500-2500: moderado, >2500: concentrado |
| CAGR (Compound Annual Growth Rate) | `CAGR = (V_f / V_i)^(1/n) - 1` | `services/scoring.py:calcular_cagr()` | Tasa de crecimiento anual compuesto de matrícula |
| Ratio de Absorcion Laboral | `graduados_anual / vacantes_est * 100` | `services/scoring.py:calcular_ratio_absorcion()` | Capacidad del mercado laboral para absorber graduados |
| Score de Pertinencia Final | `0.30*S_acad + 0.40*S_lab + 0.20*S_terr + 0.10*S_glob` | `services/scoring.py:calcular_score_final()` | Puntaje ponderado que alimenta el motor de decisión |

### 4.2 Busqueda Semantica con Embeddings Multilingues

**Modelo:** `sentence-transformers` con arquitectura MiniLM de 384 dimensiones, seleccionado por su equilibrio entre precision, tamaño compacto y desempeño en español.

**Corpus indexado:**
- Ocupaciones CUOC: 680 perfiles (`perfilesocupacionales_excel_cuoc_2025`)
- Conocimientos por ocupacion: 3,599 registros (`cuoc_conocimientos`)
- Destrezas por ocupacion: 4,422 registros (`cuoc_destrezas`)
- Programas SIET: 25,010 registros (`siet_programas`)
- NBCs: 55 nucleos con área y campo CINE (`catalogo_nbc_snies`)

**Sistema de cache:** Los embeddings se precalculan y almacenan en dos niveles:
1. Memoria (dict en Python)
2. Disco (`services/cache_data/ml_embeddings/` — 180+ archivos `.pkl`)

**Umbrales adaptativos:** El sistema intenta primero un emparejamiento exigente (similitud alta) y, si los resultados son escasos, relaja el umbral para no descartar correspondencias validas en NBCs con pocas ocupaciones asociadas.

**Fallback:** Si `sentence-transformers` no esta disponible, el sistema recurre a busqueda por palabras clave (`data/search.py`).

**Puentes habilitados:**
- SNIES (programas académicos) ↔ CUOC (ocupaciones) — `services/ml/matching.py`
- SNIES (programas académicos) ↔ SIET (formación para el trabajo) — `services/ml/snies_etdh.py`
- CUOC (ocupaciones) ↔ ESCO (taxonomia europea de habilidades) — `services/ml/matching.py`

### 4.3 Recuperacion Aumentada (RAG)

**Clase:** `EducacionRAG` (`services/rag/retrieval.py`)

**Funcionamiento:**
1. Recibe el NBC, departamento y contexto base del análisis
2. Consulta DuckDB para recuperar datos de deserción (SPADIES), resultados Saber PRO, transito inmediato, y cobertura bruta
3. Enriquece el contexto antes de enviarlo al LLM

**Integracion:** `app.py:84-90` — `rag_system.augment_context(nbc_codigo, departamento, contexto, filtros_activos)`

### 4.4 Generacion Asistida por LLM

**Modelo:** Google Gemini 2.0 Flash (con fallback a 2.5 Flash, flash-latest, flash-lite)

**Prompt del sistema (480 lineas, `app.py:194-480`):**
- Perfil de investigador senior con 25 anos de experiencia en politicas educativas
- 7 secciones obligatorias: Resumen Ejecutivo, Analisis del Mercado Educativo, Pertinencia Laboral, Diseno Curricular, Microcredenciales, Riesgos, Recomendacion Final
- Catalogo de 15 fuentes oficiales con formato de citación `(FUENTE - Periodo)`
- Notacion LaTeX para formulas, metricas y expresiones matematicas
- Tablas profesionales con alineacion, sin emojis

### 4.5 Motor de Decision

**Ubicacion:** `services/decision_engine.py`

**Funcionamiento:**
1. Recibe los scores de las 4 sintesis evaluativas
2. Aplica ponderacion: 30% académica + 40% laboral + 20% territorial + 10% global
3. Determina el tipo de oferta educativa recomendada segun la combinacion de resultados

**Seis tipos de oferta educativa:**
1. Programa formal completo
2. Microcredenciales
3. Formacion continua (ciclo corto)
4. Ruta formativa flexible (virtual/hibrida)
5. Programa con condiciones
6. No ofertar

**Logica del score laboral (el de mayor peso — 40%):** No se reduce a una comparacion simple graduados vs vacantes. Integra cuatro componentes:
- Volumen absoluto de vacantes (señal de mercado activo)
- Ratio de absorcion ajustado (corrige subreporte APE)
- Senal salarial (valoracion del mercado por la formación)
- Densidad de competencias asociadas (perfil ocupacional definido)
- Factor de ajuste por alineacion SNIES-SIET (complementariedad en lugar de competencia)

---

## Fase 5: Evaluacion

### Suite de Pruebas Automatizadas

| Metrica | Valor |
|:--------|:------|
| Archivo | `tests/test_queries.py` |
| Lineas | 666 |
| Total de pruebas | 50 |
| Ejecucion | `python -m tests.test_queries` |
| Resultado | Exit 0 = todo OK, Exit 1 = fallos |
| Tipo | Integracion contra DuckDB real, sin mocks |

### Categorias de Validacion

| Categoria | Pruebas | Descripcion |
|:----------|:--------|:------------|
| Construccion de filtros | 8 | `build_where_clause`, `build_where_clause_matriculados`, `build_nbc_condition` con distintas combinaciones de parametros |
| Consultas directas (programas) | 4 | `get_estadisticas_basicas`, `get_benchmarking_data`, `get_programas_detalle`, `get_desglose_academico` |
| Puente programas↔matriculados | 9 | `get_market_share`, `get_tendencia_matricula`, `get_graduados_historico`, `get_tendencia_inscritos`, `get_tendencia_admitidos`, `get_tendencia_primer_curso` |
| Explorador interactivo | 6 | `get_datos_explorador_interactivo` con combinaciones de dimensiones y filtros |
| Comparativas | 2 | `get_comparativa_snies_siet_por_depto`, `get_comparativa_tipo_formacion` |
| SIET | 3 | `get_estadisticas_siet`, `get_desglose_siet`, `get_programas_detalle_siet` |
| Laboral (ML matching) | 6 | `get_vacantes_reales`, `get_competencias_cuoc`, `get_salarios_reales`, `get_graduados_nacionales`, `get_tendencia_laboral_nbc`, `get_graduados_nbc_historico` |
| Territorial | 2 | `get_conectividad_territorial`, `get_municipios_pdet` |
| Consistencia interna | 4 | Case sensitivity NBCs, bridge match rate, consistencia programas↔matriculados |
| Rendimiento | 3 | Benchmarks de tiempo para funciones criticas (< 500ms) |

---

## Fase 6: Despliegue

### Contenerizacion

| Aspecto | Valor |
|:--------|:------|
| Imagen base | `python:3.13-slim` |
| Puerto | 7860 |
| Archivo | `Dockerfile` (30 lineas) |
| Estrategia BD | Clona repo desde GitHub LFS para obtener `data/repositorio.duckdb` (703 MB) |

### Plataforma

| Aspecto | Valor |
|:--------|:------|
| Hosting | HuggingFace Spaces |
| URL | `https://jeffersonca-estudio-contexto.hf.space/` |
| Autenticacion | SHA-256 via `st.secrets` |
| Git LFS | Activo para `*.duckdb`, `*.pkl`, `*.npy`, `*.parquet`, `*.safetensors` |

---

*Documento generado a partir de la metodología CRISP-ML documentada en `README.md:167`, `AGENTS.md`, el documento técnico ejecutivo (`Documento_solucion_Sistema_Analisis_Contexto_Pertinencia_Educativa_V3.docx` secciones 6-9), `services/scoring.py`, `services/decision_engine.py`, `services/rag/retrieval.py`, `services/ml/matching.py`, `services/ml/snies_etdh.py`, `tests/test_queries.py` (666 lineas, 50 pruebas), `Dockerfile` (30 lineas), y `data/filters.py`.*
