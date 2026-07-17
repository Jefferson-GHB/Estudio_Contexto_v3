---
title: Sistema de Análisis de Contexto para la Toma de Decisiones Educativas
emoji: "\U0001F4CA"
colorFrom: red
colorTo: gray
sdk: docker
app_file: app.py
pinned: false
---

<h1 align="center">
  Sistema de Análisis de Contexto<br>para la Toma de Decisiones Educativas
</h1>

<h4 align="center">Estudios de contexto para decisiones curriculares con evidencia de pertinencia y permanencia</h4>

<p align="center">
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/streamlit-1.42-red?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/duckdb-1.5-yellow?logo=duckdb&logoColor=white" alt="DuckDB"></a>
  <a href="#stack-tecnologico"><img src="https://img.shields.io/badge/gemini-2.0__flash-4285F4?logo=google&logoColor=white" alt="Gemini"></a>
  <a href="https://github.com/Jefferson-GHB/Estudio_Contexto_v3/actions"><img src="https://img.shields.io/badge/tests-50/50-brightgreen" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
</p>

---

## El problema

En Colombia, segun el Sistema para la Prevencion de la Desercion de la Educacion Superior (SPADIES), la desercion universitaria constituye una señal estructural de riesgo. Cuando una institución diseña, abre o modifica un programa sin leer contexto integrado —mercado laboral, territorio, competencias, trayectorias— genera condiciones que afectan la permanencia: programas en mercados saturados, perfiles de egreso desconectados de ocupaciones reales, o modalidades inviables para la poblacion objetivo.

---

## Justificacion — Valor Publico

Estudio Contexto democratiza el acceso a analisis de contexto educativo basados en **datos abiertos del Estado colombiano**. Es una herramienta gratuita, trazable y auditables para que directivos, comites curriculares y equipos de aseguramiento de la calidad de IES publicas y privadas tomen decisiones de oferta academica con evidencia verificable, fortaleciendo condiciones de permanencia estudiantil.

---

## Datasets utilizados (7 fuentes)

| # | Dataset | Portal | Periodo | Registros |
|---|---------|--------|---------|-----------|
| 1 | **Conectividad Internet Fijo** | **datos.gov.co** | 2016-2023 | 1,678,363 |
| 2 | Cobertura Movil 4G | **datos.gov.co** | 2015-2023 | 1,457,892 |
| 3 | **APE Vacantes** | **datos.gov.co** | 2023-2024 | 23,447 |
| 4 | SNIES Programas | snies.mineducacion.gov.co | 2024 | 12,865 |
| 5 | SIET Programas | siet.mineducacion.gov.co | 2023 | 25,010 |
| 6 | Saber PRO | icfes.gov.co | 2018-2022 | 999,891 |
| 7 | CUOC Ocupaciones | **datos.gov.co** | 2025 | 680 perfiles |

**Dataset externo complementario**: Cualificaciones MEN (MNC, 2024, 396 registros), indicadores Banco Mundial, OECD, UNESCO, OIT.

---

## Variables seleccionadas (14 variables clave)

| # | Variable | Descripcion | Fuente |
|---|----------|-------------|--------|
| 1 | NBC | Nucleo Basico del Conocimiento | SNIES |
| 2 | Matriculados | Total matriculados 2019-2024 | SNIES |
| 3 | Graduados | Total graduados anuales | SNIES |
| 4 | Nivel de formacion | Pregrado / Posgrado | SNIES |
| 5 | Modalidad | Presencial / Virtual / Distancia | SNIES |
| 6 | Departamento oferta | Departamento del programa | SNIES |
| 7 | Vacantes APE | Vacantes reportadas 2023-2024 | APE (datos.gov.co) |
| 8 | Ocupacion CUOC | Denominacion ocupacional oficial | CUOC (datos.gov.co) |
| 9 | Conocimientos CUOC | Competencias de conocimiento requeridas | CUOC |
| 10 | Destrezas CUOC | Competencias de destreza requeridas | CUOC |
| 11 | Salario promedio | Salario por departamento y NBC | GEIH |
| 12 | Conectividad 4G | Cobertura movil por municipio | MinTIC (datos.gov.co) |
| 13 | Internet fijo | Accesos de internet fijo por municipio | MinTIC (datos.gov.co) |
| 14 | Saber PRO | Puntaje promedio lectura critica + razonamiento | ICFES |

---

## Tipo de analisis y modelo

**Tipo**: Analisis descriptivo multidimensional con scoring compuesto e IA generativa.

