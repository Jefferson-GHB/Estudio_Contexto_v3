# Laboratorio ML/IA - Repositorio Analitico de Decision Institucional

**Fecha de creación:** 2026-01-12  
**Última actualización:** 2026-01-13  
**Notebook fuente:** `Complemento_ML_IA.ipynb`  
**Filosofía:** "ML/IA apoya, no gobierna" - Los resultados son insumos para decisión humana

---

## Objetivo

Construir un **Repositorio Analítico de Decisión Institucional** para el análisis de pertinencia educativa, soportando la toma de decisiones estratégicas para programas virtuales. El repositorio integra 560 archivos normalizados, clasificados en 6 comunidades Leiden y alineados con 8 dominios funcionales.

---

## Enfoques Probados

### 1) Similaridad de Jaccard (Linea Base)

**Técnica:** Coeficiente de Jaccard sobre conjuntos de columnas  
**Implementación:** Comparación pairwise de 482 archivos

| Métrica                         | Valor      |
| ------------------------------- | ---------- |
| Pares similares (Jaccard ≥ 0.3) | 11,442     |
| Pares cross-folder              | 557 (4.9%) |
| Umbral usado                    | 0.3        |

**Utilidad:** Identificar datasets con esquemas compatibles para cruces directos.

---

### 2) TF-IDF + Clustering Jerarquico

**Técnica:** Vectorización TF-IDF de columnas + Ward linkage  
**Implementación:** scikit-learn TfidfVectorizer + scipy hierarchical clustering

| Métrica             | Valor                          |
| ------------------- | ------------------------------ |
| Clusters formados   | 20                             |
| Cohesión promedio   | 0.527                          |
| Cluster más grande  | #19 (144 archivos)             |
| Cluster más diverso | #10 (136 archivos, 20 folders) |

**Utilidad:** Agrupar datasets por "familia" de estructura/esquema.

---

### 3) Grafos de Co-ocurrencia + Louvain

**Técnica:** Grafo bipartito archivo-columna → proyección → detección de comunidades  
**Implementación:** NetworkX + algoritmo Louvain

| Métrica                | Valor            |
| ---------------------- | ---------------- |
| Nodos en grafo         | 482 archivos     |
| Aristas                | 9,078 conexiones |
| Componente gigante     | 274 archivos     |
| Comunidades detectadas | 5                |

**Comunidades Identificadas:**

| ID  | Archivos | Folders | Característica Principal              |
| --- | -------- | ------- | ------------------------------------- |
| 0   | 25       | 3       | Internacional (país, indicador)       |
| 1   | 77       | 13      | Educativa (programa, modalidad)       |
| 2   | 87       | 19      | Territorial (municipio, departamento) |
| 3   | 44       | 16      | Institucional mixta                   |
| 4   | 41       | 5       | Empresarial (sector_ciiu, empresa)    |

**Utilidad:** Detectar agrupaciones naturales sin parámetros a priori.

---

### 5) Algoritmo Leiden (PRODUCCION - Enero 2026)

**Técnica:** Algoritmo Leiden con resolución optimizada para detección de comunidades de alta calidad  
**Implementación:** `leidenalg` + `igraph` sobre grafo de similaridad de columnas y conceptos

| Métrica                  | Valor          |
| ------------------------ | -------------- |
| Nodos en grafo           | 560 archivos   |
| Aristas                  | 33,069         |
| Resolución usada         | 1.2            |
| Modularidad              | 0.3426         |
| Comunidades iniciales    | 19             |
| Comunidades consolidadas | 6              |
| Cobertura                | 100% (560/560) |

**Comunidades Leiden Consolidadas:**

| Com | Archivos | %     | Carpetas Principales                       |
| --- | -------- | ----- | ------------------------------------------ |
| 0   | 323      | 57.7% | DESCUBIERTOS, INTELIGENTE, RUES, MEN, DANE |
| 1   | 120      | 21.4% | OBSERVATORIO_SENA_TENDENCIAS, SENA         |
| 2   | 61       | 10.9% | OBSERVATORIO_SENA_TENDENCIAS               |
| 3   | 24       | 4.3%  | ESTADISTA_ES, EDUCACION, MEN               |
| 4   | 23       | 4.1%  | BANCO_MUNDIAL, CTI                         |
| 5   | 9        | 1.6%  | CUOC, CIIU (clasificadores)                |

**Utilidad:** Agrupación de alta calidad con garantía de convergencia local óptima.

---

## Alineacion con 8 Dominios Funcionales

El repositorio está mapeado a los 8 dominios funcionales definidos por el coordinador del proyecto:

