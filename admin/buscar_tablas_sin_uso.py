"""Compare DB tables vs used tables and find candidates for deletion."""
import duckdb

# Tables used in code (from previous analysis)
used_tables = {
    'catalogo_curado.catalogo_nbc_snies', 'catalogo_curado.cualificaciones_men',
    'catalogo_curado.mapeo_cinef_detallado_siet', 'catalogo_curado.mapeo_cinef_snies_codigo',
    'catalogo_curado.mapeo_cuoc_area_cualificacion', 'catalogo_curado.mapeo_cuoc_ciiu',
    'catalogo_curado.mapeo_cuoc_cinef_amplio', 'catalogo_curado.mapeo_nbc_cuoc',
    'competencias.cuoc_conocimientos', 'competencias.cuoc_destrezas',
    'conectividad.cobertura_movil_tecnologia', 'conectividad.internet_fijo_accesos',
    'cuoc.cuoc_estructura_2025', 'cuoc.cuoc_limpio_2025', 'cuoc.perfilesocupacionales_excel_cuoc_2025',
    'datos_complementarios.graduados_nbc_ano', 'datos_complementarios.ole_ibc_rangos',
    'datos_complementarios.salarios_educacion_x_departamento', 'datos_complementarios.salarios_por_departamento',
    'datos_complementarios.salarios_por_nivel_educativo', 'datos_complementarios.tendencia_colocados_anual',
    'datos_complementarios.tendencia_inscritos_anual', 'datos_complementarios.tendencia_vacantes_anual',
    'divipola.divipola_departamentos', 'esco.skills_por_sector',
    'estadisticas_es.es_matricula_departamento', 'estadisticas_es.es_tcb_departamento', 'estadisticas_es.es_tti_departamento',
    'indicadores_globales.bm_desempleo_jovenes',
    'siet.siet_estudiantes_certificados_progr', 'siet.siet_instituciones', 'siet.siet_matricula_programa_', 'siet.siet_programas',
    'snies.snies_admitidos', 'snies.snies_graduados', 'snies.snies_inscritos', 'snies.snies_instituciones',
    'snies.snies_matriculados', 'snies.snies_matriculados_primer_curso', 'snies.snies_programas',
    'tendencias_laborales.vacantes_ape_clean',
    'tendencias_ocupacionales.colocados_anual_2024', 'tendencias_ocupacionales.inscritos_anual_2024',
    'tendencias_ocupacionales.vacantes_anual_2024', 'tendencias_ocupacionales.vacantes_s1_2025',
    'tendencias_tecnologicas.habilidades_futuro', 'territorial.municipios_pdet',
}

db = duckdb.connect(r'D:\UniSabana_Dev\Estudio_Contexto\repositorio.duckdb', read_only=True)

# Get all tables in DB
result = db.sql("""
    SELECT schema_name, table_name, estimated_size, 
           (SELECT count(*) FROM pg_tables WHERE schemaname = schema_name AND tablename = table_name) as row_count
    FROM duckdb_tables()
    ORDER BY estimated_size DESC
""").fetchall()

unused_tables = []
unused_size = 0

print("UNUSED TABLES (candidates for deletion):\n")
print(f"{'Schema.Table':<60} {'Size MB':>10} {'Rows':>12}")
print("-" * 85)

for schema, table, size, _ in result:
    full_name = f"{schema}.{table}".lower()
    # Skip essential schemas
    if schema.lower() in ['information_schema', 'pg_catalog', 'main']:
        continue
    
    if full_name not in used_tables:
        size_mb = (size or 0) / (1024*1024)
        unused_size += size_mb
        # Get actual row count
        try:
            row_count = db.execute(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]
        except:
            row_count = 0
        unused_tables.append((full_name, size_mb, row_count))
        print(f"{full_name:<60} {size_mb:>10.2f} {row_count:>12,}")

print("-" * 85)
print(f"{'TOTAL UNUSED':<60} {unused_size:>10.2f} MB")
print(f"\nTotal unused tables: {len(unused_tables)}")

# Show schemas with most unused data
print("\nUnused data by schema:")
from collections import defaultdict
by_schema = defaultdict(lambda: {'size': 0, 'count': 0})
for table, size, _ in unused_tables:
    schema = table.split('.')[0]
    by_schema[schema]['size'] += size
    by_schema[schema]['count'] += 1

for schema in sorted(by_schema.keys(), key=lambda s: by_schema[s]['size'], reverse=True):
    info = by_schema[schema]
    print(f"  {schema}: {info['count']} tables, {info['size']:.2f} MB")

db.close()

# Write SQL to delete these tables
with open(r'D:\UniSabana_Dev\_delete_unused_tables.sql', 'w') as f:
    f.write("-- SQL to delete unused tables\n")
    f.write("-- Total space to reclaim: {:.2f} MB\n\n".format(unused_size))
    for table, _, _ in unused_tables:
        schema, tbl = table.split('.')
        f.write(f'DROP TABLE IF EXISTS "{schema}"."{tbl}";\n')
    print(f"\nSQL script generated: _delete_unused_tables.sql")
