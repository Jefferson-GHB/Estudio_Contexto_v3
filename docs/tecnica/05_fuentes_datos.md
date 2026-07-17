# Fuentes de Datos

Documento de trazabilidad de todas las fuentes de datos integradas en el repositorio analitico. Cada fuente se documenta con su entidad de origen, URL de descarga, período de los datos, esquema y tablas asociadas en DuckDB, y evidencia de su procedencia.

---

## 1. Clasificacion General

El repositorio DuckDB (`data/repositorio.duckdb`, 703 MB, lectura exclusiva) integra datos de 54 esquemas tematicos organizados en cuatro grupos segun su origen:

| Grupo | Origen | Esquemas | Tablas aprox. | Evidencia de trazabilidad |
|:------|:-------|:---------|:--------------|:--------------------------|
| A | Portal datos.gov.co (Socrata API) | `datos_gov_co`, `dane_socrata`, `conectividad`, `men_estadisticas`, `estadisticas_es`, `empleo_publico`, `dane`, `dane_estadisticas`, `dane_indicadores`, `competencias`, `sena`, `sena_formacion`, `mintic`, `dnp`, `dnp_planes_desarrollo`, `cultura`, `mipymes_estructura_empresarial`, `rues_camaras_comercio`, `datos_complementarios` | ~188 | URLs documentadas en `services/sources.py`, schemas con nombre explicito `datos_gov_co` y `dane_socrata` |
| B | Descarga directa portales MEN/ICFES | `snies`, `siet`, `icfes_saber`, `men` | 18 | Columna `archivo_fuente` en tablas SNIES con nombres de archivo XLSX, URLs documentadas en `services/sources.py` |
| C | Fuentes internacionales | `banco_mundial`, `banco_mundial_internacional`, `indicadores_globales`, `ilo_internacional`, `oecd_internacional`, `unesco_internacional`, `esco` | 60 | URLs propias de cada organismo internacional en `services/sources.py` |
| D | Catalogos curados (elaboración propia) | `catalogo_curado`, `clasificadores`, `cuoc`, `educación`, `microcredenciales`, `tendencias_tecnologicas`, `tendencias_laborales`, `vss`, `ref`, `inventarios`, `_diccionarios`, `divipola`, `territorial`, `inteligente`, `programas_ies`, `entidades`, `empresas`, `empleadores`, `mercado_laboral`, `servicio_publico_empleo`, `laboral`, `ole`, `poblacion` | ~200 | Construidos a partir de fuentes oficiales. Mapeos NBC-CUOC, CINE-F, CIIU, MNC, DIVIPOLA verificados contra fuentes originales |

---

## 2. Grupo A — Portal datos.gov.co

Los siguientes datasets fueron obtenidos del portal oficial de datos abiertos del Estado colombiano (`https://www.datos.gov.co`), que opera sobre la plataforma Socrata. La evidencia de descarga desde este portal se respalda en:

- Schema `datos_gov_co`: nombre explicito del schema en la base de datos
- Schema `dane_socrata`: "Socrata" es el nombre de la plataforma que sirve datos.gov.co
- `services/sources.py:165,173`: URL `https://www.datos.gov.co/` documentada para conectividad

### 2.1 Conectividad

| Campo | Valor |
|:------|:------|
| Dataset | Accesos Internet Fijo |
| Entidad | MinTIC - CRC |
| URL origen | `https://www.datos.gov.co/` |
| Portal datos.gov.co | Confirmado (`services/sources.py:165`) |
| Periodo | 2016-2023 |
| Schema DuckDB | `conectividad` |
| Tabla principal | `internet_fijo_accesos` |
| Registros | 1,678,363 |
| Variables clave | `departamento`, `municipio`, `proveedor`, `tecnologia`, `velocidad_bajada`, `no_de_accesos` |

| Campo | Valor |
|:------|:------|
| Dataset | Cobertura Movil por Tecnologia |
| Entidad | MinTIC - ANE |
| URL origen | `https://www.datos.gov.co/` |
| Portal datos.gov.co | Confirmado (`services/sources.py:173`) |
| Periodo | 2015-2023 |
| Schema DuckDB | `conectividad` |
| Tabla principal | `cobertura_movil_tecnologia` |
| Registros | 177,152 |
| Variables clave | `departamento`, `municipio`, `tecnologia`, `proveedor`, `cobertura_4g` |

