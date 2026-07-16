"""
Sintesis Laboral: ratio de absorcion, vacantes APE, competencias
CUOC, salarios OLE/SIGEP, puente SNIES-SIET, cualificaciones MEN
y perfiles ocupacionales.
"""
import html

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config.constants import TEMPLATE_COLORS
from components.display import section_header
from utils.helpers import descargar_datos_grafico
from services.sources import get_citacion
from services import calcular_ratio_absorcion
from data import (
    get_vacantes_reales,
    get_competencias_cuoc,
    get_salarios_reales,
    get_tendencia_laboral_nbc,
    get_graduados_nbc_historico,
    get_graduados_nacionales,
    get_cualificaciones_por_nbc,
    get_estadisticas_cualificaciones_men,
    get_actividades_tareas_nbc,
    mapear_niveles_snies_a_mnc,
)


def render_tab_laboral(ctx):
    """Renderiza la sintesis laboral del dashboard.

    Retorna un dict con vacantes, competencias, salarios y actividades
    para que Tab 4 los use en el scoring laboral y el contexto del LLM.
    """
    section_header("02", "Pertinencia Laboral", "La formacion se conecta con ocupaciones, competencias y oportunidades reales de insercion que fortalecen la empleabilidad y la permanencia?")

    # Obtener datos reales laborales
    if len(ctx.sel_nbcs) > 1:
        _dfs_vac, _dfs_con, _dfs_des = [], [], []
        for _nbc_i in ctx.sel_nbcs[:5]:
            _v = get_vacantes_reales(_nbc_i)
            if not _v.empty:
                _dfs_vac.append(_v)
            _c, _d = get_competencias_cuoc(_nbc_i)
            if not _c.empty:
                _dfs_con.append(_c)
            if not _d.empty:
                _dfs_des.append(_d)
        df_vacantes = pd.concat(_dfs_vac, ignore_index=True).drop_duplicates(subset=['ocupacion']).head(20) if _dfs_vac else pd.DataFrame()
        df_conocimientos = pd.concat(_dfs_con, ignore_index=True).drop_duplicates().head(20) if _dfs_con else pd.DataFrame()
        df_destrezas = pd.concat(_dfs_des, ignore_index=True).drop_duplicates().head(20) if _dfs_des else pd.DataFrame()
    else:
        df_vacantes = get_vacantes_reales(ctx.sel_nbc)
        df_conocimientos, df_destrezas = get_competencias_cuoc(ctx.sel_nbc)

    _sel_depto_sal = ctx.sel_deptos[0] if ctx.sel_deptos and len(ctx.sel_deptos) > 0 else None
    if ctx.sel_deptos and len(ctx.sel_deptos) > 1:
        st.warning(f"Salarios: mostrando datos para **{html.escape(ctx.sel_deptos[0])}** (primer departamento seleccionado de {len(ctx.sel_deptos)}).")
    datos_salarios = get_salarios_reales(ctx.sel_nbc, departamento=_sel_depto_sal)

    df_tend_vac, df_tend_ins, df_tend_col = get_tendencia_laboral_nbc(ctx.sel_nbc)
    df_graduados_nbc = get_graduados_nbc_historico(ctx.sel_nbc, filtros=ctx.filtros_seleccionados)

    # =====================================================================
    # RATIO DE ABSORCION LABORAL
    # =====================================================================
    col_abs, col_sal = st.columns(2)

    with col_abs:
        st.markdown("#### Ratio de Absorcion Laboral (Nacional)")

        if not df_vacantes.empty:
            vacantes_reales = int(df_vacantes['vacantes_2024'].sum())
        else:
            vacantes_reales = ctx.vacantes_est

        es_analisis_territorial = ctx.sel_deptos is not None and len(ctx.sel_deptos) > 0

        if es_analisis_territorial and vacantes_reales > 0:
            graduados_nacionales = get_graduados_nacionales(ctx.sel_nbcs if ctx.sel_nbcs else ctx.sel_nbc, filtros=ctx.filtros_seleccionados)
            graduados_para_ratio = graduados_nacionales if graduados_nacionales > 0 else ctx.graduados_anual
            nota_territorial = True
        else:
            graduados_para_ratio = ctx.graduados_anual
            graduados_nacionales = ctx.graduados_anual
            nota_territorial = False

        ratio_abs_real, ratio_interp_real = calcular_ratio_absorcion(graduados_para_ratio, vacantes_reales)

        fig_abs = go.Figure()
        fig_abs.add_trace(go.Bar(
            name=f'Graduados/ano {"(Nacional)" if nota_territorial else ""}',
            x=['Oferta vs Demanda'],
            y=[graduados_para_ratio],
            marker_color='#9b1b30',
            text=[f'{graduados_para_ratio:,}'],
            textposition='auto'
        ))
        fig_abs.add_trace(go.Bar(
            name='Vacantes APE 2024 (Nacional)',
            x=['Oferta vs Demanda'],
            y=[vacantes_reales],
            marker_color='#6B9080',
            text=[f'{vacantes_reales:,}'],
            textposition='auto'
        ))
        fig_abs.update_layout(
            barmode='group',
            height=300,
            title=f"Ratio: {ratio_abs_real}"
        )
        st.plotly_chart(fig_abs, width='stretch')
        df_absorcion = pd.DataFrame({
            'Concepto': ['Graduados/ano', 'Vacantes APE 2024'],
            'Cantidad': [graduados_para_ratio, vacantes_reales]
        })
        descargar_datos_grafico(df_absorcion, "ratio_absorcion_laboral", "Descargar datos")
        st.caption(get_citacion("vacantes_ape"))
        st.info(ratio_interp_real)

        if nota_territorial:
            st.caption(f"""
            **Nota metodologica:** Las vacantes APE son a nivel nacional.
            Se usan graduados nacionales ({graduados_nacionales:,})
            en lugar de graduados solo de {ctx.arg_depto} ({ctx.graduados_anual:,.0f}).
            """)

        if ctx.etdh_ml_stats and ctx.etdh_ml_stats.get('tiene_datos', False):
            siet_cert = ctx.etdh_ml_stats.get('certificados_siet', 0)
            siet_mat = ctx.etdh_ml_stats.get('matricula_siet', 0)
            if siet_cert > 0 or siet_mat > 0:
                total_formados = int(graduados_para_ratio + siet_cert)
                st.caption(f"""
                Incluyendo ETDH/SENA: Total formados: {total_formados:,}
                ({graduados_para_ratio:,} graduados SNIES + {siet_cert:,} certificados SIET).
                Matricula ETDH relacionada: {siet_mat:,}.
                """)

        if not df_vacantes.empty:
            st.markdown("**Top Ocupaciones con Vacantes:**")
            st.dataframe(
                df_vacantes.head(5)[['ocupacion', 'vacantes_2024', 'vacantes_2023']].rename(
                    columns={'ocupacion': 'Ocupacion', 'vacantes_2024': 'Vacantes 2024', 'vacantes_2023': 'Vacantes 2023'}
                ),
                hide_index=True,
                width='stretch'
            )

    with col_sal:
        st.markdown("#### Referencia Salarial (Datos Oficiales)")
        smlv = 1_423_500

        if datos_salarios['tiene_datos']:
            df_ibc = datos_salarios.get('ole_ibc', pd.DataFrame())
            if not df_ibc.empty:
                ibc_formacion = df_ibc[df_ibc['tipo'] == 'nivel_formacion']
                if not ibc_formacion.empty:
                    fig_sal = go.Figure()
                    for _, row in ibc_formacion.iterrows():
                        fig_sal.add_trace(go.Bar(
                            name=str(row['categoria']),
                            x=[str(row['categoria'])],
                            y=[float(row['ibc_max_pesos'])],
                            base=[float(row['ibc_min_pesos'])],
                            text=[f"${float(row['ibc_min_pesos']):,.0f} - ${float(row['ibc_max_pesos']):,.0f}"],
                            textposition='auto',
                            marker_color='#a0522d' if 'Pregrado' in str(row['categoria']) else '#9b1b30'
                        ))
                    fig_sal.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                     annotation_text=f"SMLV: ${smlv:,}")
                    fig_sal.update_layout(
                        height=300,
                        title="IBC Graduados (OLE - MinEducacion)",
                        yaxis_title="Ingreso Base Cotizacion ($)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_sal, width='stretch')
                    ano_seg = df_ibc['ano_seguimiento'].iloc[0] if 'ano_seguimiento' in df_ibc.columns else '?'
                    cohorte = df_ibc['cohorte_graduados'].iloc[0] if 'cohorte_graduados' in df_ibc.columns else '?'
                    st.caption(f"**Fuente:** OLE - Observatorio Laboral para la Educacion (MinEducacion). "
                              f"Seguimiento {ano_seg}, cohorte graduados {cohorte}. "
                              f"IBC = Ingreso Base de Cotizacion al sistema de seguridad social.")

                ibc_sector = df_ibc[df_ibc['tipo'] == 'sector']
                if not ibc_sector.empty:
                    cols_sector = st.columns(len(ibc_sector))
                    for idx, (_, row) in enumerate(ibc_sector.iterrows()):
                        with cols_sector[idx]:
                            rango = f"{float(row['ibc_min_smmlv']):.1f}-{float(row['ibc_max_smmlv']):.1f}x SMLV"
                            st.metric(str(row['categoria']), rango,
                                     delta=f"${float(row['ibc_min_pesos']):,.0f} - ${float(row['ibc_max_pesos']):,.0f}")

            df_sigep = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame())
            if not df_sigep.empty:
                with st.expander("Ver salarios por nivel educativo (SIGEP - Empleo publico)", expanded=df_ibc.empty):
                    fig_sigep = go.Figure()
                    fig_sigep.add_trace(go.Bar(
                        x=df_sigep['nivel_educativo'],
                        y=df_sigep['salario_promedio'],
                        name='Promedio',
                        marker_color='#9b1b30',
                        text=[f"${v:,.0f}" for v in df_sigep['salario_promedio']],
                        textposition='auto'
                    ))
                    fig_sigep.add_trace(go.Bar(
                        x=df_sigep['nivel_educativo'],
                        y=df_sigep['salario_mediana'],
                        name='Mediana',
                        marker_color='#6B9080',
                        text=[f"${v:,.0f}" for v in df_sigep['salario_mediana']],
                        textposition='auto'
                    ))
                    fig_sigep.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                       annotation_text=f"SMLV: ${smlv:,}")
                    fig_sigep.update_layout(
                        barmode='group', height=350,
                        title="Salarios reales por nivel educativo",
                        yaxis_title="Salario ($)"
                    )
                    st.plotly_chart(fig_sigep, width='stretch')
                    total_emps = int(df_sigep['cantidad_empleados'].sum())
                    st.caption(f"**Fuente:** SIGEP (Sistema de Informacion y Gestion del Empleo Publico). "
                              f"Muestra: {total_emps:,} empleados. Sector publico colombiano.")

            df_depto = datos_salarios.get('sigep_departamental', pd.DataFrame())
            if not df_depto.empty:
                with st.expander(f"Ver salarios en {_sel_depto_sal} (SIGEP)", expanded=False):
                    st.dataframe(df_depto.rename(columns={
                        'nivel_educativo': 'Nivel Educativo',
                        'salario_promedio': 'Salario Promedio',
                        'salario_mediana': 'Salario Mediana',
                        'cantidad_empleados': 'N Empleados'
                    }), hide_index=True, width='stretch')
        else:
            st.warning("No se encontraron datos salariales de referencia en las fuentes oficiales (OLE/SIGEP).")

    # =====================================================================
    # RADAR DE COMPETENCIAS
    # =====================================================================
    st.markdown("---")
    st.markdown("#### Radar de Competencias Requeridas - Skills Gap (Nacional)")
    st.caption("Conocimientos y destrezas que el mercado laboral exige para las ocupaciones vinculadas a este NBC.")

    _bridge_con_names = set()
    _bridge_des_names = set()
    if ctx.skills_bridge and ctx.skills_bridge.get('has_data'):
        _bridge_con_names = set(s['nombre'] for s in ctx.skills_bridge.get('siet_conocimientos', []))
        _bridge_des_names = set(s['nombre'] for s in ctx.skills_bridge.get('siet_destrezas', []))

    col_conocimientos, col_destrezas = st.columns(2)

    with col_conocimientos:
        st.markdown("**Conocimientos Clave:**")
        if not df_conocimientos.empty:
            fig_radar_con = go.Figure()
            fig_radar_con.add_trace(go.Scatterpolar(
                r=df_conocimientos['frecuencia'].values,
                theta=df_conocimientos['conocimiento'].values,
                fill='toself',
                name='SNIES (Ed. Formal)',
                marker_color='#9b1b30',
                opacity=0.7
            ))
            if _bridge_con_names and ctx.skills_bridge.get('siet_conocimientos'):
                con_col = 'conocimiento' if 'conocimiento' in df_conocimientos.columns else df_conocimientos.columns[0]
                snies_con_names = df_conocimientos[con_col].values
                siet_values = []
                for cn in snies_con_names:
                    if cn in _bridge_con_names:
                        match_item = next((s for s in ctx.skills_bridge['siet_conocimientos'] if s['nombre'] == cn), None)
                        siet_values.append(match_item['n_ocupaciones'] if match_item else 0)
                    else:
                        siet_values.append(0)
                if any(v > 0 for v in siet_values):
                    fig_radar_con.add_trace(go.Scatterpolar(
                        r=siet_values,
                        theta=snies_con_names,
                        fill='toself',
                        name='SIET/ETDH (Ed. Trabajo)',
                        marker_color='#cc8800',
                        opacity=0.4,
                        line=dict(dash='dot')
                    ))
            show_legend = bool(_bridge_con_names)
            fig_radar_con.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, df_conocimientos['frecuencia'].max() * 1.2])),
                showlegend=show_legend,
                height=400 if show_legend else 350,
                margin=dict(l=50, r=50, t=60, b=50),
                title="Conocimientos más demandados (Nacional)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_radar_con, width='stretch')
            descargar_datos_grafico(df_conocimientos, "conocimientos_requeridos", "Descargar datos")
            st.caption(get_citacion("competencias_cuoc"))
        else:
            st.warning("Sin datos de conocimientos para este NBC")

    with col_destrezas:
        st.markdown("**Destrezas Clave:**")
        if not df_destrezas.empty:
            fig_radar_des = go.Figure()
            fig_radar_des.add_trace(go.Scatterpolar(
                r=df_destrezas['frecuencia'].values,
                theta=df_destrezas['destreza'].values,
                fill='toself',
                name='SNIES (Ed. Formal)',
                marker_color='#6B9080',
                opacity=0.7
            ))
            if _bridge_des_names and ctx.skills_bridge.get('siet_destrezas'):
                des_col = 'destreza' if 'destreza' in df_destrezas.columns else df_destrezas.columns[0]
                snies_des_names = df_destrezas[des_col].values
                siet_des_values = []
                for dn in snies_des_names:
                    if dn in _bridge_des_names:
                        match_item = next((s for s in ctx.skills_bridge['siet_destrezas'] if s['nombre'] == dn), None)
                        siet_des_values.append(match_item['n_ocupaciones'] if match_item else 0)
                    else:
                        siet_des_values.append(0)
                if any(v > 0 for v in siet_des_values):
                    fig_radar_des.add_trace(go.Scatterpolar(
                        r=siet_des_values,
                        theta=snies_des_names,
                        fill='toself',
                        name='SIET/ETDH (Ed. Trabajo)',
                        marker_color='#cc8800',
                        opacity=0.4,
                        line=dict(dash='dot')
                    ))
            show_legend_des = bool(_bridge_des_names)
            fig_radar_des.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, df_destrezas['frecuencia'].max() * 1.2])),
                showlegend=show_legend_des,
                height=400 if show_legend_des else 350,
                margin=dict(l=50, r=50, t=60, b=50),
                title="Destrezas más demandadas (Nacional)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_radar_des, width='stretch')
            descargar_datos_grafico(df_destrezas, "destrezas_requeridas", "Descargar datos")
            st.caption(get_citacion("competencias_cuoc"))
        else:
            st.warning("Sin datos de destrezas para este NBC")

    # =====================================================================
    # PUENTE DE COMPETENCIAS SNIES <-> SIET/ETDH
    # =====================================================================
    if ctx.skills_bridge and ctx.skills_bridge.get('has_data'):
        st.markdown("---")
        st.markdown('<h4 class="icon-header"><i class="fas fa-arrows-left-right"></i> '
                    'Puente de Competencias: Educacion Formal - Educacion para el Trabajo</h4>',
                    unsafe_allow_html=True)

        align_global = ctx.skills_bridge.get('alignment_score_global', 0)
        compl_siet = ctx.skills_bridge.get('complementarity_siet', 0)
        n_shared_con = len(ctx.skills_bridge.get('shared_conocimientos', []))
        n_shared_des = len(ctx.skills_bridge.get('shared_destrezas', []))
        n_snies_ocp = len(ctx.skills_bridge.get('snies_ocupaciones', []))
        n_siet_ocp = len(ctx.skills_bridge.get('siet_ocupaciones', []))

        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        col_b1.metric("Alineacion SNIES-SIET", f"{align_global:.0%}",
                     help="Jaccard similarity entre competencias SNIES y SIET (CUOC)")
        col_b2.metric("Complementariedad SIET", f"{compl_siet:.0%}",
                     help="% de competencias que SIET/ETDH aporta y NO estan en SNIES")
        col_b3.metric("Ocupaciones SNIES", f"{n_snies_ocp}",
                     help="Ocupaciones CUOC identificadas via educacion formal")
        col_b4.metric("Ocupaciones SIET", f"{n_siet_ocp}",
                     help="Ocupaciones CUOC identificadas via educacion para el trabajo")

        if n_shared_con > 0 or n_shared_des > 0:
            shared_con_list = ctx.skills_bridge.get('shared_conocimientos', [])[:5]
            shared_des_list = ctx.skills_bridge.get('shared_destrezas', [])[:5]
            resumen_parts = []
            if shared_con_list:
                resumen_parts.append(f"**Conocimientos compartidos ({n_shared_con}):** " + ", ".join(shared_con_list[:5]))
            if shared_des_list:
                resumen_parts.append(f"**Destrezas compartidas ({n_shared_des}):** " + ", ".join(shared_des_list[:5]))
            st.markdown(" | ".join(resumen_parts))

        ciiu_from_bridge = ctx.skills_bridge.get('ciiu_sectors', [])
        if ciiu_from_bridge:
            ciiu_labels = {
                'A': 'Agropecuario', 'B': 'Mineria', 'C': 'Manufactura', 'D': 'Energia',
                'E': 'Agua/Saneamiento', 'F': 'Construccion', 'G': 'Comercio', 'H': 'Transporte',
                'I': 'Hoteleria/Turismo', 'J': 'TIC/Comunicaciones', 'K': 'Financiero',
                'L': 'Inmobiliario', 'M': 'Profesionales', 'N': 'Administrativos', 'O': 'Gobierno',
                'P': 'Educacion', 'Q': 'Salud', 'R': 'Arte/Entretenimiento',
                'S': 'Otros servicios', 'T': 'Hogares', 'U': 'Organismos Int.'
            }
            sectores_str = ", ".join([f"**{s.get('seccion','?')}**-{ciiu_labels.get(s.get('seccion',''), s.get('nombre','')[:20])}" for s in ciiu_from_bridge[:6]])
            st.markdown(f"**Sectores CIIU relacionados:** {sectores_str}")

        with st.expander("Ver detalle de ocupaciones CUOC identificadas", expanded=False):
            col_bridge_l, col_bridge_r = st.columns(2)
            with col_bridge_l:
                st.markdown("**Via SNIES (Ed. Formal):**")
                if ctx.skills_bridge.get('snies_ocupaciones'):
                    for ocp in ctx.skills_bridge['snies_ocupaciones'][:10]:
                        score = ocp.get('score', 0)
                        area = ocp.get('area', '')
                        area_tag = f" *({area[:30]})*" if area else ""
                        st.markdown(f"- {ocp['nombre']} `{score:.2f}`{area_tag}")
                else:
                    st.caption("Sin datos")
            with col_bridge_r:
                st.markdown("**Via SIET (Ed. Trabajo):**")
                if ctx.skills_bridge.get('siet_ocupaciones'):
                    for ocp in ctx.skills_bridge['siet_ocupaciones'][:10]:
                        st.markdown(f"- {ocp['nombre']}")
                else:
                    st.caption("Sin datos")
            n_shared_ocp = len(ctx.skills_bridge.get('shared_ocupaciones', []))
            if n_shared_ocp > 0:
                st.markdown(f"**Ocupaciones en comun ({n_shared_ocp}):** " +
                           ", ".join(ctx.skills_bridge['shared_ocupaciones'][:5]))
            if ctx.skills_bridge.get('notas'):
                for nota in ctx.skills_bridge['notas']:
                    st.caption(f"Nota: {nota}")
            st.caption("Fuente: CUOC (MinTrabajo), CIIU Rev. 4 (DANE), matching ML con paraphrase-multilingual-MiniLM-L12-v2")
    elif ctx.sel_nbcs:
        st.markdown("---")
        st.caption("Datos de educacion formal (SNIES). Active SIET en filtros para cruce con ETDH.")

    # =====================================================================
    # TENDENCIA DE GRADUADOS
    # =====================================================================
    st.markdown("#### Tendencia de Graduados")
    if not ctx.df_graduados.empty:
        fig_grad = px.bar(ctx.df_graduados, x='anio', y='graduados',
                        title=f"Graduados por Ano ({ctx.label_ambito})")
        st.plotly_chart(fig_grad, width='stretch')
        descargar_datos_grafico(ctx.df_graduados, "tendencia_graduados_barras", "Descargar datos")
        st.caption(get_citacion("snies_graduados"))

    if not df_graduados_nbc.empty:
        with st.expander("Ver graduados NBC consolidado nacional (SNIES)", expanded=False):
            col_gnbc1, col_gnbc2 = st.columns([2, 1])
            with col_gnbc1:
                fig_gnbc = px.line(df_graduados_nbc, x='anio', y='graduados',
                                 title=f"Graduados Nacionales - {df_graduados_nbc['NBC'].iloc[0]}",
                                 markers=True)
                fig_gnbc.update_layout(xaxis_title="Ano", yaxis_title="Graduados")
                st.plotly_chart(fig_gnbc, width='stretch')
            with col_gnbc2:
                ult_grad = df_graduados_nbc.iloc[-1]['graduados']
                prom_grad = df_graduados_nbc['graduados'].mean()
                st.metric("Ultimo ano", f"{int(ult_grad):,}")
                st.metric("Promedio anual", f"{int(prom_grad):,}")
                if len(df_graduados_nbc) >= 2:
                    var_pct = ((df_graduados_nbc.iloc[-1]['graduados'] - df_graduados_nbc.iloc[0]['graduados'])
                              / df_graduados_nbc.iloc[0]['graduados'] * 100)
                    st.metric("Variacion periodo", f"{var_pct:+.1f}%")
            st.caption("Fuente: SNIES - MEN (consolidado nacional por NBC)")
    elif ctx.df_graduados.empty:
        st.info("No se encontraron datos de graduados para los filtros seleccionados.")

    # =====================================================================
    # TENDENCIA LABORAL APE
    # =====================================================================
    if not df_tend_vac.empty or not df_tend_col.empty:
        st.markdown("---")
        st.markdown("#### Tendencia del Mercado Laboral APE (Nacional)")
        st.caption("Datos reales de la Agencia Publica de Empleo (SENA) - Ocupaciones relacionadas al NBC via ML matching")

        col_tv, col_tc = st.columns(2)
        with col_tv:
            if not df_tend_vac.empty:
                df_tv_año = df_tend_vac.groupby('ano').agg(vacantes=('vacantes', 'sum')).reset_index()
                df_tv_año['ano'] = df_tv_año['ano'].astype(int)
                fig_tv = px.bar(df_tv_año, x='ano', y='vacantes',
                               title="Vacantes APE por ano", text='vacantes')
                fig_tv.update_layout(xaxis_title="Ano", yaxis_title="Vacantes")
                fig_tv.update_traces(texttemplate='%{text:,.0f}', textposition='auto')
                st.plotly_chart(fig_tv, width='stretch')
                descargar_datos_grafico(df_tv_año, "tendencia_vacantes_ape", "Descargar datos")
        with col_tc:
            if not df_tend_col.empty:
                df_tc_año = df_tend_col.groupby('ano').agg(colocados=('colocados', 'sum')).reset_index()
                df_tc_año['ano'] = df_tc_año['ano'].astype(int)
                fig_tc = px.bar(df_tc_año, x='ano', y='colocados',
                               title="Colocados APE por ano", text='colocados',
                               color_discrete_sequence=['#6B9080'])
                fig_tc.update_layout(xaxis_title="Ano", yaxis_title="Colocados")
                fig_tc.update_traces(texttemplate='%{text:,.0f}', textposition='auto')
                st.plotly_chart(fig_tc, width='stretch')
                descargar_datos_grafico(df_tc_año, "tendencia_colocados_ape", "Descargar datos")

        if not df_tend_vac.empty and not df_tend_col.empty:
            try:
                df_tv_a = df_tend_vac.groupby('ano')['vacantes'].sum().reset_index()
                df_tc_a = df_tend_col.groupby('ano')['colocados'].sum().reset_index()
                df_tasa = df_tv_a.merge(df_tc_a, on='ano', how='inner')
                df_tasa['tasa_colocacion'] = (df_tasa['colocados'] / df_tasa['vacantes'] * 100).round(1)
                if not df_tasa.empty:
                    tasa_ultima = df_tasa.iloc[-1]['tasa_colocacion']
                    st.metric("Tasa de colocacion (ultimo ano)", f"{tasa_ultima:.1f}%",
                             help="Porcentaje de vacantes que resultaron en colocacion efectiva (APE)")
            except Exception:
                pass

        with st.expander("Ver detalle de ocupaciones en tendencia", expanded=False):
            if not df_tend_vac.empty:
                ultimo_ano = df_tend_vac['ano'].max()
                df_ultimo = df_tend_vac[df_tend_vac['ano'] == ultimo_ano].sort_values('vacantes', ascending=False).head(10)
                st.dataframe(
                    df_ultimo[['ocupacion', 'vacantes']].rename(columns={
                        'ocupacion': 'Ocupacion', 'vacantes': f'Vacantes {ultimo_ano}'
                    }),
                    hide_index=True, width='stretch'
                )
        st.caption("**Fuente:** Agencia Publica de Empleo (APE) - SENA. Consolidados anuales 2017-2019.")

    # =====================================================================
    # CUALIFICACIONES MEN
    # =====================================================================
    st.markdown("---")
    st.markdown("### Cualificaciones MEN (Nacional)")
    st.caption("Catalogo oficial de cualificaciones laborales del Ministerio de Educacion. Cada cualificacion define las competencias minimas exigidas por el mercado.")

    if len(ctx.sel_nbcs) > 1:
        _dfs_cual = [get_cualificaciones_por_nbc(n) for n in ctx.sel_nbcs[:5]]
        _dfs_cual = [d for d in _dfs_cual if not d.empty]
        df_cualif_nbc = pd.concat(_dfs_cual, ignore_index=True).drop_duplicates(subset=['Codigo_MEN']) if _dfs_cual else pd.DataFrame()
    else:
        df_cualif_nbc = get_cualificaciones_por_nbc(ctx.sel_nbc)

    _mnc_filtrados = mapear_niveles_snies_a_mnc(ctx.sel_niveles)
    _cualif_filtro_aplicado = False
    if _mnc_filtrados and not df_cualif_nbc.empty:
        _pre_filter_count = len(df_cualif_nbc)
        df_cualif_nbc = df_cualif_nbc[df_cualif_nbc['Nivel_MNC'].isin(_mnc_filtrados)].copy()
        _cualif_filtro_aplicado = _pre_filter_count != len(df_cualif_nbc)

    if not df_cualif_nbc.empty:
        col_q1, col_q2, col_q3 = st.columns(3)
        n_cualif = len(df_cualif_nbc)
        niveles_cubiertos = df_cualif_nbc['Nivel_MNC'].unique()
        areas_conectadas = df_cualif_nbc['Sigla_Area'].unique()
        col_q1.metric("Cualificaciones Relacionadas", f"{n_cualif}")
        _niv_label = f"{len(niveles_cubiertos)} ({min(niveles_cubiertos)}-{max(niveles_cubiertos)})"
        if _cualif_filtro_aplicado:
            _niv_label += " (filtrado)"
        col_q2.metric("Niveles MNC Cubiertos", _niv_label)
        col_q3.metric("Áreas CUOC Conectadas", f"{len(areas_conectadas)}")

        col_nivel, col_trayectoria = st.columns(2)
        with col_nivel:
            st.markdown("#### Distribución por Nivel MNC")
            df_nivel_cualif = df_cualif_nbc.groupby('Nivel_MNC').size().reset_index(name='N')
            nivel_labels = {
                2: 'Nivel 2 - Operativo', 3: 'Nivel 3 - Técnico Básico',
                4: 'Nivel 4 - Técnico', 5: 'Nivel 5 - Tecnológico',
                6: 'Nivel 6 - Profesional', 7: 'Nivel 7 - Especialización/Maestría'
            }
            df_nivel_cualif['Nivel_Label'] = df_nivel_cualif['Nivel_MNC'].map(nivel_labels)
            fig_nivel_cualif = px.bar(
                df_nivel_cualif, x='Nivel_MNC', y='N', text='N',
                title="Cualificaciones por Nivel MNC", color='Nivel_MNC',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
            )
            fig_nivel_cualif.update_layout(
                height=300, xaxis_title="Nivel MNC", yaxis_title="N° Cualificaciones",
                showlegend=False, coloraxis_showscale=False
            )
            fig_nivel_cualif.update_traces(textposition='auto')
            st.plotly_chart(fig_nivel_cualif, width='stretch')
            descargar_datos_grafico(df_nivel_cualif, "cualificaciones_nivel_mnc", "Descargar datos")
            st.caption(get_citacion("cualificaciones_men"))

        with col_trayectoria:
            st.markdown("#### Trayectoria Formativa Sugerida")
            st.caption("Ruta de cualificación desde nivel operativo hasta especialización")
            for nivel in sorted(niveles_cubiertos):
                cualif_nivel = df_cualif_nbc[df_cualif_nbc['Nivel_MNC'] == nivel]
                n_cualif_nivel = len(cualif_nivel)
                nivel_nombre = nivel_labels.get(nivel, f'Nivel {nivel}')
                nivel_indicator = ['[2]', '[3]', '[4]', '[5]', '[6]', '[7]'][nivel - 2] if nivel <= 7 else '[N]'
                st.markdown(f"**{nivel_indicator} {nivel_nombre}** ({n_cualif_nivel} cualificaciones)")
                ejemplos = cualif_nivel['Cualificacion'].head(2).tolist()
                for ej in ejemplos:
                    st.caption(f"   → {ej[:60]}{'...' if len(ej) > 60 else ''}")

        with st.expander(f"Ver todas las {n_cualif} cualificaciones relacionadas al NBC", expanded=False):
            df_display = df_cualif_nbc[['Codigo_MEN', 'Cualificacion', 'Nivel_MNC', 'Sector', 'Sigla_Area']].copy()
            df_display.columns = ['Código MEN', 'Cualificación', 'Nivel MNC', 'Sector', 'Área CUOC']
            st.dataframe(df_display, hide_index=True, width='stretch', height=400)
            csv_cualif = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Descargar Cualificaciones (CSV)", csv_cualif,
                f"cualificaciones_men_{(ctx.sel_nbc or 'filtro').replace(' ', '_')}.csv",
                "text/csv"
            )

        _rango_mnc = f"niveles MNC {min(niveles_cubiertos)} a {max(niveles_cubiertos)}" if len(niveles_cubiertos) > 1 else f"nivel MNC {min(niveles_cubiertos)}"
        _nota_filtro = f"\n            - *Filtrado por nivel de formación: {', '.join(ctx.sel_niveles)}*" if _cualif_filtro_aplicado else ""
        st.info(f"""
        **Articulación Educación-Empleo:**
        - **{ctx.filtro_label}** se conecta con **{n_cualif}** estándares oficiales de cualificación
        - Abarca {_rango_mnc}
        - Las áreas CUOC relacionadas son: **{', '.join(areas_conectadas)}**
        - Estas cualificaciones definen las competencias mínimas exigidas por el mercado laboral colombiano{_nota_filtro}
        """)
    else:
        st.warning(f"No se encontraron cualificaciones Men directamente relacionadas con: **{ctx.filtro_label}**")
        with st.expander("Ver catálogo completo de Cualificaciones MEN"):
            stats_men = get_estadisticas_cualificaciones_men()
            st.metric("Total Cualificaciones MEN", f"{stats_men['total']}")
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.markdown("**Por Nivel MNC:**")
                if not stats_men['por_nivel'].empty:
                    st.dataframe(stats_men['por_nivel'], hide_index=True)
            with col_stat2:
                st.markdown("**Por Área de Cualificación:**")
                if not stats_men['por_area'].empty:
                    st.dataframe(stats_men['por_area'].head(10), hide_index=True)

    # =====================================================================
    # ACTIVIDADES Y TAREAS OCUPACIONALES
    # =====================================================================
    st.markdown("---")
    st.markdown('<h3 class="icon-header"><i class="fas fa-tasks"></i> Actividades y Tareas Ocupacionales (Nacional)</h3>', unsafe_allow_html=True)
    st.caption("Perfil ocupacional detallado según la Clasificación Única de Ocupaciones para Colombia (CUOC)")

    if len(ctx.sel_nbcs) > 1:
        _dfs_act = [get_actividades_tareas_nbc(n) for n in ctx.sel_nbcs[:5]]
        _dfs_act = [d for d in _dfs_act if not d.empty]
        df_actividades = pd.concat(_dfs_act, ignore_index=True).drop_duplicates(subset=['codigo_cuoc']) if _dfs_act else pd.DataFrame()
    else:
        df_actividades = get_actividades_tareas_nbc(ctx.sel_nbc)

    if not df_actividades.empty:
        df_con_desc = df_actividades[df_actividades['descripcion_actividades'].notna()].copy()
        n_perfiles = len(df_con_desc)
        if n_perfiles > 0:
            st.success(f"Se identificaron **{n_perfiles} perfiles ocupacionales** relacionados con {ctx.filtro_label}")
            for i, row in df_con_desc.head(5).iterrows():
                titulo = str(row['titulo_ocupacion'])[:80]
                codigo = str(row['codigo_cuoc'])
                descripcion = str(row['descripcion_actividades'])
                with st.expander(f"**[{codigo}]** {titulo}", expanded=(i == 0)):
                    st.markdown(f"""
                    **Actividades y tareas principales:**
                    {descripcion}
                    """)
            if n_perfiles > 5:
                with st.expander(f"Ver los {n_perfiles - 5} perfiles ocupacionales restantes"):
                    for i, row in df_con_desc.iloc[5:].iterrows():
                        titulo = str(row['titulo_ocupacion'])[:80]
                        codigo = str(row['codigo_cuoc'])
                        descripcion = str(row['descripcion_actividades'])[:200]
                        st.markdown(f"**[{codigo}] {titulo}**")
                        st.caption(f"{descripcion}...")
                        st.markdown("---")
            st.caption(get_citacion("cuoc_perfiles"))
        else:
            st.info(f"No se encontraron descripciones de actividades para {ctx.filtro_label}. Puede que los programas tengan ocupaciones relacionadas sin perfil detallado.")
    else:
        st.warning(f"No se encontraron perfiles ocupacionales directamente mapeados para: **{ctx.filtro_label}**")
        st.caption("<i class='fas fa-lightbulb icon-hint'></i> Los perfiles ocupacionales se basan en el mapeo oficial NBC → CUOC del Ministerio de Trabajo.", unsafe_allow_html=True)

    return {
        'df_vacantes': df_vacantes,
        'df_conocimientos': df_conocimientos,
        'df_destrezas': df_destrezas,
        'datos_salarios': datos_salarios,
        'df_actividades': df_actividades,
    }
