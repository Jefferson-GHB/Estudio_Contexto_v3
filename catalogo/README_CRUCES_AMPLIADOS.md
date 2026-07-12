# Catálogo de Cruces Ampliados - Análisis ML

**Generado**: Análisis ML con validación de contenido  
**Objetivo**: Maximizar aprovechamiento de los 52.6M de registros del repositorio

---

## Resultados Principales

| Métrica                         | Valor                          |
| ------------------------------- | ------------------------------ |
| **Total archivos normalizados** | 524                            |
| **Total filas en repositorio**  | 52,635,448                     |
| **Cobertura alcanzada**         | **94.7%** (49.9M filas)        |
| **Archivos con cruce**          | 472 (90.1%)                    |
| **Sin cobertura**               | 52 archivos (5.3%, 2.8M filas) |

---

## Archivos Generados

### 1. `CRUCES_FILE_TO_FILE.csv`

**53 cruces** directos entre archivos con estructura similar.

| Columna           | Descripción                             |
| ----------------- | --------------------------------------- |
| `archivo_origen`  | Archivo fuente del cruce                |
| `archivo_destino` | Archivo destino del cruce               |
| `columnas_cruce`  | Columnas compartidas para JOIN          |
| `jaccard`         | Índice de similitud (0-1)               |
| `tipo_viabilidad` | JOIN_DIRECTO, JOIN_PARCIAL, COMPARATIVO |
| `tipo_cruce`      | FILE_TO_FILE                            |

### 2. `CRUCES_CON_CLASIFICADORES.csv`

**606 cruces** con clasificadores maestros (DIVIPOLA, CUOC, CIIU, TEMPORAL).

| Columna           | Descripción                    |
| ----------------- | ------------------------------ |
| `archivo_origen`  | Archivo a enriquecer           |
| `archivo_destino` | Clasificador maestro           |
| `columnas_cruce`  | Columnas de enlace             |
| `clasificador`    | DIVIPOLA, CUOC, CIIU, TEMPORAL |
| `tipo_cruce`      | CON_CLASIFICADOR               |
| `filas`           | Número de registros en archivo |

### 3. `INVENTARIO_CRUCES_COMPLETO.csv`

**524 archivos** con indicadores de cruce.

| Columna            | Descripción                                |
| ------------------ | ------------------------------------------ |
| `archivo`          | Ruta del archivo                           |
| `folder`           | Carpeta temática                           |
| `n_columnas`       | Número de columnas                         |
| `filas_reales`     | Número real de filas                       |
| `columnas_canon`   | Columnas normalizadas (separadas por `\|`) |
| `tiene_cruce_f2f`  | True si tiene cruce file-to-file           |
| `tiene_cruce_clas` | True si cruza con clasificador             |
| `sin_cruce`        | True si no tiene ningún cruce              |

---

## Clasificadores Disponibles

### DIVIPOLA (División Político-Administrativa)

- **Archivos maestros**: 7 archivos en `DIVIPOLA/`
- **Columnas de cruce**: `departamento`, `municipio`, `cod_departamento`, `cod_municipio`, `divipola`
- **Cobertura**: 250 archivos (89.1% de los datos)

### CIIU (Clasificación Industrial)

- **Archivos maestros**: 2 archivos en `CIIU_REV4/`
- **Columnas de cruce**: `sector_ciiu`, `ciiu`, `actividad_economica`, `codigo_ciiu`
- **Cobertura**: 45 archivos (28.4% de los datos)

### CUOC (Clasificación de Ocupaciones)

- **Archivos maestros**: 4 archivos en `CUOC/`
- **Columnas de cruce**: `ocupacion`, `codigo_cuoc`, `cno`
- **Cobertura**: 193 archivos (1.0% de los datos)

### TEMPORAL (Series de Tiempo)

- **Sin archivo maestro** (cruce por consistencia temporal)
- **Columnas de cruce**: `ano`, `year`, `fecha`, `periodo`, `trimestre`, `mes`
- **Cobertura**: 118 archivos (49.5% de los datos)

---

## Cobertura por Carpeta (Top 10)

| Carpeta            | Filas      | % del Total |
| ------------------ | ---------- | ----------- |
| INTELIGENTE        | 10,878,493 | 20.7%       |
| MEN                | 9,588,709  | 18.2%       |
| ECONOMIA           | 9,126,307  | 17.3%       |
| CONECTIVIDAD       | 3,202,333  | 6.1%        |
| SECOP_CONTRATACION | 2,739,357  | 5.2%        |
| DNP_PLANES         | 2,425,810  | 4.6%        |
| SALUD              | 2,406,686  | 4.6%        |
| RUES_CAMARAS       | 2,221,202  | 4.2%        |
| DESCUBIERTOS       | 2,077,723  | 3.9%        |
| ICFES_SABER        | 2,000,000  | 3.8%        |

---

## Archivos Sin Cobertura (52 archivos, 2.8M filas)

Estos archivos no tienen columnas compatibles con ningún clasificador:

| Carpeta               | Archivos | Filas | Motivo                                 |
| --------------------- | -------- | ----- | -------------------------------------- |
| DNP_PLANES_DESARROLLO | 5        | 1.4M  | Datos específicos de proyectos         |
| DNP                   | 2        | 1.3M  | Inversión pública con estructura única |
| DESCUBIERTOS          | 7        | 52K   | Fuentes externas variadas              |
| INTELIGENTE           | 13       | 25K   | Programas locales específicos          |
| OBSERVATORIO_SENA     | 10       | 6K    | Estructura no estándar                 |

---

## Uso Recomendado

### Para cruces FILE_TO_FILE:

```python
import pandas as pd

# Cargar catálogo
cruces = pd.read_csv('CRUCES_FILE_TO_FILE.csv')

# Filtrar por tipo
join_directo = cruces[cruces['tipo_viabilidad'] == 'JOIN_DIRECTO']

# Ejecutar un cruce
for _, row in join_directo.iterrows():
    df1 = pd.read_csv(f"_NORMALIZED/{row['archivo_origen']}")
    df2 = pd.read_csv(f"_NORMALIZED/{row['archivo_destino']}")
    cols = row['columnas_cruce'].split('|')
    merged = pd.merge(df1, df2, on=cols, how='outer')
```

### Para cruces CON_CLASIFICADOR:

```python
# Cargar cruces con clasificadores
cruces_clas = pd.read_csv('CRUCES_CON_CLASIFICADORES.csv')

# Cargar maestro DIVIPOLA
divipola = pd.read_csv('DIVIPOLA/DIVIPOLA_Maestro.csv')

# Enriquecer archivo
for _, row in cruces_clas[cruces_clas['clasificador'] == 'DIVIPOLA'].iterrows():
    df = pd.read_csv(f"_NORMALIZED/{row['archivo_origen']}")
    cols = row['columnas_cruce'].split('|')
    enriquecido = pd.merge(df, divipola, on=cols, how='left')
```

---

## Evolución del Análisis

| Fase                            | Cobertura | Archivos | Método                       |
| ------------------------------- | --------- | -------- | ---------------------------- |
| Inicial (Jaccard)               | 30.7%     | 64       | Similitud de columnas        |
| **Final (ML + Clasificadores)** | **94.7%** | **472**  | ML + Clasificadores maestros |

---

_Generado por: `Analisis_Cruces_ML_Normalized.ipynb`_