### 2.2 Schema `datos_gov_co` (7 tablas)

El nombre del schema constituye evidencia directa de origen. Las tablas contenidas corresponden a datasets identificables en el portal datos.gov.co:

| Tabla | Entidad | Registros | Descripcion |
|:------|:--------|:----------|:------------|
| `funcion_publica_empleos_entidad` | Funcion Publica | 295 | Empleos y tipos de planta por entidad del Estado |
| `men_programas_etdh` | MEN | 19,867 | Programas de Educacion para el Trabajo y Desarrollo Humano |
| `sena_certificacion_fpi` | SENA | 8,538 | Certificacion de Formacion Profesional Integral |
| `sena_cupos_fpi_poblacion` | SENA | 42,080 | Cupos en formación profesional integral por tipo de poblacion |
| `sena_desercion_fpi` | SENA | 42,080 | Desercion de la formación profesional integral |
| `sena_inscritos_ape_nacional` | SENA | 566 | Total nacional de inscritos en la Agencia Publica de Empleo |
| `sena_mesas_sectoriales` | SENA | 84 | Mesas sectoriales del SENA |

### 2.3 Schema `dane_socrata` (10 tablas)

El nombre del schema referencia explicitamente la plataforma Socrata, que opera `datos.gov.co`. Las tablas corresponden a datasets del DANE y otras entidades publicados en el portal:

| Tabla | Entidad | Registros |
|:------|:--------|:----------|
| `divipola_codigos_departamentos` | DANE | 33 |
| `evaluaciones_agricolas_del_departamento_de_caldas` | DANE | 3,287 |
| `men_estadisticas_en_educacion_en_preescolar_basica_media` | MEN | 462 |
| `proyeccion_de_poblacion_municipal_de_chiquinquira` | DANE | 54 |
| `registro_nacional_de_turismo_departamento_del_choco` | MinComercio | 3,083 |
| `resguardos_indigenas_a_nivel_nacional_2020` | DANE | 966 |
| `salud_tasa_de_mortalidad_por_desnutricion_en_menores` | MinSalud | 49 |
| `seccion_de_usos_del_portal_de_datos_abiertos_del_estado` | MinTIC | 289 |
| `vista_registro_nacional_de_turismo_meta` | MinComercio | 14,375 |
| `vista_registro_nacional_de_turismo_boyaca` | MinComercio | 20,547 |

### 2.4 Schema `men_estadisticas` (3 tablas)

Datasets del Ministerio de Educacion Nacional disponibles en el portal de datos abiertos:

| Tabla | Registros | Descripcion |
|:------|:----------|:------------|
| `men_matricula_departamentos_es` | 567 | Matricula en educación superior por departamento |
| `men_matricula_estadistica_es` | 206,919 | Estadistica detallada de matrícula en educación superior |
| `men_matricula_municipios_es` | 10,429 | Matricula en educación superior por municipio |

### 2.5 Schema `estadisticas_es` (21 tablas)

Estadisticas de Educacion Superior consolidadas por el MEN. Incluyen indicadores de cobertura, deserción, matrícula, graduados, docentes, transito inmediato y cobertura bruta por departamento y municipio. Tablas principales:

| Tabla | Descripcion |
|:------|:------------|
| `es_desercion_nivel` | Tasa de deserción por nivel de formación |
| `es_cobertura_bruta` | Tasa de cobertura bruta en educación superior |
| `es_matricula_departamento` | Matricula por departamento |
| `es_matricula_modalidad` | Matricula por modalidad (presencial/virtual/distancia) |
| `es_matricula_nivel` | Matricula por nivel de formación |
| `es_matricula_sector` | Matricula por sector (oficial/privado) |
| `es_graduados_nivel` | Graduados por nivel de formación |
| `es_tti_departamento` | Tasa de transito inmediato por departamento |
| `es_tcb_departamento` | Tasa de cobertura bruta por departamento |
| `es_ies_acreditadas` | IES con acreditacion de alta calidad |

### 2.6 Schemas adicionales del Grupo A

