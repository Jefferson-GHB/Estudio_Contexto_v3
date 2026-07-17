# Planteamiento del Problema

Definicion del problema que aborda el Sistema de Analisis de Contexto para la Toma de Decisiones Educativas, su vinculo con la deserción y la permanencia estudiantil, y los objetivos que persigue la solucion.

---

## 1. El Problema: Desercion y Decisiones Curriculares sin Contexto Integrado

La deserción universitaria constituye una señal estructural de riesgo para la calidad, la equidad y la sostenibilidad de la educación superior en Colombia. Segun datos del Sistema para la Prevencion de la Desercion de la Educacion Superior (SPADIES) del Ministerio de Educacion Nacional, las tasas de deserción por cohorte varian significativamente segun nivel de formación, modalidad, departamento y área de conocimiento, reflejando que el abandono no es un fenomeno homogeneo sino que responde a condiciones especificas de contexto.

Sus causas se relacionan con factores académicos, socioeconomicos, territoriales, institucionales, vocacionales y de pertinencia formativa. Cuando la oferta académica se diseña, renueva o modifica sin una lectura integrada del contexto, las instituciones pueden ofrecer programas:

- Desconectados de las necesidades de la poblacion objetivo
- En modalidades inviables para las condiciones de acceso del territorio
- Con trayectorias formativas fragmentadas que no dialogan con el ecosistema de educación para el trabajo
- Con perfiles de egreso sin correspondencia con las oportunidades laborales reales
- En mercados educativos saturados donde la diferenciacion es baja y el valor del título se diluye

Las instituciones de educación superior disponen de multiples fuentes de información oficial:

| Fuente | Entidad | Tipo de dato |
|:-------|:--------|:-------------|
| SNIES | MEN | Programas, IES, matrícula, graduados, admitidos, inscritos, docentes |
| SIET | MEN | Programas de educación para el trabajo y desarrollo humano |
| SPADIES | MEN | Desercion por cohorte, eficiencia terminal, balance anual |
| Saber PRO/TyT/11 | ICFES | Resultados de pruebas de estado, desempeño académico |
| APE | SENA | Vacantes, inscritos, colocados por ocupacion y departamento |
| CUOC | DANE | Ocupaciones, competencias, destrezas, conocimientos |
| GEIH | DANE | Salarios, empleo, condiciones laborales |
| DIVIPOLA | DANE | Division politico-administrativa |
| Conectividad | MinTIC | Internet fijo, cobertura movil 4G |
| MDM | DNP | Medicion de desempeño municipal |
| RUES | Confecamaras | Registro único empresarial, estructura empresarial |

Sin embargo, estas fuentes suelen operar como registros separados. La fragmentacion reduce la capacidad institucional para convertir datos abiertos en conocimiento util para la gestion de permanencia, el diseño curricular y la toma de decisiones sobre portafolio académico.

---

## 2. Vinculo Analitico entre Estudios de Contexto, Permanencia y Desercion

El estudio de contexto funciona como un dispositivo analitico para anticipar condiciones que inciden en la permanencia estudiantil. Su aporte se ubica en el momento previo a la operacion de los programas académicos, cuando las instituciones definen:

- El nivel de formación (técnico, tecnologico, universitario, posgrado)
- La modalidad (presencial, virtual, distancia)
- Las competencias del perfil de egreso
- El territorio de oferta
- La ruta formativa y su articulacion con el ecosistema educativo
- La correspondencia entre la propuesta curricular, las necesidades de la poblacion y las dinamicas sociales y laborales del entorno

Desde esta perspectiva, la deserción se interpreta como una señal critica de pertinencia, trayectoria y sostenibilidad. Su análisis adquiere mayor capacidad explicativa cuando se relaciona con variables de contexto como:

- Matricula y su evolucion histórica (CAGR)
- Concentracion del mercado educativo (HHI)
- Transito inmediato a educación superior (TTI)
- Desempeno agregado en pruebas Saber
- Conectividad y condiciones territoriales de acceso
- Oportunidades laborales (vacantes, salarios, competencias demandadas)
- Brechas de competencias entre formación y mercado
- Coherencia de la oferta académica con el ecosistema de formación para el trabajo (SNIES ↔ SIET)

