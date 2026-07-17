"""
Decision Final: score ponderado de pertinencia (academico 30%,
laboral 40%, territorial 20%, global 10%), veredicto, tipo de
oferta recomendada, contexto ESCO y analisis con LLM Gemini.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from config.styles import insight_card, loading_overlay
from components.display import section_header
from utils.helpers import descargar_datos_grafico
from services.sources import get_citacion
from services import calcular_score_final, calcular_ratio_absorcion
from services.decision_engine import determinar_tipo_oferta
from services.context_builder import generar_contexto_analisis
from visualizations.charts import crear_gauge
from data import (
    get_indicadores_globales,
    get_habilidades_futuro_filtradas,
    get_habilidades_esco,
    get_destrezas_cuoc_nbc,
    get_conocimientos_cuoc_nbc,
    get_comparativa_snies_siet_por_depto,
    get_comparativa_tipo_formacion,
    get_estadisticas_siet,
    get_desglose_siet,
)
from views.etdh import render_etdh_dashboard

try:
    from utils.reporte_docx import generar_reporte_docx
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


def render_tab_decision(ctx, tab1_output, tab2_output, tab3_output, analizar_con_llm_fn=None):
    """Renderiza la decision final: score ponderado, veredicto y analisis LLM.

    Recibe los outputs de los tabs anteriores (desglose, datos laborales,
    score territorial) y la funcion del LLM por inyeccion para evitar
    dependencia circular con app.py.
    """
    section_header("04", "Decision Final: Score de Pertinencia", "Score = (Acad x 0.30) + (Lab x 0.40) + (Terr x 0.20) + (Glob x 0.10)")

    # =================================================================
    # Desempaquetar outputs de tabs anteriores
    # =================================================================
    desglose = tab1_output.get('desglose', {}) if tab1_output else {}
    df_vacantes = tab2_output.get('df_vacantes', pd.DataFrame()) if tab2_output else pd.DataFrame()
    df_conocimientos = tab2_output.get('df_conocimientos', pd.DataFrame()) if tab2_output else pd.DataFrame()
    df_destrezas = tab2_output.get('df_destrezas', pd.DataFrame()) if tab2_output else pd.DataFrame()
    datos_salarios = tab2_output.get('datos_salarios', {"tiene_datos": False}) if tab2_output else {"tiene_datos": False}
    df_actividades = tab2_output.get('df_actividades', pd.DataFrame()) if tab2_output else pd.DataFrame()
    score_territorial_total = tab3_output.get('score_territorial_total', 50) if tab3_output else 50

    # Inicializar variables SIET (pueden no definirse si tiene_filtros_siet es False)
    stats_siet = None
    desglose_siet = None

    # Obtener datos globales
    df_global_decision = get_indicadores_globales()
    df_habilidades_decision = get_habilidades_futuro_filtradas(ctx.sel_nbc)

    # =================================================================
    # SCORE ACADEMICO (30%)
    # =================================================================
    _hhi = float(ctx.hhi) if ctx.hhi and ctx.hhi > 0 else 1000.0
    _cagr = float(ctx.cagr) if ctx.cagr is not None else 0.0
    hhi_score = max(0, min(100, 100 - (_hhi / 40)))
    cagr_score = max(0, min(100, 50 + _cagr * 10))
    score_acad = round(hhi_score * 0.60 + cagr_score * 0.40, 1)

    # =================================================================
    # SCORE LABORAL (40%)
    # =================================================================
    smlv_decision = 1_423_500
    _vacantes_real = 0
    _ratio_real = 0.0
    if not df_vacantes.empty and 'vacantes_2024' in df_vacantes.columns:
        _vacantes_real = int(df_vacantes['vacantes_2024'].sum())
        _ratio_real, _ = calcular_ratio_absorcion(ctx.graduados_anual, _vacantes_real)
    else:
        _ratio_real = ctx.ratio_abs if ctx.ratio_abs else 0.0

    if _vacantes_real > 50000:   comp_volumen = 100
    elif _vacantes_real > 20000: comp_volumen = 80
    elif _vacantes_real > 5000:  comp_volumen = 60
    elif _vacantes_real > 1000:  comp_volumen = 40
    elif _vacantes_real > 100:   comp_volumen = 20
    else:                        comp_volumen = 5

    _ratio_ajust = min(2.0, _ratio_real * 3)
    comp_absorcion = min(100, _ratio_ajust * 50)

    comp_salario = 50
    if datos_salarios and datos_salarios.get('tiene_datos'):
        _df_sigep_d = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame())
        if not _df_sigep_d.empty and 'salario_mediana' in _df_sigep_d.columns:
            _sal_med = _df_sigep_d['salario_mediana'].mean()
            if _sal_med and _sal_med > 0:
                comp_salario = min(100, (_sal_med / smlv_decision / 3) * 100)
        else:
            _df_ole = datos_salarios.get('ole_ibc', pd.DataFrame())
            if not _df_ole.empty and 'ibc_min_smmlv' in _df_ole.columns:
                _ibc_avg = _df_ole['ibc_min_smmlv'].mean()
                if _ibc_avg and _ibc_avg > 0:
                    comp_salario = min(100, (_ibc_avg / 3) * 100)

    _n_comp_dec = (len(df_conocimientos) + len(df_destrezas)) if not df_conocimientos.empty else 0
    comp_skills = min(100, _n_comp_dec * 5)

    score_lab = round(
        comp_volumen * 0.30 + comp_absorcion * 0.20 +
        comp_salario * 0.25 + comp_skills * 0.25, 1
    )

    if ctx.skills_bridge and ctx.skills_bridge.get('has_data'):
        alignment = ctx.skills_bridge.get('alignment_score_global', 0)
        complementarity = ctx.skills_bridge.get('complementarity_siet', 0)
        alignment_bonus = max(0, (alignment - 0.15) * 15)
        complementarity_bonus = max(0, (complementarity - 0.1) * 8)
        score_lab = min(100, round(score_lab + alignment_bonus + complementarity_bonus, 1))

    # =================================================================
    # SCORE TERRITORIAL (20%)
    # =================================================================
    score_terr = round(float(score_territorial_total), 1)

    # =================================================================
    # SCORE GLOBAL (10%)
    # =================================================================
    if not df_global_decision.empty and 'desempleo_jovenes' in df_global_decision.columns:
        desempleo_actual = df_global_decision.iloc[0]['desempleo_jovenes']
        score_glob = max(20, min(90, 100 - desempleo_actual * 2))
    else:
        score_glob = 50

    score_final, veredicto, color = calcular_score_final(score_acad, score_lab, score_terr, score_glob)

    # =================================================================
    # GAUGES
    # =================================================================
    g1, g2, g3, g4 = st.columns(4)
    with g1: st.plotly_chart(crear_gauge(score_acad, "Académico (30%)"), width='stretch')
    with g2: st.plotly_chart(crear_gauge(score_lab, "Laboral (40%)"), width='stretch')
    with g3: st.plotly_chart(crear_gauge(score_terr, "Territorial (20%)"), width='stretch')
    with g4: st.plotly_chart(crear_gauge(score_glob, "Global (10%)"), width='stretch')

    st.caption("Pesos de la decision final: Academica 30% | Laboral 40% | Territorial 20% | Global 10%.")

    insight_card("chart-simple", "Desglose del score",
        f"Academico: {score_acad:.0f}/100 | Laboral: {score_lab:.0f}/100 | Territorial: {score_terr:.0f}/100 | Global: {score_glob:.0f}/100",
        tone="insight")

    st.divider()

    col_score, col_veredicto = st.columns([1, 2])

    with col_score:
        st.markdown("### Score Final")
        fig_final = go.Figure(go.Indicator(
            mode="gauge+number", value=score_final,
            title={'text': "SCORE DE PERTINENCIA", 'font': {'size': 16, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
            number={'font': {'size': 34, 'family': 'Inter, sans-serif', 'color': '#0B0F19'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': '#A09088'},
                'bar': {'color': "#9b1b30"},
                'steps': [
                    {'range': [0, 50], 'color': "#F0EAE4"},
                    {'range': [50, 80], 'color': "#e0cd9e"},
                    {'range': [80, 100], 'color': "#F0EAE4"}
                ],
            },
            domain={'x': [0.05, 0.95], 'y': [0.08, 0.92]}
        ))
        fig_final.update_layout(height=220, margin=dict(l=10, r=10, t=45, b=0),
                                paper_bgcolor="#FFFFFF", font_family="Inter, sans-serif", font_color="#0B0F19")
        st.plotly_chart(fig_final, width='stretch')

    with col_veredicto:
        st.markdown("### Veredicto")
        if color == "green":
            st.markdown(f'<div class="score-green"><h2><i class="fas fa-check-circle veredicto-ok"></i> {veredicto}</h2></div>', unsafe_allow_html=True)
        elif color == "yellow":
            st.markdown(f'<div class="score-yellow"><h2><i class="fas fa-exclamation-triangle veredicto-warn"></i> {veredicto}</h2></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="score-red"><h2><i class="fas fa-times-circle veredicto-err"></i> {veredicto}</h2></div>', unsafe_allow_html=True)

        st.markdown("**Desglose del Score:**")
        desglose_score = pd.DataFrame({
            'Síntesis': ['Académica', 'Laboral', 'Territorial', 'Global'],
            'Score': [round(score_acad, 1), round(score_lab, 1), round(score_terr, 1), round(score_glob, 1)],
            'Peso': ['30%', '40%', '20%', '10%'],
            'Aporte': [round(score_acad*0.3, 1), round(score_lab*0.4, 1), round(score_terr*0.2, 1), round(score_glob*0.1, 1)]
        })
        st.dataframe(desglose_score, hide_index=True, width='stretch')
        descargar_datos_grafico(desglose_score, "desglose_score_pertinencia", "Descargar desglose")

        if ctx.skills_bridge and ctx.skills_bridge.get('has_data'):
            _align = ctx.skills_bridge.get('alignment_score_global', 0)
            _compl = ctx.skills_bridge.get('complementarity_siet', 0)
            st.caption(f"El score laboral incluye bonus por alineación SNIES↔SIET ({_align:.0%}) "
                      f"y complementariedad ETDH ({_compl:.0%}) via cadena estructural CUOC.")

    # =================================================================
    # TIPO DE OFERTA RECOMENDADA
    # =================================================================
    st.markdown("---")
    st.markdown('<h3 class="icon-header"><i class="fas fa-signs-post"></i> Tipo de Oferta Recomendada</h3>', unsafe_allow_html=True)
    st.caption("Recomendación basada en la combinación de las 4 síntesis evaluativas")

    n_competencias = (len(df_conocimientos) + len(df_destrezas)) if not df_conocimientos.empty else 0
    tipo_oferta, justificacion_oferta, icono_oferta = determinar_tipo_oferta(
        score_acad, score_lab, score_terr, n_competencias
    )

    color_tipo = {
        "PROGRAMA_COMPLETO": "#6B9080", "RUTA_FORMATIVA": "#d4835a",
        "MICROCREDENCIAL": "#cc8800", "EDUCACION_CONTINUA": "#d97706",
        "EVALUAR_VIABILIDAD": "#52423C", "NO_RECOMENDADO": "#9b1b30"
    }
    descripcion_tipos = {
        "PROGRAMA_COMPLETO": "Programa formal de educación superior (pregrado, especialización, maestría o doctorado) con registro calificado.",
        "RUTA_FORMATIVA": "Secuencia articulada de diplomados, cursos de extensión o certificaciones que construyen competencias progresivamente.",
        "MICROCREDENCIAL": "Certificaciones cortas y específicas orientadas a competencias puntuales demandadas por el mercado laboral.",
        "EDUCACION_CONTINUA": "Actualización permanente para profesionales ya vinculados laboralmente. Énfasis en upskilling y reskilling.",
        "EVALUAR_VIABILIDAD": "Se requiere un análisis más profundo antes de definir el tipo de oferta más adecuado.",
        "NO_RECOMENDADO": "Los indicadores sugieren que la oferta no sería viable en las condiciones actuales."
    }

    col_tipo, col_just = st.columns([1, 2])
    with col_tipo:
        color_actual = color_tipo.get(tipo_oferta, "#52423C")
        st.markdown(f"""
        <div class="rec-card" style="--rec-bg: {color_actual}10; --rec-accent: {color_actual};">
            <h4 class="rec-title"><i class="fas fa-{icono_oferta}"></i> {tipo_oferta.replace('_', ' ')}</h4>
            <p class="rec-text">{descripcion_tipos.get(tipo_oferta, '')}</p>
        </div>""", unsafe_allow_html=True)

    with col_just:
        st.markdown("**Justificación de la recomendación:**")
        st.info(justificacion_oferta)
        st.markdown("**Indicadores considerados:**")
        _etdh_progs = ctx.etdh_ml_stats.get('programas_siet_relacionados', 0) if ctx.etdh_ml_stats and isinstance(ctx.etdh_ml_stats, dict) and ctx.etdh_ml_stats.get('tiene_datos') else 0
        _bridge_align = f"{ctx.skills_bridge.get('alignment_score_global', 0):.0%}" if ctx.skills_bridge and ctx.skills_bridge.get('has_data') else 'N/A'
        indicadores_md = f"""
        | Indicador | Valor | Interpretación |
        |-----------|-------|----------------|
        | HHI (concentración) | {_hhi:,.0f} | {'Competitivo' if _hhi < 1500 else 'Moderado' if _hhi < 2500 else 'Concentrado'} |
        | CAGR matrícula | {_cagr:+.1f}% | {'Crecimiento' if _cagr > 2 else 'Estable' if _cagr > -1 else 'Declive'} |
        | Vacantes SPE | {_vacantes_real:,} | {'Alto volumen' if _vacantes_real > 20000 else 'Moderado' if _vacantes_real > 5000 else 'Bajo'} |
        | Ratio absorción (×3 ajust.) | {_ratio_ajust:.2f} | {'Favorable' if _ratio_ajust > 1 else 'Equilibrado' if _ratio_ajust > 0.5 else 'Competido'} |
        | Competencias CUOC | {_n_comp_dec} | {'Múltiples' if _n_comp_dec > 8 else 'Moderadas' if _n_comp_dec > 4 else 'Pocas'} |
        | Score Territorial | {score_terr:.0f}/100 | {'Favorable' if score_terr >= 60 else 'Moderado' if score_terr >= 40 else 'Limitado'} |
        | Alineación SNIES↔SIET | {_bridge_align} | {'Alta' if _bridge_align != 'N/A' and ctx.skills_bridge and ctx.skills_bridge.get('alignment_score_global', 0) > 0.3 else 'Media' if _bridge_align != 'N/A' and ctx.skills_bridge and ctx.skills_bridge.get('alignment_score_global', 0) > 0.15 else 'Baja o N/A'} |
        | Programas ETDH afines | {_etdh_progs} | {'Complemento fuerte' if _etdh_progs > 10 else 'Complemento moderado' if _etdh_progs > 3 else 'Sin complemento'} |
        """
        st.markdown(indicadores_md)

    # =================================================================
    # CONTEXTO GLOBAL
    # =================================================================
    st.markdown("---")
    st.markdown("### Contexto Global y Tendencias")
    st.caption("Información macroeconómica de Colombia y tendencias globales filtradas por relevancia para el programa")

    col_bm, col_hab = st.columns(2)
    with col_bm:
        st.markdown("#### Indicadores Banco Mundial (Colombia)")
        if not df_global_decision.empty:
            fig_desempleo = px.line(df_global_decision, x='anio', y='desempleo_jovenes',
                                    title="Desempleo Juvenil (15-24 años)", markers=True)
            fig_desempleo.update_layout(yaxis_title="% Desempleo")
            st.plotly_chart(fig_desempleo, width='stretch')
            descargar_datos_grafico(df_global_decision, "desempleo_jovenil_colombia", "Descargar datos")
            ultimo_dato = df_global_decision.iloc[0]
            st.metric(f"Desempleo Juvenil {int(ultimo_dato['anio'])}", f"{ultimo_dato['desempleo_jovenes']:.1f}%")
        else:
            st.warning("Sin datos de indicadores globales disponibles")

    with col_hab:
        st.markdown(f"#### Destrezas Laborales para {ctx.filtro_label}")
        if len(ctx.sel_nbcs) > 1:
            _dfs_dest = [get_destrezas_cuoc_nbc(n) for n in ctx.sel_nbcs[:5]]
            _dfs_dest = [d for d in _dfs_dest if not d.empty]
            df_destrezas_cuoc = pd.concat(_dfs_dest, ignore_index=True).drop_duplicates(subset=['destreza']).head(20) if _dfs_dest else pd.DataFrame()
        else:
            df_destrezas_cuoc = get_destrezas_cuoc_nbc(ctx.sel_nbc)

        if not df_destrezas_cuoc.empty:
            df_top = df_destrezas_cuoc.head(10).copy()
            fig_hab = px.bar(
                df_top, x='relevancia', y='destreza', orientation='h',
                title=f"Destrezas Relevantes para {ctx.filtro_label[:30]}...",
                color='relevancia',
                color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']],
                labels={'relevancia': 'Relevancia (%)', 'destreza': 'Destreza', 'n_ocupaciones': 'Ocupaciones'}
            )
            fig_hab.update_layout(yaxis={'categoryorder': 'total ascending'})
            fig_hab.update_traces(hovertemplate='<b>%{y}</b><br>Relevancia: %{x:.0f}%<extra></extra>')
            st.plotly_chart(fig_hab, width='stretch')
            descargar_datos_grafico(df_top, "destrezas_cuoc_nbc", "Descargar datos")
        else:
            if not df_habilidades_decision.empty:
                fig_hab = px.bar(df_habilidades_decision.head(8), x='demanda_2024_score', y='habilidad',
                                 orientation='h', title="Top Habilidades por Demanda Global (Fallback)",
                                 color='crecimiento_anual_pct',
                                 color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']])
                fig_hab.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_hab, width='stretch')
            else:
                st.warning("Sin datos de destrezas disponibles para este NBC")

    # =================================================================
    # ESCO
    # =================================================================
    st.markdown("---")
    st.markdown("### Tendencias Globales de Habilidades Demandadas (ESCO)")
    _esco_sector_label = ', '.join(ctx.sel_areas[:2]) if ctx.sel_areas else ctx.filtro_label
    try:
        df_esco_top, df_esco_all = get_habilidades_esco(sel_areas=ctx.sel_areas, top_n=15)
    except Exception:
        df_esco_top, df_esco_all = pd.DataFrame(), pd.DataFrame()

    if not df_esco_top.empty:
        fig_esco = px.bar(
            df_esco_top.sort_values('n_ocupaciones_total', ascending=True),
            x='n_ocupaciones_total', y='habilidad', orientation='h',
            title=f"Top 15 Habilidades Globales — {_esco_sector_label[:40]}",
            color='n_ocupaciones_total',
            color_continuous_scale=[[0, '#F0EAE4'], [0.3, '#C7A951'], [0.6, '#D97706'], [0.85, '#9B1B30'], [1, '#7A1525']],
            labels={'n_ocupaciones_total': 'N° Ocupaciones Asociadas', 'habilidad': ''},
            hover_data={'tipo_skill': True, 'sector': True, 'categoria': True}
        )
        fig_esco.update_layout(height=480, yaxis={'categoryorder': 'total ascending'}, coloraxis_colorbar_title="Ocupaciones")
        fig_esco.update_traces(hovertemplate='<b>%{y}</b><br>Ocupaciones: %{x}<br>Tipo: %{customdata[0]}<br>Sector: %{customdata[1]}<br>Categoría: %{customdata[2]}<extra></extra>')
        st.plotly_chart(fig_esco, width='stretch')
        _col_m1, _col_m2, _col_m3 = st.columns(3)
        with _col_m1: st.metric("Habilidades en sector", f"{len(df_esco_all):,}")
        with _col_m2:
            _avg_ocup = df_esco_all['n_ocupaciones_total'].mean() if not df_esco_all.empty else 0
            st.metric("Promedio ocupaciones/habilidad", f"{_avg_ocup:.1f}")
        with _col_m3:
            _top_skill = df_esco_top.iloc[0]['habilidad'] if len(df_esco_top) > 0 else "N/A"
            st.metric("Habilidad más demandada", _top_skill[:30])
        if not df_esco_all.empty:
            _csv_esco = df_esco_all.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label=f"Descargar todas las habilidades ESCO del sector ({len(df_esco_all):,} registros)",
                             data=_csv_esco, file_name=f"habilidades_esco_{_esco_sector_label[:20].replace(' ', '_').replace(',', '')}.csv",
                             mime="text/csv", key="download_esco_all")
    else:
        st.info("No se encontraron habilidades ESCO para los filtros seleccionados.")

    # =================================================================
    # SIET/ETDH en Tab 4
    # =================================================================
    if ctx.tiene_filtros_siet:
        st.markdown("---")
        st.markdown('<h4 class="icon-header"><i class="fas fa-tools"></i> Contexto SIET / ETDH (Educación para el Trabajo)</h4>', unsafe_allow_html=True)

        _safe_areas = [a for a in ctx._ml_areas_siet if a is not None] if ctx._ml_areas_siet else []
        if _safe_areas:
            if ctx.sel_nbcs:
                st.caption(f"Filtrado por cadena NBC → SIET: **{', '.join(_safe_areas)}**")
            elif ctx.sel_campos_amplios:
                st.caption(f"Filtrado por Campo Amplio → SIET: **{', '.join(_safe_areas)}**")
            elif ctx.sel_areas:
                st.caption(f"Filtrado por Área Conocimiento → SIET: **{', '.join(_safe_areas)}**")
            else:
                st.caption(f"Áreas SIET derivadas: **{', '.join(_safe_areas)}**")
        else:
            st.caption("Información complementaria de educación técnica no formal")

        stats_siet = get_estadisticas_siet(
            areas_desempeno=ctx.effective_areas_siet, deptos=ctx.effective_deptos_siet,
            estados=ctx.sel_estados_siet if ctx.sel_estados_siet else None,
            busqueda_nombre=ctx.busqueda_programa if ctx.busqueda_programa else None
        )

        col_siet_k1, col_siet_k2, col_siet_k3, col_siet_k4 = st.columns(4)
        col_siet_k1.metric("Programas ETDH", f"{stats_siet['total_programas']:,}")
        col_siet_k2.metric("Instituciones ETDH", f"{stats_siet['total_instituciones']:,}")
        col_siet_k3.metric("Duración Promedio", f"{stats_siet['duracion_promedio']:,} hrs")
        col_siet_k4.metric("Certificados 2023", f"{stats_siet['total_certificados']:,}")

        desglose_siet = get_desglose_siet(ctx.effective_areas_siet, ctx.effective_deptos_siet,
                                          ctx.busqueda_programa,
                                          modalidades_siet=ctx.sel_modalidades_siet if ctx.sel_modalidades_siet else None,
                                          estados=ctx.sel_estados_siet if ctx.sel_estados_siet else None)
        with st.expander("Ver distribución detallada SIET", expanded=False):
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                df_area_siet = desglose_siet.get('por_area', pd.DataFrame())
                if not df_area_siet.empty:
                    fig_area_siet = px.pie(df_area_siet, values='programas', names='area',
                                           title="Programas por Área de Desempeño SIET", hole=0.3)
                    fig_area_siet.update_layout(legend=dict(font=dict(size=8)))
                    fig_area_siet.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_area_siet, width='stretch')
                    descargar_datos_grafico(df_area_siet, "siet_areas_decision", "Datos")
            with col_exp2:
                df_depto_siet = desglose_siet.get('por_depto', pd.DataFrame())
                if not df_depto_siet.empty:
                    fig_depto_siet = px.bar(df_depto_siet.head(10), x='programas', y='departamento',
                                            orientation='h', title="Top 10 Departamentos ETDH",
                                            color='programas',
                                            color_continuous_scale=[[0, '#F9F7F4'], [0.33, '#E5DDD6'], [0.66, '#A09088'], [1, '#9B1B30']])
                    fig_depto_siet.update_layout(yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_depto_siet, width='stretch')
                    descargar_datos_grafico(df_depto_siet, "siet_deptos_decision", "Datos")

        # ML matching
        if ctx.etdh_ml_stats and isinstance(ctx.etdh_ml_stats, dict) and ctx.etdh_ml_stats.get('tiene_datos'):
            st.markdown("---")
            st.markdown('<h3 class="icon-header"><i class="fas fa-link"></i> Programas ETDH Relacionados (Matching Inteligente)</h3>', unsafe_allow_html=True)
            st.caption(f"Programas de Educación para el Trabajo más afines a **{ctx.filtro_label}** identificados por similitud semántica + puente estructural")

            col_ml1, col_ml2, col_ml3, col_ml4 = st.columns(4)
            col_ml1.metric("Programas ETDH Afines", f"{ctx.etdh_ml_stats['programas_siet_relacionados']}")
            col_ml2.metric("Matrícula ETDH 2023", f"{ctx.etdh_ml_stats['matricula_siet']:,}")
            col_ml3.metric("Certificados 2023", f"{ctx.etdh_ml_stats['certificados_siet']:,}")
            areas_txt = ', '.join([a for a in ctx.etdh_ml_stats.get('areas_desempeno', []) if a is not None][:3])
            col_ml4.metric("Áreas SIET", areas_txt if areas_txt else "—")

            top_progs = ctx.etdh_ml_stats.get('top_programas', [])
            if top_progs:
                with st.expander("Ver programas ETDH más afines", expanded=True):
                    rows = []
                    for p in top_progs:
                        relevancia = "Alta" if p['score'] >= 0.6 else "Media" if p['score'] >= 0.45 else "Baja"
                        rows.append({
                            'Programa ETDH': p['nombre'], 'Área Desempeño': p['area'],
                            'Relevancia': relevancia, 'Similitud': f"{p['score']:.1%}",
                            'Matrícula 2023': f"{p['matricula']:,}" if p['matricula'] else "—",
                            'Certificados': f"{p['certificados']:,}" if p['certificados'] else "—",
                        })
                    df_ml_display = pd.DataFrame(rows)
                    st.dataframe(df_ml_display, width='stretch', hide_index=True)

        # Comparativa SNIES vs SIET
        st.markdown("---")
        st.markdown("### Comparativa SNIES vs SIET: Oferta Educativa Complementaria")
        col_comp1, col_comp2 = st.columns([3, 2])
        with col_comp1:
            df_comp_depto = get_comparativa_snies_siet_por_depto(filtros=ctx.filtros_seleccionados, areas_desempeno_siet=ctx.effective_areas_siet)
            if not df_comp_depto.empty:
                df_melt = df_comp_depto.melt(id_vars=['departamento'], value_vars=['programas_snies', 'programas_siet'], var_name='fuente', value_name='programas')
                df_melt['fuente'] = df_melt['fuente'].map({'programas_snies': 'SNIES (Edu. Superior)', 'programas_siet': 'SIET (ETDH)'})
                fig_comp = px.bar(df_melt, x='programas', y='departamento', color='fuente', orientation='h',
                                  title="Programas por Departamento: SNIES vs SIET", barmode='group',
                                  color_discrete_map={'SNIES (Edu. Superior)': '#d4835a', 'SIET (ETDH)': '#6B9080'})
                fig_comp.update_layout(height=400, yaxis={'categoryorder': 'total ascending'},
                                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_comp, width='stretch')
                descargar_datos_grafico(df_comp_depto, "comparativa_snies_siet_depto", "Descargar datos")
            else:
                st.info("Sin datos comparativos disponibles")
        with col_comp2:
            df_tipos = get_comparativa_tipo_formacion(filtros=ctx.filtros_seleccionados, areas_desempeno_siet=ctx.effective_areas_siet)
            if not df_tipos.empty:
                fig_tipos = px.treemap(df_tipos, path=['fuente', 'tipo_formacion'], values='programas',
                                       title="Distribución por Tipo de Formación", color='fuente',
                                       color_discrete_map={'SNIES (Edu. Superior)': '#d4835a', 'SIET (ETDH)': '#6B9080'})
                fig_tipos.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=30), paper_bgcolor="#FFFFFF", font_color="#0B0F19")
                st.plotly_chart(fig_tipos, width='stretch')
                descargar_datos_grafico(df_tipos, "comparativa_tipo_formacion", "Descargar datos")
            else:
                st.info("Sin datos de tipos de formacion disponibles")

    # =================================================================
    # ANALISIS CON LLM
    # =================================================================
    st.markdown("---")
    st.markdown("### Analisis Inteligente con IA")
    st.caption("Genera un analisis de pertinencia usando inteligencia artificial (Gemini)")

    instrucciones_usuario = st.text_area(
        "Instrucciones adicionales (opcional)",
        placeholder="Ej: Profundiza en microcredenciales para IA, enfocate en el sector fintech, compara con tendencias en Chile y Mexico...",
        height=80, help="Agrega indicaciones especificas para enfocar o expandir el analisis."
    )

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        analizar_btn = st.button("Analizar con IA", type="primary", width='stretch',
                                 help="Genera un analisis completo usando el LLM de Gemini")
    with col_info:
        st.caption("El analisis incluye: Sintesis ejecutiva, Oportunidades y riesgos, Recomendacion de pertinencia, Conexion SNIES-SIET")

    if analizar_btn:
        if analizar_con_llm_fn is None:
            st.error("Funcion de analisis LLM no disponible.")
        else:
            with loading_overlay("Generando análisis con IA..."):
                matriculados_ultimo = ctx.df_tendencia['matriculados'].iloc[-1] if not ctx.df_tendencia.empty else 0
                stats_snies_ctx = {
                    'total_programas': ctx.stats_originales.get('total_programas', 0),
                    'total_instituciones': ctx.stats_originales.get('total_ies', 0),
                    'hhi': round(ctx.hhi, 2) if ctx.hhi else 'N/A',
                    'cagr': round(ctx.cagr, 2) if ctx.cagr else 'N/A',
                    'graduados_anual': ctx.graduados_anual,
                    'matriculados': matriculados_ultimo
                }
                stats_siet_ctx = stats_siet if stats_siet is not None else get_estadisticas_siet()
                desglose_siet_ctx = desglose_siet if desglose_siet is not None else get_desglose_siet()

                df_salarios_ctx = datos_salarios.get('sigep_nivel_educativo', pd.DataFrame()) if datos_salarios and datos_salarios.get('tiene_datos') else pd.DataFrame()

                n_competencias_ctx = (len(df_conocimientos) + len(df_destrezas)) if not df_conocimientos.empty else 0
                tipo_oferta_ctx = {'tipo': tipo_oferta, 'justificacion': justificacion_oferta, 'icono': icono_oferta}

                contexto = generar_contexto_analisis(
                    nbc=ctx.nbc_display or ctx.sel_nbc, depto=ctx.depto_display or ctx.arg_depto,
                    stats_snies=stats_snies_ctx, stats_siet=stats_siet_ctx,
                    score_final=score_final, veredicto=veredicto,
                    df_market=ctx.df_market, df_tendencia=ctx.df_tendencia,
                    df_graduados=ctx.df_graduados, desglose=desglose, desglose_siet=desglose_siet_ctx,
                    hhi_data={'valor': ctx.hhi, 'interpretacion': ctx.hhi_interp},
                    cagr_data={'valor': ctx.cagr, 'interpretacion': ctx.cagr_interp},
                    df_vacantes=df_vacantes, df_conocimientos=df_conocimientos,
                    df_destrezas=df_destrezas, df_salarios=df_salarios_ctx,
                    df_actividades=df_actividades, tipo_oferta_data=tipo_oferta_ctx,
                    filtros_activos=ctx.filtros_seleccionados, skills_bridge=ctx.skills_bridge
                )

                if ctx.etdh_ml_stats and isinstance(ctx.etdh_ml_stats, dict) and ctx.etdh_ml_stats.get('tiene_datos'):
                    ml_ctx = "\n\n## MATCHING INTELIGENTE SNIES↔ETDH\n"
                    ml_ctx += f"Programas ETDH afines a {ctx.nbc_display or ctx.sel_nbc}: {ctx.etdh_ml_stats['programas_siet_relacionados']}\n"
                    ml_ctx += f"Matrícula ETDH 2023 en programas afines: {ctx.etdh_ml_stats['matricula_siet']:,}\n"
                    ml_ctx += f"Certificados ETDH 2023: {ctx.etdh_ml_stats['certificados_siet']:,}\n"
                    ml_ctx += f"Áreas SIET relacionadas: {', '.join([a for a in ctx.etdh_ml_stats.get('areas_desempeno', []) if a])}\n"
                    top_progs = ctx.etdh_ml_stats.get('top_programas', [])[:5]
                    if top_progs:
                        ml_ctx += "Top programas ETDH más afines:\n"
                        for p in top_progs:
                            ml_ctx += f"  - {p['nombre']} (similitud: {p['score']:.1%}, matrícula: {p['matricula']:,})\n"
                    contexto += ml_ctx

                if ctx.skills_bridge and ctx.skills_bridge.get('has_data'):
                    bridge_ctx = "\n\n## PUENTE DE COMPETENCIAS SNIES ↔ SIET/ETDH (vía CUOC)\n"
                    bridge_ctx += f"Alineación global de competencias: {ctx.skills_bridge.get('alignment_score_global', 0):.0%}\n"
                    bridge_ctx += f"Complementariedad SIET: {ctx.skills_bridge.get('complementarity_siet', 0):.0%}\n"
                    bridge_ctx += f"Conocimientos compartidos: {len(ctx.skills_bridge.get('shared_conocimientos', []))}\n"
                    bridge_ctx += f"Destrezas compartidas: {len(ctx.skills_bridge.get('shared_destrezas', []))}\n"
                    bridge_ctx += f"Ocupaciones CUOC vía SNIES: {len(ctx.skills_bridge.get('snies_ocupaciones', []))}\n"
                    bridge_ctx += f"Ocupaciones CUOC vía SIET: {len(ctx.skills_bridge.get('siet_ocupaciones', []))}\n"
                    if ctx.skills_bridge.get('ciiu_sectors'):
                        ciiu_list = [f"{s.get('seccion', '?')}: {s.get('nombre', '?')[:40]}" for s in ctx.skills_bridge['ciiu_sectors'][:5]]
                        bridge_ctx += f"Sectores CIIU relacionados: {', '.join(ciiu_list)}\n"
                    if ctx.skills_bridge.get('shared_conocimientos'):
                        bridge_ctx += f"Conocimientos en común SNIES-SIET: {', '.join(ctx.skills_bridge['shared_conocimientos'][:8])}\n"
                    if ctx.skills_bridge.get('shared_destrezas'):
                        bridge_ctx += f"Destrezas en común SNIES-SIET: {', '.join(ctx.skills_bridge['shared_destrezas'][:8])}\n"
                    contexto += bridge_ctx

                resultado_analisis = analizar_con_llm_fn(
                    contexto, nbc_codigo=ctx.sel_nbc, departamento=ctx.arg_depto,
                    filtros_activos=ctx.filtros_seleccionados, instrucciones_adicionales=instrucciones_usuario
                )

                st.markdown("---")
                st.markdown("#### Informe de Pertinencia Educativa")
                st.markdown(resultado_analisis)

                st.markdown("---")
                col_dl1, col_dl2 = st.columns([1, 2])
                with col_dl1:
                    if _DOCX_AVAILABLE:
                        try:
                            docx_bytes = generar_reporte_docx(
                                contenido_markdown=resultado_analisis,
                                nbc=ctx.nbc_display or ctx.sel_nbc,
                                depto=ctx.depto_display or ctx.arg_depto or "Nacional"
                            )
                            nombre_archivo = f"informe_pertinencia_{(ctx.nbc_display or ctx.sel_nbc or 'analisis').replace(' ', '_')[:40]}.docx"
                            st.download_button(label="Descargar Informe Word", data=docx_bytes,
                                             file_name=nombre_archivo,
                                             mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                             type="primary", width='stretch', icon=":material/download:")
                        except Exception as e_docx:
                            st.error(f"No se pudo generar el documento: {e_docx}")
                with col_dl2:
                    st.caption("Documento Word profesional con portada institucional, marca de agua, encabezados, tabla de metricas, referencias APA y diseño editorial completo.")

                with st.expander("Ver datos enviados al modelo", expanded=False):
                    st.code(contexto, language="markdown")
                    if instrucciones_usuario:
                        st.markdown("**Instrucciones adicionales del usuario:**")
                        st.info(instrucciones_usuario)