| Schema | Tablas | Entidades | Descripcion |
|:-------|:-------|:----------|:------------|
| `empleo_publico` | 30 | Funcion Publica, SENA, DAFP, MinTrabajo | Caracterizacion del empleo publico, SIGEP, ley de cuotas, pensionados, personas expuestas politicamente, PQRSD |
| `dane` + `dane_estadisticas` + `dane_indicadores` | 23 | DANE | Proyecciones de poblacion, ODS, ley de cuotas, directorio establecimientos educativos, resguardos indigenas |
| `competencias` + `sena` + `sena_formacion` | 18 | SENA | CUOC conocimientos y destrezas, certificacion FPI, deserción FPI, cursos, mesas sectoriales, georeferenciacion centros |
| `mintic` | 6 | MinTIC | Gobierno digital, centros digitales, asesorias teletrabajo, certificaciones TI |
| `dnp` + `dnp_planes_desarrollo` | 8 | DNP | Medicion desempeno municipal, planes de desarrollo, red vial, indicadores PDT |
| `cultura` | 6 | MinCultura | Espacios culturales, sitios arqueologicos, estimulos artisticos, memorias de oficio |
| `mipymes_estructura_empresarial` | 5 | MinComercio | Estructura empresarial por CIIU, tamaño, municipio, naturaleza |
| `rues_camaras_comercio` | 13 | Confecamaras | RUES, empresas activas, empresas creadas, top 10,000 empresas |
| `datos_complementarios` | 37 | SENA, OLE, DANE, SIGEP | Salarios, vacantes, graduados, ruta empleabilidad, tendencias laborales |

---

## 3. Grupo B — Descarga Directa de Portales Oficiales

Estos datos fueron obtenidos directamente de los portales de cada entidad, no a traves del portal datos.gov.co. Se documenta la URL del portal y el formato de descarga.

### 3.1 SNIES — Sistema Nacional de Informacion de la Educacion Superior

| Campo | Valor |
|:------|:------|
| Entidad | Ministerio de Educacion Nacional |
| URL | `https://snies.mineducacion.gov.co/` |
| Portal datos.gov.co | No. Descarga directa XLSX desde portal SNIES |
| Periodo | 2014-2024 |
| Evidencia | Columna `archivo_fuente` en cada tabla SNIES registra el nombre del archivo XLSX descargado (ej. `ESTUDIANTES_MATRICULADOS_2024.XLSX`) |
| Schema DuckDB | `snies` |
| Citacion | `services/sources.py:18-73` |

Tablas en DuckDB:

| Tabla | Registros | Periodo | Columnas | Archivos fuente (evidencia) |
|:------|:----------|:--------|:---------|:----------------------------|
| `snies_programas` | 30,660 | 2024 | 39 | N/A (consolidado) |
| `snies_instituciones` | 389 | 2024 | 25 | N/A |
| `snies_matriculados` | 427,727 | 2019-2024 | 37 | `ESTUDIANTES_MATRICULADOS_2019.XLSX` ... `ESTUDIANTES_MATRICULADOS_2024.XLSX` |
| `snies_matriculados_primer_curso` | 286,148 | 2019-2024 | 37 | `ESTUDIANTES_MATRICULADOS_EN_PRIMER_CURSO_2019.XLSX` ... `_2024.XLSX` |
| `snies_graduados` | 267,069 | 2014-2024 | 37 | `ESTUDIANTES_GRADUADOS_2019.XLSX` ... `ESTUDIANTES_GRADUADOS_2024.XLSX` |
| `snies_inscritos` | 324,783 | 2019-2024 | 37 | `ESTUDIANTES_INSCRITOS_2019.XLSX` ... `ESTUDIANTES_INSCRITOS_2024.XLSX` |
| `snies_admitidos` | 306,178 | 2019-2024 | 37 | `ESTUDIANTES_ADMITIDOS_2019.XLSX` ... `ESTUDIANTES_ADMITIDOS_2024.XLSX` |
| `snies_docentes` | 97,957 | 2014-2024 | 26 | `DOCENTES_2014.XLSX` ... `DOCENTES_2024.XLSX` |
| `snies_administrativos` | 24,214 | 2014-2024 | 12 | `ADMINISTRATIVOS_2014.XLSX` ... `ADMINISTRATIVOS_2024.XLSX` |

### 3.2 SIET — Sistema de Informacion de Educacion para el Trabajo

