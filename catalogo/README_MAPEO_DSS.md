# MAPEO DSS - DOCUMENTACIÓN TÉCNICA

## Sistema de Soporte a Decisiones para Pertinencia de Programas Académicos

**Versión:** 2.0 Final  
**Fecha:** 20 de Enero 2026  
**Autor:** DSS Development Team

---

## RESUMEN EJECUTIVO

El mapeo de variables es el núcleo del DSS que conecta las preguntas de análisis con las fuentes de datos disponibles en el repositorio DuckDB. Este mapeo define **106 variables** organizadas en **4 Ejes** y **8 Dominios**.

### Estadísticas del Mapeo

| Métrica                        | Valor        |
| ------------------------------ | ------------ |
| **Total Variables**            | 106          |
| **Variables Disponibles**      | 88 (83%)     |
| **Variables Calculadas**       | 6 (6%)       |
| **Variables LLM**              | 8 (8%)       |
| **Variables Parciales/Proxy**  | 4 (3%)       |
| **Schemas DuckDB Utilizados**  | 29           |
| **Total Registros Accesibles** | ~46 millones |

---

## ARQUITECTURA DEL MAPEO

### Ejes de Pertinencia

```
EJE_1_PERTINENCIA_ACADEMICA (45 variables)
├── D1: Académico-Formativo (15 vars)
├── D2: Normativo e Institucional (13 vars)
└── D3: Oferta Académica Comparada (17 vars)

EJE_2_PERTINENCIA_LABORAL (23 variables)
├── D4: Ocupacional y Laboral (14 vars)
└── D5: Competencias (9 vars)

EJE_3_PERTINENCIA_TERRITORIAL (32 variables)
├── D6: Territorial, Social y Estratégico (14 vars)
└── D7: Global y Tendencias (18 vars)

EJE_4_DECISION_VIRTUAL (6 variables)
└── D8: Decisión Integrador (6 vars)
```

---

## DESCRIPCION DE DOMINIOS

### D1: ACADÉMICO-FORMATIVO

**Propósito:** Caracterización curricular del programa propuesto.

| Variable               | Fuente                   | Registros |
| ---------------------- | ------------------------ | --------- |
| `campo_amplio`         | catalogo_nbc_snies       | 57        |
| `area_conocimiento`    | catalogo_nbc_snies       | 57        |
| `nbc`                  | snies_programas          | 30,660    |
| `programa_propuesto`   | snies_programas          | 30,660    |
| `nivel_formacion`      | snies_programas          | 30,660    |
| `nivel_formacion_siet` | siet_programas           | 25,010    |
| `ruta_formativa`       | CRUCE                    | Calculado |
| `ciclos_propedeuticos` | snies_programas          | 30,660    |
| `creditos_academicos`  | snies_programas          | 30,660    |
| `horas_formacion_siet` | siet_programas           | 25,010    |
| `duracion_programa`    | snies_programas          | 30,660    |
| `periodicidad_oferta`  | snies_programas          | 30,660    |
| `modalidad`            | snies_programas          | 30,660    |
| `metodologia`          | snies_programas          | 30,660    |
| `num_asignaturas`      | programacion_cursos_sena | 42,080    |

### D2: NORMATIVO E INSTITUCIONAL

**Propósito:** Cumplimiento regulatorio y contexto institucional.

| Variable                   | Fuente                     | Registros |
| -------------------------- | -------------------------- | --------- |
| `tipo_institucion`         | snies_instituciones        | 389       |
| `tipo_institucion_siet`    | siet_instituciones         | 4,385     |
| `naturaleza_juridica`      | snies_programas            | 30,660    |
| `estado_programa`          | snies_programas            | 30,660    |
| `estado_programa_siet`     | siet_programas             | 25,010    |
| `registro_calificado`      | snies_programas            | 30,660    |
| `fecha_registro_snies`     | snies_programas            | 30,660    |
| `vigencia_renovacion`      | snies_programas            | 30,660    |
| `acreditacion_ies`         | es_ies_acreditadas         | 132       |
| `icfes_saber_pro`          | icfes_saber_pro_resultados | 999,891   |
| `icfes_saber_tyt`          | icfes_saber_tyt_resultados | 920,983   |
| `observaciones_normativas` | LLM_GENERATED              | -         |
| `fuente_informacion`       | METADATA                   | -         |

### D3: OFERTA ACADÉMICA COMPARADA

**Propósito:** Análisis de competencia y benchmarking.

