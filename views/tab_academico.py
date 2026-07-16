"""
Sintesis Academica: concentracion de mercado, crecimiento,
calidad Saber PRO, evolucion del ciclo estudiantil, desglose
de oferta y explorador interactivo de datos.
"""
import io

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config.constants import TEMPLATE_COLORS
from config.styles import loading_overlay
from components.display import section_header
from utils.helpers import descargar_datos_grafico
from services.sources import get_citacion
from visualizations.charts import crear_gauge_hhi, crear_gauge_saber, crear_distribucion_saber
from data import (
    get_desglose_academico,
    get_programas_detalle,
    get_datos_explorador_interactivo,
)
from views.etdh import render_etdh_dashboard


def render_tab_academico(ctx):
    """Renderiza la sintesis academica del dashboard.

    Recibe el Context con datos pre-cargados y retorna un dict
    con el desglose academico para que Tab 4 lo use al construir
    el contexto del LLM.
    """
    section_header("01", "Pertinencia Academica", "La oferta actual responde a las necesidades de la poblacion o genera condiciones de riesgo para la permanencia?")

    # Obtener desglose academico completo
    desglose = get_desglose_academico(filtros=ctx.filtros_seleccionados)

    col_hhi, col_cagr = st.columns(2)

    with col_hhi:
        st.markdown("#### Concentracion de Mercado (HHI)")
        st.caption("Distribucion de matricula entre las IES. Concentracion alta = pocos dominan, baja diferenciacion y riesgo de saturacion. Concentracion baja = mercado abierto con oportunidades de insercion sostenible.")
        fig_hhi = crear_gauge_hhi(ctx.hhi)
        st.plotly_chart(fig_hhi, width='stretch')
        if not ctx.df_market.empty:
            descargar_datos_grafico(ctx.df_market, "market_share_instituciones", "Descargar market share")
        st.caption(get_citacion("snies_matriculados"))
        st.info(ctx.hhi_interp)

        if not ctx.df_market.empty:
            st.markdown("**Top 5 Instituciones:**")
            st.dataframe(
                ctx.df_market.head(5)[['institucion', 'matriculados', 'share']].rename(
                    columns={'institucion': 'Institución', 'matriculados': 'Matrículas', 'share': 'Cuota %'}
                ),
                hide_index=True,
                width='stretch'
            )

            with st.expander("Ver Detalle Completo de Programas", icon=":material/list_alt:"):
                df_detalle = get_programas_detalle(filtros=ctx.filtros_seleccionados)
                if not df_detalle.empty:
                    st.markdown(f"**{len(df_detalle)} programas encontrados** para *{ctx.filtro_label}*")
                    st.dataframe(
                        df_detalle,
                        hide_index=True,
                        width='stretch',
                        height=450,
                        column_config={
                            "Institucion": st.column_config.TextColumn("Institución", width="large"),
                            "Programa": st.column_config.TextColumn("Programa", width="large"),
                            "Nivel": st.column_config.TextColumn("Nivel", width="small"),
                            "Modalidad": st.column_config.TextColumn("Modalidad", width="small"),
                            "Sector": st.column_config.TextColumn("Sector", width="small"),
                            "Caracter": st.column_config.TextColumn("Carácter", width="medium"),
                            "Depto": st.column_config.TextColumn("Departamento", width="medium"),
                            "Municipio": st.column_config.TextColumn("Municipio", width="medium"),
                            "Estado": st.column_config.TextColumn("Estado", width="small"),
                            "Creditos": st.column_config.NumberColumn("Créditos", width="small")
                        }
                    )
                    buffer = io.BytesIO()
                    df_detalle.to_excel(buffer, index=False, engine='openpyxl')
                    buffer.seek(0)
                    file_suffix = ctx.sel_nbc.replace(' ', '_') if ctx.sel_nbc else "filtros_aplicados"
                    st.download_button(
                        label="Descargar Excel",
                        data=buffer,
                        file_name=f"programas_{file_suffix}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        icon=":material/download:"
                    )
                else:
                    st.warning("No se encontraron programas con los filtros aplicados")

    with col_cagr:
        st.markdown("#### Tasa de Crecimiento (CAGR)")
        st.caption("Tendencia anual de matricula. Un campo en crecimiento sugiere demanda sostenida y menor riesgo de abandono por perdida de valor del programa.")
        st.metric("CAGR Matricula", f"{ctx.cagr}%", help="Compound Annual Growth Rate - Tasa de crecimiento anual compuesto de matriculados")
        st.info(ctx.cagr_interp)
        st.caption(get_citacion("snies_matriculados"))

    # CAGR: solo mostrar el valor calculado
    cagr_num = float(str(ctx.cagr).replace('%', '').replace('+', ''))
    cagr_str = f"{cagr_num:+.1f}%"
    etiqueta_cagr = "Crecimiento" if cagr_num >= 5 else "Estable" if cagr_num >= 0 else "Declive"

    # Saber PRO: calidad academica via matching semantico
    try:
        from data.queries import get_saber_pro_stats
        saber_stats = get_saber_pro_stats(filtros=ctx.filtros_seleccionados)
        if saber_stats.get('n_evaluados', 0) > 0:
            st.markdown("---")
            st.markdown("### Calidad Academica (Saber PRO)")
            st.caption(f"Resultados de las pruebas Saber PRO de egresados en programas relacionados. Periodo: {saber_stats.get('periodo', '2020-2022')} | {saber_stats['n_evaluados']:,} evaluados.")

            puntaje = saber_stats['puntaje_promedio']
            nacional = saber_stats.get('nacional_promedio', 150)

            col_gauge, col_dist = st.columns([1, 2])
            with col_gauge:
                st.plotly_chart(crear_gauge_saber(puntaje or 0, nacional), width='stretch')
                diff = (puntaje or 0) - (nacional or 0)
                if diff > 0:
                    st.success(f"**{diff:+.0f} pts** sobre promedio nacional ({nacional:.0f})")
                elif diff < 0:
                    st.warning(f"**{diff:+.0f} pts** bajo promedio nacional ({nacional:.0f})")
                else:
                    st.info(f"Igual al promedio nacional ({nacional:.0f})")

            with col_dist:
                st.plotly_chart(crear_distribucion_saber(
                    saber_stats.get('puntaje_min', 0),
                    saber_stats.get('q1', 0),
                    saber_stats.get('mediana', 0),
                    saber_stats.get('q3', 0),
                    saber_stats.get('puntaje_max', 0)
                ), width='stretch')
                st.caption("Distribucion de puntajes: Min, Cuartiles y Maximo")

            st.caption(f"Fuente: ICFES — Saber PRO | Periodo: {saber_stats.get('periodo', '2020-2022')} | Promedio nacional: **{nacional:.0f}/300** | Matching semantico con MiniLM")
    except Exception:
        pass

    # =====================================================================
    # EVOLUCION ESTUDIANTIL
    # =====================================================================
    st.markdown("---")
    st.markdown("### Evolucion del Ciclo Estudiantil")
    st.caption("Seguimiento del flujo estudiantil: inscritos, admitidos, primer curso y graduados. Identificar donde se concentran las perdidas permite anticipar riesgos de desercion y disenar estrategias de retencion por etapa.")
    st.caption(f"Tendencia historica | {ctx.label_ambito}")

    col_insc, col_admi = st.columns(2)

    with col_insc:
        st.markdown("#### Inscritos")
        if not ctx.df_inscritos.empty:
            fig_insc = px.line(
                ctx.df_inscritos, x='anio', y='inscritos',
                title=f"Histórico de Inscritos (2019-2024)",
                markers=True, color_discrete_sequence=['#9b1b30']
            )
            st.plotly_chart(fig_insc, width='stretch')
            descargar_datos_grafico(ctx.df_inscritos, "historico_inscritos", "Descargar datos")
            st.caption(get_citacion("snies_inscritos"))
        else:
            st.warning("Sin datos de inscritos")

    with col_admi:
        st.markdown("#### Admitidos")
        if not ctx.df_admitidos.empty:
            fig_admi = px.line(
                ctx.df_admitidos, x='anio', y='admitidos',
                title=f"Histórico de Admitidos (2019-2024)",
                markers=True, color_discrete_sequence=['#6B9080']
            )
            st.plotly_chart(fig_admi, width='stretch')
            descargar_datos_grafico(ctx.df_admitidos, "historico_admitidos", "Descargar datos")
            st.caption(get_citacion("snies_admitidos"))
        else:
            st.warning("Sin datos de admitidos")

    col_primer, col_matr = st.columns(2)

    with col_primer:
        st.markdown("#### Matriculados Primer Curso")
        if not ctx.df_primer_curso.empty:
            fig_primer = px.line(
                ctx.df_primer_curso, x='anio', y='primer_curso',
                title=f"Histórico Primer Curso (2019-2024)",
                markers=True, color_discrete_sequence=['#cc8800']
            )
            st.plotly_chart(fig_primer, width='stretch')
            descargar_datos_grafico(ctx.df_primer_curso, "historico_primer_curso", "Descargar datos")
            st.caption(get_citacion("snies_matriculados_primer_curso"))
        else:
            st.warning("Sin datos de primer curso")

    with col_matr:
        st.markdown("#### Matriculados Total")
        if not ctx.df_tendencia.empty:
            fig_matr = px.line(
                ctx.df_tendencia, x='anio', y='matriculados',
                title=f"Histórico de Matriculados (2019-2024)",
                markers=True, color_discrete_sequence=['#a0522d']
            )
            st.plotly_chart(fig_matr, width='stretch')
            descargar_datos_grafico(ctx.df_tendencia, "historico_matriculados", "Descargar datos")
            st.caption(get_citacion("snies_matriculados"))
        else:
            st.warning("Sin datos de matriculados")

    col_grad_solo, _ = st.columns(2)

    with col_grad_solo:
        st.markdown("#### Graduados")
        if not ctx.df_graduados.empty:
            fig_grad = px.line(
                ctx.df_graduados, x='anio', y='graduados',
                title=f"Histórico de Graduados (2019-2024)",
                markers=True, color_discrete_sequence=['#a0522d']
            )
            st.plotly_chart(fig_grad, width='stretch')
            descargar_datos_grafico(ctx.df_graduados, "historico_graduados", "Descargar datos")
            st.caption(get_citacion("snies_graduados"))
        else:
            st.warning("Sin datos de graduados")

    # Grafico combinado de embudo/conversion
    with st.expander("Ver Gráfico Combinado de Evolución Estudiantil", expanded=False):
        datos_combinados = []
        if not ctx.df_inscritos.empty:
            for _, row in ctx.df_inscritos.iterrows():
                datos_combinados.append({'Año': row['anio'], 'Etapa': 'Inscritos', 'Cantidad': row['inscritos']})
        if not ctx.df_admitidos.empty:
            for _, row in ctx.df_admitidos.iterrows():
                datos_combinados.append({'Año': row['anio'], 'Etapa': 'Admitidos', 'Cantidad': row['admitidos']})
        if not ctx.df_primer_curso.empty:
            for _, row in ctx.df_primer_curso.iterrows():
                datos_combinados.append({'Año': row['anio'], 'Etapa': 'Primer Curso', 'Cantidad': row['primer_curso']})
        if not ctx.df_tendencia.empty:
            for _, row in ctx.df_tendencia.iterrows():
                datos_combinados.append({'Año': row['anio'], 'Etapa': 'Matriculados', 'Cantidad': row['matriculados']})
        if not ctx.df_graduados.empty:
            for _, row in ctx.df_graduados.iterrows():
                datos_combinados.append({'Año': row['anio'], 'Etapa': 'Graduados', 'Cantidad': row['graduados']})

        if datos_combinados:
            df_comb = pd.DataFrame(datos_combinados)
            fig_comb = px.line(
                df_comb, x='Año', y='Cantidad', color='Etapa',
                title=f"Evolución Completa del Ciclo Estudiantil | {ctx.label_ambito}",
                markers=True,
                color_discrete_map={
                    'Inscritos': '#9B1B30',
                    'Admitidos': '#6B9080',
                    'Primer Curso': '#D97706',
                    'Matriculados': '#52423C',
                    'Graduados': '#C7A951'
                }
            )
            fig_comb.update_layout(
                height=420,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                margin=dict(t=60),
                hovermode='x unified'
            )
            st.plotly_chart(fig_comb, width='stretch')
            descargar_datos_grafico(df_comb, "evolucion_estudiantil_combinado", "Descargar datos")
            st.caption("Fuente: SNIES - MEN Colombia")

    # =====================================================================
    # DESGLOSE DE LA OFERTA ACADEMICA
    # =====================================================================
    st.markdown("---")
    st.markdown("### Desglose de la Oferta Academica")
    st.caption("Como se distribuyen los programas segun modalidad, nivel, duracion, creditos y otros atributos academicos.")
    st.caption(f"Analisis detallado | {ctx.label_ambito}")

    # Fila 1: Modalidad y Sector (Tortas)
    col_mod, col_sec = st.columns([3, 2])

    with col_mod:
        st.markdown("#### Por Modalidad")
        df_mod = desglose.get('modalidad', pd.DataFrame())
        if not df_mod.empty:
            fig_mod = px.pie(
                df_mod,
                values='cantidad',
                names='categoria',
                title="Distribución por Modalidad",
                color_discrete_sequence=TEMPLATE_COLORS,
                hole=0.4
            )
            fig_mod.update_traces(textposition='inside', textinfo='percent+label')
            fig_mod.update_layout(showlegend=True)
            st.plotly_chart(fig_mod, width='stretch')
            descargar_datos_grafico(df_mod, "desglose_modalidad", "Descargar datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.warning("Sin datos de modalidad")

    with col_sec:
        st.markdown("#### Interpretación")
        presencial_pct = "mayoritariamente presencial" if not df_mod.empty and df_mod[df_mod['categoria'].str.upper().str.contains('PRESENCIAL', na=False)].empty else ""
        st.markdown(f"""<div style="font-size:0.85rem;color:#52423C;line-height:1.6;
            padding:0.6rem 0;">
            <p style="margin-bottom:0.5rem;">La modalidad <strong>dominante</strong> revela el formato preferido
            por los estudiantes en este NBC. Una alta concentración en una sola modalidad sugiere
            que el mercado ya está definido.</p>
            <p style="margin-bottom:0.5rem;">Si la modalidad virtual tiene baja participación pero el
            departamento objetivo tiene buena conectividad, existe una <strong>oportunidad de diferenciación</strong>.</p>
            <p>Combine este dato con el análisis territorial para decidir entre oferta presencial, virtual o híbrida.</p>
        </div>""", unsafe_allow_html=True)

    with col_sec:
        st.markdown("#### Por Sector")
        df_sec = desglose.get('sector', pd.DataFrame())
        if not df_sec.empty:
            fig_sec = px.pie(
                df_sec,
                values='cantidad',
                names='categoria',
                title="Distribución Oficial vs Privado",
                color_discrete_map={'Oficial': '#9b1b30', 'Privada': '#a0522d'},
                hole=0.4
            )
            fig_sec.update_traces(textposition='inside', textinfo='percent+label')
            fig_sec.update_layout(showlegend=True)
            st.plotly_chart(fig_sec, width='stretch')
            descargar_datos_grafico(df_sec, "desglose_sector", "Descargar datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.warning("Sin datos de sector")

    # Fila 2: Nivel de Formacion y Caracter Academico (Barras)
    col_niv, col_car = st.columns(2)

    with col_niv:
        st.markdown("#### Por Nivel de Formación")
        df_niv = desglose.get('nivel_formacion', pd.DataFrame())
        if not df_niv.empty:
            fig_niv = px.bar(
                df_niv.head(8),
                x='cantidad',
                y='categoria',
                orientation='h',
                title="Programas por Nivel de Formación",
                color='cantidad',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_niv.update_layout(
                height=320,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_niv, width='stretch')
            descargar_datos_grafico(df_niv, "desglose_nivel_formacion", "Descargar datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.warning("Sin datos de nivel de formación")

    with col_car:
        st.markdown("#### Por Carácter Académico IES")
        df_car = desglose.get('caracter_academico', pd.DataFrame())
        if not df_car.empty:
            fig_car = px.bar(
                df_car,
                x='cantidad',
                y='categoria',
                orientation='h',
                title="Tipo de Institución",
                color='cantidad',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_car.update_layout(
                height=320,
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_car, width='stretch')
            descargar_datos_grafico(df_car, "desglose_caracter_academico", "Descargar datos")
            st.caption(get_citacion("snies_instituciones"))
        else:
            st.warning("Sin datos de carácter académico")

    # Fila 3: Creditos y Duracion (Barras)
    col_cred, col_dur = st.columns(2)

    with col_cred:
        st.markdown("#### Distribución de Créditos")
        df_cred = desglose.get('creditos', pd.DataFrame())
        if not df_cred.empty:
            fig_cred = px.bar(
                df_cred,
                x='categoria',
                y='cantidad',
                title="Programas por Rango de Créditos",
                color='cantidad',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_cred.update_layout(
                height=300,
                xaxis_title="Rango de Créditos",
                yaxis_title="N° Programas",
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_cred, width='stretch')
            descargar_datos_grafico(df_cred, "desglose_creditos", "Descargar datos")
            st.caption(get_citacion("snies_programas"))

            stats_cred = desglose.get('estadisticas', {})
            if stats_cred:
                st.metric("Créditos Promedio", f"{stats_cred.get('creditos_promedio', 0):.0f}")
        else:
            st.warning("Sin datos de créditos")

    with col_dur:
        st.markdown("#### Distribución de Duración")
        df_dur = desglose.get('duracion', pd.DataFrame())
        if not df_dur.empty:
            fig_dur = px.bar(
                df_dur,
                x='categoria',
                y='cantidad',
                title="Programas por Duración",
                color='cantidad',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_dur.update_layout(
                height=300,
                xaxis_title="Duración (semestres)",
                yaxis_title="N° Programas",
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_dur, width='stretch')
            descargar_datos_grafico(df_dur, "desglose_duracion", "Descargar datos")
            st.caption(get_citacion("snies_programas"))

            stats_dur = desglose.get('estadisticas', {})
            if stats_dur:
                st.metric("Duración Promedio", f"{stats_dur.get('duracion_promedio', 0):.1f} semestres")
        else:
            st.warning("Sin datos de duración")

    # Fila 4: Periodicidad, Estado y Ciclos Propedeuticos
    col_per, col_est, col_cic = st.columns(3)

    with col_per:
        st.markdown("#### Periodicidad")
        df_per = desglose.get('periodicidad', pd.DataFrame())
        if not df_per.empty:
            fig_per = px.pie(
                df_per.head(5),
                values='cantidad',
                names='categoria',
                hole=0.5,
                color_discrete_sequence=TEMPLATE_COLORS
            )
            fig_per.update_traces(textposition='inside', textinfo='percent')
            fig_per.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_per, width='stretch')
            descargar_datos_grafico(df_per, "desglose_periodicidad", "Datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.info("Sin datos")

    with col_est:
        st.markdown("#### Estado Programa")
        df_est = desglose.get('estado', pd.DataFrame())
        if not df_est.empty:
            fig_est = px.pie(
                df_est,
                values='cantidad',
                names='categoria',
                hole=0.5,
                color_discrete_map={'Activo': '#6B9080', 'Inactivo': '#a0522d'}
            )
            fig_est.update_traces(textposition='inside', textinfo='percent')
            fig_est.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_est, width='stretch')
            descargar_datos_grafico(df_est, "desglose_estado", "Datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.info("Sin datos")

    with col_cic:
        st.markdown("#### Ciclos Propedéuticos")
        df_cic = desglose.get('ciclos_propedeuticos', pd.DataFrame())
        if not df_cic.empty:
            fig_cic = px.pie(
                df_cic,
                values='cantidad',
                names='categoria',
                hole=0.5,
                color_discrete_sequence=['#9b1b30', '#A09088', '#E5DDD6']
            )
            fig_cic.update_traces(textposition='inside', textinfo='percent')
            fig_cic.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_cic, width='stretch')
            descargar_datos_grafico(df_cic, "desglose_ciclos_propedeuticos", "Datos")
            st.caption(get_citacion("snies_programas"))
        else:
            st.info("Sin datos")

    # Fila 5: Distribucion Geografica
    st.markdown("---")
    st.markdown("#### Distribución Geográfica del NBC (Nacional)")
    df_deptos = desglose.get('departamentos', pd.DataFrame())
    if not df_deptos.empty:
        fig_geo = px.bar(
            df_deptos,
            x='cantidad',
            y='categoria',
            orientation='h',
            title=f"Top 10 Departamentos con programas de {ctx.filtro_label}",
            color='cantidad',
            color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
        )
        fig_geo.update_layout(
            height=400,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="N° de Programas",
            yaxis_title="Departamento",
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_geo, width='stretch')
        descargar_datos_grafico(df_deptos, "desglose_departamentos", "Descargar datos")
        st.caption(get_citacion("snies_programas"))
    else:
        st.warning("Sin datos de distribución geográfica")

    # Resumen de estadisticas clave
    st.markdown("---")
    st.markdown("#### Resumen Estadístico del NBC")
    stats_res = desglose.get('estadisticas', {})
    if stats_res:
        stat1, stat2, stat3, stat4 = st.columns(4)
        stat1.metric("Matrícula Promedio", f"${stats_res.get('costo_promedio', 0):,.0f}", help="Valor promedio matrícula estudiantes nuevos")
        stat2.metric("Matrícula Mínima", f"${stats_res.get('costo_min', 0):,.0f}")
        stat3.metric("Matrícula Máxima", f"${stats_res.get('costo_max', 0):,.0f}")
        stat4.metric("Vigencia Promedio", f"{stats_res.get('vigencia_promedio', 0):.1f} años")

    # Benchmarking original
    st.markdown("---")
    st.markdown("#### Benchmarking: Matrícula vs Duración")
    if not ctx.df_benchmark.empty:
        fig_scatter = px.scatter(
            ctx.df_benchmark,
            x='duracion',
            y='costo',
            color='acreditada',
            hover_data=['institucion', 'programa'],
            title="Posicionamiento de Programas (Duración vs Valor Matrícula)",
            labels={'duracion': 'Duración (semestres)', 'costo': 'Valor Matrícula ($)', 'acreditada': 'Acreditada'}
        )
        st.plotly_chart(fig_scatter, width='stretch')
        descargar_datos_grafico(ctx.df_benchmark, "benchmarking_matricula_duracion", "Descargar datos")
        st.caption(get_citacion("snies_programas"))
        st.caption("**Interpretación:** Buscar cuadrantes con baja densidad = oportunidad de diferenciación")
    else:
        st.warning("No hay datos suficientes para el benchmarking")

    # =====================================================================
    # EXPLORADOR INTERACTIVO DE DATOS
    # =====================================================================
    st.markdown("---")
    st.markdown("### :material/query_stats: Explorador Interactivo de Datos")
    st.caption("Construye tu propio grafico seleccionando metricas, dimensiones y tipo de visualizacion. "
               "Agrega mas dimensiones para hacer **drill-down** (desagregar por escalones).")

    col_exp_config1, col_exp_config2 = st.columns(2)

    with col_exp_config1:
        exp_metrica = st.selectbox(
            ":material/analytics: Metrica a analizar",
            options=['Matriculados', 'Graduados', 'Inscritos', 'Admitidos', 'Primer Curso'],
            index=0,
            help="Variable numerica que se sumara/agregara",
            key="exp_metrica"
        )

        dimensiones_disponibles = [
            'Ano', 'Semestre', 'Sexo', 'Nivel Academico', 'Nivel Formacion',
            'Metodologia', 'Area Conocimiento', 'NBC', 'Sector IES',
            'Caracter IES', 'Departamento', 'Municipio', 'Institucion',
            'IES Acreditada', 'Programa Acreditado'
        ]

        exp_dimensiones = st.multiselect(
            ":material/layers: Dimensiones (orden = jerarquia drill-down)",
            options=dimensiones_disponibles,
            default=['Ano'],
            help="Selecciona en orden: la primera es el eje principal, cada dimension adicional agrega un nivel de desagregacion",
            key="exp_dimensiones"
        )

    with col_exp_config2:
        tipos_grafico_disponibles = ['Barras Agrupadas', 'Linea Temporal', 'Barras Apiladas',
                                     'Sunburst (Drill-Down)', 'Treemap (Mapa de arbol)',
                                     'Tabla Pivot', 'Heatmap']

        default_tipo = 0
        if exp_dimensiones:
            if 'Ano' in exp_dimensiones and len(exp_dimensiones) <= 2:
                default_tipo = 1
            elif len(exp_dimensiones) >= 3:
                default_tipo = 3
            elif len(exp_dimensiones) == 2:
                default_tipo = 0

        exp_tipo_grafico = st.selectbox(
            ":material/bar_chart: Tipo de grafico",
            options=tipos_grafico_disponibles,
            index=default_tipo,
            help="Sunburst y Treemap son ideales para drill-down con 3+ dimensiones",
            key="exp_tipo_grafico"
        )

        exp_anio_rango = st.slider(
            ":material/date_range: Rango de anos",
            min_value=2010, max_value=2025,
            value=(2018, 2024),
            key="exp_anio_rango"
        )

        exp_top_n = st.slider(
            ":material/filter_list: Top N resultados",
            min_value=5, max_value=100, value=20,
            help="Limitar a los N valores mas grandes (evita graficos saturados)",
            key="exp_top_n"
        )

    if exp_dimensiones:
        with loading_overlay("Consultando datos..."):
            df_exp = get_datos_explorador_interactivo(
                metrica=exp_metrica,
                dimensiones=exp_dimensiones,
                anio_inicio=exp_anio_rango[0],
                anio_fin=exp_anio_rango[1],
                filtros_base=ctx.filtros_seleccionados
            )

        if not df_exp.empty:
            total_valor = df_exp['valor'].sum()
            st.info(f"**{len(df_exp):,} combinaciones** | Total {exp_metrica}: **{total_valor:,.0f}** | "
                    f"Periodo: {exp_anio_rango[0]}-{exp_anio_rango[1]}")

            dim1 = exp_dimensiones[0]
            dim2 = exp_dimensiones[1] if len(exp_dimensiones) >= 2 else None
            dim3 = exp_dimensiones[2] if len(exp_dimensiones) >= 3 else None

            es_temporal = exp_tipo_grafico == 'Linea Temporal'

            if es_temporal and dim1 == 'Ano':
                df_exp_sorted = df_exp.sort_values('valor', ascending=False)
                if dim2:
                    group_totals = df_exp.groupby(dim2)['valor'].sum().nlargest(exp_top_n).index
                    df_plot = df_exp[df_exp[dim2].isin(group_totals)].sort_values(dim1).copy()
                else:
                    df_plot = df_exp.sort_values(dim1).copy()
                df_plot[dim1] = df_plot[dim1].astype(int)
            else:
                df_exp_sorted = df_exp.sort_values('valor', ascending=False)
                if len(df_exp_sorted) > exp_top_n and exp_tipo_grafico not in ['Sunburst (Drill-Down)', 'Treemap (Mapa de arbol)', 'Tabla Pivot']:
                    df_plot = df_exp_sorted.head(exp_top_n)
                    st.caption(f"Mostrando top {exp_top_n} de {len(df_exp_sorted)} combinaciones")
                else:
                    df_plot = df_exp_sorted

            color_palette = TEMPLATE_COLORS * 4

            try:
                if exp_tipo_grafico == 'Barras Agrupadas':
                    if dim2:
                        df_plot[dim1] = df_plot[dim1].astype(str)
                        fig_exp = px.bar(
                            df_plot, x=dim1, y='valor', color=dim2,
                            barmode='group',
                            title=f"{exp_metrica} por {dim1} y {dim2}",
                            labels={'valor': exp_metrica},
                            color_discrete_sequence=color_palette,
                            text_auto=True
                        )
                        if dim3:
                            fig_exp = px.bar(
                                df_plot, x=dim1, y='valor', color=dim2,
                                facet_col=dim3, facet_col_wrap=3,
                                barmode='group',
                                title=f"{exp_metrica} por {dim1}, {dim2} y {dim3}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=color_palette
                            )
                    else:
                        df_plot[dim1] = df_plot[dim1].astype(str)
                        fig_exp = px.bar(
                            df_plot, x=dim1, y='valor',
                            title=f"{exp_metrica} por {dim1}",
                            labels={'valor': exp_metrica},
                            color='valor', color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                            text_auto=True
                        )
                    st.plotly_chart(fig_exp, width='stretch')

                elif exp_tipo_grafico == 'Linea Temporal':
                    if dim2:
                        fig_exp = px.line(
                            df_plot, x=dim1, y='valor', color=dim2,
                            markers=True,
                            title=f"Tendencia {exp_metrica} por {dim1} y {dim2}",
                            labels={'valor': exp_metrica},
                            color_discrete_sequence=color_palette
                        )
                        if dim3:
                            fig_exp = px.line(
                                df_plot, x=dim1, y='valor', color=dim2,
                                facet_col=dim3, facet_col_wrap=3,
                                markers=True,
                                title=f"Tendencia {exp_metrica} por {dim1}, {dim2} y {dim3}",
                                labels={'valor': exp_metrica},
                                color_discrete_sequence=color_palette
                            )
                    else:
                        fig_exp = px.line(
                            df_plot, x=dim1, y='valor',
                            markers=True,
                            title=f"Tendencia {exp_metrica} por {dim1}",
                            labels={'valor': exp_metrica},
                            color_discrete_sequence=['#9b1b30']
                        )
                    st.plotly_chart(fig_exp, width='stretch')

                elif exp_tipo_grafico == 'Barras Apiladas':
                    if dim2:
                        df_plot[dim1] = df_plot[dim1].astype(str)
                        fig_exp = px.bar(
                            df_plot, x=dim1, y='valor', color=dim2,
                            barmode='stack',
                            title=f"{exp_metrica} apilado por {dim1} y {dim2}",
                            labels={'valor': exp_metrica},
                            color_discrete_sequence=color_palette,
                            text_auto=True
                        )
                    else:
                        df_plot[dim1] = df_plot[dim1].astype(str)
                        fig_exp = px.bar(
                            df_plot, x=dim1, y='valor',
                            title=f"{exp_metrica} por {dim1}",
                            labels={'valor': exp_metrica},
                            color='valor', color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                            text_auto=True
                        )
                    st.plotly_chart(fig_exp, width='stretch')

                elif exp_tipo_grafico == 'Sunburst (Drill-Down)':
                    path_dims = exp_dimensiones[:min(len(exp_dimensiones), 5)]
                    for d in path_dims:
                        df_exp_sorted[d] = df_exp_sorted[d].fillna('Sin dato').astype(str)

                    fig_exp = px.sunburst(
                        df_exp_sorted,
                        path=path_dims,
                        values='valor',
                        title=f"Drill-Down: {exp_metrica} por {' > '.join(path_dims)}",
                        color='valor',
                        color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                        maxdepth=3
                    )
                    fig_exp.update_layout(height=450, uniformtext=dict(minsize=9, mode='hide'))
                    fig_exp.update_traces(
                        textinfo='label+percent parent',
                        insidetextorientation='radial',
                        textfont_size=11
                    )
                    st.plotly_chart(fig_exp, width='stretch')
                    st.caption("Haz clic en un segmento para hacer drill-down. Clic en el centro para volver atras.")

                elif exp_tipo_grafico == 'Treemap (Mapa de arbol)':
                    path_dims = exp_dimensiones[:min(len(exp_dimensiones), 5)]
                    for d in path_dims:
                        df_exp_sorted[d] = df_exp_sorted[d].fillna('Sin dato').astype(str)

                    fig_exp = px.treemap(
                        df_exp_sorted,
                        path=[px.Constant("Total")] + path_dims,
                        values='valor',
                        title=f"Treemap: {exp_metrica} por {' > '.join(path_dims)}",
                        color='valor',
                        color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                    )
                    fig_exp.update_layout(height=450, uniformtext=dict(minsize=9, mode='hide'))
                    fig_exp.update_traces(textinfo='label+percent parent', textfont_size=10)
                    st.plotly_chart(fig_exp, width='stretch')
                    st.caption("Haz clic en un bloque para hacer drill-down. Clic en el encabezado superior para volver.")

                elif exp_tipo_grafico == 'Tabla Pivot':
                    if dim2:
                        try:
                            pivot_df = df_exp.pivot_table(
                                index=dim1, columns=dim2, values='valor',
                                aggfunc='sum', fill_value=0
                            )
                            pivot_df['TOTAL'] = pivot_df.sum(axis=1)
                            pivot_df = pivot_df.sort_values('TOTAL', ascending=False)

                            st.markdown(f"**Tabla cruzada: {dim1} vs {dim2}** (valores = {exp_metrica})")
                            st.dataframe(
                                pivot_df.style.format("{:,.0f}").background_gradient(cmap='Blues', axis=None),
                                width='stretch', height=max(300, min(600, len(pivot_df) * 35))
                            )
                        except Exception:
                            st.dataframe(df_exp_sorted, hide_index=True, width='stretch', height=max(300, min(600, len(df_exp_sorted) * 35)))
                    else:
                        st.dataframe(
                            df_exp_sorted.style.format({'valor': '{:,.0f}', 'registros': '{:,.0f}'}),
                            hide_index=True, width='stretch', height=max(300, min(600, len(df_exp_sorted) * 35))
                        )

                elif exp_tipo_grafico == 'Heatmap':
                    if dim2:
                        try:
                            pivot_heat = df_exp.pivot_table(
                                index=dim2, columns=dim1, values='valor',
                                aggfunc='sum', fill_value=0
                            )
                            fig_exp = go.Figure(data=go.Heatmap(
                                z=pivot_heat.values,
                                x=[str(c) for c in pivot_heat.columns],
                                y=[str(i) for i in pivot_heat.index],
                                colorscale='YlOrRd',
                                text=[[f"{v:,.0f}" for v in row] for row in pivot_heat.values],
                                texttemplate="%{text}",
                                textfont={"size": 9},
                            ))
                            fig_exp.update_layout(
                                title=f"Heatmap: {exp_metrica} ({dim1} vs {dim2})",
                                height=max(400, len(pivot_heat) * 30 + 100),
                                xaxis_title=dim1, yaxis_title=dim2
                            )
                            st.plotly_chart(fig_exp, width='stretch')
                        except Exception as e_heat:
                            st.warning(f"No se pudo generar heatmap: {e_heat}")
                    else:
                        st.warning("El heatmap requiere al menos 2 dimensiones")

            except Exception as e_chart:
                st.error(f"Error generando grafico: {e_chart}")
                st.dataframe(df_exp_sorted.head(50), hide_index=True, width='stretch')

            descargar_datos_grafico(df_exp_sorted, f"explorador_{exp_metrica.lower()}", "Descargar datos del explorador")

            with st.expander(":material/help: Tips de uso del Explorador", expanded=False):
                st.markdown("""
                **Como usar el Explorador Interactivo:**

                1. **Selecciona una metrica** (Matriculados, Graduados, etc.)
                2. **Agrega dimensiones en orden de jerarquia:**
                   - 1 dimension = grafico simple (barras o linea)
                   - 2 dimensiones = grafico agrupado/coloreado
                   - 3+ dimensiones = drill-down con Sunburst o Treemap
                3. **Orden importa:** La primera dimension es el nivel mas alto, cada una agrega un escalon de detalle
                4. **Drill-down interactivo:** En Sunburst y Treemap, haz clic para profundizar

                **Ejemplos utiles:**
                - `Ano + Metodologia` = Tendencia por modalidad
                - `Ano + Nivel Formacion + Sexo` = Tendencia por nivel y genero
                - `Departamento + NBC + Institucion` = Drill-down geografico
                - `Sector IES + Nivel Formacion + Metodologia` = Composicion institucional

                **Tipos de grafico recomendados:**
                - **Linea Temporal**: Cuando la primera dimension es Ano
                - **Sunburst/Treemap**: Para 3+ dimensiones (drill-down real)
                - **Heatmap**: Para cruce de 2 dimensiones categoricas
                - **Tabla Pivot**: Para analisis numerico detallado
                """)
        else:
            st.warning("No se encontraron datos con los filtros y dimensiones seleccionadas. "
                       "Intente ampliar el rango de anos o cambiar las dimensiones.")
    else:
        st.info(":material/touch_app: Selecciona al menos una dimension para generar el grafico interactivo.")

    # =====================================================================
    # SECCION COMPLEMENTARIA SIET/ETDH
    # =====================================================================
    if ctx.tiene_filtros_siet:
        st.markdown("---")
        st.markdown("### Contexto Complementario: Educación para el Trabajo (ETDH)")
        render_etdh_dashboard(
            areas_desempeno=ctx.effective_areas_siet,
            deptos=ctx.effective_deptos_siet,
            estados_siet=ctx.sel_estados_siet if ctx.sel_estados_siet else None,
            busqueda_nombre=ctx.busqueda_programa if ctx.busqueda_programa else None,
            ml_areas_siet=ctx._ml_areas_siet,
            etdh_ml_stats=ctx.etdh_ml_stats,
            sel_nbcs=ctx.sel_nbcs, sel_campos_amplios=ctx.sel_campos_amplios, sel_areas=ctx.sel_areas,
            tiene_filtros_academicos_snies=ctx.tiene_filtros_academicos_snies,
            modalidades_siet=ctx.sel_modalidades_siet if ctx.sel_modalidades_siet else None,
            key_prefix="etdh_academic"
        )

    return {'desglose': desglose}
