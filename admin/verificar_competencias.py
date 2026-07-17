import duckdb
conn = duckdb.connect('D:/UniSabana_Dev/Dataset/DuckDB/repositorio.duckdb', read_only=True)

# CUOC Conocimientos
print('=== CUOC CONOCIMIENTOS ===')
sample = conn.execute('SELECT * FROM competencias.cuoc_conocimientos LIMIT 10').fetchdf()
print(sample.to_string())
count = conn.execute("SELECT COUNT(*) FROM competencias.cuoc_conocimientos").fetchone()[0]
print(f'Total: {count}')

# CUOC Destrezas
print('\n=== CUOC DESTREZAS ===')
sample = conn.execute('SELECT * FROM competencias.cuoc_destrezas LIMIT 10').fetchdf()
print(sample.to_string())
count = conn.execute("SELECT COUNT(*) FROM competencias.cuoc_destrezas").fetchone()[0]
print(f'Total: {count}')

# Ver ocupaciones disponibles en competencias
print('\n=== OCUPACIONES CON COMPETENCIAS ===')
ocupaciones = conn.execute("""
    SELECT DISTINCT c.codigo_ocupacion, c.nombre_ocupacion
    FROM competencias.cuoc_conocimientos c
    ORDER BY c.codigo_ocupacion
    LIMIT 30
""").fetchdf()
print(ocupaciones.to_string())

# Ver competencias para código 2151
print('\n=== EJEMPLO: Competencias para 2151 ===')
conocimientos = conn.execute("""
    SELECT codigo_ocupacion, conocimiento 
    FROM competencias.cuoc_conocimientos 
    WHERE codigo_ocupacion = 2151
""").fetchdf()
print('Conocimientos:', conocimientos['conocimiento'].tolist() if not conocimientos.empty else 'No encontrado')

destrezas = conn.execute("""
    SELECT codigo_ocupacion, destreza 
    FROM competencias.cuoc_destrezas 
    WHERE codigo_ocupacion = 2151
""").fetchdf()
print('Destrezas:', destrezas['destreza'].tolist() if not destrezas.empty else 'No encontrado')

# Ver cómo se relaciona con NBC
print('\n=== MAPEO NBC -> OCUPACIONES CUOC ===')
mapeo = conn.execute("""
    SELECT NBC, Areas_Cualificacion_CUOC, N_Ocupaciones_CUOC
    FROM catalogo_curado.mapeo_nbc_cuoc
    WHERE N_Ocupaciones_CUOC > 0
    LIMIT 10
""").fetchdf()
print(mapeo.to_string())

conn.close()
