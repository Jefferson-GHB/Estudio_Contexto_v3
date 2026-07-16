"""
Contenedor de estado compartido del dashboard.

Agrupa los filtros, datos cargados y metricas calculadas que
los distintos tabs necesitan. Se construye una sola vez en
data_loader.cargar_datos_base() y se pasa por parametro a
cada funcion de renderizado.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
import pandas as pd


@dataclass
class Context:
    """Estado del dashboard que fluye entre tabs."""

    # Filtros del sidebar
    filtros_seleccionados: dict = field(default_factory=dict)
    filtros_siet_seleccionados: dict = field(default_factory=dict)

    # Filtros SNIES desempacados
    sel_campos_amplios: list = field(default_factory=list)
    sel_areas: list = field(default_factory=list)
    sel_nbcs: list = field(default_factory=list)
    sel_nbc: Optional[str] = None
    sel_deptos: list = field(default_factory=list)
    sel_munis: list = field(default_factory=list)
    sel_modalidades: list = field(default_factory=list)
    sel_sectores: list = field(default_factory=list)
    sel_niveles: list = field(default_factory=list)
    sel_caracteres: list = field(default_factory=list)
    sel_estados: list = field(default_factory=list)
    busqueda_programa: str = ""
    sel_cod_snies_programas: list = field(default_factory=list)
    arg_depto: Optional[str] = None

    # Filtros SIET
    sel_areas_siet: list = field(default_factory=list)
    sel_deptos_siet: list = field(default_factory=list)
    sel_estados_siet: list = field(default_factory=list)
    sel_modalidades_siet: list = field(default_factory=list)
    mostrar_siet: bool = False

    # Flags de estado
    nbcs_explicitos: bool = False
    tiene_filtros_snies: bool = False
    tiene_filtros_siet: bool = False
    tiene_filtros_academicos_snies: bool = False

    # Labels para display
    filtro_label: str = ""
    nbc_display: str = ""
    depto_display: Optional[str] = None
    label_ambito: str = ""

    # Datos SNIES pre-tab
    stats: dict = field(default_factory=dict)
    stats_originales: dict = field(default_factory=dict)
    df_benchmark: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_market: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_tendencia: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_graduados: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_inscritos: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_admitidos: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_primer_curso: pd.DataFrame = field(default_factory=pd.DataFrame)
    df_conectividad: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Metricas calculadas
    hhi: Any = 0
    hhi_interp: str = ""
    cagr: Any = 0
    cagr_interp: str = ""
    graduados_anual: int = 0
    vacantes_est: int = 0
    ratio_abs: Any = 0
    ratio_interp: str = ""

    # ML / SIET
    etdh_ml_stats: Optional[dict] = None
    skills_bridge: Optional[dict] = None
    _ml_areas_siet: Optional[list] = None
    effective_areas_siet: Optional[list] = None
    effective_deptos_siet: Optional[list] = None
