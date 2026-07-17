# Documentación Técnica — Sistema de Análisis de Contexto

Equipo 195 | Concurso Datos al Ecosistema 2026: IA para Colombia | Nivel Intermedio

---

## Indice de Documentos

| Documento | Archivo | Contenido |
|:----------|:--------|:----------|
| Arquitectura del Sistema | `01_arquitectura.md` | Diagrama de 4 capas, stack tecnologico, flujo de datos, componentes de IA (embeddings, RAG, LLM), sistema de filtros en cascada, infraestructura de despliegue, API, estructura de directorios |
| Diccionario de Datos | `02_diccionario_datos.md` | 114 variables organizadas en 5 ejes y 8 dominios, mapeo exacto a esquema.tabla.columna en DuckDB, clasificadores transversales (CINE-F, NBC, CUOC, CIIU, MNC, DIVIPOLA), motor de decision, convenciones de la base de datos |
| Planteamiento del Problema | `03_planteamiento_problema.md` | Desercion universitaria como problema estructural, vinculo analitico estudios de contexto-permanencia-desercion, objetivo general y 4 objetivos especificos, poblacion objetivo, alcance y limitaciones |
| Marco Metodologico | `04_marco_metodologico.md` | CRISP-ML aplicado fase por fase: comprension del problema, comprension de datos (54 esquemas), preparacion ETL (homologacion CINE-F/NBC/CUOC/CIIU/MNC/DIVIPOLA), modelado (HHI, CAGR, embeddings, RAG, LLM, motor de decision), evaluacion (50 tests), despliegue (Docker + HF Spaces) |
| Fuentes de Datos | `05_fuentes_datos.md` | Trazabilidad completa de todas las fuentes: Grupo A (datos.gov.co, ~188 tablas), Grupo B (descarga directa SNIES/SIET/ICFES, 18 tablas), Grupo C (internacionales Banco Mundial/OECD/UNESCO/ILO/ESCO, 60 tablas), Grupo D (catalogos curados, ~200 tablas). Mapa de trazabilidad por esquema DuckDB (54 esquemas). Evidencia de origen documentada |
| Conclusiones | `06_conclusiones.md` | Hallazgos del piloto (integracion de fuentes, indicadores, matching semantico, generacion de informes, impacto esperado), 6 limitaciones identificadas, ruta de evolucion a corto/mediano/largo plazo, lectura responsable del alcance |
| Guia de Validacion | `07_guia_validacion.md` | Requisitos de entorno, ejecucion de los 50 tests automatizados (`python -m tests.test_queries`), flujo de validacion completo del dashboard, reproducibilidad de resultados, validacion cruzada de fuentes, reporte de issues |
| Validacion de Componentes IA | `08_validacion_componentes_ia.md` | Metricas reales de los 3 componentes de IA: threshold adaptativo del matching semantico, validacion del puente SNIES-SIET (4 checks automaticos), integridad del pipeline (50 tests), coherencia del scoring, y por que no se reportan metricas de clasificacion tradicionales |

---

## Referencia Rapida

| Que busca | Donde esta |
|:----------|:-----------|
| De donde vienen los datos | `05_fuentes_datos.md` |
| Que significa cada variable | `02_diccionario_datos.md` |
| Como funciona el sistema por dentro | `01_arquitectura.md` |
| Que metodologia se uso | `04_marco_metodologico.md` |
| Cual es el problema que resuelve | `03_planteamiento_problema.md` |
| Que se encontro y que sigue | `06_conclusiones.md` |
| Como verifico que funciona | `07_guia_validacion.md` |
| Como se valido la IA | `08_validacion_componentes_ia.md` |

---

## Archivos de Soporte

Estos archivos en el repositorio complementan la documentacion:

| Archivo | Funcion | Lineas |
|:--------|:--------|:-------|
| `services/sources.py` | Diccionario centralizado de fuentes con URLs, periodos y citaciones | 376 |
| `catalogo/MAPEO_DSS_OFICIAL.csv` | Mapeo de 114 variables a esquemas, tablas y columnas DuckDB | 115 |
| `tests/test_queries.py` | 50 tests de integracion automatizados | 666 |
| `AGENTS.md` | Guia para agentes de desarrollo con convenciones del proyecto | 56 |
| `data/queries.py` | 56 consultas SQL parametrizadas | 3,138 |
| `app.py` | Dashboard principal Streamlit | 387 |
| `Dockerfile` | Contenedor de despliegue | 30 |
| `.gitignore` / `.gitattributes` | Git LFS y exclusiones | 48 / 36 |

---

## Datos del Proyecto

| Campo | Valor |
|:------|:------|
| Equipo | Grupo 195 |
| Concurso | Datos al Ecosistema 2026: IA para Colombia |
| Nivel | Intermedio |
| Reto | Educacion |
| Categoria | Innovacion social |
| Demo | `https://jeffersonca-estudio-contexto.hf.space/` |
| Repositorio | `https://github.com/Jefferson-GHB/Estudio_Contexto_v3` |
| Licencia | MIT |

---

*Documentacion generada a partir de evidencia extraida del codigo fuente, la base de datos DuckDB y el documento tecnico ejecutivo. Julio 2026.*