| Variable                     | Fuente                        | Registros |
| ---------------------------- | ----------------------------- | --------- |
| `denominacion_programa`      | snies_programas               | 30,660    |
| `denominacion_programa_siet` | siet_programas                | 25,010    |
| `institucion_oferente`       | snies_programas               | 30,660    |
| `institucion_oferente_siet`  | siet_instituciones            | 4,385     |
| `valor_matricula`            | snies_programas               | 30,660    |
| `costo_programa_siet`        | siet_programas                | 25,010    |
| `region_programa`            | divipola_departamentos        | 33        |
| `municipio_programa`         | snies_programas               | 30,660    |
| `tipo_cobertura`             | CALCULADO                     | -         |
| `oferta_internacional`       | indicadores_educacion         | 7,329     |
| `pais_referencia`            | consolidado_global            | 29,984    |
| `programas_similares_count`  | CALCULADO                     | -         |
| `snies_graduados`            | snies_graduados               | 307,586   |
| `snies_matriculados`         | snies_matriculados            | 737,691   |
| `snies_admitidos`            | snies_admitidos               | 509,345   |
| `siet_matricula`             | siet*matricula_programa*      | 41,424    |
| `siet_certificados`          | siet_estudiantes_certificados | 41,424    |

### D4: OCUPACIONAL Y LABORAL

**Propósito:** Demanda laboral y empleabilidad.

| Variable                    | Fuente                    | Registros |
| --------------------------- | ------------------------- | --------- |
| `ocupacion_cuoc`            | cuoc_limpio_2025          | 14,462    |
| `codigo_cuoc`               | cuoc_limpio_2025          | 14,462    |
| `sector_ciiu`               | ciiu_rev4                 | 700       |
| `nivel_cualificacion_mnc`   | cuoc_limpio_2025          | 14,462    |
| `actividades_profesionales` | cuoc                      | 14,462    |
| `tareas_criticas`           | perfilesocupacionales     | 681       |
| `salario_promedio`          | salarios_nivel_educativo  | 1,890     |
| `rango_salarial`            | salarios_categoria_empleo | 23        |
| `formalidad_empleo`         | formalidad_regimen_salud  | 1         |
| `tendencia_demanda_laboral` | vacantes_anual_2024       | 615       |
| `colocaciones_ape`          | colocaciones_ape          | 605       |
| `estructura_empresarial`    | RUES                      | 9,125,440 |
| `mesas_sectoriales`         | mesas_sectoriales_sena    | 84        |
| `fuente_laboral`            | METADATA                  | -         |

### D5: COMPETENCIAS

**Propósito:** Competencias técnicas y transversales requeridas.

| Variable                     | Fuente                | Registros |
| ---------------------------- | --------------------- | --------- |
| `competencias_tecnicas`      | cuoc_conocimientos    | 3,599     |
| `destrezas_ocupacionales`    | cuoc_destrezas        | 4,422     |
| `competencias_transversales` | catalogo_competencias | 36        |
| `competencias_digitales`     | habilidades_futuro    | 12        |
| `habilidades_ciencia_datos`  | habilidades_digitales | 5,231     |
| `nivel_competencia_esperado` | mapeo_cuoc_nivel      | 680       |
| `marco_referencia`           | METADATA              | -         |
| `brechas_competencia`        | brechas_competencia   | 41        |
| `certificaciones_sena`       | certificacion_fpi     | 8,538     |

### D6: TERRITORIAL, SOCIAL Y ESTRATÉGICO

**Propósito:** Contexto geográfico y prioridades de desarrollo.

| Variable                    | Fuente                 | Registros |
| --------------------------- | ---------------------- | --------- |
| `region`                    | divipola_departamentos | 33        |
| `departamento`              | divipola_departamentos | 33        |
| `municipio`                 | divipola_municipios    | 1,122     |
| `plan_desarrollo`           | dnp_indicadores        | 16,261    |
| `desempeno_municipal`       | dnp_desempeno          | 22,020    |
| `sector_priorizado`         | mesas_sectoriales      | 84        |
| `cluster_productivo`        | mapeo_cuoc_ciiu        | 41        |
| `pertinencia_territorial`   | CALCULADO              | -         |
| `justificacion_territorial` | LLM_GENERATED          | -         |
| `conectividad_internet`     | internet_fijo_accesos  | 2,704,353 |
| `cobertura_movil`           | cobertura_movil        | 407,280   |
| `municipios_pdet`           | municipios_pdet        | 170       |
| `potencial_virtual`         | CALCULADO              | -         |
| `matricula_departamento`    | men_matricula          | 567       |

### D7: GLOBAL Y TENDENCIAS

**Propósito:** Perspectiva global e indicadores internacionales.