| Campo | Valor |
|:------|:------|
| Entidad | Ministerio de Educacion Nacional |
| URL | `https://siet.mineducacion.gov.co/` |
| Portal datos.gov.co | No. Descarga directa desde portal SIET |
| Periodo | 2024 |
| Schema DuckDB | `siet` |
| Citacion | `services/sources.py:74-89` |

| Tabla | Registros | Columnas |
|:------|:----------|:---------|
| `siet_programas` | 25,010 | 35 |
| `siet_instituciones` | 4,385 | 27 |
| `siet_matricula_programa` | 41,424 | 29 |
| `siet_estudiantes_certificados_progr` | 41,424 | 29 |

### 3.3 ICFES — Pruebas Saber

| Campo | Valor |
|:------|:------|
| Entidad | ICFES |
| URL | `https://www.icfes.gov.co/` |
| Portal datos.gov.co | No. Datos obtenidos directamente del ICFES |
| Schema DuckDB | `icfes_saber`, `men` |
| Citacion | `services/sources.py` — Sistema de citación |

| Tabla | Registros | Descripcion |
|:------|:----------|:------------|
| `icfes_saber_pro_resultados` | 999,891 | Resultados Saber PRO (57 columnas, competencias genericas y especificas) |
| `icfes_saber_tyt_resultados` | 920,983 | Resultados Saber TYT |
| `men.resultados_saber_pro_competencias_especificas_2019` | 401,815 | Competencias especificas Saber PRO |
| `men.resultados_saber_pro_competencias_genericas_2019_2` | 260,756 | Competencias genericas Saber PRO (105 columnas) |
| `men.saber_11_2020_2` | 504,872 | Resultados Saber 11 (81 columnas) |

---

## 4. Grupo C — Fuentes Internacionales

Datos de organismos multilaterales utilizados para comparativas globales y contextualizacion de tendencias.

| Schema | Tablas | Fuente | URL | Periodo |
|:-------|:-------|:------|:----|:--------|
| `banco_mundial` | 22 | Banco Mundial | `https://datos.bancomundial.org/` | 2023 |
| `banco_mundial_internacional` | 7 | Banco Mundial (API) | `https://datos.bancomundial.org/` | Multi-anual |
| `indicadores_globales` | 22 | Banco Mundial (duplicado funcional) | `https://datos.bancomundial.org/` | 2023 |
| `ilo_internacional` | 2 | OIT (ILO) | `https://ilostat.ilo.org/` | 2015-2023 |
| `oecd_internacional` | 2 | OECD | `https://www.oecd.org/` | 2022-2023 |
| `unesco_internacional` | 3 | UNESCO | `https://uis.unesco.org/` | Multi-anual |
| `esco` | 2 | Comision Europea | `https://esco.ec.europa.eu/` | v1.2.0 |

Principales indicadores utilizados:

| Indicador | Tabla DuckDB | Cobertura |
|:----------|:-------------|:----------|
| PIB per capita | `bm_pib_per_capita` | 35 paises |
| Tasa de desempleo | `bm_tasa_desempleo` | 34 paises |
| Gasto en educación (%PIB) | `bm_gasto_educacion_pib` | 23 paises |
| Tasa matrícula terciaria | `bm_tasa_matricula_terciaria` | 22 paises |
| Usuarios de internet (%) | `bm_usuarios_internet_pct` | 31 paises |
| Desempleo juvenil | `bm_desempleo_jovenes` + `ilo_internacional.empleo_global` | 34 paises |
| PISA scores | `oecd_internacional.pisa_scores` | 39 paises |
| Habilidades ESCO | `esco.skills_global` + `esco.skills_por_sector` | 13,939 + 13,492 registros |

---

## 5. Grupo D — Catalogos Curados (Elaboracion Propia)

Conjuntos de datos construidos por el equipo a partir de fuentes oficiales para habilitar los cruces analiticos entre dominios (educación, trabajo, territorio).

### 5.1 Clasificadores Oficiales

