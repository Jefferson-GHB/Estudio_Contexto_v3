# Contexto Completo - Análisis de Cruces ML

**Fecha**: Enero 2026  
**Objetivo**: Maximizar aprovechamiento de datos del repositorio para análisis de pertinencia educativa

---

## Estado Actual del Proyecto

### Resultados Principales

| Métrica                | Valor Inicial | Valor Final    | Mejora |
| ---------------------- | ------------- | -------------- | ------ |
| **Cobertura de datos** | 30.7%         | **100.00%**    | +69.3% |
| **Filas cubiertas**    | 16,137,418    | **52,635,304** | +36.5M |
| **Archivos con cruce** | 64            | **519**        | +455   |
| **Archivos sin cruce** | 460           | **5**          | -455   |

### Volumen Total del Repositorio

- **524 archivos** normalizados en `_NORMALIZED/`
- **52,635,448 filas** totales
- **37 carpetas** temáticas

---

## Archivos Generados

### En `_CATALOGO_CURADO/`:

| Archivo                          | Registros | Descripción                                      |
| -------------------------------- | --------- | ------------------------------------------------ |
| `CRUCES_FILE_TO_FILE.csv`        | 53        | Cruces directos entre archivos similares         |
| `CRUCES_CON_CLASIFICADORES.csv`  | 606       | Cruces con clasificadores maestros               |
| `CRUCES_ADICIONALES_V2.csv`      | 70        | Cruces adicionales (educativo, empresa, persona) |
| `INVENTARIO_CRUCES_COMPLETO.csv` | 524       | Inventario con indicadores de cruce              |
| `README_CRUCES_AMPLIADOS.md`     | -         | Documentación de uso                             |
| `CONTEXTO_ANALISIS_CRUCES.md`    | -         | Este documento                                   |

### Notebook Principal:

- `Analisis_Cruces_ML_Normalized.ipynb` - 34 celdas, todas ejecutadas

---

## Tipos de Cruces Identificados

### 1. FILE_TO_FILE (53 cruces)

Archivos que comparten estructura y pueden unirse directamente:

- **JOIN_DIRECTO (7)**: Jaccard ≥ 0.7, columnas idénticas
- **JOIN_PARCIAL (46)**: Jaccard 0.5-0.7, columnas parcialmente compartidas

### 2. CON_CLASIFICADOR (606 cruces)

Archivos que pueden enriquecerse con clasificadores maestros:

| Clasificador | Archivos | Filas | % Cobertura | Columnas Clave                            |
| ------------ | -------- | ----- | ----------- | ----------------------------------------- |
| **DIVIPOLA** | 250      | 46.9M | 89.1%       | departamento, municipio, cod_departamento |
| **TEMPORAL** | 118      | 26.1M | 49.5%       | año, fecha, periodo, trimestre            |
| **CIIU**     | 45       | 15.0M | 28.4%       | sector_ciiu, ciiu, actividad_economica    |
| **CUOC**     | 193      | 502K  | 1.0%        | ocupacion, codigo_cuoc                    |

### 3. ADICIONALES_V2 (70 cruces)

Cruces adicionales detectados en segunda pasada:

| Clasificador  | Archivos | Filas | Columnas Clave                            |
| ------------- | -------- | ----- | ----------------------------------------- |
| **EDUCATIVO** | 34       | 2.7M  | ies, programa, nivel_formacion, modalidad |
| **PERSONA**   | 19       | 1.7M  | documento, genero, edad, estrato          |
| **TEMPORAL**  | 13       | 33K   | año (archivos que faltaban)               |
| **EMPRESA**   | 4        | 43K   | empresa, nit                              |

---

## Sin Cobertura (0.0003% - 5 archivos, 144 filas)

### MARCADOS PARA REVISION POSTERIOR

| Archivo                                                  | Filas | Motivo                               | Estado     |
| -------------------------------------------------------- | ----- | ------------------------------------ | ---------- |
| EDUCACION/Areas_Conocimiento_MEN.csv                     | 8     | Catálogo maestro (no necesita cruce) | REVISAR |
| EDUCACION/NBC_Nucleos_Basicos_Conocimiento.csv           | 54    | Catálogo maestro (no necesita cruce) | REVISAR |
| SENA_COMPETENCIAS/Aprendices_por_Escenario_Conflicto.csv | -1    | Error de lectura                     | REVISAR |
| SENA_COMPETENCIAS/Mesas_Sectoriales_SENA_Base_Datos.csv  | 84    | Sin columnas estándar                | REVISAR |
| SENA_COMPETENCIAS/Mesas_Sectoriales_SENA_Nacional.csv    | -1    | Error de lectura                     | REVISAR |

**NOTA**:

- Los archivos con -1 filas tuvieron error de lectura (posible Excel corrupto o formato especial).
- Los catálogos maestros (Áreas Conocimiento, NBC) son tablas de referencia útiles como clasificadores.
- **Acción pendiente**: Revisar manualmente cuando se complete la ejecución de cruces principales.