**Modelo**: Sistema multi-componente que integra:
- **Indicadores estadisticos**: HHI (concentracion de mercado), CAGR (tasa de crecimiento compuesta), Ratio de Absorcion Laboral
- **Matching semantico**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers, 384 dim) para cruzar programas academicos con ocupaciones CUOC y programas SIET — ~30K embeddings cacheados en disco
- **RAG**: Recuperacion aumentada con datos de desercion SPADIES que enriquecen el contexto del LLM
- **LLM**: Google Gemini 2.0 Flash con prompt estructurado de ~500 lineas generando informe en formato APA 7a edicion con citacion de fuentes verificables
- **Motor de decision heuristica**: Scoring ponderado (30% academico + 40% laboral + 20% territorial + 10% global) que produce recomendacion trazable: OFERTAR / NO OFERTAR / MICROCREDENCIAL

---

## Resultados clave

| Metrica | Valor |
|---------|-------|
| Pruebas de integracion automatizadas | 50/50 contra repositorio DuckDB real |
| Sintesis evaluativas | 4 (Academica, Laboral, Territorial, Decision Final) |
| Schemas integrados | 54 (488 tablas, 703 MB) |
| Embeddings semanticos indexados | ~30,000 programas SNIES + SIET |
| Fallback del LLM | 4 modelos Gemini con degradacion progresiva |
| Validacion del puente SNIES-SIET | Umbral adaptativo de similitud por NBC (0.639-0.650) |

**Pipeline de ejecucion**: `pip install -r requirements.txt` → `python -m streamlit run app.py` → seleccionar NBC → 4 tabs con resultados en tiempo real.

---

## Interpretacion

- **Score ≥ 80 (OFERTAR)**: Condiciones favorables de mercado, empleabilidad y territorio. Baja concentracion, crecimiento positivo, vacantes activas, salarios competitivos y conectividad suficiente.
- **Score 50-79 (OFERTAR CON AJUSTES)**: Señales mixtas. Se recomienda revisar modalidad, departamento o nivel de formacion antes de comprometer recursos.
- **Score < 50 (REVALUAR)**: Mercado saturado o sin demanda laboral detectable. Explorar formacion complementaria de corta duracion alineada con competencias CUOC especificas.

La recomendacion es **trazable**: cada componente del score se desglosa con su valor numerico y fuente de datos, permitiendo auditoria completa del resultado.

---

## Impacto potencial

- **Instituciones de educacion superior**: Decisiones de oferta academica basadas en evidencia integrada de mercado laboral, territorio y calidad, reduciendo el riesgo de abrir programas en mercados saturados o sin demanda laboral.
- **Entidades gubernamentales**: Modelo de referencia para estudios de pertinencia educativa con datos abiertos del Estado, reproducible y escalable a cualquier departamento o NBC.
- **Ciudadania**: Transparencia sobre la relacion entre formacion y empleabilidad, fortaleciendo expectativas de retorno de la inversion educativa.

---

## Demo en vivo

**Aplicacion Web**: [https://jeffersonca-estudio-contexto.hf.space/](https://jeffersonca-estudio-contexto.hf.space/)

- Usuario: `admin`
- Contrasena: `EstudioContexto2026!`
- Seleccione un NBC (ej: "Ingenieria de sistemas, telematica y afines") y explore las 4 sintesis.

**Contenedor Docker**:
```bash
docker build -t estudio-contexto .
docker run -p 7860:7860 estudio-contexto
```

---

## Documentacion y enlaces

| Recurso | Acceso |
|---------|--------|
| Presentacion (PDF) | [RECURSOS/presentacion.pdf](RECURSOS/presentacion.pdf) |
| Documentacion tecnica | [docs/tecnica/](docs/tecnica/) — Arquitectura, Datos, Metodologia, Validacion |
| Repositorio GitHub | [github.com/Jefferson-GHB/Estudio_Contexto_v3](https://github.com/Jefferson-GHB/Estudio_Contexto_v3) |
| Changelog | [Changelog.md](Changelog.md) |

---

## Instalacion local

```bash
git clone https://github.com/Jefferson-GHB/Estudio_Contexto_v3.git
cd Estudio_Contexto_v3
pip install -r requirements.txt
python -m streamlit run app.py
```

> Credenciales por defecto: `admin` / `EstudioContexto2026!`. Variable `GEMINIAPIKEY` requerida para el componente LLM.

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| **Jefferson Cuastusa** | Lider tecnico BI, modelado de datos, ETL, visualizacion. Ingeniero de Sistemas. |
| **Ximena Molano** | Especialista en educacion superior, calidad, evaluacion curricular. Economista. |
| **Claudia Milena Munoz** | Lider academica y de aseguramiento de la calidad. Ingeniera Industrial, Mg. y candidata a Dra. en Educacion. |

---

## Metodologia

CRISP-ML (Cross-Industry Standard Process for Machine Learning) adaptado al dominio educativo: comprension del problema → comprension de datos → preparacion ETL → modelado de indicadores → evaluacion (50 tests automatizados) → despliegue (Docker + HuggingFace Spaces).

---

<p align="center">
  <sub>Desarrollado por Equipo 195 — Concurso Datos al Ecosistema 2026</sub>
</p>