| Schema | Tabla | Registros | Descripcion |
|:-------|:------|:----------|:------------|
| `clasificadores` | `cuoc` | 14,462 | Clasificacion Unica de Ocupaciones CUOC 2025 |
| `clasificadores` | `cine_f` | 10,431 | Clasificacion CINE-F UNESCO 2013 adaptada a Colombia |
| `clasificadores` | `ciiu_rev4` | 700 | Clasificacion Industrial Internacional Uniforme Rev.4 |
| `cuoc` | `cuoc_limpio_2025` | 14,462 | CUOC 2025 limpio y estructurado |
| `cuoc` | `perfilesocupacionales_excel_cuoc_2025` | 681 | Perfiles ocupacionales detallados |
| `divipola` | `divipola_departamentos` | 33 | Codigos DANE de departamentos |
| `divipola` | `divipola_municipios` | 1,122 | Codigos DANE de municipios |
| `educación` | `nbc_nucleos_basicos_conocimiento` | 54 | 55 NBCs con área de conocimiento y campo CINE asociado |
| `educación` | `areas_conocimiento_men` | 8 | 8 áreas de conocimiento definidas por el MEN |
| `educación` | `niveles_formacion_men` | 7 | Niveles de formación (Tecnico a Doctorado) |
| `educación` | `modalidades_formacion` | 4 | Presencial, Distancia, Virtual, Dual |
| `educación` | `sectores_ies` | 2 | Oficial, Privado |
| `educación` | `caracteres_ies` | 4 | Universidad, Inst. Universitaria, Tecnologica, Tecnica |

### 5.2 Catalogos de Mapeo y Articulacion

| Schema | Tabla | Registros | Funcion de cruce |
|:-------|:------|:----------|:-----------------|
| `catalogo_curado` | `mapeo_nbc_cuoc` | 56 | NBC (SNIES) ↔ Areas de Cualificacion CUOC |
| `catalogo_curado` | `mapeo_cuoc_ciiu` | 41 | Ocupaciones CUOC ↔ Sectores economicos CIIU |
| `catalogo_curado` | `mapeo_cinef_snies_codigo` | 106 | Codigos CINE-F ↔ Codigos SNIES |
| `catalogo_curado` | `mapeo_cinef_detallado_siet` | 106 | CINE-F detallado ↔ Areas de desempeno SIET |
| `catalogo_curado` | `mapeo_cuoc_area_cualificacion` | 680 | CUOC ↔ Areas de cualificacion |
| `catalogo_curado` | `mapeo_cuoc_cinef_amplio` | 26 | CUOC ↔ Campos amplios CINE-F |
| `catalogo_curado` | `mapeo_observatorio_cuoc` | 1,881 | Observatorio laboral ↔ CUOC |
| `catalogo_curado` | `cualificaciones_men` | 396 | Catalogo de Cualificaciones del MEN (MNC) |
| `catalogo_curado` | `mapeo_variables` | 114 | Mapeo de variables del modelo analitico (114 variables en 4 ejes y 9 dominios) |

### 5.3 Tendencias Laborales — Agencia Publica de Empleo

| Schema | Descripcion | Tablas | Periodo |
|:-------|:------------|:-------|:--------|
| `tendencias_laborales` | Series historicas de vacantes, colocados e inscritos APE por ocupacion, departamento y período | 142 | 2017-2025 |
| `tendencias_laborales` | `vacantes_ape_clean` | 599 registros | Consolidado limpio para matching |

Fuente original: Agencia Publica de Empleo del SENA (`https://observatorio.sena.edu.co/`). Los datos de la APE tambien estan disponibles en datos.gov.co, pero la descarga masiva de series trimestrales se realizo desde el observatorio del SENA.

---

## 6. Mapa de Trazabilidad por Esquema DuckDB

Cada esquema del repositorio se mapea a su fuente y grupo de trazabilidad:

