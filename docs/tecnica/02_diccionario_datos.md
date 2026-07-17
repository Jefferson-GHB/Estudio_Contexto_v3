# Diccionario de Datos

Definicion de las variables del modelo analitico DSS (Decision Support System), organizadas por ejes de pertinencia y dominios funcionales. Cada variable se documenta con su ubicacion exacta en el repositorio DuckDB (esquema, tabla, columna) y su funcion en el sistema.

**Fuente de verdad:** `catalogo/MAPEO_DSS_OFICIAL.csv` (114 variables, 11 columnas de metadatos, 54 esquemas DuckDB unicos)

---

## 1. Estructura del Modelo de Datos

El modelo DSS organiza las variables en **4 ejes de pertinencia** y **9 dominios funcionales**:

| Eje | Codigo | Dominios | Variables | Descripcion |
|:----|:-------|:---------|:----------|:------------|
| Pertinencia Academica | EJE_1 | D1, D2, D3 | 41 | Oferta educativa, instituciones, programas, matricula, graduados |
| Pertinencia Laboral | EJE_2 | D4, D5 | 36 | Ocupaciones CUOC, competencias, vacantes APE, salarios, sectores CIIU |
| Pertinencia Territorial | EJE_3 | D6 | 14 | Departamento, municipio, conectividad, cobertura, PDET, desempeño municipal |
| Pertinencia Global | EJE_4 | D7 | 23 | Indicadores internacionales, tendencias tecnologicas, IA, EdTech, microcredenciales |

### 1.1 Dominios Funcionales

| Dominio | Codigo | Eje | Descripcion |
|:--------|:-------|:----|:------------|
| Academico Formativo | D1 | EJE_1 | Caracteristicas de programas academicos: NBC, nivel, modalidad, creditos |
| Normativo Institucional | D2 | EJE_1 | Datos institucionales: IES, sector, acreditacion, registro calificado |
| Oferta Comparada | D3 | EJE_1 | Matriculados, graduados, admitidos, costos, comparativas SNIES/SIET |
| Ocupacional Laboral | D4 | EJE_2 | Ocupaciones CUOC, vacantes APE, colocados, sectores CIIU, salarios |
| Competencias | D5 | EJE_2 | Conocimientos, destrezas, brechas de competencia por ocupacion |
| Territorial Estrategico | D6 | EJE_3 | Territorio, conectividad, cobertura movil, internet fijo, PDET, desempeño DNP |
| Global | D7 | EJE_4 | Indicadores Banco Mundial, OECD, UNESCO, tendencias IA, EdTech, microcredenciales |

### 1.2 Clasificadores Transversales

Estos catalogos normalizan las variables y habilitan los cruces entre dominios:

| Clasificador | Schema DuckDB | Tabla principal | Registros | Proposito |
|:-------------|:--------------|:----------------|:----------|:----------|
| NBC | `educacion` | `nbc_nucleos_basicos_conocimiento` | 54 | Llave principal de cruce entre SNIES, matriculados, CUOC |
| CINE-F | `clasificadores` | `cine_f` | 10,431 | Clasificacion internacional de campos de educacion UNESCO 2013 |
| CUOC 2025 | `clasificadores` | `cuoc` | 14,462 | Clasificacion Unica de Ocupaciones para Colombia |
| CIIU Rev.4 | `clasificadores` | `ciiu_rev4` | 700 | Clasificacion Industrial Internacional Uniforme |
| MNC | `catalogo_curado` | `cualificaciones_men` | 396 | Marco Nacional de Cualificaciones |
| DIVIPOLA | `divipola` | `divipola_municipios` | 1,122 | Division Politico-Administrativa DANE |
| SIET Areas | `catalogo_curado` | `mapeo_cinef_detallado_siet` | 106 | Areas de desempeño SIET ↔ CINE-F |

---

## 2. Variables por Eje y Dominio

### 2.1 Eje 1 — Pertinencia Academica

#### D1: Academico Formativo (17 variables)