| Dominio                     | Archivos | Carpetas Clave                                  | Externos Clave                               |
| --------------------------- | -------- | ----------------------------------------------- | -------------------------------------------- |
| **Decisión Institucional**  | 198      | INTELIGENTE, RUES, EMPRESAS, MIPYMES            | CIIU_Rev4_Limpio, CINE_F_Limpio              |
| **Oferta Comparada**        | 190      | OBSERVATORIO_SENA_TENDENCIAS, SENA              | Consolidado_SIET_2023                        |
| **Académico-Formativo**     | 71       | MEN, ESTADISTA_ES, GRADUADOS_IES, PROGRAMAS_IES | SNIES (7 archivos), Instituciones, Programas |
| **Territorial-Social**      | 35       | POBLACION, DANE, CULTURA, SALUD, TERRITORIAL    | -                                            |
| **Global-Tendencias**       | 25       | BANCO_MUNDIAL, BANREP, ECONOMIA                 | -                                            |
| **Normativo-Institucional** | 16       | DNP, DNP_PLANES_DESARROLLO, SECOP               | -                                            |
| **Ocupacional-Laboral**     | 14       | EMPLEO, LABORAL, EMPLEADORES, SERVICIO_EMPLEO   | CUOC_Limpio_2025                             |
| **Competencias**            | 11       | CTI, SENA_COMPETENCIAS                          | -                                            |

**Cobertura:** 8/8 dominios cubiertos (100%)

---

## Archivos Externos Clave (13 archivos LIMPIO)

Archivos normalizados fuera de `Descargas_Automaticas/` que funcionan como filtradores y clasificadores:

### SNIES (Académico-Formativo)

| Archivo                                         | Ubicación                | Uso                       |
| ----------------------------------------------- | ------------------------ | ------------------------- |
| SNIES_Admitidos_Consolidado.csv                 | SNIES/consolidado        | Filtrar admitidos por IES |
| SNIES_Matriculados_Consolidado.csv              | SNIES/consolidado        | Filtrar matriculados      |
| SNIES_Graduados_Consolidado.csv                 | SNIES/consolidado        | Filtrar graduados         |
| SNIES_Inscritos_Consolidado.csv                 | SNIES/consolidado        | Filtrar inscritos         |
| SNIES_Docentes.csv                              | SNIES/consolidado        | Personal docente          |
| SNIES_Administrativos.csv                       | SNIES/consolidado        | Personal administrativo   |
| SNIES_Matriculados_Primer_Curso_Consolidado.csv | SNIES/consolidado        | Primer curso              |
| Instituciones.xlsx                              | SNIES/SNIES_Programa_IES | Catálogo IES              |
| Programas.xlsx                                  | SNIES/SNIES_Programa_IES | Catálogo programas        |

### Clasificadores

| Archivo                 | Ubicación    | Uso                                   |
| ----------------------- | ------------ | ------------------------------------- |
| CUOC_Limpio_2025.xlsx   | CUOC/        | Clasificador Único de Ocupaciones     |
| CIIU_Rev4_Limpio.xlsx   | CIIU_REV4/   | Clasificador Industrial Internacional |
| CINE_F_Limpio_2024.xlsx | Clas_CINE_F/ | Clasificación campos educativos       |

### SIET

| Archivo                    | Ubicación | Uso                           |
| -------------------------- | --------- | ----------------------------- |
| Consolidado_SIET_2023.xlsx | SIET/     | Oferta formación técnica SENA |

---

### 4) Word2Vec Embeddings

**Técnica:** Skip-gram sobre secuencias de columnas  
**Implementación:** Gensim Word2Vec

| Métrica     | Valor       |
| ----------- | ----------- |
| Vocabulario | 71 columnas |
| Dimensiones | 50          |
| Window size | 5           |
| Min count   | 3           |

**Relaciones Semánticas Aprendidas:**

```
programa → modalidad (sim: 0.89)
sector_ciiu → empresa (sim: 0.85)
municipio → departamento (sim: 0.91)
año → periodo (sim: 0.78)
```

**Utilidad:** Encontrar columnas semánticamente relacionadas para sugerir equivalencias.

---

## Archivos Puente (Alta Conectividad Cross-Domain)

Los siguientes archivos tienen mayor número de conexiones con otros folders, ideales para cruces:

