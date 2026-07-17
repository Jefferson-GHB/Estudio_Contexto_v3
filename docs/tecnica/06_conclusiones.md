# Conclusiones, Limitaciones y Proximos Pasos

Hallazgos del piloto del Sistema de Analisis de Contexto, limitaciones actuales identificadas por el equipo, y ruta de evolucion del proyecto.

---

## 1. Hallazgos Principales

### 1.1 Sobre la Integracion de Fuentes

La construccion del repositorio unificado DuckDB (703 MB, 54 esquemas, 488 tablas) demuestra que es viable integrar datos de fuentes oficiales colombianas —SNIES, SIET, APE, CUOC, GEIH, ICFES, DNP, SENA, MinTIC, DANE— con clasificadores internacionales —CINE-F, CIIU, ESCO— en un solo motor analitico. El esfuerzo de armonizacion, que incluyo la homologacion con NBC, CUOC, MNC y DIVIPOLA, permite que los datos dialoguen entre si en lugar de operar como silos.

La suite de 50 pruebas automatizadas contra datos reales (`tests/test_queries.py`, 666 lineas) valida que los cruces entre fuentes son consistentes y que el sistema de filtros en cascada produce resultados correctos bajo distintas combinaciones de parametros.

### 1.2 Sobre los Indicadores de Pertinencia

El sistema produce indicadores cuantitativos trazables que permiten caracterizar un NBC en cuatro dimensiones:

| Dimension | Indicador | Que revela |
|:----------|:----------|:-----------|
| Academica | HHI | Concentracion del mercado: identifica campos saturados donde la diferenciacion es baja |
| Academica | CAGR | Tendencia de matricula: crecimiento, estabilidad o declive del campo |
| Laboral | Ratio de Absorcion | Capacidad del mercado laboral para absorber graduados del NBC |
| Laboral | Densidad de Competencias | Que tan definido esta el perfil ocupacional asociado al NBC |
| Territorial | Conectividad | Condiciones de acceso para modalidades virtuales o hibridas |
| Territorial | Desempeño Municipal (MDM) | Capacidad institucional del territorio |
| Global | Brecha de Talento IA | Oportunidad o riesgo segun la disponibilidad de talento en el campo |

### 1.3 Sobre el Matching Semantico

El uso de embeddings multilingues (MiniLM 384d) para establecer correspondencias entre programas academicos, ocupaciones CUOC y competencias laborales resuelve un problema concreto del ecosistema de datos colombianos: las ocupaciones que demanda el mercado laboral rara vez se nombran con las mismas palabras que utilizan los programas academicos. La evidencia del piloto muestra que:

- El puente SNIES ↔ CUOC permite asociar un NBC con ocupaciones y competencias incluso cuando las denominaciones no comparten una sola palabra
- El puente SNIES ↔ SIET revela complementariedades entre educacion formal y formacion para el trabajo que los datos estructurados no harian visibles
- El sistema de cache de dos niveles (memoria + disco) permite que las consultas semanticas respondan en tiempos aceptables (< 500ms para funciones criticas)

### 1.4 Sobre la Generacion de Informes

La integracion con Google Gemini 2.0 Flash para generacion de informes academicos demuestra que es viable automatizar la produccion de estudios de contexto con:

- Citacion automatica de fuentes oficiales (catalogo de 15 fuentes con formato `FUENTE - Periodo`)
- Notacion LaTeX para metricas y formulas
- Estructura de paper academico en 7 secciones
- Recomendacion final con justificacion basada en evidencia

### 1.5 Sobre el Impacto Esperado

La solucion reduce el tiempo necesario para producir un estudio de contexto, integrando en una sola consulta lo que tradicionalmente exigia recopilar y cruzar manualmente informacion de multiples fuentes dispersas. Estructura la evidencia de manera que cada hallazgo es trazable hasta la fuente y el periodo de origen. En terminos sociales, una oferta mejor sustentada contribuye a disminuir brechas de acceso, permanencia y empleabilidad.

---

## 2. Limitaciones Identificadas

### 2.1 Alcance Predictivo

La herramienta aporta a la comprension de condiciones asociadas a la desercion y al fortalecimiento de decisiones de permanencia. Su alcance actual **no equivale a una prediccion individual de abandono**, ni sustituye los sistemas institucionales de acompanamiento estudiantil. La prediccion individual o agregada de riesgo de desercion se propone como fase de evolucion futura.

### 2.2 Dependencia de Actualizacion de Fuentes

La mayoria de los datos operan con cortes periodicos (anuales, semestrales). La actualizacion del repositorio depende de que las fuentes oficiales publiquen nuevos cortes. El sistema cuenta con scripts de ingestion (`admin/ingestar_*.py`) que documentan el proceso de actualizacion, pero este no esta automatizado.

### 2.3 Cobertura de Conectividad

Los datos de conectividad (internet fijo, cobertura movil 4G) provienen de fuentes oficiales (MinTIC) y reflejan sus limitaciones de cobertura. En zonas rurales y municipios PDET, la ausencia de datos de conectividad puede introducir sesgo territorial en la sintesis respectiva. Esta limitacion esta declarada en la documentacion de fuentes (`docs/tecnica/05_fuentes_datos.md`).