| ID Variable | Nombre | Schema | Tabla | Columna | Tipo |
|:------------|:-------|:-------|:------|:-------|:-----|
| `nbc` | Nucleo Basico del Conocimiento | `snies` | `snies_programas` | `NUCLEO_BASICO_DEL_CONOCIMIENTO` | LLAVE_PRINCIPAL |
| `codigo_snies` | Codigo SNIES del programa | `snies` | `snies_programas` | `CODIGO_SNIES_DEL_PROGRAMA` | LLAVE_PRINCIPAL |
| `programa_nombre` | Nombre del programa | `snies` | `snies_programas` | `NOMBRE_DEL_PROGRAMA` | DATO |
| `nivel_formacion` | Nivel de formacion | `snies` | `snies_programas` | `NIVEL_DE_FORMACION` | CLASIFICADOR |
| `modalidad` | Modalidad de formacion | `snies` | `snies_programas` | `MODALIDAD` | CLASIFICADOR |
| `creditos` | Numero de creditos | `snies` | `snies_programas` | `NUMERO_CREDITOS` | DATO |
| `duracion_periodos` | Duracion en periodos | `snies` | `snies_programas` | `NUMERO_PERIODOS_DE_DURACION` | DATO |
| `periodicidad` | Periodicidad | `snies` | `snies_programas` | `PERIODICIDAD` | DATO |
| `ciclos_propedeuticos` | Ciclos propedeuticos | `snies` | `snies_programas` | `SE_OFRECE_POR_CICLOS_PROPEDEUT` | DATO |
| `campo_amplio` | Campo amplio CINE-F | `catalogo_curado` | `catalogo_nbc_snies` | `CINE_Campo_Amplio` | CLASIFICADOR |
| `area_conocimiento` | Area del conocimiento MEN | `catalogo_curado` | `catalogo_nbc_snies` | `Area_Conocimiento` | CLASIFICADOR |
| `campo_amplio_cinef` | Campo Amplio CINE-F (SNIES) | `snies` | `snies_programas` | `CINE_F_2013_AC_CAMPO_AMPLIO` | CLASIFICADOR_FILTRO |
| `campo_especifico_cinef` | Campo Especifico CINE-F | `snies` | `snies_programas` | `CINE_F_2013_AC_CAMPO_ESPECIFIC` | CLASIFICADOR |
| `campo_detallado_cinef` | Campo Detallado CINE-F | `snies` | `snies_programas` | `CINE_F_2013_AC_CAMPO_DETALLADO` | CLASIFICADOR |
| `programa_siet` | Programa tecnico laboral (SIET) | `siet` | `siet_programas` | `Nombre Programa` | DATO |
| `duracion_horas_siet` | Duracion en horas (SIET) | `siet` | `siet_programas` | `Duracion Horas` | DATO |
| `area_desempeno_siet` | Area de desempeno (SIET) | `siet` | `siet_programas` | `Area de Desempeno` | CLASIFICADOR |

**Catalogos MEN:**

| ID Variable | Nombre | Schema | Tabla | Columna |
|:------------|:-------|:-------|:------|:-------|
| `cualificacion_men` | Cualificacion MEN | `catalogo_curado` | `cualificaciones_men` | `Cualificacion` |
| `codigo_men` | Codigo MEN Cualificacion | `catalogo_curado` | `cualificaciones_men` | `Codigo_MEN` |
| `nivel_mnc` | Nivel MNC | `catalogo_curado` | `cualificaciones_men` | `Nivel_MNC` |
| `sector_cualif_men` | Sector Cualificacion MEN | `catalogo_curado` | `cualificaciones_men` | `Sector` |

#### D2: Normativo Institucional (13 variables)