| Archivo                                       | Conexiones Cross-Folder | Columnas Clave                 |
| --------------------------------------------- | ----------------------- | ------------------------------ |
| MEN/Deserción_académica_1-2019.csv            | 31                      | estrato, estado, modalidad     |
| MEN/Deserción_no_académica_1-2019.csv         | 31                      | estrato, estado, modalidad     |
| INTELIGENTE/Pasantías_y_practicas\*.csv       | 28                      | programa, modalidad, facultad  |
| GRADUADOS_IES/Graduados_Pregrado_Posgrado.csv | 24                      | programa, modalidad, graduados |

---

## Columnas Clave para Cruces

Columnas que más aparecen en pares cross-folder válidos:

| Columna      | Pares donde aparece |
| ------------ | ------------------- |
| total        | 325                 |
| programa     | 237                 |
| nombre       | 213                 |
| genero       | 212                 |
| modalidad    | 198                 |
| municipio    | 184                 |
| departamento | 154                 |
| año          | 149                 |
| tipo         | 130                 |
| periodo      | 100                 |

---

## Artefactos Generados

| Archivo                        | Descripción                                         | Registros |
| ------------------------------ | --------------------------------------------------- | --------- |
| `ARCHIVOS_METADATOS_ML.csv`    | Cada archivo con cluster TF-IDF y comunidad Louvain | 482       |
| `CRUCES_RECOMENDADOS_ML.csv`   | Pares cross-folder con Jaccard ≥ 0.5                | 99        |
| `COMUNIDADES_LOUVAIN_ML.json`  | Detalle de 5 comunidades con miembros               | 5         |
| `EMBEDDINGS_COLUMNAS_W2V.json` | Vectores 50D para columnas frecuentes               | 71        |

### Artefactos Leiden (Enero 2026)

| Archivo                         | Descripción                                        | Registros |
| ------------------------------- | -------------------------------------------------- | --------- |
| `ARCHIVOS_METADATOS_ML.csv`     | Metadatos con comunidad Leiden y dominio funcional | 560       |
| `COMUNIDADES_LEIDEN_ML.json`    | Detalle de 6 comunidades consolidadas              | 6         |
| `REPORTE_ALINEACION_FINAL.json` | Alineación con 8 dominios del coordinador          | 8         |

---

## Conclusiones

### Lo que Funciona

1. **Jaccard canónico** es excelente para identificar pares específicos de cruce
2. **Louvain** detecta comunidades temáticas sin necesidad de definir K
3. **Word2Vec** captura relaciones semánticas implícitas
4. **TF-IDF clustering** agrupa por "familia" de estructura
5. **Leiden** (PRODUCCIÓN) mejora Louvain con convergencia garantizada y mayor modularidad

### Limitaciones

1. **Word2Vec** requiere más datos para vocabulario robusto (solo 71 de 2,830 columnas)
2. **Sentence-transformers** no disponible por conflicto Keras 3
3. **HDBSCAN/UMAP** no instalados en el ambiente

### Recomendación

**Combinar enfoques:**

- Usar **Leiden** para organización temática general (PRODUCCIÓN)
- Usar **Jaccard** para matching de alta precisión
- Usar **embeddings** para sugerir equivalencias nuevas
- Mapear a **dominios funcionales** para alineación estratégica

---

## Integracion con Fase 1.2

Los resultados de este laboratorio complementan la ontología semántica:

```
Fase 1.2 (Ontología)          +    Laboratorio ML/IA (Leiden)
─────────────────────              ──────────────────────────
42 conceptos definidos             6 comunidades Leiden
611 mappings manuales              8 dominios funcionales
89.9% clasificación                560 archivos indexados
                                   33,069 conexiones en grafo
                                   100% cobertura archivos
```

**Estado actual:** Repositorio completo para soportar 34 programas virtuales.

---

## Mapeos Criticos

### CARPETA_A_DOMINIO

