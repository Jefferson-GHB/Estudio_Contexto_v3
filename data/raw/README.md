# Datos crudos (raw)

Los datos fuente originales se almacenan en DuckDB (`data/repositorio.duckdb`, 703 MB), no como archivos sin procesar en este directorio.

## Procedencia de los datos

Los datos crudos provienen de descargas directas de los portales oficiales y de la API Socrata (`datos.gov.co`):

- **SNIES** (`snies.*`): Archivos XLSX descargados de `https://snies.mineducacion.gov.co/` — programas, matriculados, graduados, inscritos, admitidos, docentes, administrativos, instituciones
- **SIET** (`siet.*`): Datos de `https://siet.mineducacion.gov.co/` — educación para el trabajo y desarrollo humano
- **Portal datos.gov.co** (`datos_gov_co.*`, `dane_socrata.*`, `men_estadisticas.*`, `estadisticas_es.*`, `empleo_publico.*`): Datasets del portal de datos abiertos del Estado colombiano via API Socrata
- **ICFES** (`icfes_saber.*`, `men.*`): Resultados pruebas Saber PRO, Saber TYT, Saber 11
- **SENA** (`competencias.*`, `sena.*`, `tendencias_laborales.*`): Agencia Publica de Empleo, formación profesional integral, mesas sectoriales
- **Banco Mundial** (`banco_mundial.*`, `indicadores_globales.*`): Indicadores de desarrollo global
- **OECD, UNESCO, ILO, ESCO**: Estadisticas internacionales comparativas

## Estructura del repositorio DuckDB

El repositorio DuckDB (`data/repositorio.duckdb`) contiene 56 esquemas con ~316 tablas. La documentación detallada de cada fuente se encuentra en `docs/tecnica/05_fuentes_datos.md`.

## Actualizacion

Los scripts de ingestion en `admin/ingestar_*.py` documentan el proceso de extraccion desde cada fuente original. Los scripts de auditoria en `admin/auditar_*.py` verifican la consistencia entre catalogos y fuentes.
