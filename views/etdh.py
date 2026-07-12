"""Dashboard SIET/ETDH — Educacion para el Trabajo y Desarrollo Humano."""

import pandas as pd
import streamlit as st
from data import (
    get_estadisticas_siet, get_siet_tendencia_matricula,
    get_siet_tendencia_certificados, get_siet_tasa_certificacion_historica,
    get_siet_tendencia_por_area, get_siet_top_instituciones,
    get_siet_top_programas, get_siet_matricula_por_depto,
    get_siet_desglose_oferta, get_programas_detalle_siet,
)
from services.sources import get_citacion
from utils.helpers import descargar_datos_grafico

# Nombres de columna en DataFrames de queries SIET (evita bugs de acentos)
COL_ANIO = 'Año'
COL_MATRICULADOS = 'Matriculados'
COL_CERTIFICADOS = 'Certificados'
COL_TASA_CERT = 'Tasa Certificación (%)'
COL_AREA = 'Área'
COL_DEPARTAMENTO = 'Departamento'


def render_etdh_dashboard(areas_desempeno, deptos, estados_siet, busqueda_nombre,
                          ml_areas_siet=None, etdh_ml_stats=None,
                          sel_nbcs=None, sel_campos_amplios=None, sel_areas=None,
                          tiene_filtros_academicos_snies=False, key_prefix="etdh",
                          modalidades_siet=None):
    _safe_ml_areas = [a for a in ml_areas_siet if a is not None] if ml_areas_siet else []
    if _safe_ml_areas:
        if sel_nbcs:
            nbc_list_str = ', '.join(sel_nbcs[:3])
            st.caption(f"Filtrado por cadena estructural: NBC ({nbc_list_str}) -> CINE-F -> Area Cualificacion CUOC -> "
                      f"Areas SIET identificadas: **{', '.join(ml_areas_siet)}**")
        elif sel_campos_amplios:
            ca_list_str = ', '.join(sel_campos_amplios[:3])
            st.caption(f"Filtrado por mapeo Campo Amplio ({ca_list_str}) -> "
                      f"Areas SIET identificadas: **{', '.join(ml_areas_siet)}**")
        elif sel_areas:
            area_list_str = ', '.join(sel_areas[:3])
            st.caption(f"Filtrado por Area de Conocimiento ({area_list_str}) -> Campo Amplio CINE-F -> "
                      f"Areas SIET identificadas: **{', '.join(ml_areas_siet)}**")
    elif tiene_filtros_academicos_snies:
        st.caption("Filtros academicos activos pero sin matching ML disponible — mostrando datos SIET con filtros directos")
    else:
        st.caption("Sistema de Informacion de la Educacion para el Trabajo — Datos SIET/MEN 2010-2023")

    stats_siet = get_estadisticas_siet(
        areas_desempeno=areas_desempeno,
        deptos=deptos,
        estados=estados_siet,
        busqueda_nombre=busqueda_nombre,
        modalidades_siet=modalidades_siet
    )

    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    if etdh_ml_stats and etdh_ml_stats.get('tiene_datos'):
        col_s1.metric("Programas ML", f"{etdh_ml_stats['programas_siet_relacionados']:,}",
                     help="Programas matcheados via competencias CUOC")
        col_s2.metric("Programas (Area)", f"{stats_siet['total_programas']:,}")
    else:
        col_s1.metric("Programas ETDH", f"{stats_siet['total_programas']:,}")
        col_s2.metric("Instituciones", f"{stats_siet['total_instituciones']:,}")
    col_s3.metric("Matriculados 2023", f"{stats_siet['total_matriculados']:,}")
    col_s4.metric("Certificados 2023", f"{stats_siet['total_certificados']:,}")

    tasa_cert = round(stats_siet['total_certificados'] / max(stats_siet['total_matriculados'], 1) * 100, 1)
    col_s5.metric("Tasa Certificacion", f"{tasa_cert}%",
                 help="Certificados / Matriculados x 100")

    st.markdown("#### Tendencia Historica ETDH (2010-2023)")

    df_tend_mat = get_siet_tendencia_matricula(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    df_tend_cert = get_siet_tendencia_certificados(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    df_tasa_hist = get_siet_tasa_certificacion_historica(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)

    _render_tendencias(df_tend_mat, df_tend_cert, df_tasa_hist, key_prefix)
    _render_tendencia_por_area(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet)
    _render_rankings(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet)
    _render_distribucion_geografica(areas_desempeno, estados_siet, busqueda_nombre, key_prefix, modalidades_siet)
    _render_caracterizacion_oferta(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet)
    _render_ml_top_programas(etdh_ml_stats, key_prefix)
    _render_detalle_completo(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet)

    st.caption("**SIET:** Sistema de Informacion de la Educacion para el Trabajo — MEN Colombia (2010-2023)")


def _render_tendencias(df_tend_mat, df_tend_cert, df_tasa_hist, key_prefix):
    import plotly.graph_objects as go
    import plotly.express as px

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if not df_tend_mat.empty and not df_tend_cert.empty:
            fig_tend = go.Figure()
            fig_tend.add_trace(go.Bar(
                x=df_tend_mat['Año'], y=df_tend_mat['Matriculados'],
                name='Matriculados', marker_color='#A09088', opacity=0.7,
                hovertemplate='Año: %{x}<br>Matriculados: %{y:,.0f}<extra></extra>'
            ))
            fig_tend.add_trace(go.Scatter(
                x=df_tend_cert['Año'], y=df_tend_cert['Certificados'],
                name='Certificados', line=dict(color='#a0522d', width=3),
                yaxis='y2',
                hovertemplate='Año: %{x}<br>Certificados: %{y:,.0f}<extra></extra>'
            ))
            fig_tend.update_layout(
                title=dict(text="Matricula vs Certificados ETDH", y=0.97),
                yaxis=dict(title=dict(text="Matriculados", font=dict(size=11)), side='left'),
                yaxis2=dict(title=dict(text="Certificados", font=dict(size=11)), side='right', overlaying='y'),
                margin=dict(r=70, t=50),
                height=460,
                legend=dict(orientation='h', yanchor='top', y=-0.18, xanchor='center', x=0.5),
                hovermode='x unified'
            )
            fig_tend.update_xaxes(tickangle=-45, tickmode='linear', dtick=2, tickfont=dict(size=9))
            st.plotly_chart(fig_tend, width='stretch', key=f"{key_prefix}_tend_mat_cert")
            descargar_datos_grafico(df_tend_mat, f"siet_tendencia_matricula_{key_prefix}", "Descargar datos")
        else:
            st.info("Sin datos de tendencia ETDH")

    with col_t2:
        if not df_tasa_hist.empty:
            fig_tasa = px.line(
                df_tasa_hist, x=COL_ANIO, y=COL_TASA_CERT,
                title="Tasa de Certificacion ETDH (%)",
                markers=True, line_shape='spline'
            )
            fig_tasa.update_traces(line=dict(color='#6B9080', width=3))
            fig_tasa.update_layout(yaxis_title="Tasa (%)")
            last = df_tasa_hist.iloc[-1]
            fig_tasa.add_annotation(
                x=last[COL_ANIO], y=last[COL_TASA_CERT],
                text=f"{last[COL_TASA_CERT]}%", showarrow=True,
                arrowhead=2, font=dict(size=12, color='#6B9080')
            )
            st.plotly_chart(fig_tasa, width='stretch', key=f"{key_prefix}_tasa_cert")
            descargar_datos_grafico(df_tasa_hist, f"siet_tasa_certificacion_{key_prefix}", "Descargar datos")
        else:
            st.info("Sin datos de tasa de certificacion")


def _render_tendencia_por_area(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet):
    import plotly.express as px

    df_tend_area = get_siet_tendencia_por_area(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    if not df_tend_area.empty:
        n_areas = df_tend_area['Área'].nunique()
        with st.expander("Tendencia por Area de Desempeno", expanded=False, icon=":material/trending_up:"):
            if n_areas > 1:
                fig_area_tend = px.line(
                    df_tend_area, x='Año', y='Matriculados', color='Área',
                    title="Evolucion de Matricula ETDH por Area de Desempeno",
                    markers=True
                )
                fig_area_tend.update_layout(legend=dict(font=dict(size=9)))
            else:
                area_nombre = df_tend_area['Área'].iloc[0]
                fig_area_tend = px.line(
                    df_tend_area, x='Año', y='Matriculados',
                    title=f"Evolucion de Matricula ETDH — {area_nombre}",
                    markers=True,
                    color_discrete_sequence=['#d4a017']
                )
                fig_area_tend.update_layout(legend=dict(font=dict(size=9)))
            st.plotly_chart(fig_area_tend, width='stretch', key=f"{key_prefix}_tend_area")
            descargar_datos_grafico(df_tend_area, f"siet_tendencia_area_{key_prefix}", "Descargar datos")
            st.caption(get_citacion("siet_matricula_programa_"))


def _render_rankings(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet):
    import plotly.express as px

    st.markdown("#### Rankings ETDH")

    df_top_inst = get_siet_top_instituciones(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    df_top_prog = get_siet_top_programas(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("##### Top Instituciones por Matricula")
        if not df_top_inst.empty:
            fig_inst = px.bar(
                df_top_inst.head(10),
                x='matricula_2023', y='institucion', orientation='h',
                color='naturaleza', title="Top 10 Instituciones ETDH",
                hover_data=['programas', 'certificados_2023', 'variacion_pct']
            )
            fig_inst.update_layout(
                height=400, yaxis={'categoryorder': 'total ascending'},
                legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=9)),
                yaxis_title="", xaxis_title="Matricula 2023"
            )
            fig_inst.update_yaxes(tickfont=dict(size=9))
            st.plotly_chart(fig_inst, width='stretch', key=f"{key_prefix}_top_inst")

            with st.expander("Ver tabla detallada", expanded=False):
                df_show = df_top_inst.rename(columns={
                    'institucion': 'Institucion', 'naturaleza': 'Naturaleza',
                    'programas': 'Programas', 'matricula_2023': 'Matricula 2023',
                    'certificados_2023': 'Certificados 2023', 'variacion_pct': 'Var. % Anual'
                })
                st.dataframe(df_show[['Institucion', 'Naturaleza', 'Programas',
                                       'Matricula 2023', 'Certificados 2023', 'Var. % Anual']],
                            hide_index=True, width='stretch')
                descargar_datos_grafico(df_show, f"siet_top_instituciones_{key_prefix}", "Descargar datos")
        else:
            st.info("Sin datos de instituciones")

    with col_r2:
        st.markdown("##### Top Programas por Matricula")
        if not df_top_prog.empty:
            fig_prog = px.bar(
                df_top_prog.head(10),
                x='matricula_2023', y='programa', orientation='h',
                color='area', title="Top 10 Programas ETDH",
                hover_data=['instituciones', 'certificados_2023', 'tasa_certificacion']
            )
            fig_prog.update_layout(
                height=400, yaxis={'categoryorder': 'total ascending'},
                legend=dict(orientation='h', yanchor='bottom', y=1.02, font=dict(size=9)),
                yaxis_title="", xaxis_title="Matricula 2023"
            )
            fig_prog.update_yaxes(tickfont=dict(size=9))
            st.plotly_chart(fig_prog, width='stretch', key=f"{key_prefix}_top_prog")

            with st.expander("Ver tabla detallada", expanded=False):
                df_show = df_top_prog.rename(columns={
                    'programa': 'Programa', 'area': 'Area', 'tipo_certificado': 'Tipo',
                    'instituciones': 'Instituciones', 'matricula_2023': 'Matricula 2023',
                    'certificados_2023': 'Certificados 2023', 'tasa_certificacion': 'Tasa Cert. %'
                })
                st.dataframe(df_show[['Programa', 'Area', 'Tipo', 'Instituciones',
                                       'Matricula 2023', 'Certificados 2023', 'Tasa Cert. %']],
                            hide_index=True, width='stretch')
                descargar_datos_grafico(df_show, f"siet_top_programas_{key_prefix}", "Descargar datos")
        else:
            st.info("Sin datos de programas")


def _render_distribucion_geografica(areas_desempeno, estados_siet, busqueda_nombre, key_prefix, modalidades_siet):
    import plotly.express as px

    df_mat_depto = get_siet_matricula_por_depto(areas_desempeno, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    if not df_mat_depto.empty:
        with st.expander("Distribucion Geografica ETDH", expanded=False, icon=":material/map:"):
            col_g1, col_g2 = st.columns([3, 2])
            with col_g1:
                fig_geo = px.bar(
                    df_mat_depto.head(15),
                    x='matricula_2023', y='departamento', orientation='h',
                    title="Top Departamentos ETDH — Matricula 2023",
                    color='variacion_anual_pct',
                    color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                    color_continuous_midpoint=0,
                    hover_data=['instituciones', 'programas', 'cagr_4y_pct']
                )
                fig_geo.update_layout(
                    height=450, yaxis={'categoryorder': 'total ascending'},
                    coloraxis_colorbar=dict(title="Var. Anual %"),
                    yaxis_title="", xaxis_title="Matricula 2023"
                )
                st.plotly_chart(fig_geo, width='stretch', key=f"{key_prefix}_geo")
            with col_g2:
                st.markdown("**Detalle por Departamento**")
                df_geo_show = df_mat_depto.rename(columns={
                    'departamento': 'Departamento', 'matricula_2023': 'Mat. 2023',
                    'variacion_anual_pct': 'Var. Anual %', 'cagr_4y_pct': 'CAGR 4A %',
                    'instituciones': 'Instit.', 'programas': 'Progs.'
                })
                st.dataframe(df_geo_show[['Departamento', 'Mat. 2023', 'Var. Anual %',
                                           'CAGR 4A %', 'Instit.', 'Progs.']],
                            hide_index=True, width='stretch', height=max(300, min(600, len(df_geo_show)*35)))
                descargar_datos_grafico(df_geo_show, f"siet_deptos_{key_prefix}", "Descargar datos")
            st.caption(get_citacion("siet_matricula_programa_"))


def _render_caracterizacion_oferta(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet):
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd

    desglose = get_siet_desglose_oferta(areas_desempeno, deptos, estados_siet, busqueda_nombre, modalidades_siet=modalidades_siet)
    if not desglose:
        return

    with st.expander("Caracterizacion de la Oferta ETDH", expanded=False, icon=":material/school:"):
        col_c1, col_c2, col_c3 = st.columns(3)

        with col_c1:
            df_tc = desglose.get('tipo_certificado', pd.DataFrame())
            if not df_tc.empty:
                fig_tc = px.pie(df_tc, values='programas', names='tipo',
                               title="Tipo de Certificado", hole=0.35)
                fig_tc.update_layout(showlegend=True, legend=dict(font=dict(size=9)))
                fig_tc.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_tc, width='stretch', key=f"{key_prefix}_tipo_cert")

            df_esc = desglose.get('escolaridad', pd.DataFrame())
            if not df_esc.empty:
                fig_esc = px.bar(df_esc, x='programas', y='escolaridad', orientation='h',
                                title="Escolaridad Requerida", color='programas',
                                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']])
                fig_esc.update_layout(yaxis={'categoryorder': 'total ascending'},
                                     coloraxis_showscale=False, yaxis_title="")
                st.plotly_chart(fig_esc, width='stretch', key=f"{key_prefix}_escolaridad")

        with col_c2:
            df_met = desglose.get('metodologia', pd.DataFrame())
            if not df_met.empty:
                fig_met = px.pie(df_met, values='programas', names='metodologia',
                                title="Metodologia", hole=0.35)
                fig_met.update_layout(showlegend=True, legend=dict(font=dict(size=9)))
                fig_met.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_met, width='stretch', key=f"{key_prefix}_metodologia")

            df_jor = desglose.get('jornada', pd.DataFrame())
            if not df_jor.empty:
                fig_jor = px.bar(df_jor, x='programas', y='jornada', orientation='h',
                                title="Jornada", color='programas',
                                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']])
                fig_jor.update_layout(yaxis={'categoryorder': 'total ascending'},
                                     coloraxis_showscale=False, yaxis_title="")
                st.plotly_chart(fig_jor, width='stretch', key=f"{key_prefix}_jornada")

        with col_c3:
            df_cos = desglose.get('costos', pd.DataFrame())
            if not df_cos.empty:
                fig_cos = px.bar(df_cos, x='rango_costo', y='programas',
                                title="Distribucion de Costos",
                                color='duracion_promedio',
                                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                                text='programas')
                fig_cos.update_layout(coloraxis_colorbar=dict(title="Dur. (h)"),
                                     xaxis_title="Rango de Costo")
                fig_cos.update_traces(textposition='auto')
                st.plotly_chart(fig_cos, width='stretch', key=f"{key_prefix}_costos")

            df_est = desglose.get('estado', pd.DataFrame())
            if not df_est.empty:
                fig_est = px.pie(df_est, values='programas', names='estado',
                                title="Estado del Programa", hole=0.35)
                fig_est.update_layout(showlegend=True, legend=dict(font=dict(size=9)))
                fig_est.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_est, width='stretch', key=f"{key_prefix}_estado")

        df_cpa = desglose.get('costo_por_area', pd.DataFrame())
        if not df_cpa.empty:
            st.markdown("**Costo Promedio y Duracion por Area de Desempeno**")
            fig_cpa = go.Figure()
            fig_cpa.add_trace(go.Bar(
                x=df_cpa['area'], y=df_cpa['costo_promedio'],
                name='Costo Promedio ($)', marker_color='#d4835a'
            ))
            fig_cpa.add_trace(go.Scatter(
                x=df_cpa['area'], y=df_cpa['duracion_promedio'],
                name='Duracion (hrs)', yaxis='y2',
                line=dict(color='#a0522d', width=3), mode='lines+markers'
            ))
            fig_cpa.update_layout(
                height=350,
                yaxis=dict(title="Costo Promedio ($)", side='left'),
                yaxis2=dict(title="Duracion (hrs)", side='right', overlaying='y'),
                margin=dict(r=70),
                legend=dict(orientation='h', yanchor='bottom', y=1.02)
            )
            st.plotly_chart(fig_cpa, width='stretch', key=f"{key_prefix}_costo_area")

        st.caption(get_citacion("siet_programas"))


def _render_ml_top_programas(etdh_ml_stats, key_prefix):
    if not (etdh_ml_stats and etdh_ml_stats.get('top_programas')):
        return

    with st.expander("Top Programas ETDH Relacionados (Matching ML)", expanded=True, icon=":material/psychology:"):
        top_progs = etdh_ml_stats['top_programas'][:10]
        df_top_ml = pd.DataFrame(top_progs)
        if not df_top_ml.empty:
            df_top_display = df_top_ml.rename(columns={
                'nombre': 'Programa ETDH', 'area': 'Area Desempeno',
                'score': 'Score ML', 'matricula': 'Matricula 2023',
                'certificados': 'Certificados 2023', 'duracion_horas': 'Duracion (Hrs)'
            })
            cols_show = [c for c in ['Programa ETDH', 'Area Desempeno', 'Score ML',
                                      'Matricula 2023', 'Certificados 2023', 'Duracion (Hrs)']
                        if c in df_top_display.columns]
            st.dataframe(
                df_top_display[cols_show], hide_index=True, width='stretch',
                column_config={"Score ML": st.column_config.ProgressColumn(
                    "Score ML", min_value=0, max_value=1, format="%.3f"
                )}
            )
            st.caption("Matching basado en competencias CUOC — paraphrase-multilingual-MiniLM-L12-v2")


def _render_detalle_completo(areas_desempeno, deptos, estados_siet, busqueda_nombre, key_prefix, modalidades_siet):
    import io

    with st.expander("Ver Detalle Completo de Programas ETDH", expanded=False, icon=":material/list_alt:"):
        df_detalle_siet = get_programas_detalle_siet(
            areas_desempeno=areas_desempeno, deptos=deptos,
            estados=estados_siet, busqueda_nombre=busqueda_nombre,
            modalidades_siet=modalidades_siet
        )
        if not df_detalle_siet.empty:
            st.markdown(f"**{len(df_detalle_siet):,} programas ETDH encontrados**")
            st.dataframe(
                df_detalle_siet, hide_index=True, width='stretch', height=max(300, min(600, len(df_detalle_siet)*35)),
                column_config={
                    "Institucion": st.column_config.TextColumn("Institucion", width="large"),
                    "Programa": st.column_config.TextColumn("Programa", width="large"),
                    "Departamento": st.column_config.TextColumn("Departamento", width="medium"),
                    "Area Desempeno": st.column_config.TextColumn("Area", width="medium"),
                    "Estado": st.column_config.TextColumn("Estado", width="small"),
                    "Duracion (Hrs)": st.column_config.NumberColumn("Duracion (Hrs)", width="small"),
                    "Costo": st.column_config.NumberColumn("Costo", format="$%d", width="small")
                }
            )
            buffer_siet = io.BytesIO()
            df_detalle_siet.to_excel(buffer_siet, index=False, engine='openpyxl')
            buffer_siet.seek(0)
            st.download_button(
                label="Descargar Excel completo",
                data=buffer_siet,
                file_name="programas_ETDH.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
                key=f"download_siet_excel_{key_prefix}"
            )
        else:
            st.info("No se encontraron programas ETDH con los filtros aplicados")