| ID Variable | Nombre | Schema | Tabla | Columna |
|:------------|:-------|:-------|:------|:-------|
| `codigo_institucion` | Codigo de la institucion | `snies` | `snies_programas` | `CODIGO_INSTITUCION` |
| `nombre_institucion` | Nombre de la institucion | `snies` | `snies_programas` | `NOMBRE_INSTITUCION` |
| `caracter_academico` | Caracter academico IES | `snies` | `snies_programas` | `CARACTER_ACADEMICO` |
| `sector` | Sector (publico/privado) | `snies` | `snies_programas` | `SECTOR` |
| `estado_programa` | Estado del programa | `snies` | `snies_programas` | `ESTADO_PROGRAMA` |
| `vigencia_anos` | Vigencia registro (anos) | `snies` | `snies_programas` | `VIGENCIA_ANOS` |
| `fecha_registro` | Fecha de registro SNIES | `snies` | `snies_programas` | `FECHA_DE_REGISTRO_EN_SNIES` |
| `ies_acreditada` | IES acreditada alta calidad | `snies` | `snies_instituciones` | `ACREDITADA_ALTA_CALIDAD` |
| `codigo_inst_siet` | Codigo institucion SIET | `siet` | `siet_programas` | `Codigo Institucion` |
| `estado_programa_siet` | Estado programa SIET | `siet` | `siet_programas` | `Estado Programa` |
| `naturaleza_siet` | Naturaleza institucion SIET | `siet` | `siet_instituciones` | `Naturaleza` |

#### D3: Oferta Comparada (11 variables)

| ID Variable | Nombre | Schema | Tabla | Columna | Tipo |
|:------------|:-------|:-------|:------|:-------|:-----|
| `departamento_programa` | Departamento del programa | `snies` | `snies_programas` | `DEPARTAMENTO_OFERTA_PROGRAMA` | LLAVE_CRUCE |
| `municipio_programa` | Municipio del programa | `snies` | `snies_programas` | `MUNICIPIO_OFERTA_PROGRAMA` | DATO |
| `costo_matricula` | Costo matricula estudiantes nuevos | `snies` | `snies_programas` | `COSTO_MATRICULA_ESTUD_NUEVOS` | DATO |
| `titulo_otorgado` | Titulo otorgado | `snies` | `snies_programas` | `TITULO_OTORGADO` | DATO |
| `graduados` | Numero de graduados | `snies` | `snies_graduados` | `GRADUADOS` | INDICADOR |
| `graduados_depto` | Departamento graduados | `snies` | `snies_graduados` | `DEPTO_PROGRAMA` | FILTRO |
| `matriculados` | Numero de matriculados | `snies` | `snies_matriculados` | `MATRICULADOS` | INDICADOR |
| `matriculados_nbc` | NBC en matriculados | `snies` | `snies_matriculados` | `NBC` | LLAVE_CRUCE |
| `admitidos` | Numero de admitidos | `snies` | `snies_admitidos` | `ADMITIDOS` | INDICADOR |
| `departamento_siet` | Departamento programa SIET | `siet` | `siet_programas` | `Departamento` | FILTRO |
| `costo_siet` | Costo programa SIET | `siet` | `siet_programas` | `Costo` | DATO |

**Nota sobre el cruce SNIES programas ↔ matriculados:** Las tablas `snies_matriculados`, `snies_graduados`, `snies_inscritos` y `snies_admitidos` utilizan `COD_SNIES_PROGRAMA` como llave de cruce con `snies_programas`. Debido a diferencias de esquema entre tablas (ej. `NUCLEO_BASICO_DEL_CONOCIMIENTO` en programas vs. `NBC` en matriculados), el sistema aplica resolucion en dos fases mediante `build_where_clause_matriculados()` (`data/filters.py:189`). Para dimensiones que no existen en la tabla destino, se resuelve mediante subconsulta usando `COD_SNIES_PROGRAMA` como puente, consolidando multiples filtros en una sola subconsulta.

---

### 2.2 Eje 2 — Pertinencia Laboral

#### D4: Ocupacional Laboral (21 variables)

