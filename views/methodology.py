"""Metodologia: referencia rapida de metricas, formulas y fuentes del sistema."""
import streamlit as st


@st.dialog("Metodologia", width="large")
def mostrar_metodologia():
    st.markdown("### Metodologia del Sistema")
    st.caption("Metricas, formulas y fuentes. Consulte aqui si olvida que significa cada indicador.")

    with st.expander("1. Indicadores Academicos", expanded=True):
        st.markdown("#### HHI — Concentracion de mercado")
        st.latex(r"HHI = \sum s_i^2")
        st.markdown("""
        | HHI | Clasificacion (DOJ 2023) |
        |-----|--------------------------|
        | < 1,000 | Mercado competitivo |
        | 1,000 - 1,800 | Moderadamente concentrado |
        | > 1,800 | Alta concentracion |

        **Validacion**: No aplica si hay menos de 4 IES ofertando o menos de 1,000 estudiantes.
        En esos casos se muestra "Mercado incipiente — HHI no determinante".

        **Fuente**: SNIES Matriculados (MEN).
        """)

        st.markdown("---")
        st.markdown("#### CAGR — Crecimiento anual de matricula")
        st.latex(r"CAGR = \left(\frac{V_{final}}{V_{inicial}}\right)^{1/n} - 1")
        st.markdown("""
        | CAGR | Clasificacion |
        |------|---------------|
        | > 5% | Crecimiento fuerte |
        | 0% - 5% | Crecimiento moderado |
        | -5% - 0% | Estancamiento |
        | < -5% | Declive |

        **Validacion**: Requiere al menos 3 años de datos historicos.

        **Fuente**: SNIES Matricula 2014-2024 (MEN).
        """)

    with st.expander("2. Indicadores Laborales"):
        st.markdown("#### Ratio de Absorcion")
        st.latex(r"Ratio = \frac{Vacantes}{Graduados}")
        st.markdown("""
        | Ratio | Clasificacion |
        |-------|---------------|
        | > 1.5 | Alta demanda laboral |
        | 1.0 - 1.5 | Demanda favorable |
        | 0.7 - 1.0 | Equilibrio |
        | < 0.7 | Sobreoferta de graduados |

        **Validacion**: Si no hay graduados registrados, se muestra advertencia.

        **Fuentes**: APE (vacantes, Min. Trabajo) + SNIES (graduados, MEN).
        """)

        st.markdown("---")
        st.markdown("#### Matching NBC-CUOC")
        st.markdown("Modelo de IA (sentence-transformers MiniLM) que relaciona campos academicos (NBC) con ocupaciones laborales (CUOC) por similitud semantica. Fuente CUOC: DANE.")

    with st.expander("3. Indicadores Territoriales"):
        st.markdown("""
        | Indicador | Que mide | Fuente |
        |-----------|----------|--------|
        | Tasa de Cobertura Bruta | % de jovenes en educacion superior | MEN |
        | Transito Inmediato | % de bachilleres que ingresan directo a ES | MEN |
        | Conectividad | Internet fijo + cobertura 4G | MinTIC |
        | MDM | Desempeno municipal integral | DNP |
        | PDET | Municipios priorizados por Acuerdo de Paz | ART |
        """)

    with st.expander("4. Score Final"):
        st.latex(r"Score = (Acad \times 0.30) + (Lab \times 0.40) + (Terr \times 0.20) + (Glob \times 0.10)")
        st.markdown("""
        | Sintesis | Peso | Que evalua |
        |----------|------|------------|
        | Academica | 30% | Saturacion vs oportunidad del mercado |
        | Laboral | 40% | Empleabilidad real de los egresados |
        | Territorial | 20% | Contexto geografico y social |
        | Global | 10% | Tendencias macro e internacionales |

        **Veredicto**:
        | Score | Resultado |
        |-------|-----------|
        | >= 80 | OFERTAR |
        | 50 - 79 | OFERTAR CON AJUSTES |
        | < 50 | REVALUAR |
        """)

    with st.expander("5. Busqueda Inteligente"):
        st.markdown("""
        La busqueda usa IA (modelo MiniLM multilingue) para encontrar programas por similitud semantica:
        - "mecanica" encuentra "Ingenieria Mecanica", "Mecanica Dental", "Tecnologia en Mecanica"
        - Busca en 30,000+ programas SNIES y 25,000+ programas SIET simultaneamente
        - La primera carga tarda ~30s (prepara el indice). Cargas posteriores son instantaneas.
        """)

    with st.expander("6. Fuentes de Datos"):
        st.markdown("""
        | Fuente | Entidad | Contenido |
        |--------|---------|-----------|
        | SNIES | MEN | Programas, matricula, graduados, admitidos |
        | SIET | SENA | Educacion para el Trabajo (ETDH) |
        | APE | Min. Trabajo | Vacantes laborales |
        | CUOC | DANE | Clasificacion de ocupaciones |
        | MinTIC | MinTIC | Conectividad digital |
        | DNP | DNP | Indicadores territoriales |
        | ICFES | ICFES | Resultados Saber PRO y TyT |
        """)

    st.markdown("---")
    st.caption("Sistema de Analisis de Pertinencia Educativa v3.1.0")