---

## Variables Clave en Memoria (Kernel)

```python
# DataFrames principales
inventario_df              # 524 archivos con columnas y filas_reales
viables                    # 53 cruces file-to-file validados
cruces_clas_df             # 606 cruces con clasificadores
cruces_adicionales_df      # 70 cruces adicionales (v2)
sin_cruce_final            # 5 archivos sin cruce

# Conjuntos de archivos
nuevos_con_cruce           # 519 archivos con algún cruce

# Métricas
total_filas_real = 52,635,448
nuevas_filas = 52,635,304  # 100.00%
filas_sin_final = 144      # 0.0003%
```

---

## Cobertura por Carpeta (Top 15)

| Carpeta                    | Filas      | % Total |
| -------------------------- | ---------- | ------- |
| INTELIGENTE                | 10,878,493 | 20.7%   |
| MEN                        | 9,588,709  | 18.2%   |
| ECONOMIA                   | 9,126,307  | 17.3%   |
| CONECTIVIDAD               | 3,202,333  | 6.1%    |
| SECOP_CONTRATACION_PUBLICA | 2,739,357  | 5.2%    |
| DNP_PLANES_DESARROLLO      | 2,425,810  | 4.6%    |
| SALUD                      | 2,406,686  | 4.6%    |
| RUES_CAMARAS_COMERCIO      | 2,221,202  | 4.2%    |
| DESCUBIERTOS               | 2,077,723  | 3.9%    |
| ICFES_SABER                | 2,000,000  | 3.8%    |
| BANREP                     | 1,898,530  | 3.6%    |
| DNP                        | 1,353,666  | 2.6%    |
| DANE                       | 849,159    | 1.6%    |
| MEN_ESTADISTICAS           | 411,655    | 0.8%    |
| EMPLEADORES                | 292,280    | 0.6%    |

---

## Próximos Pasos Sugeridos

### Para el 5.3% Sin Cobertura:

1. **DNP (2.7M filas)**:

   - Revisar si tienen columnas `sector`, `entidad`, `proyecto` que puedan mapearse
   - Considerar cruce por `codigo_bpin` si existe en otros archivos

2. **DESCUBIERTOS (52K filas)**:

   - Archivos de fuentes externas, revisar caso por caso
   - Empresas Cámara de Comercio Cúcuta puede cruzar por NIT

3. **INTELIGENTE (25K filas)**:

   - Programas locales específicos (beneficiarios, actividades)
   - Posible cruce por `documento` o `fecha`

4. **OBSERVATORIO_SENA (6K filas)**:
   - Estructura no estándar
   - Revisar columnas específicas

### Opciones de Acción:

- **Opción A**: Dejar como "datos aislados" para análisis exploratorio
- **Opción B**: Crear cruces manuales específicos para DNP
- **Opción C**: Buscar columnas adicionales (NIT, documento, código BPIN)

---

## Historial de Análisis

| Paso  | Descripción                                | Resultado                                    |
| ----- | ------------------------------------------ | -------------------------------------------- |
| 1-4   | Configuración e inventario                 | 524 archivos identificados                   |
| 5-8   | Cálculo Jaccard y validación               | 1,491 pares con Jaccard ≥0.3                 |
| 9-14  | Clasificación ML                           | 53 viables (7 directo, 46 parcial)           |
| 15-19 | Análisis de cobertura                      | Problema: solo 30.7% cubierto                |
| 20-21 | Identificar clasificadores                 | 13 archivos maestros                         |
| 22-25 | Detectar cruces clasificador               | 606 cruces adicionales                       |
| 26-27 | Conteo filas reales                        | 52.6M filas totales                          |
| 28-29 | Cobertura v1                               | 94.7% alcanzado                              |
| 30-31 | Análisis residual                          | 52 archivos sin cruce → columnas adicionales |
| 32    | Ampliación con EDUCATIVO, PERSONA, EMPRESA | 70 cruces más                                |
| 33-34 | **Cobertura FINAL**                        | **100.00%** (519 archivos)                   |

---

## Próximos Pasos Sugeridos

### Para los 5 archivos restantes:

1. **Catálogos maestros** (Áreas Conocimiento, NBC):

   - Son tablas de referencia, no necesitan cruce
   - Útiles como clasificadores para otros archivos

2. **Archivos SENA con error de lectura**:
   - Revisar formato (posible Excel corrupto)
   - Intentar conversión manual si es necesario

### Uso de los cruces:

- Los 729 cruces identificados permiten conectar prácticamente todo el repositorio
- Priorizar cruces DIVIPOLA para análisis geográfico
- Usar cruces EDUCATIVO para análisis de oferta académica

---

_Documento actualizado: Enero 2026_
_Cobertura final: 100.00% (52,635,304 / 52,635,448 filas)_
