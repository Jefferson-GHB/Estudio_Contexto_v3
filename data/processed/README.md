# Datos procesados (processed)

Los datos transformados y limpios residen en el repositorio DuckDB (`data/repositorio.duckdb`), no como archivos independientes en este directorio.

## Procesos aplicados

1. **Extraccion diferenciada** desde fuentes oficiales y repositorios descargables
2. **Estandarizacion** de nombres, formatos, períodos, codigos y unidades de análisis
3. **Homologacion** con clasificaciones CINE-F, NBC, CUOC, CIIU, MNC y DIVIPOLA
4. **Depuracion** de duplicados, control de campos nulos y validación de consistencia entre tablas
5. **Carga** en estructuras DuckDB para consultas SQL, visualización y recuperación aumentada

## Catalogos curados

Los catalogos de mapeo que habilitan los cruces entre dominios (educación, trabajo, territorio) se almacenan en `catalogo/` (26 archivos CSV/JSON) y en `catalogo_curado.*` dentro de DuckDB.

Ver `docs/tecnica/04_marco_metodologico.md` para el detalle de la metodología CRISP-ML aplicada.
