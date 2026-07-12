---
title: Estudio Contexto
emoji: 📊
colorFrom: red
colorTo: gray
sdk: docker
app_file: app.py
pinned: false
---

<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/1f4da.svg" width="80" alt="books">
  <br>
  Estudio Contexto
  <br>
</h1>

<h4 align="center">Estudios de contexto para decisiones curriculares con evidencia de pertinencia y permanencia</h4>

<p align="center">
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/streamlit-1.42-red?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/duckdb-1.2-yellow?logo=duckdb&logoColor=white" alt="DuckDB"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/gemini-2.0_flash-4285F4?logo=google&logoColor=white" alt="Gemini"></a>
  <a href="https://github.com/Jefferson-GHB/Estudio_Contexto_v3/actions"><img src="https://img.shields.io/badge/tests-50/50-brightgreen" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT"></a>
</p>

<p align="center">
  <b>Plataforma que integra datos abiertos educativos, laborales y territoriales</b><br>
  para orientar decisiones sobre oferta academica que fortalezcan condiciones de permanencia estudiantil.
</p>

---

## El problema: desercion y decisiones curriculares sin contexto integrado

Cuando una institucion disena, abre o modifica un programa sin leer el contexto (mercado, territorio, competencias, trayectorias), puede generar **condiciones que afectan la permanencia**: programas en mercados saturados, modalidades inviables para la poblacion objetivo, rutas formativas fragmentadas, o perfiles de egreso desconectados de las oportunidades laborales reales.

Estudio Contexto convierte datos abiertos —SNIES, SIET, SPADIES, APE, CUOC, GEIH, ICFES— en **evidencia trazable** para que directivos, comites curriculares y equipos de aseguramiento de la calidad respondan preguntas como:

Estudio Contexto responde automáticamente conectando **7 fuentes oficiales** en tiempo real:

```
SNIES (programas)  ←──────────────→  SIET (formación trabajo)
       │                                    │
       └────────── CINE-F UNESCO ───────────┘
       │                                    │
       ▼                                    ▼
  CUOC (ocupaciones)              APE (vacantes reales)
       │                                    │
       └──────────→  GEIH (salarios)  ←─────┘
                          │
                          ▼
                   Gemini (análisis)
```

## Capturas

<p align="center">
  <em>4 síntesis navegables — cada una revela una dimensión del análisis</em>
</p>

| Síntesis | Qué responde | Aporte a permanencia |
|----------|-------------|---------------------|
| **Académica** | ¿La oferta actual esta saturada? ¿Crece o decrece? ¿Hay calidad? | Anticipa mercados con baja diferenciacion que pueden generar desercion por perdida de valor del titulo |
| **Laboral** | ¿Existen ocupaciones, vacantes y competencias que respalden la empleabilidad? | Conecta formacion con oportunidades reales de insercion, fortaleciendo expectativas de retorno |
| **Territorial** | ¿El departamento tiene conectividad, demanda y condiciones de acceso? | Identifica barreras de acceso que pueden afectar la continuidad en programas virtuales o hibridos |
| **Decisión** | ¿La evidencia integrada respalda ofertar, ajustar o revaluar el programa? | Produce recomendacion trazable antes de comprometer recursos institucionales |

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| **Frontend** | Streamlit 1.42 | Dashboard interactivo con 4 pestañas |
| **Base de datos** | DuckDB 1.2 | 703 MB, read-only, 25 tablas normalizadas |
| **ML / NLP** | sentence-transformers (MiniLM) | Matching semántico programas, ocupaciones, competencias |
| **LLM** | Google Gemini 2.0 Flash | Informe académico con APA 7ª edición |
| **Visualización** | Plotly 6 | Gráficos interactivos, gauges, distribución |
| **Reportes** | python-docx | Documento Word profesional con portada y marca de agua |
| **Deploy** | Docker + HuggingFace Spaces | Puerto 7860, Python 3.13-slim |

## Instalación

