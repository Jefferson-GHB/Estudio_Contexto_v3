"""Componentes de renderizado reutilizables — reemplazan HTML inline con unsafe_allow_html."""

import streamlit as st
from config.styles import T


def section_header(number: str, title: str, subtitle: str = "", icon: str = ""):
    """Renderiza un header de seccion con numero, titulo y subtitulo.

    Reemplaza patrones como:
        st.markdown('<div class="section-header"><span class="section-eyebrow">01</span>
                    <h2>Titulo</h2><p>Subtitulo</p></div>', unsafe_allow_html=True)
    """
    icon_html = f'<i class="{icon}" style="margin-right:8px;color:{T["crimson"]}"></i>' if icon else ""
    st.markdown(f"""
    <div class="section-header">
        <span class="section-eyebrow">{number}</span>
        <h2>{icon_html}{title}</h2>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def icon_header(icon_class: str, title: str, tag: str = "h3"):
    """Renderiza un header con icono Font Awesome.

    Reemplaza: st.markdown('<h3 class="icon-header"><i class="fas fa-xxx"></i> Title</h3>', unsafe_allow_html=True)
    """
    st.markdown(f'<{tag} class="icon-header"><i class="{icon_class}"></i> {title}</{tag}>', unsafe_allow_html=True)


def icon_hint(icon_class: str, text: str = ""):
    """Renderiza un icono de pista/sugerencia.

    Reemplaza: st.markdown('<i class="fas fa-lightbulb icon-hint"></i>', unsafe_allow_html=True)
    """
    inner = f'<i class="{icon_class}"></i> {text}' if text else f'<i class="{icon_class}"></i>'
    st.caption(inner, unsafe_allow_html=True)


def veredicto_card(score: float, label: str, icon_class: str, level: str):
    """Renderiza una tarjeta de veredicto (OK / Warning / Error).

    level: 'success', 'warning', 'error'
    Reemplaza bloques de 30+ lineas con divs score-green/yellow/red.
    """
    color_map = {
        'success': T['success'],
        'warning': T['warning'],
        'error': T['error'],
    }
    color = color_map.get(level, T['earth'])
    score_class = f"score-{'green' if level == 'success' else 'yellow' if level == 'warning' else 'red'}"

    st.markdown(f"""
    <div class="{score_class}">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
            <i class="{icon_class}" style="font-size:1.5rem;color:{color};"></i>
            <span style="font-size:1.3rem;font-weight:600;color:{T['deep']};">{label}</span>
        </div>
        <span style="font-size:2.5rem;font-weight:700;color:{color};">{score:.1f}</span>
    </div>
    """, unsafe_allow_html=True)


def offer_card(tipo: str, description: str, color: str):
    """Renderiza una tarjeta de tipo de oferta recomendada.

    Reemplaza bloques div.rec-card con estilos inline.
    """
    st.markdown(f"""
    <div class="rec-card" style="border-left:4px solid {color};background:{T['cream']};border-radius:8px;padding:16px 20px;margin:12px 0;">
        <div class="rec-title" style="font-family:Lora,serif;font-size:1.2rem;font-weight:600;color:{T['deep']};margin-bottom:4px;">{tipo}</div>
        <div class="rec-text" style="font-size:0.9rem;color:{T['earth_light']};">{description}</div>
    </div>
    """, unsafe_allow_html=True)


def insight_box(icon: str, title: str, body: str, tone: str = "info"):
    """Renderiza una caja de insight/interpretacion.

    tone: 'info', 'success', 'warning', 'error'
    """
    colors = {
        'info': (T['info'], T['cream'], '#EFF6FF'),
        'success': (T['success'], T['cream'], '#ECFDF5'),
        'warning': (T['warning'], T['cream'], '#FFFBEB'),
        'error': (T['error'], T['cream'], '#FDF2F4'),
    }
    accent, _, bg = colors.get(tone, colors['info'])

    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 16px;
                background:{bg};border-left:3px solid {accent};border-radius:8px;margin:10px 0;">
        <i class="fas fa-{icon}" style="font-size:1.2rem;color:{accent};margin-top:2px;"></i>
        <div>
            <strong style="color:{T['deep']};">{title}</strong><br>
            <span style="font-size:0.9rem;color:{T['earth_light']};">{body}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def metric_row(metrics: list[tuple[str, str, str]]):
    """Renderiza una fila de metricas con iconos.

    metrics: [(label, value, icon_class), ...]
    """
    cols = st.columns(len(metrics))
    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div style="text-align:center;padding:8px;">
                <i class="{icon}" style="font-size:1.2rem;color:{T['crimson']};margin-bottom:4px;"></i>
                <div style="font-size:0.8rem;color:{T['earth_light']};">{label}</div>
                <div style="font-size:1.4rem;font-weight:700;color:{T['deep']};">{value}</div>
            </div>
            """, unsafe_allow_html=True)