La solucion no es un predictor individual de abandono. No sustituye los sistemas institucionales de acompanamiento estudiantil ni infiere riesgo a nivel de estudiante. Su funcion es mejorar la calidad de las decisiones sobre oferta académica, de manera que los programas se diseñen y actualicen con evidencia contextual suficiente para fortalecer condiciones de permanencia.

---

## 3. Objetivo General

Implementar una aplicación web que integre datos abiertos educativos, laborales y territoriales para producir estudios de contexto, indicadores de pertinencia y recomendaciones accionables sobre oferta académica, incorporando la deserción como variable que permita comprender las condiciones de permanencia, sostenibilidad y toma de decisiones curriculares.

---

## 4. Objetivos Especificos

| Objetivo | Resultado esperado | Evidencia de cumplimiento |
|:---------|:-------------------|:--------------------------|
| Integrar conjuntos de datos oficiales y abiertos relacionados con oferta académica, matrícula, deserción, graduacion, transito, desempeño, ocupaciones, vacantes, competencias y conectividad | Repositorio unificado DuckDB con 488 tablas en 54 esquemas | `data/repositorio.duckdb` (703 MB), `docs/tecnica/05_fuentes_datos.md` |
| Normalizar los datos mediante CINE-F, NBC, CUOC, CIIU, MNC y DIVIPOLA para habilitar cruces comparables entre educación, trabajo y territorio | Sistema de filtros en cascada con bridge programas↔matriculados | `data/filters.py`, `catalogo/` (26 archivos de mapeo), `docs/tecnica/02_diccionario_datos.md` |
| Generar indicadores de pertinencia académica, laboral, territorial y global, incluyendo HHI, CAGR, ratio de absorcion laboral, indice de conectividad y puntaje final de decisión | 4 sintesis evaluativas con scoring ponderado y motor de decisión de 6 tipos de oferta | `services/scoring.py`, `services/decision_engine.py`, `docs/tecnica/01_arquitectura.md` |
| Producir reportes de contexto y recomendaciones institucionales trazables, auditables y comprensibles para usuarios directivos, oficinas de planeacion, aseguramiento de la calidad y comites curriculares | Dashboard interactivo (Streamlit) + informe Word (python-docx) + informe LLM (Gemini) | `app.py` (387 lineas), `views/tab_academico.py` (907 L), `views/tab_laboral.py` (674 L), `views/tab_territorial.py` (560 L), `views/tab_decision.py` (592 L), `utils/reporte_docx.py`, `docs/tecnica/07_guia_validacion.md` |

---

## 5. Poblacion Objetivo

| Usuario | Necesidad | Como responde el sistema |
|:--------|:----------|:-------------------------|
| Directivos y rectores | Decisiones estrategicas sobre portafolio académico | Sintesis evaluativas con semaforo de decisión y recomendacion de tipo de oferta |
| Comites curriculares | Diseno y actualizacion de programas | Evidencia de pertinencia académica, laboral y territorial trazable a fuentes oficiales |
| Oficinas de planeacion | Estudios de contexto para registro calificado | Informe académico con formato APA, citación de fuentes, indicadores cuantitativos |
| Aseguramiento de la calidad | Evidencia para acreditacion y autoevaluacion | Datos de deserción, desempeño, conectividad y mercado laboral integrados en un solo panel |
| Investigadores y analistas | Datos abiertos integrados para estudios propios | Base DuckDB consultable, 56 consultas SQL parametrizadas, documentación técnica completa |

---

## 6. Alcance y Limitaciones

### Alcance actual

- Analitica contextual y busqueda semantica para estudios de contexto
- Generacion de indicadores de pertinencia educativa
- Recomendacion institucional basada en scoring ponderado
- Generacion asistida de informes de pertinencia
- Integracion de 54 esquemas de datos de fuentes oficiales colombianas e internacionales

### Fuera del alcance actual

- Prediccion individual o agregada de riesgo de deserción (fase futura — ver Anexo C del documento técnico)
- Integracion con sistemas institucionales de acompanamiento estudiantil
- Datos en tiempo real (toda la base opera con cortes periodicos)
- Cobertura total de zonas rurales con conectividad limitada (los datos de conectividad provienen de fuentes oficiales y reflejan sus limitaciones de cobertura)

---

*Documento generado a partir del documento técnico ejecutivo (`Documento_solucion_Sistema_Analisis_Contexto_Pertinencia_Educativa_V3.docx` secciones 1-3), `README.md` (lineas 37-57), `services/sources.py` (376 lineas), y la base de datos DuckDB.*
