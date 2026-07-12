"""Design system — color tokens, CSS, and UI helpers for Estudio Contexto."""

import streamlit as st
from contextlib import contextmanager

# Color tokens
T = {
    # Foundation
    "deep":     "#0B0F19",
    "paper":    "#F9F7F4",
    "surface":  "#FFFFFF",
    # Primary — institutional crimson
    "crimson":        "#9B1B30",
    "crimson_light":  "#C5304A",
    "crimson_dark":   "#7A1525",
    "crimson_glow":   "rgba(155,27,48,0.12)",
    # Secondary — premium gold
    "gold":           "#C7A951",
    "gold_light":     "#DFC278",
    "gold_dark":      "#A88E3D",
    "gold_glow":      "rgba(199,169,81,0.15)",
    # Tertiary — sage growth
    "sage":           "#6B9080",
    "sage_light":     "#8BB5A5",
    "sage_dark":      "#4A6B5E",
    # Semantic
    "success":        "#10B981",
    "warning":        "#F59E0B",
    "error":          "#EF4444",
    "info":           "#3B82F6",
    # Neutrals
    "earth":          "#52423C",
    "earth_light":    "#7A6E68",
    "stone":          "#A09088",
    "sand":           "#E5DDD6",
    "cream":          "#F0EAE4",
    # Glass
    "glass_bg":       "rgba(255,255,255,0.72)",
    "glass_border":   "rgba(255,255,255,0.35)",
    "glass_blur":     "blur(14px)",
    # Chart palette
    "chart_crimson":  "#9B1B30",
    "chart_gold":     "#C7A951",
    "chart_sage":     "#6B9080",
    "chart_earth":    "#52423C",
    "chart_rose":     "#C5304A",
    "chart_amber":    "#D97706",
    "chart_teal":     "#0D9488",
    "chart_plum":     "#7C3AED",
}

# Shadow tokens
S = {
    "xs":   "0 1px 2px rgba(0,0,0,0.04)",
    "sm":   "0 2px 8px rgba(0,0,0,0.06)",
    "md":   "0 4px 16px rgba(0,0,0,0.07)",
    "lg":   "0 8px 32px rgba(0,0,0,0.09)",
    "xl":   "0 16px 48px rgba(0,0,0,0.11)",
    "glow": "0 0 24px rgba(155,27,48,0.12)",
    "card": "0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.06)",
}


