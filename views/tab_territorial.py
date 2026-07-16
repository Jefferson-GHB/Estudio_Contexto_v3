"""
Sintesis Territorial: indicadores educativos departamentales,
oferta del NBC en el territorio, conectividad digital, contexto
socioinstitucional (PDET/DNP), cluster empresarial y score
territorial integrado.
"""
import html

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from components.display import section_header
from utils.helpers import descargar_datos_grafico
from services.sources import get_citacion
from data import (
    get_indicadores_educativos_depto,
    get_graduados_depto_nbc,
    get_matriculados_depto_nbc,
    get_oferta_programas_depto,
    get_ranking_departamental_nbc,
    get_municipios_pdet,
    get_salarios_depto,
)

try:
    from services.territorial.functions import get_desempeno_dnp, get_cluster_empresarial
    from services.territorial.normalization import get_region
    TERRITORIAL_ROBUST = True
except ImportError:
    TERRITORIAL_ROBUST = False


def render_tab_territorial(ctx):
    """Renderiza la sintesis territorial del dashboard.

    Retorna un dict con el score territorial integrado para que
    Tab 4 lo use en el score final ponderado.
    """
    nivel_territorial = "departamental" if ctx.arg_depto else "nacional"
    etiqueta_territorio = ctx.arg_depto or "Colombia (Nacional)"
    st.markdown(f'<div class="section-header"><span class="section-eyebrow">03</span><h2>Pertinencia Territorial y Social</h2><p>El territorio cuenta con condiciones de acceso, conectividad y demanda que favorezcan trayectorias educativas viables?</p></div>', unsafe_allow_html=True)
    if ctx.sel_deptos and len(ctx.sel_deptos) > 1:
        st.warning(f"Análisis territorial enfocado en **{html.escape(ctx.sel_deptos[0])}**. Los demás departamentos ({html.escape(', '.join(ctx.sel_deptos[1:3]))}{' …' if len(ctx.sel_deptos) > 3 else ''}) se incluyen en filtros de oferta y matriculados pero los indicadores territoriales corresponden al primero.")
    st.markdown(f"""
    **Pregunta clave:** ¿El territorio soporta este programa?

    Análisis **{nivel_territorial}** con datos reales: indicadores educativos,
    oferta académica, infraestructura digital, tejido empresarial y contexto socioeconómico.
    {"" if ctx.arg_depto else "<i class='fas fa-info-circle' style='margin-right:0.3rem'></i> *Seleccione un departamento en filtros para detallar a nivel territorial.*"}
    """)

    # =================================================================
    # OBTENCION DE DATOS TERRITORIALES
    # =================================================================
    with st.spinner("Consultando datos territoriales..."):
        datos_edu_depto = get_indicadores_educativos_depto(ctx.arg_depto)

    if ctx.sel_nbc:
        df_grad_depto = get_graduados_depto_nbc(ctx.sel_nbc, ctx.arg_depto, filtros=ctx.filtros_seleccionados)
        df_mat_depto = get_matriculados_depto_nbc(ctx.sel_nbc, ctx.arg_depto, filtros=ctx.filtros_seleccionados)
        df_oferta_depto = get_oferta_programas_depto(ctx.sel_nbc, ctx.arg_depto, filtros=ctx.filtros_seleccionados)
        df_ranking_nbc = get_ranking_departamental_nbc(ctx.sel_nbc, filtros=ctx.filtros_seleccionados)
    else:
        df_grad_depto = pd.DataFrame()
        df_mat_depto = pd.DataFrame()
        df_oferta_depto = pd.DataFrame()
        df_ranking_nbc = pd.DataFrame()

    df_pdet = get_municipios_pdet(ctx.arg_depto) if ctx.arg_depto else pd.DataFrame()
    es_territorio_pdet = not df_pdet.empty
    n_municipios_pdet = len(df_pdet) if es_territorio_pdet else 0

    if TERRITORIAL_ROBUST and ctx.arg_depto:
        datos_dnp = get_desempeno_dnp(ctx.arg_depto)
        en_plan_desarrollo = datos_dnp['en_plan_desarrollo']
        mdm_score = datos_dnp['puntaje_mdm']
    else:
        datos_dnp = {}
        en_plan_desarrollo = False
        mdm_score = None

    if TERRITORIAL_ROBUST and ctx.sel_nbc and ctx.arg_depto:
        datos_cluster = get_cluster_empresarial(ctx.sel_nbc, ctx.arg_depto)
        hay_cluster = datos_cluster['hay_cluster']
        n_empresas_cluster = datos_cluster['total_empresas']
        sectores_ciiu = datos_cluster['sectores_relacionados']
    else:
        datos_cluster = {}
        hay_cluster = False
        n_empresas_cluster = 0
        sectores_ciiu = []

    datos_sal_depto = get_salarios_depto(ctx.arg_depto)

    if TERRITORIAL_ROBUST and ctx.arg_depto:
        region_depto = get_region(ctx.arg_depto)
    else:
        region_depto = None

    df_conectividad_terr = ctx.df_conectividad
    if not df_conectividad_terr.empty:
        avg_conectividad = df_conectividad_terr['indice_conectividad'].mean()
        avg_4g = df_conectividad_terr['cobertura_4g_pct'].mean() if 'cobertura_4g_pct' in df_conectividad_terr.columns else 0
    else:
        avg_conectividad = 0.5
        avg_4g = 0.5

    # =================================================================
    # SECCION 1: INDICADORES EDUCATIVOS
    # =================================================================
    st.markdown("---")
    st.markdown(f"#### Indicadores Educativos: {etiqueta_territorio}")

    if datos_edu_depto.get('tiene_datos'):
        col_tcb, col_tti, col_mat = st.columns(3)
        with col_tcb:
            tcb_val = datos_edu_depto.get('tcb_actual')
            st.metric("Tasa Cobertura Bruta ES", f"{tcb_val:.1f}%" if tcb_val else "N/D",
                     help="Porcentaje de la población en edad de estudiar que está matriculada en educación superior")
            if tcb_val:
                if tcb_val >= 50:
                    st.success("Por encima del promedio nacional (~55%)")
                else:
                    st.warning("Por debajo del promedio nacional (~55%)")
        with col_tti:
            tti_val = datos_edu_depto.get('tti_actual')
            st.metric("Tasa Tránsito Inmediato", f"{tti_val:.1f}%" if tti_val else "N/D",
                     help="Porcentaje de bachilleres que ingresan a educación superior al año siguiente")
            if tti_val:
                if tti_val >= 40:
                    st.success("Buen tránsito a educación superior")
                else:
                    st.warning("Bajo tránsito — potencial demanda insatisfecha")
        with col_mat:
            mat_val = datos_edu_depto.get('matricula_actual')
            st.metric("Matrícula ES Total", f"{mat_val:,}" if mat_val else "N/D",
                     help="Total de estudiantes matriculados en educación superior en el departamento")

        col_hist1, col_hist2 = st.columns(2)
        with col_hist1:
            df_tcb_hist = datos_edu_depto.get('tcb_historico', pd.DataFrame())
            df_tti_hist = datos_edu_depto.get('tti_historico', pd.DataFrame())
            if not df_tcb_hist.empty or not df_tti_hist.empty:
                fig_tasas = go.Figure()
                if not df_tcb_hist.empty:
                    fig_tasas.add_trace(go.Scatter(
                        x=df_tcb_hist['anio'], y=df_tcb_hist['tasa'],
                        mode='lines+markers', name='Cobertura Bruta ES (%)',
                        marker_color='#9b1b30', line=dict(width=2)
                    ))
                if not df_tti_hist.empty:
                    fig_tasas.add_trace(go.Scatter(
                        x=df_tti_hist['anio'], y=df_tti_hist['tasa'],
                        mode='lines+markers', name='Tránsito Inmediato (%)',
                        marker_color='#6B9080', line=dict(width=2, dash='dot')
                    ))
                fig_tasas.update_layout(
                    height=300, title=f"Evolución Tasas Educativas — {etiqueta_territorio}",
                    yaxis_title="Porcentaje (%)", xaxis_title="Año",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3)
                )
                st.plotly_chart(fig_tasas, width='stretch')
                df_tasas_export = pd.DataFrame()
                if not df_tcb_hist.empty:
                    df_tasas_export = df_tcb_hist.rename(columns={'tasa': 'TCB_%'})
                if not df_tti_hist.empty:
                    if not df_tasas_export.empty:
                        df_tasas_export = df_tasas_export.merge(
                            df_tti_hist.rename(columns={'tasa': 'TTI_%'}), on='anio', how='outer')
                    else:
                        df_tasas_export = df_tti_hist.rename(columns={'tasa': 'TTI_%'})
                descargar_datos_grafico(df_tasas_export, "tasas_educativas_depto", "Descargar datos")

        with col_hist2:
            df_mat_hist = datos_edu_depto.get('matricula_historico', pd.DataFrame())
            if not df_mat_hist.empty:
                fig_mat = go.Figure()
                fig_mat.add_trace(go.Bar(
                    x=df_mat_hist['anio'], y=df_mat_hist['matriculados'],
                    marker_color='#a0522d',
                    text=[f"{v:,}" for v in df_mat_hist['matriculados']],
                    textposition='auto'
                ))
                fig_mat.update_layout(
                    height=300, title=f"Matrícula ES Total — {etiqueta_territorio}",
                    yaxis_title="Estudiantes", xaxis_title="Año"
                )
                st.plotly_chart(fig_mat, width='stretch')
                descargar_datos_grafico(df_mat_hist, "matricula_es_depto", "Descargar datos")
        st.caption(f"**Fuente:** {datos_edu_depto['fuente']}")
    else:
        st.info("No se encontraron indicadores educativos con los filtros actuales.")

    # =================================================================
    # SECCION 2: OFERTA ACADEMICA DEL NBC EN EL TERRITORIO
    # =================================================================
    st.markdown("---")
    st.markdown("#### Oferta y Demanda del NBC en el Territorio")
    col_oferta1, col_oferta2 = st.columns(2)

    with col_oferta1:
        if not df_grad_depto.empty or not df_mat_depto.empty:
            fig_nbc_depto = go.Figure()
            if not df_mat_depto.empty:
                fig_nbc_depto.add_trace(go.Bar(
                    x=df_mat_depto['anio'], y=df_mat_depto['matriculados'],
                    name='Matriculados', marker_color='#9b1b30',
                    text=[f"{v:,}" for v in df_mat_depto['matriculados']],
                    textposition='auto'
                ))
            if not df_grad_depto.empty:
                fig_nbc_depto.add_trace(go.Bar(
                    x=df_grad_depto['anio'], y=df_grad_depto['graduados'],
                    name='Graduados', marker_color='#6B9080',
                    text=[f"{v:,}" for v in df_grad_depto['graduados']],
                    textposition='auto'
                ))
            fig_nbc_depto.update_layout(
                barmode='group', height=320,
                title=f"{ctx.filtro_label} en {etiqueta_territorio}",
                yaxis_title="Estudiantes", xaxis_title="Año",
                legend=dict(orientation="h", yanchor="bottom", y=-0.25)
            )
            st.plotly_chart(fig_nbc_depto, width='stretch')
            df_nbc_depto_export = pd.DataFrame()
            if not df_mat_depto.empty:
                df_nbc_depto_export = df_mat_depto.copy()
            if not df_grad_depto.empty:
                if not df_nbc_depto_export.empty:
                    df_nbc_depto_export = df_nbc_depto_export.merge(df_grad_depto, on='anio', how='outer')
                else:
                    df_nbc_depto_export = df_grad_depto.copy()
            descargar_datos_grafico(df_nbc_depto_export, "nbc_depto_historico", "Descargar datos")
            st.caption(get_citacion("snies_graduados"))
        elif ctx.sel_nbc:
            st.warning(f"Sin datos de graduados/matriculados de este NBC en {etiqueta_territorio}")
        else:
            st.info("Seleccione un NBC para ver la oferta académica")

    with col_oferta2:
        if not df_ranking_nbc.empty:
            df_rank_top = df_ranking_nbc.head(15).copy()
            df_rank_top['color'] = df_rank_top['departamento'].apply(
                lambda x: '#a0522d' if ctx.arg_depto and ctx.arg_depto.upper() in str(x).upper() else '#A09088'
            )
            fig_rank = go.Figure()
            fig_rank.add_trace(go.Bar(
                y=df_rank_top['departamento'], x=df_rank_top['graduados'],
                orientation='h', marker_color=df_rank_top['color'],
                text=[f"{v:,}" for v in df_rank_top['graduados']], textposition='auto'
            ))
            fig_rank.update_layout(
                height=400, title=f"Ranking Departamental: {ctx.filtro_label}",
                xaxis_title="Graduados acumulados (2019-2024)",
                yaxis={'categoryorder': 'total ascending'},
            )
            st.plotly_chart(fig_rank, width='stretch')
            descargar_datos_grafico(df_ranking_nbc, "ranking_depto_nbc", "Descargar datos")
            if ctx.arg_depto:
                pos = df_ranking_nbc[df_ranking_nbc['departamento'].str.upper().str.contains(ctx.arg_depto.upper(), na=False)]
                if not pos.empty:
                    idx = df_ranking_nbc.index.get_loc(pos.index[0]) + 1
                    total = len(df_ranking_nbc)
                    st.caption(f"**{ctx.arg_depto}** ocupa la posición **#{idx}** de {total} departamentos en graduados de este NBC.")
        elif ctx.sel_nbc:
            st.info("Sin datos de ranking departamental para este NBC")

    if not df_oferta_depto.empty:
        n_activos = len(df_oferta_depto[df_oferta_depto['estado'] == 'ACTIVO']) if 'estado' in df_oferta_depto.columns else len(df_oferta_depto)
        n_total = len(df_oferta_depto)
        with st.expander(f"Ver programas de {ctx.filtro_label} en {etiqueta_territorio} ({n_activos} activos / {n_total} total)", expanded=False):
            df_display = df_oferta_depto.rename(columns={
                'ies': 'IES', 'programa': 'Programa', 'nivel': 'Nivel',
                'metodologia': 'Metodología', 'estado': 'Estado', 'municipio': 'Municipio'
            })
            st.dataframe(df_display, hide_index=True, width='stretch')

    # =================================================================
    # SECCION 3: INFRAESTRUCTURA Y CONTEXTO TERRITORIAL
    # =================================================================
    st.markdown("---")
    st.markdown("#### Infraestructura y Contexto Territorial")
    st.caption("Conectividad digital, municipios PDET y capacidad institucional (MDM) del departamento.")
    col_conect, col_contexto = st.columns(2)

    with col_conect:
        st.markdown("##### Conectividad Digital")
        if not df_conectividad_terr.empty:
            df_con_top = df_conectividad_terr.nlargest(10, 'indice_conectividad')
            fig_con = go.Figure()
            fig_con.add_trace(go.Bar(
                y=df_con_top['municipio'], x=df_con_top['indice_conectividad'],
                orientation='h', marker_color='#6B9080',
                text=[f"{v:.2f}" for v in df_con_top['indice_conectividad']], textposition='auto'
            ))
            fig_con.update_layout(
                height=300, title=f"Conectividad — {etiqueta_territorio}",
                xaxis_title="Índice (0-1)", yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig_con, width='stretch')
            col_4g, col_inet = st.columns(2)
            col_4g.metric("Cobertura 4G/LTE promedio", f"{avg_4g*100:.1f}%")
            col_inet.metric(f"{'Municipios' if ctx.arg_depto else 'Departamentos'} con datos", f"{len(df_conectividad_terr)}")
            if avg_conectividad > 0.7:
                st.success("Alta conectividad — viable modalidad virtual 100%")
                modalidad_recomendada = "Virtual 100%"
                potencial_virtual = 100
            elif avg_conectividad > 0.4:
                st.warning("Conectividad media — recomendable modalidad híbrida")
                modalidad_recomendada = "Híbrida"
                potencial_virtual = 60
            else:
                st.warning("Baja conectividad — priorizar modalidad presencial")
                modalidad_recomendada = "Presencial"
                potencial_virtual = 20
            descargar_datos_grafico(df_conectividad_terr, "conectividad_municipal", "Descargar datos")
            st.caption(get_citacion("internet_fijo") + " | " + get_citacion("cobertura_movil"))
        else:
            st.warning("Sin datos de conectividad disponibles")
            modalidad_recomendada = "N/D"
            potencial_virtual = 50

    with col_contexto:
        st.markdown("##### Contexto Socioinstitucional")
        if region_depto:
            st.info(f"**Región:** {region_depto}  |  **Departamento:** {ctx.arg_depto}")
        elif not ctx.arg_depto:
            st.info("**Nivel:** Nacional — seleccione departamento para detalle territorial")
        if es_territorio_pdet:
            st.success(f"Territorio PDET: {n_municipios_pdet} municipios priorizados para el postconflicto")
            with st.expander("Ver municipios PDET"):
                if 'subregion' in df_pdet.columns:
                    st.dataframe(df_pdet[['municipio', 'subregion']].rename(columns={'municipio': 'Municipio', 'subregion': 'Subregión'}), hide_index=True, width='stretch')
                else:
                    st.dataframe(df_pdet, hide_index=True, width='stretch')
            st.caption(get_citacion("pdet"))
        elif ctx.arg_depto:
            st.info("No es territorio PDET")
        if en_plan_desarrollo and mdm_score is not None:
            if mdm_score >= 70:
                mdm_texto = "Alta capacidad institucional"
                st.success(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
            elif mdm_score >= 50:
                mdm_texto = "Capacidad institucional media"
                st.warning(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
            else:
                mdm_texto = "Capacidad institucional limitada"
                st.error(f"MDM DNP: **{mdm_score:.1f}/100** — {mdm_texto}")
            st.caption(f"Medición de Desempeño Municipal (DNP) — {datos_dnp.get('municipios_evaluados', 0)} municipios evaluados")
        elif ctx.arg_depto:
            st.info("Sin datos de desempeño municipal (DNP)")

    # =================================================================
    # SECCION 4: CLUSTER EMPRESARIAL + SALARIOS TERRITORIALES
    # =================================================================
    st.markdown("---")
    st.markdown("#### Contexto Económico y Laboral del Territorio")
    col_cluster, col_sal_terr = st.columns(2)

    with col_cluster:
        st.markdown(f"##### Clúster Empresarial: {ctx.filtro_label}")
        if hay_cluster:
            st.success(f"**{n_empresas_cluster:,} empresas** en sectores relacionados")
            if sectores_ciiu:
                seccion_nombres = {
                    'A': 'Agropecuario', 'B': 'Minería', 'C': 'Manufactura',
                    'D': 'Energía', 'E': 'Agua/Saneamiento', 'F': 'Construcción',
                    'G': 'Comercio', 'H': 'Transporte', 'I': 'Hotelería/Turismo',
                    'J': 'TIC/Comunicaciones', 'K': 'Financiero', 'L': 'Inmobiliario',
                    'M': 'Profesionales', 'N': 'Administrativos', 'O': 'Gobierno',
                    'P': 'Educación', 'Q': 'Salud', 'R': 'Arte/Entretenimiento',
                    'S': 'Otros servicios', 'T': 'Hogares', 'U': 'Organismos Int.'
                }
                st.markdown("**Sectores CIIU relacionados:** " + ", ".join(
                    [f"{seccion_nombres.get(s, s)} ({s})" for s in sectores_ciiu[:5]]
                ))
            if datos_cluster.get('top_sectores'):
                df_top_sect = pd.DataFrame(datos_cluster['top_sectores'])
                if not df_top_sect.empty:
                    fig_cluster = px.bar(
                        df_top_sect.head(5), x='empresas', y='sector', orientation='h',
                        title="Top Sectores CIIU Relacionados", color='empresas',
                        color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']]
                    )
                    fig_cluster.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_cluster, width='stretch')
                    descargar_datos_grafico(df_top_sect, "cluster_empresarial", "Descargar datos")
            st.caption(get_citacion("rues"))
        elif ctx.sel_nbc and ctx.arg_depto:
            st.warning("Bajo tejido empresarial del sector en el territorio")
            st.markdown("Considerar: migración laboral a otros dptos o modalidad virtual para ampliar alcance.")
        elif ctx.sel_nbc:
            st.info("Clúster empresarial disponible al seleccionar un departamento")
        else:
            st.info("Seleccione un NBC para analizar el clúster empresarial")

    with col_sal_terr:
        st.markdown(f"##### Referencia Salarial: {etiqueta_territorio}")
        if datos_sal_depto.get('tiene_datos'):
            sal_prom = datos_sal_depto['salario_promedio']
            sal_med = datos_sal_depto['salario_mediana']
            n_emps = datos_sal_depto['cantidad_empleados']
            col_s1, col_s2 = st.columns(2)
            col_s1.metric("Salario Promedio", f"${sal_prom:,.0f}" if sal_prom else "N/D")
            col_s2.metric("Salario Mediana", f"${sal_med:,.0f}" if sal_med else "N/D")
            smlv = 1_423_500
            if sal_med and smlv:
                st.caption(f"Mediana = **{sal_med/smlv:.1f}x SMLV** (${smlv:,}). Muestra: {n_emps:,} empleados públicos (SIGEP).")
            df_sal_edu = datos_sal_depto.get('por_nivel_educativo', pd.DataFrame())
            if not df_sal_edu.empty:
                fig_sal_edu = go.Figure()
                fig_sal_edu.add_trace(go.Bar(
                    x=df_sal_edu['nivel_educativo'], y=df_sal_edu['salario_promedio'],
                    name='Promedio', marker_color='#9b1b30',
                    text=[f"${v:,.0f}" for v in df_sal_edu['salario_promedio']], textposition='auto'
                ))
                fig_sal_edu.add_trace(go.Bar(
                    x=df_sal_edu['nivel_educativo'], y=df_sal_edu['salario_mediana'],
                    name='Mediana', marker_color='#6B9080',
                    text=[f"${v:,.0f}" for v in df_sal_edu['salario_mediana']], textposition='auto'
                ))
                fig_sal_edu.add_hline(y=smlv, line_dash="dash", line_color="#9b1b30",
                                     annotation_text=f"SMLV: ${smlv:,}")
                fig_sal_edu.update_layout(
                    barmode='group', height=300,
                    title=f"Salarios por Nivel Educativo — {etiqueta_territorio}",
                    yaxis_title="Salario ($)"
                )
                st.plotly_chart(fig_sal_edu, width='stretch')
                descargar_datos_grafico(df_sal_edu, "salarios_nivel_educativo_depto", "Descargar datos")
            st.caption(f"**Fuente:** {datos_sal_depto['fuente']}")
        else:
            st.warning(f"Sin datos salariales de referencia para {etiqueta_territorio}")

    # =================================================================
    # SINTESIS TERRITORIAL - SCORE INTEGRADO
    # =================================================================
    st.markdown("---")
    st.markdown("#### Síntesis de Pertinencia Territorial")

    score_educativo = 0
    if datos_edu_depto.get('tiene_datos'):
        tcb = datos_edu_depto.get('tcb_actual', 0) or 0
        tti = datos_edu_depto.get('tti_actual', 0) or 0
        score_educativo = min(100, (tcb / 55 * 50) + (tti / 50 * 50))

    score_oferta = 0
    if not df_grad_depto.empty:
        grad_total = df_grad_depto['graduados'].sum()
        if grad_total > 5000: score_oferta = 100
        elif grad_total > 1000: score_oferta = 70
        elif grad_total > 100: score_oferta = 40
        else: score_oferta = 20

    score_conectividad = avg_conectividad * 100

    score_contexto = 0
    tiene_contexto = False
    if ctx.arg_depto:
        tiene_contexto = True
        if region_depto: score_contexto += 20
        if es_territorio_pdet: score_contexto += 30
        if en_plan_desarrollo and mdm_score and mdm_score >= 50: score_contexto += 50
        elif en_plan_desarrollo: score_contexto += 25
        score_contexto = min(score_contexto, 100)

    tiene_cluster = bool(ctx.arg_depto and ctx.sel_nbc)
    score_cluster = min(100, (n_empresas_cluster / 50) * 100) if n_empresas_cluster > 0 else (20 if tiene_cluster else 0)

    if ctx.arg_depto:
        score_territorial_total = (
            score_educativo * 0.25 +
            score_oferta * 0.20 +
            score_conectividad * 0.20 +
            score_contexto * 0.15 +
            score_cluster * 0.20
        )
    else:
        score_territorial_total = (
            score_educativo * 0.35 +
            score_oferta * 0.35 +
            score_conectividad * 0.30
        )

    col_sint1, col_sint2 = st.columns([2, 1])

    with col_sint1:
        if ctx.arg_depto:
            componentes = ['Indicadores Educativos (TCB/TTI)', 'Oferta Académica NBC',
                           'Infraestructura Digital', 'Contexto Institucional', 'Clúster Empresarial']
            scores = [round(score_educativo, 1), round(score_oferta, 1),
                      round(score_conectividad, 1), round(score_contexto, 1), round(score_cluster, 1)]
            pesos = ['25%', '20%', '20%', '15%', '20%']
        else:
            componentes = ['Indicadores Educativos (TCB/TTI)', 'Oferta Académica NBC',
                           'Infraestructura Digital']
            scores = [round(score_educativo, 1), round(score_oferta, 1), round(score_conectividad, 1)]
            pesos = ['35%', '35%', '30%']
        niveles = ['Alto' if s >= 70 else ('Medio' if s >= 40 else 'Bajo') for s in scores]
        sintesis_df = pd.DataFrame({'Componente': componentes, 'Score': scores, 'Peso': pesos, 'Nivel': niveles})
        st.dataframe(sintesis_df, hide_index=True, width='stretch')
        descargar_datos_grafico(sintesis_df, "sintesis_territorial", "Descargar síntesis")

        st.markdown("**Hallazgos territoriales:**")
        hallazgos = []
        if datos_edu_depto.get('tiene_datos'):
            tcb = datos_edu_depto.get('tcb_actual', 0) or 0
            tti = datos_edu_depto.get('tti_actual', 0) or 0
            if tcb < 40:
                hallazgos.append(f"Baja cobertura ES ({tcb:.1f}%) — hay demanda potencial insatisfecha")
            elif tcb >= 50:
                hallazgos.append(f"Cobertura ES adecuada ({tcb:.1f}%) — ecosistema educativo consolidado")
            if tti < 35:
                hallazgos.append(f"Bajo tránsito inmediato ({tti:.1f}%) — programas técnicos pueden captar esta población")
        if not df_grad_depto.empty:
            grad_total = df_grad_depto['graduados'].sum()
            hallazgos.append(f"{int(grad_total):,} graduados acumulados del NBC en {etiqueta_territorio}")
        if es_territorio_pdet:
            hallazgos.append(f"Territorio PDET con {n_municipios_pdet} municipios priorizados")
        if hay_cluster:
            hallazgos.append(f"Clúster empresarial con {n_empresas_cluster:,} empresas del sector")
        if avg_conectividad > 0.6:
            hallazgos.append("Conectividad digital adecuada para educación virtual")
        elif avg_conectividad < 0.3:
            hallazgos.append("Baja conectividad — priorizar modalidad presencial o centros de acceso")
        if hallazgos:
            for h in hallazgos:
                st.markdown(f"- {h}")
        else:
            st.markdown("_Seleccione filtros territoriales para generar hallazgos_")
        st.markdown(f"**Modalidad recomendada:** {modalidad_recomendada}")

    with col_sint2:
        fig_sint = go.Figure(go.Indicator(
            mode="gauge+number", value=score_territorial_total,
            title={'text': "SCORE TERRITORIAL", 'font': {'size': 14, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
            number={'font': {'size': 28, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#A09088'},
                'bar': {'color': "#9B1B30"},
                'steps': [
                    {'range': [0, 50], 'color': "#F0EAE4"},
                    {'range': [50, 75], 'color': "#E5DDD6"},
                    {'range': [75, 100], 'color': "#F9F7F4"}
                ],
            },
            domain={'x': [0.05, 0.95], 'y': [0.08, 0.92]}
        ))
        fig_sint.update_layout(margin=dict(l=10, r=10, t=45, b=0))
        st.plotly_chart(fig_sint, width='stretch')
        if score_territorial_total >= 75:
            st.success("Alta pertinencia territorial")
        elif score_territorial_total >= 50:
            st.warning("Pertinencia territorial media")
        else:
            st.warning("Baja pertinencia territorial")

    return {'score_territorial_total': score_territorial_total}