```python
CARPETA_A_DOMINIO = {
    # Académico-Formativo
    "MEN": "Académico-Formativo",
    "MEN_ESTADISTICAS": "Académico-Formativo",
    "ICFES_SABER": "Académico-Formativo",
    "GRADUADOS_IES": "Académico-Formativo",
    "PROGRAMAS_IES": "Académico-Formativo",
    "OLE": "Académico-Formativo",
    "ESTADISTA_ES": "Académico-Formativo",
    "SNIES": "Académico-Formativo",
    "EDUCACION": "Académico-Formativo",

    # Normativo-Institucional
    "DNP": "Normativo-Institucional",
    "DNP_PLANES_DESARROLLO": "Normativo-Institucional",
    "SECOP_CONTRATACION_PUBLICA": "Normativo-Institucional",

    # Oferta Comparada
    "SENA": "Oferta Comparada",
    "SENA_FORMACION": "Oferta Comparada",
    "OBSERVATORIO_SENA_TENDENCIAS": "Oferta Comparada",
    "SIET": "Oferta Comparada",

    # Ocupacional-Laboral
    "SERVICIO_PUBLICO_EMPLEO": "Ocupacional-Laboral",
    "EMPLEO": "Ocupacional-Laboral",
    "MERCADO_LABORAL": "Ocupacional-Laboral",
    "LABORAL": "Ocupacional-Laboral",
    "EMPLEADORES": "Ocupacional-Laboral",
    "CUOC": "Ocupacional-Laboral",

    # Competencias
    "SENA_COMPETENCIAS": "Competencias",
    "CTI": "Competencias",

    # Territorial-Social
    "POBLACION": "Territorial-Social",
    "SALUD": "Territorial-Social",
    "CULTURA": "Territorial-Social",
    "TERRITORIAL": "Territorial-Social",
    "CONECTIVIDAD": "Territorial-Social",
    "MINTIC": "Territorial-Social",
    "DANE": "Territorial-Social",
    "DANE_INDICADORES": "Territorial-Social",

    # Global-Tendencias
    "BANCO_MUNDIAL": "Global-Tendencias",
    "BANREP": "Global-Tendencias",
    "ECONOMIA": "Global-Tendencias",

    # Decisión Institucional
    "EMPRESAS": "Decisión Institucional",
    "MIPYMES_ESTRUCTURA_EMPRESARIAL": "Decisión Institucional",
    "RUES_CAMARAS_COMERCIO": "Decisión Institucional",
    "INTELIGENTE": "Decisión Institucional",
    "CIIU": "Decisión Institucional",
    "DESCUBIERTOS": "Decisión Institucional",
}
```

### ARCHIVOS_EXTERNOS_CLAVE

```python
ARCHIVOS_EXTERNOS_CLAVE = {
    "CUOC": "CUOC/CUOC_Limpio_2025.xlsx",
    "CIIU": "CIIU_REV4/CIIU_Rev4_Limpio.xlsx",
    "CINE_F": "Clas_CINE_F/CINE_F_Limpio_2024.xlsx",
    "SNIES_Admitidos": "SNIES/consolidado/SNIES_Admitidos_Consolidado.csv",
    "SNIES_Matriculados": "SNIES/consolidado/SNIES_Matriculados_Consolidado.csv",
    "SNIES_Graduados": "SNIES/consolidado/SNIES_Graduados_Consolidado.csv",
    "SNIES_Inscritos": "SNIES/consolidado/SNIES_Inscritos_Consolidado.csv",
    "SNIES_Docentes": "SNIES/consolidado/SNIES_Docentes.csv",
    "SNIES_Administrativos": "SNIES/consolidado/SNIES_Administrativos.csv",
    "SNIES_PrimerCurso": "SNIES/consolidado/SNIES_Matriculados_Primer_Curso_Consolidado.csv",
    "Instituciones": "SNIES/SNIES_Programa_IES/Instituciones.xlsx",
    "Programas": "SNIES/SNIES_Programa_IES/Programas.xlsx",
    "SIET": "SIET/Consolidado_SIET_2023.xlsx"
}
```

---

## Dependencias Verificadas

```python
sklearn      OK  TfidfVectorizer, AgglomerativeClustering
networkx     OK  Graph, community_louvain
gensim       OK  Word2Vec
scipy        OK  hierarchical clustering
pandas       OK  DataFrames
leidenalg    OK  Leiden algorithm (NUEVO)
igraph       OK  Graph representation (NUEVO)
```

---

## Estructura de Archivos Generados

```
./Dataset/
├── ARCHIVOS_METADATOS_ML.csv          # 560 registros, columnas: archivo, folder, comunidad_leiden, dominio_funcional
├── COMUNIDADES_LEIDEN_ML.json         # 6 comunidades con metadata y archivos
├── REPORTE_ALINEACION_FINAL.json      # 8 dominios con status y archivos
├── INVENTARIO_REPOSITORIO_FINAL.csv   # Inventario completo
└── _CATALOGO_CURADO/
    └── README_LABORATORIO_ML_IA.md    # Esta documentación
```

---

## Historico de Cambios

| Fecha      | Cambio                                                  |
| ---------- | ------------------------------------------------------- |
| 2026-01-12 | Creación inicial con Jaccard, TF-IDF, Louvain, Word2Vec |
| 2026-01-13 | Migración a Leiden, integración 13 externos, 8 dominios |

---

_Documentación generada desde Complemento_ML_IA.ipynb_