### 2.4 Subreporte de la Agencia Publica de Empleo

Las vacantes registradas por la APE no capturan la totalidad del mercado laboral colombiano. El sistema aplica un factor de ajuste en el calculo del ratio de absorcion laboral para corregir parcialmente este subreporte, pero la señal laboral debe interpretarse como una aproximacion, no como un censo.

### 2.5 Dependencia del Modelo de Lenguaje

El componente de busqueda semantica depende de la disponibilidad de `sentence-transformers` y un modelo de 384 dimensiones. Si la libreria no esta disponible, el sistema recurre a busqueda por palabras clave (`data/search.py`), que es menos precisa pero funcional. El sistema de cache de embeddings mitiga el costo computacional de revectorizacion, pero la construccion inicial del cache requiere recursos.

### 2.6 Interpretabilidad del Motor de Decision

El motor de decision produce recomendaciones basadas en scoring ponderado, pero los pesos (30% academica, 40% laboral, 20% territorial, 10% global) reflejan una priorizacion de empleabilidad sobre otras dimensiones. Esta decision de diseño esta documentada y justificada, pero instituciones con prioridades diferentes pueden requerir recalibracion de pesos.

---

## 3. Proximos Pasos

### 3.1 Corto Plazo (0-3 meses)

| Accion | Prioridad | Descripcion |
|:-------|:----------|:------------|
| Documentar URLs especificas de datasets en datos.gov.co | Alta | Reemplazar URLs genericas en `services/sources.py` por URLs directas a cada dataset (formato `https://www.datos.gov.co/d/xxxx-xxxx`) |
| Ampliar cobertura de pruebas | Alta | Incorporar pruebas unitarias para `test_data.py`, `test_models.py`, `test_features.py` |
| Crear notebooks de proceso | Media | `notebooks/01-05` con flujo completo de exploracion, limpieza, analisis, modelo y reportes |
| Pipeline ML | Media | `pipelines/pipeline_ml.py` con flujo end-to-end reproducible |

### 3.2 Mediano Plazo (3-12 meses)

| Accion | Descripcion |
|:-------|:------------|
| Modelado predictivo de desercion | Definir variable objetivo, preparar matriz de entrenamiento con variables academicas, territoriales y de modalidad, evaluar Random Forest y Gradient Boosting con metricas estandar (Accuracy, F1-Score, AUC) |
| Automatizacion de actualizacion de fuentes | Pipeline ETL automatizado que detecte nuevos cortes en las fuentes oficiales y actualice el repositorio DuckDB |
| API REST productiva | Migrar el prototipo FastAPI (`api/`) a produccion, con autenticacion, limites de tasa y documentacion completa |
| Integracion con sistemas institucionales | Conectores para SIA (Sistema de Informacion Academica), SPADIES institucional, y sistemas de aseguramiento de la calidad |

### 3.3 Largo Plazo (> 12 meses)

| Accion | Descripcion |
|:-------|:------------|
| Datos en tiempo real | Incorporacion de fuentes con actualizacion en tiempo real (ej. vacantes APE diarias, matricula en linea) |
| Modelos de simulacion | Simulacion de escenarios de oferta academica (que pasaria si se abre un programa en el departamento X bajo modalidad Y) |
| Sistema multi-agente | Agentes especializados por sintesis evaluativa que colaboren en la generacion de recomendaciones |
| Cobertura regional ampliada | Incorporacion de datos de otros paises de la region (Mexico, Chile, Brasil) para comparativas latinoamericanas |

---

## 4. Lectura Responsable del Alcance

El Sistema de Analisis de Contexto para la Toma de Decisiones Educativas es un **sistema de apoyo a la decision**, no un sustituto del criterio experto. Las siguientes salvaguardas estan incorporadas en el diseño:

1. **Validacion experta requerida:** Los informes generados por el asistente de IA requieren revision humana antes de orientar decisiones formales. El sistema lo declara explicitamente en su interfaz.
2. **Datos agregados, no individuales:** El sistema opera con datos agregados por NBC, departamento y nivel de formacion. No infiere ni expone informacion a nivel de estudiante individual.
3. **Sesgo territorial declarado:** Las zonas con baja conectividad o escasa presencia institucional generan menos datos. El sistema declara esta limitacion en la sintesis territorial.
4. **Transparencia de fuentes:** Cada dato presentado en el dashboard incluye su citacion de fuente, periodo y entidad responsable. La trazabilidad es completa hasta el registro en la base de datos.
5. **No es un predictor de desercion:** El sistema analiza condiciones de contexto asociadas a la permanencia, pero no predice abandono individual. Esta distincion esta documentada en todas las sintesis evaluativas.

---

*Documento generado a partir del documento tecnico ejecutivo (`Documento_solucion_Sistema_Analisis_Contexto_Pertinencia_Educativa_V3.docx` secciones 8 y 10), `README.md` (secciones de alcance y fuentes), `AGENTS.md`, y el estado actual del codigo (`tests/test_queries.py`, `services/decision_engine.py`, `services/scoring.py`).*