def configure_page():
    st.set_page_config(
        page_title="Estudio Contexto",
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_custom_styles():
    t = T
    s = S
    st.markdown(f"""
<style>
    /* ==== FONTS ==== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');

    /* ==== BASE ==== */
    .stApp {{
        background: linear-gradient(135deg, {t["cream"]} 0%, {t["paper"]} 50%, {t["sand"]} 100%);
        background-attachment: fixed;
    }}

    .main .block-container {{
        padding: 1.4rem 1.4rem 2rem 1.4rem;
        max-width: 1480px;
        margin-top: 0.8rem;
    }}

    /* ==== TYPOGRAPHY ==== */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Lora', Georgia, 'Times New Roman', serif !important;
        color: {t["deep"]};
        letter-spacing: -0.3px;
    }}
    h1 {{ font-size: 1.75rem; font-weight: 700; }}
    h2 {{ font-size: 1.4rem;  font-weight: 600; }}
    h3 {{ font-size: 1.15rem; font-weight: 600; }}
    h4 {{ font-size: 1.0rem;  font-weight: 600; }}

    body, p, span, li, label, div {{
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: {t["deep"]};
    }}
    p {{ font-size: 0.9375rem; line-height: 1.7; }}
    small, .stCaption {{ color: {t["stone"]}; }}

    /* ==== GLASS CARDS ==== */
    .glass-card {{
        background: {t["glass_bg"]};
        backdrop-filter: {t["glass_blur"]};
        -webkit-backdrop-filter: {t["glass_blur"]};
        border: 1px solid {t["glass_border"]};
        border-radius: 14px;
        box-shadow: {s["card"]};
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .glass-card:hover {{
        box-shadow: {s["md"]}, {s["glow"]};
        transform: translateY(-1px);
    }}

    /* ==== SOLID CARDS ==== */
    .card {{
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        border-radius: 14px;
        box-shadow: {s["card"]};
        transition: box-shadow 0.25s ease, transform 0.25s ease;
    }}
    .card:hover {{
        box-shadow: {s["md"]};
    }}

    /* ==== ACCENT BORDER CARDS ==== */
    .accent-card {{
        background: {t["surface"]};
        border-radius: 0 12px 12px 0;
        border: 1px solid {t["sand"]};
        border-left: 4px solid var(--accent, {t["crimson"]});
        padding: 1.2rem 1.4rem;
        box-shadow: {s["xs"]};
    }}

    /* ==== HERO / WELCOME BANNER ==== */
    .hero-banner {{
        background: linear-gradient(135deg, {t["crimson"]}08 0%, {t["gold"]}10 100%);
        border: 1px solid {t["sand"]};
        border-radius: 16px;
        padding: 1.1rem 1.5rem;
        margin: 0 0 1.2rem 0;
        box-shadow: {s["sm"]};
    }}
    .hero-inner {{ display: flex; align-items: center; gap: 1rem; }}
    .hero-icon {{
        width: 56px; height: 56px;
        border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.7rem;
        background: linear-gradient(135deg, {t["crimson"]}, {t["crimson_light"]});
        color: #fff;
        box-shadow: 0 4px 16px {t["crimson_glow"]};
    }}
    .hero-title {{
        margin: 0; color: {t["deep"]}; font-weight: 700; font-size: 1.1rem;
        font-family: 'Lora', Georgia, serif;
    }}
    .hero-subtitle {{
        margin: 0.2rem 0 0 0; color: {t["stone"]}; font-size: 0.85rem; font-weight: 400;
    }}

    /* ==== SECTION HEADERS ==== */
    .section-header {{
        margin-bottom: 1.5rem;
    }}
    .section-eyebrow {{
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 2px;
        color: {t["crimson"]};
        margin-bottom: 0.3rem;
        display: block;
    }}
    .section-header h2 {{
        font-family: 'Lora', Georgia, serif;
        font-size: clamp(1.3rem, 2.2vw, 1.7rem);
        font-weight: 700; margin-bottom: 0.4rem;
        color: {t["deep"]};
    }}
    .section-header p {{
        color: {t["stone"]}; font-size: 0.88rem; line-height: 1.65;
    }}

    /* ==== ICON HEADER ==== */
    .icon-header {{
        font-family: 'Lora', Georgia, serif;
        color: {t["deep"]};
        margin: 0.6rem 0 0.3rem 0;
        font-weight: 600;
    }}
    .icon-header i {{
        color: {t["crimson"]};
        margin-right: 0.45rem;
        font-size: 0.9em;
    }}
    .icon-hint {{
        color: {t["gold"]};
    }}
    .icon-hint i {{
        color: {t["gold"]};
        margin-right: 0.3rem;
    }}

    /* ==== DIVIDERS ==== */
    hr {{
        border: none; height: 1px;
        background: linear-gradient(90deg, transparent, {t["sand"]}, transparent);
        margin: 1.5rem 0;
    }}

    /* ==== SCORE CARDS ==== */
    .score-green, .score-yellow, .score-red {{
        padding: 1.4rem; border-radius: 14px; text-align: center;
        border: 1px solid {t["sand"]};
        box-shadow: {s["card"]};
        transition: all 0.25s ease;
    }}
    .score-green:hover, .score-yellow:hover, .score-red:hover {{
        box-shadow: {s["md"]};
        transform: translateY(-2px);
    }}
    .score-green {{
        background: linear-gradient(135deg, #ECFDF5, #D1FAE5);
        border-left: 4px solid {t["success"]};
    }}
    .score-yellow {{
        background: linear-gradient(135deg, #FFFBEB, #FEF3C7);
        border-left: 4px solid {t["warning"]};
    }}
    .score-red {{
        background: linear-gradient(135deg, #FEF2F2, #FEE2E2);
        border-left: 4px solid {t["error"]};
    }}
    .score-green h2 {{ color: {t["success"]} !important; font-weight: 700; font-family: 'Lora', Georgia, serif; }}
    .score-yellow h2 {{ color: {t["warning"]} !important; font-weight: 700; font-family: 'Lora', Georgia, serif; }}
    .score-red h2 {{ color: {t["error"]} !important; font-weight: 700; font-family: 'Lora', Georgia, serif; }}

    /* ==== VEREDICTO ICONS ==== */
    .veredicto-ok   {{ color: {t["success"]} !important; }}
    .veredicto-warn {{ color: {t["warning"]} !important; }}
    .veredicto-err  {{ color: {t["error"]} !important; }}

    /* ==== RECOMMENDATION CARDS ==== */
    .rec-card {{
        background: var(--rec-bg, {t["surface"]});
        border: 1px solid {t["sand"]};
        border-left: 4px solid var(--rec-accent, {t["crimson"]});
        border-radius: 0 12px 12px 0;
        padding: 1.1rem 1.3rem;
        margin: 0.4rem 0;
        box-shadow: {s["xs"]};
        transition: box-shadow 0.2s ease;
    }}
    .rec-card:hover {{ box-shadow: {s["sm"]}; }}
    .rec-title {{
        color: var(--rec-accent, {t["crimson"]});
        margin: 0; font-size: 0.95rem; font-weight: 600;
        font-family: 'Lora', Georgia, serif;
    }}
    .rec-text {{
        margin: 0.4rem 0 0 0; font-size: 0.85rem;
        color: {t["earth"]}; line-height: 1.55;
    }}

    /* ==== STAT CARDS ==== */
    .stat-card {{
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        border-radius: 14px;
        padding: 1.3rem 1.2rem;
        box-shadow: {s["card"]};
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }}
    .stat-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, {t["crimson"]}, {t["gold"]});
        opacity: 0;
        transition: opacity 0.3s ease;
    }}
    .stat-card:hover::before {{ opacity: 1; }}
    .stat-card:hover {{
        box-shadow: {s["md"]};
        transform: translateY(-2px);
    }}
    .stat-value {{
        font-family: 'Lora', Georgia, serif;
        font-size: 2rem; font-weight: 700;
        color: {t["deep"]};
        font-variant-numeric: tabular-nums;
    }}
    .stat-label {{
        font-size: 0.7rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 1px;
        color: {t["stone"]};
        margin-top: 0.15rem;
    }}
    .stat-delta {{
        font-size: 0.72rem; font-weight: 600;
        margin-top: 0.35rem;
    }}
    .stat-delta.up   {{ color: {t["success"]}; }}
    .stat-delta.down {{ color: {t["error"]}; }}

    /* ==== TABS ==== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: {t["cream"]};
        padding: 5px 6px;
        border-radius: 14px;
        margin-bottom: 20px;
        border: 1px solid {t["sand"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px; padding: 6px 18px;
        background: transparent;
        border-radius: 10px;
        color: {t["stone"]};
        font-size: 0.82rem; font-weight: 500;
        letter-spacing: 0.3px;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        border-radius: 14px;
        padding: 1.2rem;
        box-shadow: {s["sm"]};
        margin-top: 0.4rem;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: {t["surface"]};
        border-color: {t["sand"]};
        color: {t["deep"]};
    }}
    .stTabs [aria-selected="true"] {{
        background: {t["surface"]} !important;
        color: {t["crimson"]} !important;
        font-weight: 600;
        border: 1px solid {t["sand"]};
        box-shadow: {s["xs"]};
    }}

    /* ==== METRICS ==== */
    .stMetric, [data-testid="metric-container"], [data-testid="stMetric"] {{
        background: {t["surface"]};
        padding: 16px 14px;
        border-radius: 14px;
        border: 1px solid {t["sand"]};
        box-shadow: {s["xs"]};
        transition: all 0.2s ease;
        height: auto !important;
        min-height: unset !important;
        overflow: visible !important;
    }}
    .stMetric:hover {{ box-shadow: {s["sm"]}; }}
    .stMetric label {{
        color: {t["stone"]} !important;
        font-weight: 500; font-size: 0.78rem;
        letter-spacing: 0.2px;
    }}
    .stMetric [data-testid="stMetricValue"] {{
        color: {t["deep"]} !important;
        font-weight: 700;
        font-family: 'Lora', Georgia, serif;
        font-size: 1.5rem !important;
    }}
    .stMetric [data-testid="stMetricValue"], .stMetric label,
    [data-testid="metric-container"] label {{
        overflow: visible !important;
        text-overflow: clip !important;
        word-break: break-word;
        white-space: normal !important;
        line-height: 1.25;
        min-height: auto;
    }}
    .stMetric label {{ font-size: 0.72rem !important; }}

    /* ==== BUTTONS ==== */
    div.stButton > button {{
        width: 100%; border-radius: 10px; font-weight: 600;
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        color: {t["deep"]};
        padding: 10px 20px;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }}
    div.stButton > button:hover {{
        background: {t["crimson"]};
        border-color: {t["crimson"]};
        color: #ffffff;
        box-shadow: 0 4px 14px {t["crimson_glow"]};
        transform: translateY(-1px);
    }}
    div.stButton > button:active {{
        transform: translateY(0) scale(0.98);
    }}

    /* Primary button variant */
    .stButton > [kind="primary"] {{
        background: linear-gradient(135deg, {t["crimson"]}, {t["crimson_dark"]}) !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 4px 14px {t["crimson_glow"]};
    }}

    /* ==== SIDEBAR ==== */
    section[data-testid="stSidebar"] {{
        background: {t["surface"]} !important;
        border-right: 1px solid {t["sand"]};
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {t["deep"]} !important;
        font-family: 'Lora', Georgia, serif;
    }}
    section[data-testid="stSidebar"] h4 {{
        font-family: 'Lora', Georgia, serif !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        color: {t["deep"]} !important;
        padding: 0.4rem 0 0.2rem 0;
        border-bottom: 2px solid {t["crimson"]};
        margin: 0.5rem 0;
    }}
    section[data-testid="stSidebar"] .stButton > button {{
        background: {t["crimson"]};
        color: #ffffff;
        border: none;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: {t["crimson_dark"]};
    }}
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
        background: {t["crimson"]}15;
        color: {t["deep"]};
    }}
    section[data-testid="stSidebar"] .stCaption {{
        color: {t["stone"]} !important;
        font-size: 0.72rem !important;
        font-weight: 400;
        letter-spacing: 0.3px;
    }}

    /* ==== INPUTS ==== */
    [data-baseweb="input"] {{
        border-color: {t["sand"]};
        border-radius: 10px;
    }}
    [data-baseweb="input"]:focus {{
        border-color: {t["crimson"]};
        box-shadow: 0 0 0 3px {t["crimson_glow"]};
    }}

    /* ==== CHARTS ==== */
    .stPlotlyChart {{
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        border-radius: 14px;
        padding: 8px;
        box-shadow: {s["sm"]};
        overflow: clip;
    }}

    /* ==== DATAFRAMES ==== */
    [data-testid="stDataFrame"] {{
        background: {t["surface"]};
        border: 1px solid {t["sand"]};
        border-radius: 14px;
    }}
    [data-testid="stDataFrame"] th {{
        background: {t["cream"]} !important;
        font-weight: 600;
        color: {t["deep"]};
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ==== SPINNER ==== */
    .spinner-modal {{
        display: flex; flex-direction: column; align-items: center; gap: 1.2rem; padding: 1.8rem;
    }}
    .spinner-ring {{
        width: 40px; height: 40px;
        border: 3px solid {t["sand"]};
        border-top-color: {t["crimson"]};
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

    /* ==== SCROLLBAR ==== */
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: {t["cream"]}; border-radius: 8px; }}
    ::-webkit-scrollbar-thumb {{ background: {t["sand"]}; border-radius: 8px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {t["stone"]}; }}

    /* ==== CALLOUTS ==== */
    .stAlert {{
        border-radius: 10px;
        border: 1px solid {t["sand"]};
    }}

    /* ==== RESPONSIVE ==== */
    @media (max-width: 1200px) {{
        .main .block-container {{
            padding: 1rem 1rem 1.5rem 1rem;
        }}
        section[data-testid="stSidebar"] {{
            min-width: 240px !important;
            max-width: 260px !important;
        }}
    }}
    @media (max-width: 900px) {{
        .main .block-container {{
            padding: 0.6rem 0.6rem 1rem 0.6rem;
            max-width: 100%;
        }}
        section[data-testid="stSidebar"] {{
            min-width: 200px !important;
            max-width: 220px !important;
        }}
    }}
    @media (max-width: 600px) {{
        .main .block-container {{
            padding: 0.4rem 0.4rem 0.8rem 0.4rem;
        }}
    }}

    /* ==== ANIMATIONS ==== */
    @keyframes fadeSlideUp {{
        from {{ opacity: 0; transform: translateY(16px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pulseGlow {{
        0%, 100% {{ box-shadow: 0 0 8px {t["crimson_glow"]}; }}
        50%      {{ box-shadow: 0 0 24px rgba(155,27,48,0.22); }}
    }}
    @keyframes shimmer {{
        0%   {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}
    .animate-in {{
        animation: fadeSlideUp 0.5s ease-out both;
    }}
    .animate-in:nth-child(odd)  {{ animation-delay: 0.05s; }}
    .animate-in:nth-child(even) {{ animation-delay: 0.12s; }}
    .pulse-highlight {{
        animation: pulseGlow 2.5s ease-in-out infinite;
        border-radius: 12px;
    }}
    .skeleton {{
        background: linear-gradient(90deg, {t["cream"]} 25%, {t["sand"]} 50%, {t["cream"]} 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s ease-in-out infinite;
    }}

    /* ==== ACCESSIBILITY ==== */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
        }}
    }}
</style>
    """, unsafe_allow_html=True)


# UTILITY FUNCTIONS

def get_score_card_class(score: float) -> str:
    if score >= 80: return "score-green"
    if score >= 50: return "score-yellow"
    return "score-red"


def score_card(score: float, label: str) -> str:
    icon = "check-circle" if score >= 80 else "bolt" if score >= 50 else "triangle-exclamation"
    cls = get_score_card_class(score)
    return f"""<div class="{cls}">
        <div style="font-size:2.4rem;font-weight:700;margin-bottom:0.15rem;">{score:.0f}<span style="font-size:1rem;">/100</span></div>
        <div style="font-size:0.85rem;opacity:0.85;"><i class="fas fa-{icon}" style="margin-right:0.3rem;"></i>{label}</div>
    </div>"""


def loading_spinner(text: str) -> str:
    t = T
    return f"""<div class="spinner-modal">
        <div class="spinner-ring"></div>
        <div style="color:{t['stone']};font-size:0.9rem;">{text}</div>
    </div>"""


@contextmanager
def loading_overlay(text: str = "Cargando datos..."):
    placeholder = st.empty()
    placeholder.markdown(loading_spinner(text), unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()


def render_welcome_banner(title: str = "Estudio Contexto",
                         subtitle: str = "Análisis de Pertinencia Educativa",
                         mascot: str = "<i class='fas fa-chart-bar'></i>") -> None:
    st.markdown(f"""<div class="hero-banner"><div class="hero-inner">
        <div class="hero-icon">{mascot}</div>
        <div><div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div></div>
    </div></div>""", unsafe_allow_html=True)


def stat_card(value: str, label: str, delta: str = "", delta_up: bool = True) -> str:
    """Reusable KPI stat card for hero rows."""
    delta_html = ""
    if delta:
        direction = "up" if delta_up else "down"
        arrow = "↑" if delta_up else "↓"
        delta_html = f'<div class="stat-delta {direction}">{arrow} {delta}</div>'
    return f"""<div class="stat-card">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
        {delta_html}
    </div>"""


def insight_card(icon: str, title: str, body: str, tone: str = "info") -> None:
    """Render an inline insight card with icon + title + body. Tones: info, warning, success, insight."""
    t = T
    tone_colors = {
        "info":    (t["info"],    "#EFF6FF"),
        "warning": (t["warning"], "#FFFBEB"),
        "success": (t["sage"],    "#ECFDF5"),
        "insight": (t["crimson"], "#FDF2F4"),
    }
    accent, bg = tone_colors.get(tone, tone_colors["insight"])
    st.markdown(f"""<div style="background:{bg};border:1px solid {t['sand']};
        border-left:4px solid {accent};border-radius:0 10px 10px 0;
        padding:0.8rem 1rem;margin:0.6rem 0;font-size:0.88rem;">
        <strong style="color:{accent};font-family:'Lora',Georgia,serif;">
        <i class="fas fa-{icon}" style="margin-right:0.4rem;"></i>{title}</strong>
        <p style="margin:0.25rem 0 0 0;color:{t['earth']};line-height:1.55;">{body}</p>
    </div>""", unsafe_allow_html=True)


def section_summary(title: str, bullets: list[str], tone: str = "insight") -> None:
    """Render an end-of-section synthesis card with bullet points — like a paper abstract."""
    t = T
    accent = {"insight": t["crimson"], "success": t["sage"], "warning": t["warning"], "info": t["info"]}.get(tone, t["crimson"])
    bg = {"insight": "#FDF2F4", "success": "#ECFDF5", "warning": "#FFFBEB", "info": "#EFF6FF"}.get(tone, "#FDF2F4")
    bullets_html = "".join(f'<li style="margin-bottom:0.3rem;color:{t["earth"]};">{b}</li>' for b in bullets)
    st.markdown(f"""<div class="animate-in" style="background:{bg};border:1px solid {t['sand']};
        border-left:5px solid {accent};border-radius:0 14px 14px 0;
        padding:1rem 1.2rem;margin:0.8rem 0;">
        <div style="font-family:'Lora',Georgia,serif;font-weight:700;font-size:0.95rem;
        color:{accent};margin-bottom:0.5rem;">
        <i class="fas fa-file-lines" style="margin-right:0.4rem;"></i>{title}</div>
        <ul style="margin:0;padding-left:1.2rem;font-size:0.85rem;line-height:1.6;">{bullets_html}</ul>
    </div>""", unsafe_allow_html=True)