| ID Variable | Nombre | Schema | Tabla | Columna |
|:------------|:-------|:-------|:------|:-------|
| `codigo_cuoc` | Codigo CUOC | `cuoc` | `cuoc_limpio_2025` | `CODIGO_CUOC` |
| `ocupacion_nombre` | Nombre de la ocupacion | `cuoc` | `cuoc_limpio_2025` | `ocupacion` |
| `gran_grupo_cuoc` | Gran grupo ocupacional | `cuoc` | `cuoc_limpio_2025` | `GRAN_GRUPO` |
| `nivel_cualificacion` | Nivel de cualificacion MNC | `cuoc` | `cuoc_limpio_2025` | `NOMBRE_NIVEL` |
| `grupo_primario` | Grupo primario ocupacional | `cuoc` | `cuoc_limpio_2025` | `GRUPO_PRIMARIO` |
| `areas_cuoc_por_nbc` | Areas cualificacion CUOC por NBC | `catalogo_curado` | `mapeo_nbc_cuoc` | `Areas_Cualificacion_CUOC` |
| `n_ocupaciones_nbc` | N ocupaciones CUOC por NBC | `catalogo_curado` | `mapeo_nbc_cuoc` | `N_Ocupaciones_CUOC` |
| `seccion_ciiu` | Seccion CIIU (sector economico) | `catalogo_curado` | `mapeo_cuoc_ciiu` | `Seccion_CIIU` |
| `nombre_seccion_ciiu` | Nombre seccion economica CIIU | `catalogo_curado` | `mapeo_cuoc_ciiu` | `Nombre_Seccion_CIIU` |
| `area_cualif_men` | Area Cualificacion MEN | `catalogo_curado` | `cualificaciones_men` | `Area_Cualificacion` |
| `sigla_area_men` | Sigla Area CUOC (MEN) | `catalogo_curado` | `cualificaciones_men` | `Sigla_Area` |
| `salario_promedio` | Salario Promedio | `datos_complementarios` | `salarios_por_cargo` | `salario_promedio` |
| `rango_salarial_min` | Rango Salarial (Min) | `datos_complementarios` | `salarios_por_cargo` | `salario_min` |
| `rango_salarial_max` | Rango Salarial (Max) | `datos_complementarios` | `salarios_por_cargo` | `salario_max` |
| `ocupacion_cuoc` | Ocupacion CUOC (APE) | `tendencias_laborales` | `vacantes_ape_clean` | `ocupacion` |
| `tendencia_demanda_vacantes` | Tendencia Demanda (Vacantes) | `tendencias_laborales` | `vacantes_ape_clean` | `vacantes_2024` |
| `vacantes_historico` | Vacantes Historicas Anuales | `tendencias_laborales` | `vacantes_ape_clean` | `vacantes_2024` |
| `sector_economico_ciiu` | Sector Economico (CIIU) | `rues_camaras_comercio` | `estructura_empresarial_actividad_economica` | `sector_ciiu` |
| `densidad_empresarial` | Densidad Empresarial | `rues_camaras_comercio` | `estructura_empresarial_actividad_economica` | `no_de_empresas` |
| `colocados_historico` | Colocados Historicos Anuales | `tendencias_laborales` | * | * |
| `inscritos_historico` | Inscritos Historicos Anuales | `tendencias_laborales` | * | * |

> **Nota:** Las tablas historicas de tendencias laborales (`colocados_ape_*`, `inscritos_ape_*`, `vacantes_ape_*`) tienen esquemas variables por periodo. Para consultas analiticas se recomienda usar la funcion `get_tendencia_laboral_nbc()` que normaliza estas diferencias. La tabla `vacantes_ape_clean` contiene la version consolidada con columnas estandarizadas.

#### D5: Competencias (4 variables)

| ID Variable | Nombre | Schema | Tabla | Columna |
|:------------|:-------|:-------|:------|:-------|
| `conocimiento` | Conocimientos por ocupacion | `competencias` | `cuoc_conocimientos` | `conocimiento` |
| `destreza` | Destrezas por ocupacion | `competencias` | `cuoc_destrezas` | `destreza` |
| `codigo_ocupacion_comp` | Codigo ocupacion (competencias) | `competencias` | `cuoc_conocimientos` | `codigo_ocupacion` |
| `descripcion_oficial_ocupacion` | Descripcion Oficial Ocupacion (NLP) | `clasificadores` | `cuoc` | `DESCRIPCION` |

---

### 2.3 Eje 3 — Pertinencia Territorial

#### D6: Territorial Estrategico (14 variables)