```bash
# 1. Clonar (incluye DuckDB de 703 MB vía Git LFS)
git clone https://github.com/Jefferson-GHB/Estudio_Contexto_v3.git
cd Estudio_Contexto_v3

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
streamlit run app.py
```

> **Credenciales por defecto**: usuario `admin` · contraseña `EstudioContexto2026!`

## Variables de entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `DUCKDB_PATH` | No | Ruta personalizada a la base de datos |
| `GEMINI_API_KEY` | Sí (para IA) | API key de Google Gemini |
| `GITHUB_TOKEN` | No | Token para GitHub API |
| `HUGGINGFACE_TOKEN` | No | Token para HuggingFace Hub |

## Estructura del proyecto

```
Estudio_Contexto_v3/
├── app.py                  # Dashboard principal (4000+ líneas)
├── data/
│   ├── queries.py          # 50+ consultas SQL parametrizadas
│   ├── filters.py          # Constructor de cláusulas WHERE + cascada NBC
│   ├── search.py           # Búsqueda semántica con embeddings en disco
│   └── repositorio.duckdb  # Base de datos (703 MB, Git LFS)
├── components/
│   └── sidebar.py          # Sidebar con búsqueda inteligente y filtros
├── services/
│   ├── ml/                 # Matching semántico (MiniLM) + puente SNIES↔SIET
│   ├── llm.py              # Integración Gemini + RAG
│   ├── scoring.py          # Métricas: HHI, CAGR, Ratio de Absorción
│   └── decision_engine.py  # Motor de recomendación (OFERTAR / NO OFERTAR)
├── utils/
│   ├── reporte_docx.py     # Generador de informe Word profesional
│   └── auth.py             # Autenticación SHA-256
├── visualizations/
│   └── charts.py           # Gauges Plotly (HHI, Saber PRO, Score)
├── catalogo/               # 26 archivos de mapeo (SNIES, CUOC, SIET, MEN)
├── admin/                  # Scripts de auditoría, evaluación e ingesta
└── tests/
    └── test_queries.py     # 50 tests de integración contra DuckDB real
```

## Fuentes de datos

Todos los datos provienen de fuentes oficiales del gobierno colombiano:

| Dataset | Periodo | Filas | Fuente |
|---------|---------|-------|--------|
| SNIES Programas | 2024 | 12,865 | [snies.mineducacion.gov.co](https://snies.mineducacion.gov.co) |
| SNIES Matriculados | 2019-2024 | 297,554 | MEN |
| SIET Programas | 2023 | 25,010 | [siet.mineducacion.gov.co](https://siet.mineducacion.gov.co) |
| Saber PRO | 2018-2022 | 999,891 | [icfes.gov.co](https://www.icfes.gov.co) |
| APE Vacantes | 2023-2024 | 23,447 | [mintrabajo.gov.co](https://www.mintrabajo.gov.co) |
| CUOC Ocupaciones | 2025 | 680 perfiles | [dane.gov.co](https://www.dane.gov.co) |
| Cualificaciones MEN | 2024 | 396 | MEN - MNC |

## Licencia

MIT — ver [LICENSE](LICENSE)

---

## Equipo

| Integrante | Rol |
|-----------|-----|
| **Jefferson Cuastusa** | Lider tecnico BI, modelado de datos, ETL, visualizacion. Ingeniero de Sistemas. |
| **Ximena Molano** | Especialista en educacion superior, calidad, evaluacion curricular. Economista. |
| **Claudia Milena Munoz** | Lider academica y de aseguramiento de la calidad. Ingeniera Industrial, Mg. y candidata a Dra. en Educacion. |

## Metodologia

El desarrollo sigue el marco **CRISP-ML** (Cross-Industry Standard Process for Machine Learning) adaptado al dominio educativo: comprension del problema → comprension de datos → preparacion ETL → modelado de indicadores → evaluacion con 50 tests automatizados → despliegue en contenedor Docker.

---

<p align="center">
  <sub>Desarrollado con ❤️ por <a href="https://github.com/Jefferson-GHB">Equipo 195</a> — Concurso Datos al Ecosistema 2026</sub>
</p>
