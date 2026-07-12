# Catálogos y Puente Estructural SNIES ↔ SIET

> Documento técnico — Julio 2026

## Qué hace este módulo

El sistema conecta dos ecosistemas educativos que el MEN mantiene separados: **SNIES** (educación formal universitaria) y **SIET** (educación para el trabajo). El puente se construye sobre la clasificación internacional **CINE-F 2013** de UNESCO, que ambos sistemas referencian pero con granularidad y nomenclatura distintas.

La cadena de resolución es:

```
NBC → Área de Conocimiento → CINE-F Campo Amplio → CINE-F Campo Detallado → Área de Desempeño SIET
```

El punto de articulación crítico está en **CINE-F Campo Detallado**: es la granularidad más fina donde SNIES y SIET comparten vocabulario. A partir de allí se proyectan las ocupaciones CUOC, los sectores CIIU, y las competencias laborales del Marco Nacional de Cualificaciones.

## Decisiones que definieron la arquitectura

**1. Catálogos ingeridos a DuckDB, no cargados con pandas en runtime**

Originalmente el bridge cargaba 2 CSVs (`MAPEO_CINEF_DETALLADO_SIET.csv` y `MAPEO_CINEF_SNIES_CODIGO.csv`) con `pd.read_csv()` en cada ejecución, los unía en Python y cacheaba en memoria global. Esto era frágil: cambios en los CSVs no se reflejaban hasta reiniciar, y la carga agregaba ~500ms al startup.

Se migró a SQL directo: los catálogos existen como tablas nativas en DuckDB (`catalogo_curado.*`), ingeridas una sola vez mediante scripts de administración. La consulta JOIN se hace en SQL, no en pandas. El resultado: cero dependencia de pandas en el hot path del bridge.

**2. NBCs corregidos como tabla prioritaria**

El catálogo oficial de NBCs tiene errores de origen: algunos NBCs no tienen mapeo a CINE-F o están asignados incorrectamente. Se creó `CATALOGO_NBC_SNIES_CORREGIDO.csv` con 57 correcciones manuales auditadas, ingerido como tabla `catalogo_nbc_snies_corregido`. La cadena estructural consulta primero esta tabla, y solo si no encuentra match cae en la tabla original. Esto permite corregir el sistema sin modificar los datos fuente.

**3. Matching ML como complemento, no como único camino**

El puente estructural (NBC → SIET vía CINE-F) funciona para ~85% de los NBCs. Para el 15% restante — NBCs con nombres ambiguos, áreas interdisciplinarias, o catálogos incompletos — se activa el matching semántico con `paraphrase-multilingual-MiniLM-L12-v2`. El modelo codifica el nombre del NBC y todas las áreas SIET, calcula cosine similarity, y selecciona las mejores coincidencias.

Esta arquitectura dual (determinista + ML) evita el problema de "caja negra" que tendría un sistema puramente basado en embeddings, mientras mantiene cobertura para casos edge.

**4. Audición automatizada de divergencias**

Cada vez que se actualizan los catálogos fuente, el script `admin/auditar_catalogos.py` compara los CSVs contra las tablas DuckDB y genera un reporte de divergencias. Esto detecta desincronización entre fuentes antes de que afecte al usuario final.

## Estructura de archivos relevantes

| Archivo | Rol |
|---------|-----|
| `data/filters.py` | `resolver_nbcs_desde_filtros()` — construye la cascada desde cualquier punto de entrada (NBC, Área, Campo Amplio, o búsqueda textual) |
| `services/ml/snies_etdh.py` | `_resolve_structural_chain()` — implementa la cadena NBC→SIET con prioridad corregida y fallback ML |
| `services/ml/matching.py` | `match_nbc_to_ocupaciones()`, `match_nbc_to_vacantes()` — matching semántico con MiniLM para vacantes APE y ocupaciones CUOC |
| `data/queries.py:1968-2326` | `get_vacantes_reales()`, `get_tendencia_laboral_nbc()` — consultas laborales que consumen el bridge |
| `catalogo/` | CSVs fuente de todos los mapeos (26 archivos) |
| `admin/` | Scripts de ingesta, auditoría y evaluación de modelos |

## Flujo de datos en una consulta típica

1. Usuario selecciona "Enfermería" en el sidebar → `resolver_nbcs_desde_filtros()` extrae NBCs de programas SNIES que contienen ese nombre
2. `_resolve_structural_chain("Enfermería")` busca en `catalogo_nbc_snies_corregido` → obtiene CINE-F "Salud y Bienestar" → mapea a Área SIET "Salud"
3. Las queries de SIET reciben el filtro de áreas de desempeño y retornan solo programas, matrículas y certificados del sector salud
4. Simultáneamente, `match_nbc_to_vacantes("Enfermería")` codifica semánticamente el NBC y encuentra ocupaciones CUOC como "Auxiliares en enfermería", "Enfermeros", etc.
5. El tablero muestra ambos mundos alineados: oferta académica + demanda laboral para el mismo campo

## Limitaciones conocidas

- El catálogo CUOC de cualificaciones MEN tiene solo 396 registros (cobertura parcial). Las cualificaciones específicas de algunos NBCs pueden no existir aún en el marco oficial.
- La tabla de CINE-F en SIET usa nombres de área de desempeño que a veces difieren de los nombres CINE-F estándar. Los 11 mapeos hardcodeados en `snies_etdh.py` cubren estas discrepancias conocidas.
- El modelo MiniLM es multilingüe pero pequeño (120 MB). Para matching de ocupaciones muy especializadas, el threshold debe ser conservador para evitar falsos positivos.