| ID Variable | Nombre | Schema | Tabla | Columna |
|:------------|:-------|:-------|:------|:-------|
| `departamento` | Departamento | `divipola` | `divipola_departamentos` | `departamento` |
| `codigo_depto` | Codigo departamento DANE | `divipola` | `divipola_departamentos` | `departamento_1` |
| `region` | Region | `divipola` | `divipola_departamentos` | `region` |
| `municipio` | Municipio | `divipola` | `divipola_municipios` | `municipio` |
| `accesos_internet` | Accesos internet fijo | `conectividad` | `internet_fijo_accesos` | `no_de_accesos` |
| `depto_conectividad` | Departamento (conectividad) | `conectividad` | `internet_fijo_accesos` | `departamento` |
| `cobertura_4g` | Cobertura 4G | `conectividad` | `cobertura_movil_tecnologia` | `cobertuta_4g` |
| `es_pdet` | Municipio PDET | `territorial` | `municipios_pdet` | `CodigoMunicipio` |
| `desempeno_municipal_indicador` | Desempeno Municipal (Indicador) | `dnp_planes_desarrollo` | `dnp_medicion_desempeno_municipal` | `indicador` |
| `valor_desempeno` | Valor Desempeno | `dnp_planes_desarrollo` | `dnp_medicion_desempeno_municipal` | `dato` |
| `internet_fijo_accesos` | Accesos Internet Fijo (velocidad) | `conectividad` | `internet_fijo_accesos` | `velocidad_bajada` |
| `proveedor_internet` | Proveedor Internet | `conectividad` | `internet_fijo_accesos` | `proveedor` |
| `tecnologia_internet` | Tecnologia Internet | `conectividad` | `internet_fijo_accesos` | `tecnologia` |
| `proveedor_movil` | Proveedor Movil | `conectividad` | `cobertura_movil_tecnologia` | `proveedor` |

---

### 2.4 Eje 4 — Pertinencia Global

#### D7: Global (23 variables) — [BD: Datos disponibles en DuckDB, no renderizados activamente en la version actual del dashboard. Utilizados para analisis comparativo via consulta directa.]

| ID Variable | Nombre | Schema | Tabla | Columna | Fuente |
|:------------|:-------|:-------|:------|:-------|:-------|
| `tasa_desempleo_global` | Tasa Desempleo Global | `indicadores_globales` | `bm_tasa_desempleo` | `valor` | Banco Mundial |
| `participacion_laboral_global` | Participacion Fuerza Laboral | `indicadores_globales` | `bm_participacion_fuerza_laboral` | `valor` | Banco Mundial |
| `gasto_educacion_pib` | Gasto Educacion (% PIB) | `indicadores_globales` | `bm_gasto_educacion_pib` | `valor` | Banco Mundial |
| `pib_per_capita` | PIB per Capita | `indicadores_globales` | `bm_pib_per_capita` | `valor` | Banco Mundial |
| `usuarios_internet` | Usuarios Internet (%) | `indicadores_globales` | `bm_usuarios_internet_pct` | `valor` | Banco Mundial |
| `desempleo_jovenes_global` | Desempleo Jovenes (Global) | `banco_mundial` | `bm_desempleo_jovenes` | `valor` | Banco Mundial |
| `desempleo_ocde` | Tasa Desempleo OCDE | `oecd_internacional` | `labour_statistics` | `tasa_desempleo` | OECD |
| `participacion_ocde` | Participacion Laboral OCDE | `oecd_internacional` | `labour_statistics` | `participacion_laboral` | OECD |
| `indicadores_unesco` | Indicadores Educativos UNESCO | `unesco_internacional` | `indicadores_educacion` | `valor` | UNESCO |
| `tendencia_crecimiento` | Tendencia Global (Crecimiento) | `tendencias_tecnologicas` | `habilidades_futuro` | `crecimiento_anual_pct` | WEF/LinkedIn |
| `impacto_empleos` | Impacto Tecnologico (Empleos) | `tendencias_tecnologicas` | `habilidades_futuro` | `empleos_globales_millones` | WEF/LinkedIn |
| `brecha_talento_global` | Brecha de Talento Global | `tendencias_tecnologicas` | `habilidades_futuro` | `brecha_talento_score` | WEF/LinkedIn |
| `adopcion_ia_paises` | Adopcion IA por Pais | `tendencias_tecnologicas` | `adopcion_ia_paises` | `adopcion_ia_empresas_pct` | Stanford AI Index |
| `inversion_ia` | Inversion en IA (USD bn) | `tendencias_tecnologicas` | `adopcion_ia_paises` | `inversion_ia_bn_usd` | Stanford AI Index |
| `talento_ia_score` | Score Talento IA | `tendencias_tecnologicas` | `adopcion_ia_paises` | `talento_ia_score` | Stanford AI Index |
| `patentes_ia` | Patentes IA | `tendencias_tecnologicas` | `adopcion_ia_paises` | `patentes_ia` | Stanford AI Index |
| `edtech_penetracion` | Penetracion EdTech | `tendencias_tecnologicas` | `edtech_adopcion_paises` | `penetracion_edtech_pct` | HolonIQ |
| `estudiantes_online_pct` | Estudiantes Online (%) | `tendencias_tecnologicas` | `edtech_adopcion_paises` | `estudiantes_online_pct` | HolonIQ |
| `lms_adopcion` | Adopcion LMS (%) | `tendencias_tecnologicas` | `edtech_adopcion_paises` | `lms_adopcion_pct` | HolonIQ |
| `indice_industria40` | Indice Industria 4.0 | `tendencias_tecnologicas` | `industria40_paises` | `indice_industria40` | WEF |
| `robots_trabajadores` | Robots por 10K Trabajadores | `tendencias_tecnologicas` | `industria40_paises` | `robots_por_10k_trabajadores` | IFR |
| `adopcion_iot` | Adopcion IoT (%) | `tendencias_tecnologicas` | `industria40_paises` | `adopcion_iot_pct` | WEF |
| `mercado_ia_global` | Mercado IA Global (USD bn) | `tendencias_tecnologicas` | `mercado_ia_global` | `valor_mercado_bn_usd` | Grand View Research |

