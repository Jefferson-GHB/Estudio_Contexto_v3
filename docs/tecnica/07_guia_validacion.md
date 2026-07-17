# Guia de Validacion

Procedimiento detallado para que evaluadores y pares puedan verificar, ejecutar y reproducir los resultados del Sistema de Analisis de Contexto.

---

## 1. Requisitos del Entorno

### 1.1 Software

| Componente | Version requerida | Verificacion |
|:-----------|:------------------|:-------------|
| Python | 3.13+ | `python --version` |
| DuckDB | 1.2+ (incluido en requirements.txt) | `pip show duckdb` |
| Git LFS | 2.0+ | `git lfs version` |
| Streamlit | 1.42+ | `streamlit version` |

### 1.2 Dependencias Python

Archivo: `requirements.txt` (13 dependencias)

```
streamlit>=1.30.0
duckdb>=1.0.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.18.0
google-generativeai>=0.3.0
sentence-transformers>=2.2.0
torch>=2.0.0
scikit-learn>=1.3.0
openpyxl>=3.1.0
python-docx>=1.0.0
```

Instalacion:

```bash
pip install -r requirements.txt
```

### 1.3 Base de Datos

- Archivo: `data/repositorio.duckdb`
- Tamaño: 703 MB
- Gestion: Git LFS
- Modo: Lectura exclusiva (read-only)

Si el repositorio se clono sin Git LFS, la base de datos debe descargarse manualmente:

```bash
git lfs pull --include="data/repositorio.duckdb"
```

### 1.4 Variables de Entorno

| Variable | Requerida para | Proposito |
|:---------|:---------------|:----------|
| `DUCKDB_PATH` | No (opcional) | Ruta personalizada a la base de datos |
| `GEMINIAPIKEY` | Si (para generación de informes IA) | API key de Google Gemini |
| `GOOGLEAPIKEY` | Si (alternativa) | API key de Google (alternativa a GEMINIAPIKEY) |
| `GITHUB_TOKEN` | No (opcional) | Token para GitHub API |
| `HUGGINGFACE_TOKEN` | No (opcional) | Token para HuggingFace Hub |

---

## 2. Ejecucion de Pruebas Automatizadas

### 2.1 Suite de Pruebas

| Aspecto | Valor |
|:--------|:------|
| Archivo | `tests/test_queries.py` |
| Lineas | 666 |
| Total de pruebas | 50 |
| Tipo | Integracion contra DuckDB real, sin mocks |
| Framework | Runner casero (no pytest) |

### 2.2 Comando de Ejecucion

```bash
python -m tests.test_queries
```

### 2.3 Interpretacion de Resultados

El script produce una salida estructurada con tres tipos de resultado:

```
[OK]   Nombre de la prueba  detalle
[FAIL] Nombre de la prueba  razon del fallo
[SKIP] Nombre de la prueba  razon de omision
```

Al finalizar, imprime un resumen:

```
TOTAL: 50 OK  |  0 FAIL  |  0 SKIP
```

**Codigo de salida:**
- `exit 0` = Todas las pruebas pasaron
- `exit 1` = Al menos una prueba fallo

### 2.4 Categorias de Pruebas

| Categoria | Numero de pruebas | Que validan |
|:----------|:------------------|:------------|
| Construccion de filtros | 8 | `build_where_clause`, `build_where_clause_matriculados`, `build_nbc_condition` con combinaciones de parametros NBC, departamento, modalidad, sector, nivel, carácter, campo amplio, área, estado |
| Consultas directas (programas) | 4 | `get_estadisticas_basicas`, `get_benchmarking_data`, `get_programas_detalle`, `get_desglose_academico` |
| Puente programas↔matriculados | 9 | `get_market_share`, `get_tendencia_matricula`, `get_graduados_historico`, `get_tendencia_inscritos`, `get_tendencia_admitidos`, `get_tendencia_primer_curso` — validan que el bridge via `COD_SNIES_PROGRAMA` funciona para filtros que no existen en las tablas destino |
| Explorador interactivo | 6 | `get_datos_explorador_interactivo` con combinaciones de Ano, Sexo, Departamento, Modalidad, Sector, Nivel, Campo Amplio |
| Comparativas | 2 | `get_comparativa_snies_siet_por_depto`, `get_comparativa_tipo_formacion` |
| SIET | 3 | `get_estadisticas_siet`, `get_desglose_siet`, `get_programas_detalle_siet` |
| Laboral (ML matching) | 6 | `get_vacantes_reales`, `get_competencias_cuoc`, `get_salarios_reales`, `get_graduados_nacionales`, `get_tendencia_laboral_nbc`, `get_graduados_nbc_historico` |
| Territorial | 2 | `get_conectividad_territorial`, `get_municipios_pdet` |
| Consistencia interna | 4 | Case sensitivity NBCs (UPPER), bridge match rate (porcentaje de COD_SNIES_PROGRAMA que hacen match), consistencia programas↔matriculados |
| Rendimiento | 3 | Benchmarks de tiempo para `get_estadisticas_basicas` (< 500ms), `get_market_share` (< 1000ms), `get_tendencia_matricula` (< 500ms) |

### 2.5 Valores de Prueba

Las pruebas utilizan valores reales extraidos de la base de datos:

| Parametro | Valor de prueba | Origen |
|:----------|:----------------|:-------|
| NBC | "Ingenieria de Sistemas" (o similar con LIKE '%SISTEMA%') | `snies.snies_programas` |
| Departamento | "BOGOTA D.C." | `snies.snies_programas` |
| Modalidad | "PRESENCIAL" | `snies.snies_programas` |
| Sector | "OFICIAL" o "PRIVADO" | `snies.snies_programas` |

---

## 3. Ejecucion de la Aplicacion Completa

### 3.1 Dashboard Streamlit

```bash
# 1. Clonar repositorio (incluye Git LFS)
git clone https://github.com/Jefferson-GHB/Estudio_Contexto_v3.git
cd Estudio_Contexto_v3

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python -m streamlit run app.py
```

### 3.2 Credenciales de Acceso

| Campo | Valor |
|:------|:------|
| Usuario | `admin` |
| Contrasena | `EstudioContexto2026!` |

En producción (HuggingFace Spaces), las credenciales se administran via `st.secrets` con hash SHA-256.

### 3.3 Demo en Linea

URL: `https://jeffersonca-estudio-contexto.hf.space/`

### 3.4 Flujo de Validacion Recomendado

Para validar el sistema completo, se sugiere el siguiente flujo:

1. **Autenticacion:** Ingresar con las credenciales proporcionadas
2. **Seleccion de filtros:** En el panel lateral, seleccionar:
   - Campo Amplio: "Ingenieria, Industria y Construccion"
   - Area: "Ingenieria, Arquitectura, Urbanismo y afines"
   - NBC: "Ingenieria de Sistemas"
   - Departamento: "BOGOTA D.C."
3. **Sintesis Academica:** Verificar que se muestren los indicadores HHI, CAGR, evolucion de matrícula, graduados
4. **Sintesis Laboral:** Verificar que se muestren vacantes APE, competencias CUOC, salarios
5. **Sintesis Territorial:** Verificar conectividad del departamento
6. **Decision Final:** Verificar el semaforo de decisión y la recomendacion de tipo de oferta
7. **Informe IA:** Si `GEMINIAPIKEY` esta configurada, generar informe de pertinencia

---

## 4. Reproducibilidad de Resultados

### 4.1 Consultas SQL Directas

Todas las consultas SQL estan parametrizadas en `data/queries.py`. Para reproducir un resultado especifico, se puede importar la funcion correspondiente:

```python
from data.queries import get_estadisticas_basicas

filtros = {
    "nbcs": ["Ingenieria de Sistemas"],
    "deptos": ["BOGOTA D.C."]
}
resultado = get_estadisticas_basicas(filtros=filtros)
print(resultado)
# {'total_programas': N, 'total_ies': M, 'costo_promedio': X, 'modalidades': Y}
```

### 4.2 Acceso Directo a DuckDB

```python
import duckdb
conn = duckdb.connect("data/repositorio.duckdb", read_only=True)

# Ejemplo: programas de un NBC especifico
nbc = "Ingenieria de Sistemas"
df = conn.execute(f'''
    SELECT "NOMBRE_INSTITUCION", "NOMBRE_DEL_PROGRAMA", "MODALIDAD", "DEPARTAMENTO_OFERTA_PROGRAMA"
    FROM snies.snies_programas
    WHERE "NUCLEO_BASICO_DEL_CONOCIMIENTO" = '{nbc}'
''').fetchdf()

conn.close()
```

### 4.3 Docker

```bash
docker build -t estudio-contexto .
docker run -p 7860:7860 \
  -e GEMINIAPIKEY=tu_api_key \
  estudio-contexto
```

---

## 5. Validacion Cruzada de Fuentes

Para verificar la trazabilidad de los datos, se pueden consultar las columnas de fuente en las tablas:

| Tabla | Columna de trazabilidad | Ejemplo de valor |
|:------|:------------------------|:-----------------|
| `snies.snies_matriculados` | `archivo_fuente` | `ESTUDIANTES_MATRICULADOS_2024.XLSX` |
| `snies.snies_graduados` | `archivo_fuente` | `ESTUDIANTES_GRADUADOS_2024.XLSX` |
| `snies.snies_inscritos` | `archivo_fuente` | `ESTUDIANTES_INSCRITOS_2024.XLSX` |
| `snies.snies_admitidos` | `archivo_fuente` | `ESTUDIANTES_ADMITIDOS_2024.XLSX` |
| `snies.snies_docentes` | `archivo_fuente` | `DOCENTES_2024.XLSX` |

Estas columnas contienen el nombre exacto del archivo descargado desde el portal SNIES del MEN.

Las URLs de descarga y metadata de cada fuente estan documentadas en `services/sources.py` (376 lineas) y en `docs/tecnica/05_fuentes_datos.md`.

---

## 6. Reporte de Issues

Si durante la validación se encuentra alguna inconsistencia, se debe reportar con:

1. El NBC, departamento y filtros utilizados
2. La sintesis evaluativa donde se observo el problema
3. El resultado esperado vs. el resultado obtenido
4. Captura de pantalla del dashboard (si aplica)

Los issues deben dirigirse al repositorio del proyecto: `https://github.com/Jefferson-GHB/Estudio_Contexto_v3`

---

*Documento generado a partir de `tests/test_queries.py` (666 lineas, 50 pruebas), `AGENTS.md` (seccion Testing), `Dockerfile` (30 lineas), `requirements.txt` (13 dependencias), `utils/auth.py`, `services/sources.py` (376 lineas), y `data/queries.py` (50+ funciones parametrizadas).*