| Variable                  | Fuente                 | Registros |
| ------------------------- | ---------------------- | --------- |
| `tendencia_global`        | habilidades_futuro     | 12        |
| `impacto_tecnologico`     | industria40_paises     | 12        |
| `adopcion_ia_paises`      | adopcion_ia_paises     | 16        |
| `edtech_mercado`          | edtech_mercado         | 17        |
| `impacto_social`          | bm_empleo_vulnerable   | 33        |
| `impacto_ambiental_ods`   | ods_soc                | 25,674    |
| `referente_internacional` | consolidado_global     | 29,984    |
| `horizonte_temporal`      | LLM_GENERATED          | -         |
| `riesgo_obsolescencia`    | CALCULADO              | -         |
| `bm_pib_per_capita`       | bm_pib_per_capita      | 35        |
| `bm_tasa_desempleo`       | bm_tasa_desempleo      | 34        |
| `bm_matricula_terciaria`  | bm_matricula_terciaria | 22        |
| `bm_gasto_educacion`      | bm_gasto_educacion     | 23        |
| `bm_usuarios_internet`    | bm_usuarios_internet   | 31        |
| `bm_desempleo_jovenes`    | bm_desempleo_jovenes   | 34        |
| `oecd_indicadores`        | labour_statistics      | 13        |
| `unesco_sdg4`             | indicadores_unesco     | 12,089    |
| `oit_empleo_global`       | empleo_global_oit      | 23        |

### D8: DECISIÓN INTEGRADOR

**Propósito:** Síntesis ejecutiva y recomendaciones.

| Variable                  | Fuente        | Estado     |
| ------------------------- | ------------- | ---------- |
| `juicio_academico`        | LLM_GENERATED | LLM        |
| `juicio_laboral`          | LLM_GENERATED | LLM        |
| `juicio_territorial`      | LLM_GENERATED | LLM        |
| `viabilidad`              | LLM_GENERATED | LLM        |
| `tipo_oferta_recomendada` | LLM_GENERATED | LLM        |
| `evidencias`              | CONSOLIDADO   | Automático |

---

## FUENTES DE DATOS PRINCIPALES

### Educación Superior (ES)

| Schema        | Tabla                | Registros | Descripción                      |
| ------------- | -------------------- | --------- | -------------------------------- |
| `snies`       | snies_programas      | 30,660    | Programas ES activos e inactivos |
| `snies`       | snies_instituciones  | 389       | IES de Colombia                  |
| `snies`       | snies_graduados      | 307,586   | Histórico de graduados           |
| `snies`       | snies_matriculados   | 737,691   | Histórico de matrícula           |
| `snies`       | snies_admitidos      | 509,345   | Histórico de admitidos           |
| `icfes_saber` | saber_pro_resultados | 999,891   | Resultados Saber PRO             |
| `icfes_saber` | saber_tyt_resultados | 920,983   | Resultados Saber TyT             |

### Educación para el Trabajo (ETDH)

| Schema | Tabla                    | Registros | Descripción               |
| ------ | ------------------------ | --------- | ------------------------- |
| `siet` | siet_programas           | 25,010    | Programas técnico laboral |
| `siet` | siet_instituciones       | 4,385     | Instituciones ETDH        |
| `siet` | siet*matricula_programa* | 41,424    | Matrícula ETDH            |

### Ocupaciones y Competencias

| Schema           | Tabla              | Registros | Descripción                 |
| ---------------- | ------------------ | --------- | --------------------------- |
| `cuoc`           | cuoc_limpio_2025   | 14,462    | Clasificación ocupaciones   |
| `competencias`   | cuoc_conocimientos | 3,599     | Conocimientos por ocupación |
| `competencias`   | cuoc_destrezas     | 4,422     | Destrezas por ocupación     |
| `clasificadores` | ciiu_rev4          | 700       | Clasificación económica     |

### Territorial y Conectividad

| Schema         | Tabla                 | Registros | Descripción         |
| -------------- | --------------------- | --------- | ------------------- |
| `divipola`     | divipola_municipios   | 1,122     | Municipios Colombia |
| `conectividad` | internet_fijo_accesos | 2,704,353 | Accesos internet    |
| `conectividad` | cobertura_movil       | 407,280   | Cobertura móvil     |

### Indicadores Internacionales

| Schema                        | Tabla                 | Registros | Descripción          |
| ----------------------------- | --------------------- | --------- | -------------------- |
| `banco_mundial_internacional` | consolidado_global    | 29,984    | Indicadores BM       |
| `unesco_internacional`        | indicadores_educacion | 12,089    | Indicadores UNESCO   |
| `oecd_internacional`          | labour_statistics     | 13        | Mercado laboral OECD |

---

## TIPOS DE VARIABLES