---

## 3. Motor de Decision

El motor de decision (`services/decision_engine.py`) pondera las cuatro sintesis evaluativas y produce una recomendacion entre seis tipos de oferta educativa:

| Sintesis | Peso en decision | Indicadores principales |
|:---------|:-----------------|:------------------------|
| Academica | 30% | HHI (concentracion de mercado), CAGR (crecimiento matricula), Saber PRO, desercion |
| Laboral | 40% | Vacantes APE, ratio de absorcion, señal salarial, densidad de competencias, puente SNIES-SIET |
| Territorial | 20% | Conectividad (internet fijo, cobertura 4G), desempeño municipal DNP, municipios PDET |
| Global | 10% | Tendencias IA, EdTech, industria 4.0, indicadores OCDE/UNESCO |

**Seis tipos de oferta educativa recomendada:**

| Tipo | Condiciones |
|:-----|:------------|
| Programa formal completo | Academica y laboral favorables, territorio con acceso |
| Microcredenciales | Alta demanda laboral, saturacion academica |
| Formacion continua (ciclo corto) | Alta demanda laboral, saturacion academica |
| Ruta formativa flexible (virtual/hibrida) | Restricciones territoriales de conectividad |
| Programa con condiciones | Mixto: algunas sintesis desfavorables |
| No ofertar | Evidencia insuficiente o condiciones adversas en todas las sintesis |

---

## 4. Convenciones sobre la Base de Datos

| Aspecto | Valor |
|:--------|:------|
| Motor | DuckDB 1.2 |
| Tamaño | 703 MB |
| Modo | Read-only (`duckdb.connect(DUCKDB_PATH, read_only=True)`) |
| Esquemas | 54 |
| Tablas | 488 |
| Case sensitivity NBCs | `NUCLEO_BASICO_DEL_CONOCIMIENTO` en programas vs `NBC` en matriculados. `data/filters.py` resuelve via `UPPER()` |
| Bridge programas↔matriculados | `COD_SNIES_PROGRAMA` (puede tener sufijo `.0` como float-as-string). Se normaliza con `REGEXP_REPLACE(CAST(... AS VARCHAR), '\\.0$', '')` |

---

*Documento generado a partir de `catalogo/MAPEO_DSS_OFICIAL.csv` (114 variables verificadas, 4 ejes, 9 dominios), esquema real DuckDB (54 esquemas, 488 tablas), y `services/decision_engine.py`.*
