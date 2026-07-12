"""Chart visualizations — Plotly gauge charts."""
import plotly.graph_objects as go
from config.styles import T

_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_family="Inter, sans-serif",
    font_color=T['deep'],
    autosize=True,
)


def crear_gauge(valor, titulo, max_val=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        title={'text': titulo, 'font': {'size': 13, 'family': 'Inter, sans-serif', 'color': T['deep']}},
        number={'font': {'size': 28, 'family': 'Inter, sans-serif', 'color': T['deep']}, 'suffix': ''},
        gauge={
            'axis': {'range': [0, max_val], 'tickwidth': 1, 'tickcolor': T['stone']},
            'bar': {'color': T['crimson']},
            'steps': [
                {'range': [0, max_val * 0.33], 'color': T['cream']},
                {'range': [max_val * 0.33, max_val * 0.66], 'color': T['sand']},
                {'range': [max_val * 0.66, max_val], 'color': T['paper']}
            ],
            'threshold': {
                'line': {'color': T['stone'], 'width': 1.5},
                'thickness': 0.75,
                'value': valor
            },
        },
        domain={'x': [0.1, 0.9], 'y': [0.05, 0.85]}
    ))
    fig.update_layout(**_BASE_LAYOUT, height=220, margin=dict(l=0, r=0, t=40, b=0, pad=4))
    return fig


def crear_gauge_hhi(hhi_valor):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=hhi_valor,
        title={'text': "Indice HHI", 'font': {'size': 13, 'family': 'Inter, sans-serif', 'color': T['deep']}},
        number={'font': {'size': 28, 'family': 'Inter, sans-serif', 'color': T['deep']}, 'suffix': '', 'valueformat': '.0f'},
        gauge={
            'axis': {'range': [0, 5000], 'tickwidth': 1, 'tickcolor': T['stone']},
            'bar': {'color': T['crimson']},
            'steps': [
                {'range': [0, 1500], 'color': T['cream']},
                {'range': [1500, 2500], 'color': T['sand']},
                {'range': [2500, 5000], 'color': T['paper']}
            ],
            'threshold': {
                'line': {'color': T['stone'], 'width': 1.5},
                'thickness': 0.75,
                'value': hhi_valor
            },
        },
        domain={'x': [0.1, 0.9], 'y': [0.05, 0.85]}
    ))
    fig.update_layout(**_BASE_LAYOUT, height=220, margin=dict(l=0, r=0, t=40, b=0, pad=4))
    return fig


def crear_gauge_saber(puntaje: float, nacional: float = 150):
    """Gauge de puntaje Saber PRO con delta vs promedio nacional."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=puntaje,
        delta={'reference': nacional, 'increasing': {'color': T['success']}, 'decreasing': {'color': T['error']}},
        title={'text': "Saber PRO (/300)", 'font': {'size': 13, 'family': 'Inter, sans-serif', 'color': T['deep']}},
        number={'suffix': " pts", 'font': {'size': 22, 'family': 'Inter, sans-serif', 'color': T['deep']}},
        gauge={
            'axis': {'range': [0, 300], 'tickwidth': 1, 'tickcolor': T['stone']},
            'bar': {'color': T['crimson']},
            'steps': [
                {'range': [0, 100], 'color': '#FEE2E2'},
                {'range': [100, 180], 'color': '#FEF3C7'},
                {'range': [180, 300], 'color': '#D1FAE5'}
            ],
            'threshold': {'line': {'color': T['success'], 'width': 2}, 'thickness': 0.75, 'value': nacional}
        },
        domain={'x': [0.1, 0.9], 'y': [0.05, 0.85]}
    ))
    fig.update_layout(**_BASE_LAYOUT, height=200, margin=dict(l=0, r=0, t=40, b=0, pad=4))
    return fig


def crear_distribucion_saber(pmin, q1, mediana, q3, pmax):
    """Box-plot simplificado: barras de distribucion de puntajes Saber PRO."""
    valores = [pmin, q1, mediana, q3, pmax]
    etiquetas = ['Min', 'Q1', 'Mediana', 'Q3', 'Max']
    colores = ['#cbd5e1', '#fbbf24', T['crimson'], '#fbbf24', '#cbd5e1']
    ymax = max(valores) * 1.15 if max(valores) > 0 else 300
    positions = ['inside', 'outside', 'outside', 'outside', 'inside']
    fig = go.Figure()
    for i, (etiq, val, col, pos) in enumerate(zip(etiquetas, valores, colores, positions)):
        fig.add_trace(go.Bar(
            x=[etiq], y=[val], marker_color=col, name=etiq,
            text=[f'{val:.0f}'], textposition=pos,
            textfont=dict(size=11, color=T['deep'] if pos == 'outside' else T['cream']),
            hovertemplate=f'%{{x}}: %{{y:.0f}} pts<extra></extra>',
            showlegend=False
        ))
    fig.update_layout(
        **_BASE_LAYOUT,
        height=260, margin=dict(l=5, r=5, t=50, b=5, pad=4),
        yaxis=dict(range=[0, ymax], showticklabels=False, showgrid=False, zeroline=False),
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color=T['stone'])),
        bargap=0.3
    )
    return fig
