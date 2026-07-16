"""
Carga centralizada de datos para el dashboard.

Toda la logica de consulta a DuckDB que necesita el dashboard
antes de renderizar tabs vive aqui: estadisticas SNIES,
tendencias historicas, matching ML SNIES-SIET, metricas HHI/CAGR
y areas SIET efectivas derivadas de filtros.

Es agnostica de la UI: no llama a st.* directamente. El llamador
puede envolverla en loading_overlay() para mostrar un spinner.
"""
import pandas as pd
from config.database import get_conn
from data import (
    resolver_nbcs_desde_filtros,
    get_estadisticas_basicas,
    get_benchmarking_data,
    get_market_share,
    get_tendencia_matricula,
    get_graduados_historico,
    get_tendencia_inscritos,
    get_tendencia_admitidos,
    get_tendencia_primer_curso,
    get_conectividad_territorial,
)
from services import calcular_hhi, calcular_cagr, calcular_ratio_absorcion
from services.context import Context

try:
    from services.ml.snies_etdh import match_nbc_to_siet_v2, get_skills_bridge_analysis_v2
    _ML_AVAILABLE = True
except ImportError:
    _ML_AVAILABLE = False


def cargar_datos_base(filtros_seleccionados: dict, filtros_siet_seleccionados: dict) -> Context:
    """
    Construye el Context con todos los datos del dashboard.

    Realiza:
    - Resolucion de NBCs (explicitos o via cascada Campo/Area)
    - Estadisticas SNIES, benchmark, market share, tendencias
    - Matching ML SNIES-ETDH y skills bridge via CUOC
    - Metricas HHI, CAGR, ratio de absorcion
    - Areas SIET efectivas derivadas de filtros
    """
    ctx = Context()

    # =====================================================================
    # DESEMPACAR FILTROS
    # =====================================================================
    ctx.filtros_seleccionados = filtros_seleccionados
    ctx.filtros_siet_seleccionados = filtros_siet_seleccionados

    ctx.sel_campos_amplios = filtros_seleccionados['campos_amplios']
    ctx.sel_areas = filtros_seleccionados['areas']
    ctx.sel_nbcs = filtros_seleccionados['nbcs']
    ctx.sel_deptos = filtros_seleccionados['deptos']
    ctx.sel_munis = filtros_seleccionados['municipios']
    ctx.sel_modalidades = filtros_seleccionados['modalidades']
    ctx.sel_sectores = filtros_seleccionados['sectores']
    ctx.sel_niveles = filtros_seleccionados['niveles']
    ctx.sel_caracteres = filtros_seleccionados['caracteres']
    ctx.sel_estados = filtros_seleccionados['estados']
    ctx.busqueda_programa = filtros_seleccionados['busqueda_nombre']
    ctx.sel_cod_snies_programas = filtros_seleccionados['cod_snies_programas']

    ctx.sel_areas_siet = filtros_siet_seleccionados['areas_desempeno']
    ctx.sel_deptos_siet = filtros_siet_seleccionados['deptos_siet']
    ctx.sel_estados_siet = filtros_siet_seleccionados['estados_siet']
    ctx.sel_modalidades_siet = filtros_siet_seleccionados.get('modalidades_siet', [])
    ctx.mostrar_siet = filtros_siet_seleccionados['mostrar']

    # =====================================================================
    # RESOLUCION DE NBCs
    # =====================================================================
    ctx.nbcs_explicitos = bool(ctx.sel_nbcs)
    if not ctx.sel_nbcs and (ctx.sel_areas or ctx.sel_campos_amplios or ctx.busqueda_programa):
        ctx.sel_nbcs = resolver_nbcs_desde_filtros(filtros_seleccionados)
        if ctx.busqueda_programa and ctx.sel_nbcs:
            filtros_seleccionados['nbcs'] = ctx.sel_nbcs

    ctx.sel_nbc = ctx.sel_nbcs[0] if ctx.sel_nbcs else None

    # =====================================================================
    # LABELS PARA DISPLAY
    # =====================================================================
    if ctx.nbcs_explicitos:
        ctx.filtro_label = ', '.join(ctx.sel_nbcs[:3]) + ('...' if len(ctx.sel_nbcs) > 3 else '')
    elif ctx.sel_nbcs:
        ctx.filtro_label = ', '.join(ctx.sel_nbcs[:3]) + ('...' if len(ctx.sel_nbcs) > 3 else '')
    elif ctx.sel_areas:
        ctx.filtro_label = ', '.join(ctx.sel_areas[:2])
    elif ctx.sel_campos_amplios:
        ctx.filtro_label = ', '.join(ctx.sel_campos_amplios[:2])
    else:
        ctx.filtro_label = 'Filtros aplicados'

    ctx.arg_depto = ctx.sel_deptos[0] if ctx.sel_deptos else None
    ctx.nbc_display = ctx.filtro_label
    ctx.depto_display = (
        ', '.join(ctx.sel_deptos[:3]) + ('...' if len(ctx.sel_deptos) > 3 else '')
        if ctx.sel_deptos else None
    )

    # =====================================================================
    # CARGA DE DATOS SNIES
    # =====================================================================
    ctx.stats = get_estadisticas_basicas(filtros=filtros_seleccionados)
    ctx.stats_originales = ctx.stats.copy()
    ctx.df_benchmark = get_benchmarking_data(filtros=filtros_seleccionados)
    ctx.df_market = get_market_share(filtros=filtros_seleccionados)
    ctx.df_tendencia = get_tendencia_matricula(filtros=filtros_seleccionados)
    ctx.df_graduados = get_graduados_historico(filtros=filtros_seleccionados)
    ctx.df_inscritos = get_tendencia_inscritos(filtros=filtros_seleccionados)
    ctx.df_admitidos = get_tendencia_admitidos(filtros=filtros_seleccionados)
    ctx.df_primer_curso = get_tendencia_primer_curso(filtros=filtros_seleccionados)
    ctx.df_conectividad = get_conectividad_territorial(ctx.arg_depto)

    # =====================================================================
    # ML MATCHING SNIES <-> ETDH
    # =====================================================================
    ctx.etdh_ml_stats = None
    ctx.skills_bridge = None
    if ctx.sel_nbcs:
        conn_etdh = get_conn()
        try:
            if len(ctx.sel_nbcs) == 1:
                df_siet = match_nbc_to_siet_v2(ctx.sel_nbcs[0], conn_etdh, top_k=30)
                if df_siet is not None and not df_siet.empty:
                    ctx.etdh_ml_stats = {
                        'programas_siet_relacionados': len(df_siet),
                        'matricula_siet': int(df_siet['matricula_2023'].sum()) if 'matricula_2023' in df_siet.columns else 0,
                        'certificados_siet': int(df_siet['certificados_2023'].sum()) if 'certificados_2023' in df_siet.columns else 0,
                        'areas_desempeno': df_siet['area_desempeno'].dropna().unique().tolist() if 'area_desempeno' in df_siet.columns else [],
                        'top_programas': [
                            {
                                'nombre': row['nombre_programa'],
                                'area': row.get('area_desempeno', ''),
                                'score': float(row.get('score_final', 0)),
                                'matricula': int(row.get('matricula_2023', 0)),
                                'certificados': int(row.get('certificados_2023', 0)),
                            }
                            for _, row in df_siet.head(20).iterrows()
                        ],
                        'tiene_datos': True,
                    }
                try:
                    ctx.skills_bridge = get_skills_bridge_analysis_v2(
                        ctx.sel_nbcs[0], conn_etdh, depto=ctx.arg_depto
                    )
                except Exception as e_bridge:
                    print(f"[Bridge-v2] Error: {e_bridge}")
            else:
                combined = {
                    'programas_siet_relacionados': 0,
                    'matricula_siet': 0, 'certificados_siet': 0,
                    'areas_desempeno': [], 'top_programas': [],
                    'tiene_datos': False
                }
                seen_progs = set()
                for nbc_i in ctx.sel_nbcs[:5]:
                    df_i = match_nbc_to_siet_v2(nbc_i, conn_etdh, top_k=30)
                    if not df_i.empty:
                        combined['tiene_datos'] = True
                        combined['matricula_siet'] += int(df_i['matricula_2023'].sum())
                        combined['certificados_siet'] += int(df_i['certificados_2023'].sum())
                        for area in df_i['area_desempeno'].dropna().unique():
                            if area not in combined['areas_desempeno']:
                                combined['areas_desempeno'].append(area)
                        for _, row in df_i.iterrows():
                            key = row['nombre_programa']
                            if key not in seen_progs:
                                seen_progs.add(key)
                                combined['top_programas'].append({
                                    'nombre': key,
                                    'area': row.get('area_desempeno', ''),
                                    'score': float(row.get('score_final', 0)),
                                    'matricula': int(row.get('matricula_2023', 0)),
                                    'certificados': int(row.get('certificados_2023', 0)),
                                })
                combined['programas_siet_relacionados'] = len(combined['top_programas'])
                combined['top_programas'] = sorted(
                    combined['top_programas'], key=lambda x: x['score'], reverse=True
                )[:20]
                if combined['tiene_datos']:
                    ctx.etdh_ml_stats = combined
                try:
                    ctx.skills_bridge = get_skills_bridge_analysis_v2(
                        ctx.sel_nbcs[0], conn_etdh, depto=ctx.arg_depto
                    )
                except Exception as e_bridge:
                    print(f"[Bridge-v2] Error multi-NBC: {e_bridge}")
        except Exception as e:
            print(f"[Bridge] Error: {e}")
        finally:
            try:
                conn_etdh.close()
            except Exception:
                pass

    # =====================================================================
    # AREAS SIET EFECTIVAS
    # =====================================================================
    ctx._ml_areas_siet = None
    if ctx.etdh_ml_stats is not None and isinstance(ctx.etdh_ml_stats, dict) \
            and ctx.etdh_ml_stats.get('tiene_datos') \
            and ctx.etdh_ml_stats.get('areas_desempeno'):
        ctx._ml_areas_siet = ctx.etdh_ml_stats['areas_desempeno']

    ctx.effective_areas_siet = (
        ctx._ml_areas_siet if ctx._ml_areas_siet
        else (ctx.sel_areas_siet if ctx.sel_areas_siet else None)
    )
    ctx.effective_deptos_siet = (
        ctx.sel_deptos_siet if ctx.sel_deptos_siet
        else (ctx.sel_deptos if ctx.sel_deptos else None)
    )

    # =====================================================================
    # METRICAS CALCULADAS
    # =====================================================================
    ctx.hhi, ctx.hhi_interp = calcular_hhi(ctx.df_market)
    ctx.cagr, ctx.cagr_interp = calcular_cagr(ctx.df_tendencia)

    ctx.graduados_anual = ctx.df_graduados['graduados'].iloc[-1] if not ctx.df_graduados.empty else 0
    ctx.vacantes_est = int(ctx.graduados_anual * 1.1)
    ctx.ratio_abs, ctx.ratio_interp = calcular_ratio_absorcion(ctx.graduados_anual, ctx.vacantes_est)

    # =====================================================================
    # LABEL_AMBITO
    # =====================================================================
    tiene_filtros_activos = (
        ctx.sel_deptos or ctx.sel_modalidades or ctx.sel_sectores or
        ctx.sel_niveles or ctx.sel_estados or ctx.busqueda_programa or
        ctx.sel_cod_snies_programas
    )
    if tiene_filtros_activos:
        partes_contexto = []
        if ctx.sel_deptos:
            partes_contexto.append("/".join(d[:8] for d in ctx.sel_deptos[:2]))
        if ctx.sel_modalidades:
            partes_contexto.append("/".join(m[:4] for m in ctx.sel_modalidades[:2]))
        if ctx.sel_sectores:
            partes_contexto.append("/".join(s[:4] for s in ctx.sel_sectores[:2]))
        if ctx.sel_niveles:
            partes_contexto.append("/".join(n[:4] for n in ctx.sel_niveles[:2]))
        if ctx.sel_estados:
            partes_contexto.append("/".join(e[:6] for e in ctx.sel_estados[:2]))
        if ctx.busqueda_programa:
            partes_contexto.append(f"Búsq: {ctx.busqueda_programa[:15]}")
        if ctx.sel_cod_snies_programas:
            partes_contexto.append(f"CódSNIES: {len(ctx.sel_cod_snies_programas)}")
        contexto_filtros = " | ".join(partes_contexto)
        ctx.label_ambito = f"Filtrado: {contexto_filtros}"
    else:
        ctx.label_ambito = "Análisis Nacional"

    return ctx
