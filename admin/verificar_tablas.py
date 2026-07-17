import duckdb

conn = duckdb.connect('D:/UniSabana_Dev/Dataset/DuckDB/repositorio.duckdb', read_only=True)

# Verificar columnas de tablas importantes que faltan en el mapeo
print('=== TABLAS IMPORTANTES NO EN MAPEO ===')

nuevas_tablas = [
    ('tendencias_tecnologicas', 'adopcion_ia_paises'),
    ('tendencias_tecnologicas', 'edtech_adopcion_paises'),
    ('tendencias_tecnologicas', 'industria40_paises'),
    ('tendencias_tecnologicas', 'mercado_ia_global'),
    ('indicadores_globales', 'bm_tasa_desempleo'),
    ('indicadores_globales', 'bm_participacion_fuerza_laboral'),
    ('indicadores_globales', 'bm_gasto_educacion_pib'),
    ('indicadores_globales', 'bm_pib_per_capita'),
    ('indicadores_globales', 'bm_usuarios_internet_pct'),
    ('microcredenciales', 'tendencias'),
    ('microcredenciales', 'mercado_global'),
    ('oecd_internacional', 'labour_statistics'),
    ('unesco_internacional', 'indicadores_educacion'),
    ('conectividad', 'internet_fijo_accesos'),
    ('competencias_tic', 'cobertura_móvil_por_tecnología_departamento_y_muni'),
]

for schema, tabla in nuevas_tablas:
    try:
        cols = conn.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{tabla}'").fetchdf()
        print(f'\n{schema}.{tabla}:')
        for c in cols['column_name'].tolist()[:10]:
            print(f'  - {c}')
    except Exception as e:
        print(f'{schema}.{tabla}: Error - {str(e)[:40]}')

conn.close()
