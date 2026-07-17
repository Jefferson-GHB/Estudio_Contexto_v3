# Estado de Ingesta y Regenerabilidad

Documento que clasifica cada esquema del repositorio DuckDB segun el método
de obtencion de sus datos y la disponibilidad de scripts para regenerarlos.

---

## Metodos de ingesta

Los datos del repositorio se obtuvieron por tres vias complementarias. Los scripts
en `admin/ingestar_*.py` son **ejemplos ejecutables representativos** de la
metodología ETL para cada tipo de fuente. Cada script demuestra el patron completo:
descarga/lectura → validación → normalización → carga → verificacion.

| Via | Codigo | Descripcion | Scripts representativos |
|:----|:-------|:------------|:------------------------|
| **A. API / Portal oficial** | A | Datos obtenidos via API publica o XLSX descargable de portal oficial con formato estable. Totalmente automatizable. | `ingestar_snies.py`, `ingestar_socrata.py`, `ingestar_internacional.py` |
| **B. Descarga manual** | B | Datos de portales sin API, con formatos cambiantes, que requieren descarga interactiva desde el portal web oficial. Los archivos fuente originales se conservan en `data/raw/`. | — (procedimiento documentado en cada fuente) |
| **C. Compilacion / Curacion** | C | Datasets construidos por el equipo a partir de fuentes oficiales: catalogos normalizados, mapeos entre clasificadores (NBC↔CUOC↔CIIU↔MNC), compilaciones historicas. | `ingestar_catalogos.py` |

El orquestador `pipelines/pipeline_etl.py` ejecuta los scripts de la via A en orden.
Las vias B y C se documentan en `data/raw/README.md` y `data/external/README.md`
respectivamente.

---

## Clasificacion por esquema

### Grupo A — Portal datos.gov.co (Socrata API)

| Esquema | Via | Tablas | Script | Notas |
|:--------|:----|:-------|:-------|:------|
| `conectividad` | A | 2 | `ingestar_socrata.py` | Internet fijo (1.6M) y cobertura movil. Datasets mapeados en script |
| `dane_socrata` | A + B | 10 | `ingestar_socrata.py` (2 datasets) | Proyecciones y GEIH via API Socrata. Tablas complementarias por descarga manual |
| `datos_gov_co` | B | 7 | — | Datasets con formato no estandarizado. Descarga manual documentada en `services/sources.py` |
| `men_estadisticas` | A | 3 | `ingestar_socrata.py` (2 datasets) | Matricula estadística via API Socrata |
| `estadisticas_es` | A + B | 21 | `ingestar_socrata.py` (3 datasets) | Desercion, TCB, TTI via API. Datasets históricos complementarios por descarga manual |
| `empleo_publico` | A + B | 30 | `ingestar_socrata.py` (1 dataset) | SIGEP salarios via API. Datasets adicionales por descarga manual |
| `mintic` | A + B | 6 | `ingestar_socrata.py` (1 dataset) | Gobierno digital via API. Complementos por descarga manual |
| `dnp_planes_desarrollo` | A + B | 7 | `ingestar_socrata.py` (1 dataset) | MDM via API. Planes de desarrollo complementarios por descarga manual |
| `tendencias_laborales` | B + C | 142 | `ingestar_ape.py` (dataset consolidado) | Vacantes APE consolidadas desde archivos históricos. Tablas trimestrales (~140) por compilacion manual de los reportes publicados por el SENA |

### Grupo B — Portales MEN / ICFES (descarga directa)

| Esquema | Via | Tablas | Script | Notas |
|:--------|:----|:-------|:-------|:------|
| `snies` | A | 8 | `ingestar_snies.py` | XLSX descargables del portal SNIES. El script cubre programas, matriculados, graduados, inscritos, admitidos y primer curso |
| `siet` | B | 6 | — | Portal SIET sin API publica. Descarga manual. Estructura documentada en `data/raw/siet/` |
| `icfes_saber` | B | 4 | — | Archivos de resultados Saber PRO descargados del portal ICFES. Formato documentado en `services/sources.py` |
| `men` | B | 2 | — | Dataset complementario MEN. Descarga manual |

### Grupo C — Fuentes internacionales

| Esquema | Via | Tablas | Script | Notas |
|:--------|:----|:-------|:-------|:------|
| `indicadores_globales` | A + B | 22 | `ingestar_internacional.py` | Banco Mundial via API. Script cubre ~15 indicadores. Resto via descarga manual del portal de datos abiertos del BM |
| `banco_mundial` | B | 22 | — | Respaldo histórico (duplicado de indicadores_globales). Segunda ronda de ingesta independiente |
| `oecd_internacional` | B | 2 | — | Descarga manual del portal estadístico OECD |
| `unesco_internacional` | B | 3 | — | Descarga manual del portal UIS UNESCO |
| `ilo_internacional` | B | 2 | — | Descarga manual del portal ILOSTAT |
| `esco` | B | 2 | — | Descarga manual del portal ESCO (habilidades europeas) |

### Grupo D — Catalogos curados

| Esquema | Via | Tablas | Script | Notas |
|:--------|:----|:-------|:-------|:------|
| `catalogo_curado` | C | 7+ | `ingestar_catalogos.py` | CSVs desde `catalogo/`. NBC corregido (57 filas), mapeo de variables (114), MNC (396), y catalogos derivados |
| `clasificadores` | C | 5 | `ingestar_catalogos.py` | CUOC (14,462), CIIU Rev.4 (700), CINE-F (10,431). CSVs curados desde fuentes oficiales |
| `divipola` | C | 1+ | `ingestar_territorial.py` | Codificacion DIVIPOLA DANE (1,122 municipios) |
| `territorial` | B + C | 4+ | `ingestar_territorial.py` | Conectividad, PDET, desempeno municipal. Combinacion de API Socrata y compilacion de fuentes oficiales |

---

## Resumen de cobertura

| Grupo | Total tablas | Scripts representativos | Metodo predominante |
|:------|:------------|:------------------------|:--------------------|
| A (datos.gov.co) | ~188 | `ingestar_socrata.py` (13 datasets mapeados) | API Socrata + descarga manual complementaria |
| B (MEN/ICFES) | 18 | `ingestar_snies.py` (5 tablas SNIES) | XLSX + descarga manual |
| C (internacionales) | 60 | `ingestar_internacional.py` (API Banco Mundial) | API + descarga manual de portales |
| D (catalogos) | ~200 | `ingestar_catalogos.py` (7 catalogos) | CSV curados desde fuentes oficiales |
| **Total** | **488** | **6 scripts, ~30 datasets mapeados** | — |

---

## Nota sobre regenerabilidad

Los scripts en `admin/` cubren los datasets principales que alimentan el dashboard
en producción. Para los datasets complementarios (descarga manual), los archivos
fuente se conservan en `data/raw/` y su procedencia esta documentada en
`docs/tecnica/05_fuentes_datos.md` con URLs especificas y fechas de descarga
registradas en `services/sources.py`.

El patron de ingenieria ETL es uniforme en todos los scripts: la funcion
`ingestar_*()` recibe un directorio de archivos fuente (o parametros de API),
valida contra catalogos, normaliza columnas, carga en el esquema DuckDB
correspondiente y verifica el conteo final. Este mismo patron se aplica a
cualquier fuente adicional que requiera regeneracion.

---

*Documento generado a partir de la auditoria del repositorio DuckDB (54 esquemas, 488 tablas), los scripts en `admin/ingestar_*.py` (6 archivos, ~1,100 lineas), `pipelines/pipeline_etl.py`, `services/sources.py` (376 lineas), y los directorios `data/raw/` y `data/external/`.*