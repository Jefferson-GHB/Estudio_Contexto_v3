<h1 align="center">
  <br>
  <img src="https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/1f4da.svg" width="80" alt="books">
  <br>
  Estudio Contexto
  <br>
</h1>

<h4 align="center">Dashboard de pertinencia educativa para educación superior en Colombia</h4>

<p align="center">
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white" alt="Python 3.13"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/streamlit-1.42-red?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/duckdb-1.2-yellow?logo=duckdb&logoColor=white" alt="DuckDB"></a>
  <a href="#-stack-tecnologico"><img src="https://img.shields.io/badge/gemini-2.0_flash-4285F4?logo=google&logoColor=white" alt="Gemini"></a>
  <a href="https://github.com/Jefferson-GHB/Estudio_Contexto_v3/actions"><img src="https://img.shields.io/badge/tests-50/50-brightgreen" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT"></a>
</p>

<p align="center">
  <b>Sistema de análisis que cruza oferta educativa (SNIES, SIET) con demanda laboral (APE, CUOC, GEIH)</b><br>
  usando inteligencia artificial para determinar si un programa académico tiene cabida en el mercado colombiano.
</p>

---

## ¿Para qué sirve?

Imagina que una universidad quiere abrir un nuevo programa de **Enfermería** en Bogotá. ¿Hay mercado? ¿Cuántos compiten? ¿Qué salario ganan los egresados? ¿Qué competencias pide realmente el sector salud?

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

| Síntesis | Qué responde | Fuentes |
|----------|-------------|---------|
| **Académica** | ¿El mercado está saturado? ¿Crece o decrece? ¿Calidad Saber PRO? | SNIES, ICFES |
| **Laboral** | ¿Hay vacantes reales? ¿Cuánto pagan? ¿Qué competencias piden? | APE, CUOC, GEIH, OLE |
| **Territorial** | ¿En qué departamento conviene abrir el programa? ¿Hay conectividad? | SNIES, DANE, PDET |
| **Decisión** | Informe ejecutivo generado por IA con recomendación final | Gemini + todas las anteriores |

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

<p align="center">
  <sub>Desarrollado con ❤️ por <a href="https://github.com/Jefferson-GHB">JeffersonCA</a></sub>
</p>
