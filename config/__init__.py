"""
Configuration Package
====================
Database connections, constants, and styling.
"""

from .constants import (
    SEXO_NORMALIZE_SQL,
)

from .database import (
    DUCKDB_PATH,
    get_conn,
    get_dss_engine
)

from .styles import (
    configure_page,
    apply_custom_styles,
    get_score_card_class,
    score_card,
    loading_spinner,
    loading_overlay,
    insight_card,
    section_summary,
)

__all__ = [
    'SEXO_NORMALIZE_SQL',
    'DUCKDB_PATH',
    'get_conn',
    'get_dss_engine',
    'configure_page',
    'apply_custom_styles',
    'get_score_card_class',
    'score_card',
    'loading_spinner',
    'loading_overlay',
    'insight_card',
    'section_summary'
]
