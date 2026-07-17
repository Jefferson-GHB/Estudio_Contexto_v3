import duckdb
conn = duckdb.connect('repositorio_hf.duckdb', read_only=True)

# Analizar las 4 tablas SNIES de estudiantes
tablas_analizar = [
    'snies.snies_inscritos',
    'snies.snies_admitidos', 
    'snies.snies_matriculados_primer_curso',
    'snies.snies_graduados',
    'snies.snies_matriculados'
]

for tabla in tablas_analizar:
    print(f"\n{'='*60}")
    print(f"TABLA: {tabla}")
    print('='*60)
    
    # Columnas
    cols = conn.execute(f"DESCRIBE {tabla}").fetchdf()
    print("\nCOLUMNAS:")
    print(cols[['column_name', 'column_type']].to_string(index=False))
    
    # Rango de años
    print("\nRANGO DE AÑOS:")
    try:
        anos = conn.execute(f'SELECT MIN("ANO") as min_ano, MAX("ANO") as max_ano, COUNT(*) as registros FROM {tabla}').fetchdf()
        print(anos.to_string(index=False))
    except:
        print("  Error al consultar años")
    
    # Muestra de NBC
    print("\nEJEMPLO NBCs disponibles:")
    try:
        nbcs = conn.execute(f'SELECT DISTINCT "NBC" FROM {tabla} WHERE "NBC" IS NOT NULL LIMIT 5').fetchdf()
        for nbc in nbcs['NBC'].values:
            print(f"  - {nbc}")
    except:
        print("  Error al consultar NBCs")

conn.close()