| Tipo             | Cantidad | Descripción                             |
| ---------------- | -------- | --------------------------------------- |
| **DATO**         | 30       | Valor directo de la base de datos       |
| **INDICADOR**    | 35       | Métricas calculadas o agregadas         |
| **CLASIFICADOR** | 22       | Categorías y taxonomías                 |
| **LLM**          | 8        | Generado por el modelo de lenguaje      |
| **CALCULADO**    | 6        | Derivado de cruces de datos             |
| **METADATA**     | 3        | Información del sistema                 |
| **PROXY**        | 1        | Aproximación cuando no hay dato directo |
| **CONSOLIDADO**  | 1        | Compilación automática                  |

---

## CRUCES Y JOINS PRINCIPALES

### Cruce NBC ↔ SNIES

```sql
catalogo_nbc_snies.NBC = snies_programas.NUCLEO_BASICO_DEL_CONOCIMIENTO
```

### Cruce CUOC ↔ NBC (Ocupación → Formación)

```sql
mapeo_nbc_cuoc.CODIGO_CUOC = cuoc_limpio_2025.CODIGO_CUOC
mapeo_nbc_cuoc.NBC = snies_programas.NUCLEO_BASICO_DEL_CONOCIMIENTO
```

### Cruce Territorial

```sql
divipola_departamentos.nombre_departamento = snies_programas.DEPARTAMENTO_OFERTA_PROGRAMA
divipola_municipios.codigo_municipio = conectividad.codigo_municipio
```

### Cruce CIIU ↔ CUOC (Sector ↔ Ocupación)

```sql
mapeo_cuoc_ciiu.CIIU_CODIGO = ciiu_rev4.CODIGO
mapeo_cuoc_ciiu.CUOC_CODIGO = cuoc_limpio_2025.CODIGO_CUOC
```

---

## ARCHIVOS GENERADOS

| Archivo                            | Descripción                                       |
| ---------------------------------- | ------------------------------------------------- |
| `MAPEO_DSS_VARIABLES_COMPLETO.csv` | Versión completa con 15 columnas de metadatos     |
| `MAPEO_DSS_81_VARIABLES.csv`       | Versión simplificada compatible con dss_engine.py |

### Estructura del CSV Completo

| Columna                | Descripción                                     |
| ---------------------- | ----------------------------------------------- | --- |
| `Eje`                  | Eje de pertinencia (1-4)                        |
| `Dominio`              | Dominio (D1-D8)                                 |
| `ID_Variable`          | Identificador único                             |
| `Nombre_Variable`      | Nombre descriptivo                              |
| `Tipo_Variable`        | DATO/INDICADOR/CLASIFICADOR/LLM/CALCULADO       |
| `Schema`               | Schema en DuckDB                                |
| `Tabla`                | Tabla principal                                 |
| `Columna_Principal`    | Columna con el dato                             |
| `Columnas_Secundarias` | Columnas adicionales (separadas por `           | `)  |
| `Join_Con`             | Tabla para JOIN (formato: schema.tabla.columna) |
| `Filtros_Sugeridos`    | Columnas para filtrar                           |
| `Registros`            | Cantidad de registros                           |
| `Cobertura_Temporal`   | Rango de años                                   |
| `Estado`               | DISPONIBLE/CALCULADO/LLM_REQUIRED/PARCIAL/PROXY |
| `Prioridad`            | CRITICA/ALTA/MEDIA/BAJA                         |
| `Nota`                 | Observaciones                                   |

---

## USO EN EL SISTEMA DSS

### Motor de Búsqueda (dss_engine.py)

```python
# El mapeo se carga automáticamente
mapeo = pd.read_csv("MAPEO_DSS_81_VARIABLES.csv")

# Para cada variable, el motor:
# 1. Identifica el schema y tabla
# 2. Construye la consulta SQL
# 3. Ejecuta contra DuckDB
# 4. Retorna los resultados
```

### Agente SQL (llm_sql_agent.py)

```python
# El agente usa el mapeo para:
# 1. Entender qué tablas consultar
# 2. Construir JOINs correctos
# 3. Aplicar filtros territoriales
# 4. Generar SQL válido
```

---

## VALIDACIONES

- [x] Todas las tablas referenciadas existen en DuckDB
- [x] Los campos de JOIN son compatibles
- [x] Cobertura temporal documentada
- [x] Estados de disponibilidad verificados
- [x] Registros contabilizados
- [x] Dominios completos según documento formal

---

## SOPORTE

Para modificar el mapeo:

1. Editar `scripts/generar_mapeo_completo.py`
2. Ejecutar: `python scripts/generar_mapeo_completo.py`
3. Verificar archivos generados en `_CATALOGO_CURADO/`

---

**Estudio Contexto - 2026**
