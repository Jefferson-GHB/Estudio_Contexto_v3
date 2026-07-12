"""Metricas de negocio para analisis de pertinencia educativa: HHI, CAGR, ratios y scoring."""

import numpy as np
import pandas as pd


def calcular_hhi(df_market_share):
    """Indice Herfindahl-Hirschman con validacion de tamaño muestral.
    HHI = Sum(si^2). Se aplica solo si el mercado es suficientemente grande.
    Umbrales DOJ 2023: < 1000 competitivo, 1000-1800 moderado, > 1800 concentrado.
    """
    if df_market_share.empty or 'share' not in df_market_share.columns:
        return 0, "Sin datos"

    n = len(df_market_share)
    total_mat = df_market_share['matriculados'].sum() if 'matriculados' in df_market_share.columns else 0
    hhi = np.sum(df_market_share['share'] ** 2)

    # Validacion de contexto: el HHI no es fiable con pocos actores o mercado pequeño
    if total_mat < 1000:
        return round(hhi, 0), f"Mercado incipiente ({total_mat:,.0f} estudiantes) — HHI no determinante"
    if n < 4:
        return round(hhi, 0), f"Solo {n} IES ofertando — HHI no aplica con pocos actores"

    # Umbrales DOJ 2023
    if hhi < 1000:
        interpretacion = "Mercado competitivo"
    elif hhi < 1800:
        interpretacion = "Moderadamente concentrado"
    else:
        interpretacion = "Alta concentracion"

    return round(hhi, 0), f"{interpretacion} ({n} IES, {total_mat:,.0f} estudiantes)"


def calcular_cagr(df_tendencia):
    """Tasa de Crecimiento Anual Compuesto con validacion de datos.
    CAGR = (Vf/Vi)^(1/n) - 1. Requiere al menos 3 años de datos."""
    if df_tendencia.empty or len(df_tendencia) < 2:
        return 0, "Sin datos historicos"

    n_years = len(df_tendencia)
    if n_years < 3:
        return 0, f"Tendencia con pocos datos ({n_years} años) — CAGR no fiable"

    df_sorted = df_tendencia.sort_values('anio')
    v_inicial = df_sorted.iloc[0]['matriculados']
    v_final = df_sorted.iloc[-1]['matriculados']

    try:
        n = int(df_sorted['anio'].iloc[-1]) - int(df_sorted['anio'].iloc[0])
    except (ValueError, TypeError):
        n = len(df_sorted) - 1

    if n <= 0:
        return 0, "Periodo insuficiente"

    if v_inicial <= 0 or v_final <= 0:
        return 0, "Datos insuficientes"

    cagr = ((v_final / v_inicial) ** (1 / n)) - 1
    cagr_pct = cagr * 100

    if cagr_pct > 5:
        interpretacion = "Crecimiento fuerte"
    elif cagr_pct > 0:
        interpretacion = "Crecimiento moderado"
    elif cagr_pct > -5:
        interpretacion = "Estancamiento"
    else:
        interpretacion = "Declive"

    return round(cagr_pct, 2), f"{interpretacion} ({n_years} años)"


def calcular_ratio_absorcion(graduados, vacantes):
    """Ratio de Absorcion Laboral = Vacantes / Graduados.
    > 1.5: Alta demanda | > 1: Favorable | > 0.7: Equilibrio | < 0.7: Sobreoferta
    """
    if graduados <= 0:
        return 0, "Sin graduados registrados en este NBC"

    ratio = vacantes / graduados

    if ratio > 1.5:
        interpretacion = "Alta demanda laboral"
    elif ratio > 1:
        interpretacion = "Demanda favorable"
    elif ratio > 0.7:
        interpretacion = "Equilibrio"
    else:
        interpretacion = "Sobreoferta de graduados"

    return round(ratio, 2), interpretacion


def calcular_score_final(score_acad, score_lab, score_terr, score_glob):
    """Score Final = (Acad * 0.30) + (Lab * 0.40) + (Terr * 0.20) + (Glob * 0.10)."""
    score = (score_acad * 0.30) + (score_lab * 0.40) + (score_terr * 0.20) + (score_glob * 0.10)

    if score >= 80:
        veredicto = "OFERTAR"
        color = "green"
    elif score >= 50:
        veredicto = "OFERTAR CON AJUSTES"
        color = "yellow"
    else:
        veredicto = "REVALUAR"
        color = "red"

    return round(score, 1), veredicto, color