```
_sdiccionarios          → D (Catalogos curados)
banco_mundial            → C (Banco Mundial)
banco_mundial_internacional → C (Banco Mundial API)
catalogo_curado          → D (Catalogos curados — elaboración propia)
clasificadores           → D (Clasificadores oficiales — procesados)
competencias             → A (SENA — datos.gov.co)
conectividad             → A (MinTIC — datos.gov.co, URL confirmada)
cultura                  → A (datos.gov.co)
cuoc                     → D (CUOC 2025 — procesado)
dane                     → A (DANE — datos.gov.co)
dane_estadisticas        → A (DANE — datos.gov.co)
dane_indicadores         → A (DANE — datos.gov.co)
dane_socrata             → A (DANE via Socrata — datos.gov.co)
datos_complementarios    → A (datos.gov.co)
datos_gov_co             → A (datos.gov.co — schema explicito)
divipola                 → D (DIVIPOLA — procesado)
dnp                      → A (DNP — datos.gov.co)
dnp_planes_desarrollo    → A (DNP — datos.gov.co)
educación                → D (Catalogos educativos — procesados)
empleadores              → A (datos.gov.co)
empleo_publico           → A (Funcion Publica — datos.gov.co)
empresas                 → A (datos.gov.co)
entidades                → A (datos.gov.co)
esco                     → C (Comision Europea)
estadisticas_es          → A (MEN Estadisticas ES — datos.gov.co)
icfes_saber              → B (ICFES — descarga directa)
ilo_internacional        → C (OIT/ILO)
indicadores_globales     → C (Banco Mundial — duplicado funcional)
inteligente              → D (Catalogos internos)
inventarios              → D (Metadata interna)
laboral                  → A (datos.gov.co)
men                      → B (MEN/ICFES — descarga directa)
men_estadisticas         → A (MEN — datos.gov.co)
mercado_laboral          → A (datos.gov.co)
microcredenciales        → D (Investigacion propia — curado)
mintic                   → A (MinTIC — datos.gov.co)
mipymes_estructura_empresarial → A (datos.gov.co)
oecd_internacional       → C (OECD)
ole                      → A (Observatorio Laboral para la Educacion — datos.gov.co)
poblacion                → A (datos.gov.co)
programas_ies            → A (datos.gov.co)
ref                      → D (Referencias y mapeos)
rues_camaras_comercio    → A (Confecamaras — datos.gov.co)
sena                     → A (SENA — datos.gov.co)
sena_formacion           → A (SENA — datos.gov.co)
servicio_publico_empleo  → A (datos.gov.co)
siet                     → B (SIET — descarga directa MEN)
snies                    → B (SNIES — descarga directa MEN)
tendencias_laborales     → A (APE/SENA — datos.gov.co)
tendencias_tecnologicas  → D (Investigacion propia — WEF, HolonIQ, LinkedIn)
territorial              → D (Catalogos territoriales — procesados)
unesco_internacional     → C (UNESCO)
vss                      → D (Vector Storage — embeddings internos)
```

---

## 7. Archivos de Soporte

| Archivo | Funcion | Lineas |
|:--------|:--------|:-------|
| `services/sources.py` | Diccionario centralizado de fuentes con URLs, períodos y citaciones | 376 |
| `catalogo/MAPEO_DSS_OFICIAL.csv` | Mapeo de 114 variables a esquemas, tablas y columnas DuckDB | 115 |
| `data/queries.py` | 56 funciones de consulta SQL parametrizadas con filtros | 3,138 |
| `admin/ingestar_*.py` | Scripts de ingestion, limpieza y homologacion de fuentes | ~20 archivos |
| `admin/auditar_*.py` | Scripts de auditoria de consistencia entre catalogos y fuentes | ~5 archivos |
| `pipelines/pipeline_etl.py` | Orquestador que ejecuta todos los ingestar en orden | 1 archivo |

---

**Nota metodologica:** La clasificación de fuentes en los Grupos A, B, C y D se fundamenta en evidencia documental y de código, no en supuestos. Los datos del Grupo A tienen al menos uno de los siguientes respaldos: (a) nombre de schema que referencia explicitamente el portal o la plataforma Socrata, (b) URL documentada en `services/sources.py` con dominio `datos.gov.co`, o (c) nombre de tabla que coincide con datasets publicados en el portal. Los datos del Grupo B tienen columna `archivo_fuente` con los nombres de los archivos XLSX descargados desde los portales originales. Los datos del Grupo C tienen URLs propias de cada organismo internacional. Los datos del Grupo D son productos derivados del procesamiento y curacion del equipo.

*Documento generado a partir de evidencia extraida del repositorio DuckDB (703 MB, 54 esquemas, 488 tablas), `services/sources.py` (376 lineas), `catalogo/MAPEO_DSS_OFICIAL.csv` (114 variables), y los scripts de ingestion en `admin/`.*
