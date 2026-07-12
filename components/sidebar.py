"""
Sidebar component - Filter panel
"""
import streamlit as st
import pandas as pd
from typing import Optional, List

# Import necessary functions
from config.database import get_conn
from config.styles import T
from utils.helpers import icon
from utils.auth import logout


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

@st.cache_data(ttl=300)
def cargar_listas_filtros():
    """Carga todas las opciones de filtros básicos de una sola vez (cacheado 5 min)."""
    conn = get_conn()
    data = {}
    try:
        # Filtros geográficos
        data['deptos'] = [r[0] for r in conn.execute('SELECT DISTINCT "DEPARTAMENTO_OFERTA_PROGRAMA" FROM snies.snies_programas WHERE "DEPARTAMENTO_OFERTA_PROGRAMA" IS NOT NULL ORDER BY 1').fetchall()]
        
        # Filtros académicos jerárquicos
        data['campos_amplios'] = [r[0] for r in conn.execute('SELECT DISTINCT "CINE_F_2013_AC_CAMPO_AMPLIO" FROM snies.snies_programas WHERE "CINE_F_2013_AC_CAMPO_AMPLIO" IS NOT NULL ORDER BY 1').fetchall()]
        data['areas'] = [r[0] for r in conn.execute('SELECT DISTINCT "ÁREA_DE_CONOCIMIENTO" FROM snies.snies_programas WHERE "ÁREA_DE_CONOCIMIENTO" IS NOT NULL ORDER BY 1').fetchall()]
        data['nbcs'] = [r[0] for r in conn.execute('SELECT DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" FROM snies.snies_programas WHERE "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL ORDER BY 1').fetchall()]
        
        # Filtros de caracterización (desde snies_programas — fuente canónica)
        data['niv_acad'] = [r[0] for r in conn.execute('SELECT DISTINCT "NIVEL_ACADÉMICO" FROM snies.snies_programas WHERE "NIVEL_ACADÉMICO" IS NOT NULL ORDER BY 1').fetchall()]
        data['niv_form'] = [r[0] for r in conn.execute('SELECT DISTINCT "NIVEL_DE_FORMACIÓN" FROM snies.snies_programas WHERE "NIVEL_DE_FORMACIÓN" IS NOT NULL ORDER BY 1').fetchall()]
        data['modalidad'] = [r[0] for r in conn.execute('SELECT DISTINCT "MODALIDAD" FROM snies.snies_programas WHERE "MODALIDAD" IS NOT NULL ORDER BY 1').fetchall()]
        data['sector'] = [r[0] for r in conn.execute('SELECT DISTINCT "SECTOR" FROM snies.snies_programas WHERE "SECTOR" IS NOT NULL ORDER BY 1').fetchall()]
        data['caracter'] = [r[0] for r in conn.execute('SELECT DISTINCT "CARÁCTER_ACADÉMICO" FROM snies.snies_programas WHERE "CARÁCTER_ACADÉMICO" IS NOT NULL ORDER BY 1').fetchall()]
        data['estado'] = [r[0] for r in conn.execute('SELECT DISTINCT "ESTADO_PROGRAMA" FROM snies.snies_programas WHERE "ESTADO_PROGRAMA" IS NOT NULL ORDER BY 1').fetchall()]
        
        # NOTA: Ya no se cargan valores de matriculados; sidebar usa snies_programas
    except Exception as e:
        st.error(f"Error cargando filtros: {e}")
    finally:
        conn.close()
    return data


@st.cache_data
def cargar_listas_filtros_siet():
    """Carga todas las opciones de filtros SIET (Educación para el Trabajo)."""
    conn = get_conn()
    data = {}
    try:
        # Áreas de Desempeño SIET (9 categorías)
        data['areas_desempeno'] = [r[0] for r in conn.execute('''
            SELECT DISTINCT "Area de Desempeño" 
            FROM siet.siet_programas 
            WHERE "Area de Desempeño" IS NOT NULL 
            ORDER BY 1
        ''').fetchall()]
        
        # Departamentos SIET
        data['deptos_siet'] = [r[0] for r in conn.execute('''
            SELECT DISTINCT "Departamento" 
            FROM siet.siet_instituciones 
            WHERE "Departamento" IS NOT NULL 
            ORDER BY 1
        ''').fetchall()]
        
        # Estados del programa SIET
        data['estados_siet'] = [r[0] for r in conn.execute('''
            SELECT DISTINCT "Estado Programa" 
            FROM siet.siet_programas 
            WHERE "Estado Programa" IS NOT NULL 
            ORDER BY 1
        ''').fetchall()]
        
        # Naturaleza institución SIET
        data['naturaleza_siet'] = [r[0] for r in conn.execute('''
            SELECT DISTINCT "Naturaleza" 
            FROM siet.siet_instituciones 
            WHERE "Naturaleza" IS NOT NULL 
            ORDER BY 1
        ''').fetchall()]
        
        # Modalidades SIET (UNION de Metodología 1, 2 y 3 de siet_programas)
        data['modalidades_siet'] = [r[0] for r in conn.execute('''
            SELECT DISTINCT metodologia FROM (
                SELECT "Metodología 1" as metodologia FROM siet.siet_programas WHERE "Metodología 1" IS NOT NULL
                UNION
                SELECT "Metodología 2" FROM siet.siet_programas WHERE "Metodología 2" IS NOT NULL
                UNION
                SELECT "Metodología 3" FROM siet.siet_programas WHERE "Metodología 3" IS NOT NULL
            )
            ORDER BY 1
        ''').fetchall()]
        
    except Exception as e:
        # SIET puede no estar disponible, no es crítico
        data['areas_desempeno'] = []
        data['deptos_siet'] = []
        data['estados_siet'] = []
        data['naturaleza_siet'] = []
        data['modalidades_siet'] = []
    finally:
        conn.close()
    return data


def cargar_opciones_cruzadas(
    campos_amplios=None, areas=None, nbcs=None,
    deptos=None, municipios=None,
    modalidades=None, sectores=None, niveles=None,
    caracteres=None, estados=None,
    busqueda_nombre=None
):
    """
    Carga opciones de filtro considerando todos los filtros seleccionados.
    Cada filtro restringe las opciones de los demas (cascada).
    
    Opera sobre snies_programas como fuente canonica de opciones.
    Retorna un dict con las opciones disponibles para cada dimension.
    """
    conn = get_conn()
    resultado = {
        'campos_amplios': [], 'areas': [], 'nbcs': [],
        'deptos': [], 'municipios': [],
        'modalidades': [], 'sectores': [], 'niveles': [],
        'caracteres': [], 'estados': [],
        'count': 0
    }

    try:
        # Construir cláusula WHERE base con TODOS los filtros activos
        conditions = []

        if campos_amplios:
            vals = "', '".join([c.replace("'", "''") for c in campos_amplios])
            conditions.append(f'"CINE_F_2013_AC_CAMPO_AMPLIO" IN (\'{vals}\')')

        if areas:
            vals = "', '".join([a.replace("'", "''") for a in areas])
            conditions.append(f'"ÁREA_DE_CONOCIMIENTO" IN (\'{vals}\')')

        if nbcs:
            vals = "', '".join([n.replace("'", "''") for n in nbcs])
            conditions.append(f'"NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IN (\'{vals}\')')

        if deptos:
            vals = "', '".join([d.replace("'", "''") for d in deptos])
            conditions.append(f'"DEPARTAMENTO_OFERTA_PROGRAMA" IN (\'{vals}\')')

        if municipios:
            vals = "', '".join([m.replace("'", "''") for m in municipios])
            conditions.append(f'"MUNICIPIO_OFERTA_PROGRAMA" IN (\'{vals}\')')

        if modalidades:
            vals = "', '".join([m.replace("'", "''") for m in modalidades])
            conditions.append(f'"MODALIDAD" IN (\'{vals}\')')

        if sectores:
            vals = "', '".join([s.replace("'", "''") for s in sectores])
            conditions.append(f'"SECTOR" IN (\'{vals}\')')

        if niveles:
            vals = "', '".join([n.replace("'", "''") for n in niveles])
            conditions.append(f'"NIVEL_DE_FORMACIÓN" IN (\'{vals}\')')

        if caracteres:
            vals = "', '".join([c.replace("'", "''") for c in caracteres])
            conditions.append(f'"CARÁCTER_ACADÉMICO" IN (\'{vals}\')')

        if estados:
            vals = "', '".join([e.replace("'", "''") for e in estados])
            conditions.append(f'"ESTADO_PROGRAMA" IN (\'{vals}\')')

        if busqueda_nombre and busqueda_nombre.strip():
            texto = busqueda_nombre.strip().replace("'", "''")
            conditions.append(f"UPPER(\"NOMBRE_DEL_PROGRAMA\") LIKE UPPER('%{texto}%')")

        where_all = " AND ".join(conditions) if conditions else "1=1"

        # Una sola query: obtener DISTINCT de cada dimensión dado el filtro completo
        # Esto es eficiente porque DuckDB optimiza bien las queries con múltiples DISTINCT
        query = f"""
        SELECT 
            COUNT(*) as total,
            -- Para cada dimensión, recolectamos los valores únicos disponibles
            LIST(DISTINCT "CINE_F_2013_AC_CAMPO_AMPLIO") as campos,
            LIST(DISTINCT "ÁREA_DE_CONOCIMIENTO") as areas,
            LIST(DISTINCT "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO") as nbcs,
            LIST(DISTINCT "DEPARTAMENTO_OFERTA_PROGRAMA") as deptos,
            LIST(DISTINCT "MUNICIPIO_OFERTA_PROGRAMA") as municipios,
            LIST(DISTINCT "MODALIDAD") as modalidades,
            LIST(DISTINCT "SECTOR") as sectores,
            LIST(DISTINCT "NIVEL_DE_FORMACIÓN") as niveles,
            LIST(DISTINCT "CARÁCTER_ACADÉMICO") as caracteres,
            LIST(DISTINCT "ESTADO_PROGRAMA") as estados
        FROM snies.snies_programas
        WHERE {where_all}
        """
        row = conn.execute(query).fetchone()

        if row:
            resultado['count'] = row[0] or 0
            resultado['campos_amplios'] = sorted([v for v in (row[1] or []) if v]) 
            resultado['areas'] = sorted([v for v in (row[2] or []) if v])
            resultado['nbcs'] = sorted([v for v in (row[3] or []) if v])
            resultado['deptos'] = sorted([v for v in (row[4] or []) if v])
            resultado['municipios'] = sorted([v for v in (row[5] or []) if v])
            resultado['modalidades'] = sorted([v for v in (row[6] or []) if v])
            resultado['sectores'] = sorted([v for v in (row[7] or []) if v])
            resultado['niveles'] = sorted([v for v in (row[8] or []) if v])
            resultado['caracteres'] = sorted([v for v in (row[9] or []) if v])
            resultado['estados'] = sorted([v for v in (row[10] or []) if v])

    except Exception as e:
        st.warning(f"Error en filtros cruzados: {e}")
    finally:
        conn.close()

    return resultado


# ==============================================================================
# MAIN SIDEBAR RENDERER
# ==============================================================================

def render_sidebar(mostrar_metodologia_callback) -> tuple[dict, dict]:
    """
    Renders the sidebar filter panel and returns selected filters.
    
    Args:
        mostrar_metodologia_callback: Function to call when "Ver Metodología" is clicked
    
    Returns:
        tuple: (filtros_seleccionados, filtros_siet_seleccionados)
            - filtros_seleccionados: Dictionary with all selected SNIES filters
            - filtros_siet_seleccionados: Dictionary with all selected SIET filters
    """
    with st.sidebar:
        st.markdown('<h2 class="icon-header"><i class="fas fa-sliders"></i> Filtros de Analisis</h2>', unsafe_allow_html=True)
        
        filtros_data = cargar_listas_filtros()
        
        # =====================================================================
        # SECCION 0: BUSQUEDA POR NOMBRE DE PROGRAMA
        # =====================================================================
        st.markdown('<h4 class="icon-header"><i class="fas fa-search"></i> Busqueda por Nombre</h4>', unsafe_allow_html=True)
        busqueda_programa = st.text_input(
            "Buscar por nombre o palabras clave",
            placeholder="Ej: ingenieria sistemas, salud, virtual...",
            help="Busqueda inteligente: encuentra programas aunque no escribas el nombre exacto.",
            key="busqueda_programa"
        )
        if busqueda_programa and len(busqueda_programa.strip()) >= 3:
            # Busqueda semantica para sugerencias
            try:
                from data.search import buscar_programas
                sugerencias = buscar_programas(busqueda_programa, top_k=5)
                if sugerencias:
                    st.caption("Coincidencias sugeridas:")
                    for nombre, fuente, score in sugerencias[:3]:
                        label = f"{nombre[:60]}... [{fuente}]" if len(nombre) > 60 else f"{nombre} [{fuente}]"
                        if st.button(label, key=f"sug_{hash(nombre)}", width='stretch'):
                            # Al hacer click, usar este nombre como busqueda
                            st.session_state.busqueda_programa = nombre
                            st.rerun()
            except Exception:
                pass  # fallback silencioso: LIKE funciona sin busqueda semantica
        
        st.divider()
        
        # =====================================================================
        # SECCION 1: CLASIFICACION ACADEMICA (Cascada flexible)
        # Todos los filtros siempre habilitados. Las opciones se cruzan
        # por interseccion con los demas filtros ya seleccionados.
        # =====================================================================
        st.markdown('<h4 class="icon-header"><i class="fas fa-graduation-cap"></i> Clasificacion Academica</h4>', unsafe_allow_html=True)
        
        # Area de Conocimiento (todas siempre disponibles)
        sel_areas = st.multiselect(
            "Area de Conocimiento (MEN)",
            options=filtros_data.get('areas', []),
            default=[],
            help="8 areas del conocimiento del MEN.",
            placeholder="Todas las areas..."
        )
        
        # NBC — se cruza con Area si hay seleccion
        if sel_areas:
            cascada_nbc = cargar_opciones_cruzadas(areas=sel_areas)
            opciones_nbcs = cascada_nbc['nbcs']
        else:
            opciones_nbcs = filtros_data.get('nbcs', [])
        
        sel_nbcs = st.multiselect(
            "NBC (Nucleo Basico del Conocimiento)",
            options=opciones_nbcs,
            default=[],
            help=f"{len(opciones_nbcs)} NBCs disponibles." if opciones_nbcs else "Cargando NBCs...",
            placeholder="Todos los NBCs..."
        )
        
        # Campo Amplio — se cruza con Area y/o NBC si hay seleccion
        if sel_areas or sel_nbcs:
            cascada_campo = cargar_opciones_cruzadas(areas=sel_areas or None, nbcs=sel_nbcs or None)
            opciones_campos = cascada_campo['campos_amplios']
        else:
            opciones_campos = filtros_data.get('campos_amplios', [])
        
        sel_campos_amplios = st.multiselect(
            "Campo Amplio (CINE-F)",
            options=opciones_campos,
            default=[],
            help=f"{len(opciones_campos)} campos amplios CINE-F disponibles." if opciones_campos else "Cargando campos...",
            placeholder="Todos los campos..."
        )
        
        if sel_areas or sel_nbcs or sel_campos_amplios:
            final_cross = cargar_opciones_cruzadas(
                areas=sel_areas or None, nbcs=sel_nbcs or None,
                campos_amplios=sel_campos_amplios or None
            )
            st.caption(f"{final_cross.get('count', '?')} programas con estos filtros academicos")
        
        st.divider()
        
        # =====================================================================
        # SECCIÓN 2: TERRITORIO (Cascada Depto → Municipio)
        # =====================================================================
        st.markdown('<h4 class="icon-header"><i class="fas fa-map-marker-alt"></i> Territorio</h4>', unsafe_allow_html=True)
        
        # 2.1 Departamento(s)
        sel_deptos = st.multiselect(
            "Departamento(s)",
            options=filtros_data.get('deptos', []),
            default=[],
            help="Filtrar por uno o mas departamentos",
            placeholder="Todos los departamentos..."
        )
        
        # 2.2 Cargar municipios en cascada
        if sel_deptos:
            cascada_muni = cargar_opciones_cruzadas(deptos=sel_deptos)
            opciones_munis = cascada_muni['municipios']
        else:
            opciones_munis = []
        
        # Municipio(s) — siempre habilitado
        sel_munis = st.multiselect(
            "Municipio(s)",
            options=opciones_munis,
            default=[],
            help="Municipios disponibles para los departamentos seleccionados." if sel_deptos else "Todos los municipios.",
            placeholder="Todos los municipios..."
        )
        
        st.divider()
        
        # =====================================================================
        # SECCION 3: CARACTERISTICAS DEL PROGRAMA (esenciales)
        # =====================================================================
        st.markdown('<h4 class="icon-header"><i class="fas fa-award"></i> Caracteristicas</h4>', unsafe_allow_html=True)
        
        # Modalidad
        sel_modalidades = st.multiselect(
            "Modalidad",
            options=filtros_data.get('modalidad', []),
            default=[],
            help="Modalidad del programa (fuente: catalogo SNIES programas).",
            placeholder="Todas las modalidades..."
        )
        
        # Nivel de Formacion
        sel_niveles = st.multiselect(
            "Nivel de Formacion",
            options=filtros_data.get('niv_form', []),
            default=[],
            help="Nivel de formacion del programa (fuente: catalogo SNIES programas).",
            placeholder="Todos los niveles..."
        )
        
        # =====================================================================
        # FILTROS AVANZADOS (colapsados por defecto)
        # =====================================================================
        with st.expander("Filtros avanzados", expanded=False):
            # Sector
            sel_sectores = st.multiselect(
                "Sector",
                options=filtros_data.get('sector', []),
                default=[],
                help="Oficial (publico) o Privada",
                placeholder="Todos los sectores..."
            )
            
            # Caracter Academico IES
            sel_caracteres = st.multiselect(
                "Caracter Academico IES",
                options=filtros_data.get('caracter', []),
                default=[],
                help="Universidad, Institucion Universitaria, Tecnologica, Tecnica",
                placeholder="Todos los caracteres..."
            )
            
            # Estado del Programa
            sel_estados = st.multiselect(
                "Estado del Programa",
                options=filtros_data.get('estado', []),
                default=[],
                help="Activo o Inactivo",
                placeholder="Todos los estados..."
            )
        # --- fin filtros avanzados ---
        
        # Selector de Programas Especificos (compacto)
        st.caption("Programas especificos por codigo SNIES:")
        # Inicializar session_state para opciones de programas
        if 'opciones_programas_list' not in st.session_state:
            st.session_state.opciones_programas_list = []
        
        # Crear clave de cache basada en los filtros actuales
        programas_cache_key = f"{tuple(sel_nbcs) if sel_nbcs else ()}|{tuple(sel_deptos) if sel_deptos else ()}|{tuple(sel_modalidades) if sel_modalidades else ()}|{tuple(sel_sectores) if sel_sectores else ()}|{tuple(sel_niveles) if sel_niveles else ()}"
        
        if 'programas_last_cache_key' not in st.session_state:
            st.session_state.programas_last_cache_key = ""
        
        # Solo recargar opciones si cambiaron los filtros
        if st.session_state.programas_last_cache_key != programas_cache_key:
            try:
                from data.desercion import get_programas_disponibles as get_progs_disp
                conn_prog = get_conn()
                filtros_prog = {}
                if sel_modalidades:
                    filtros_prog['modalidades'] = sel_modalidades
                if sel_sectores:
                    filtros_prog['sectores'] = sel_sectores
                if sel_niveles:
                    filtros_prog['niveles'] = sel_niveles

                df_programas = get_progs_disp(
                    conn_prog,
                    nbc=sel_nbcs[0] if sel_nbcs else None,
                    depto=sel_deptos[0] if sel_deptos else None,
                    filtros=filtros_prog if filtros_prog else None,
                    min_anos_datos=3
                )
                conn_prog.close()

                nuevas_opciones = []
                if not df_programas.empty:
                    for _, row in df_programas.iterrows():
                        cod = str(row['cod_snies']).strip()
                        nombre = str(row['nombre_programa']).strip()[:55]
                        ies = str(row['nombre_ies']).strip()[:35]
                        opcion = f"{nombre} ({cod}) - {ies}"
                        nuevas_opciones.append(opcion)
                
                st.session_state.opciones_programas_list = nuevas_opciones
                st.session_state.programas_last_cache_key = programas_cache_key
            except Exception as e:
                st.caption(f"Error cargando programas: {str(e)[:60]}")

        opciones_programas = st.session_state.opciones_programas_list

        # Multiselect con key única para persistencia
        sel_programas_especificos = st.multiselect(
            "Programas Específicos",
            options=opciones_programas,
            default=[],
            help="Formato: Nombre (Código SNIES) - IES",
            placeholder="Buscar por nombre o código...",
            key="multisel_programas_snies"
        )

        # Extraer códigos SNIES de los programas seleccionados
        sel_cod_snies_programas = []
        if sel_programas_especificos:
            for prog in sel_programas_especificos:
                if '(' in prog and ')' in prog:
                    start = prog.find('(') + 1
                    end = prog.find(')')
                    cod = prog[start:end].strip()
                    sel_cod_snies_programas.append(cod)
            st.caption(f"{len(sel_cod_snies_programas)} programa(s) seleccionado(s)")
        elif opciones_programas:
            st.caption(f"{len(opciones_programas)} programas disponibles")

        
        # =====================================================================
        # EDUCACION PARA EL TRABAJO (SIET/ETDH)
        # =====================================================================
        with st.expander("Educacion para el Trabajo (SIET/ETDH)", expanded=False):
            st.caption("Filtros para programas de formacion tecnica laboral")
            filtros_siet = cargar_listas_filtros_siet()
            
            mostrar_siet = st.checkbox("Incluir datos ETDH en el analisis", value=False)
            
            sel_areas_siet = st.multiselect(
                "Area de Desempeno",
                options=filtros_siet.get('areas_desempeno', []),
                default=[],
                placeholder="Todas las areas SIET..."
            )
            
            sel_deptos_siet = st.multiselect(
                "Departamento",
                options=filtros_siet.get('deptos_siet', []),
                default=[],
                placeholder="Todos los departamentos..."
            )
            
            sel_estados_siet = st.multiselect(
                "Estado Programa",
                options=filtros_siet.get('estados_siet', []),
                default=[],
                placeholder="Todos los estados..."
            )
            
            # Auto-cascada: Modalidad SNIES -> Modalidad SIET
            _MODALIDADES_EXACTAS = {"PRESENCIAL", "VIRTUAL", "A DISTANCIA"}
            _siet_modalidades_disponibles = filtros_siet.get('modalidades_siet', [])
            _auto_cascade_siet_mod = []
            if sel_modalidades:
                for m in sel_modalidades:
                    if m.upper() in _MODALIDADES_EXACTAS and m.upper() in [s.upper() for s in _siet_modalidades_disponibles]:
                        _auto_cascade_siet_mod.append(m)
            
            _default_siet_mod = _auto_cascade_siet_mod if _auto_cascade_siet_mod else []
            
            sel_modalidades_siet = st.multiselect(
                "Modalidad",
                options=_siet_modalidades_disponibles,
                default=[s for s in _siet_modalidades_disponibles if _auto_cascade_siet_mod and s.upper() in [m.upper() for m in _auto_cascade_siet_mod]],
                help="Se auto-selecciona si coincide con modalidad SNIES.",
                placeholder="Todas las modalidades..."
            )
        
        st.divider()
        
        # =====================================================================
        # RESUMEN DE FILTROS
        # =====================================================================
        n_filtros = sum([
            len(sel_campos_amplios) > 0,
            len(sel_areas) > 0,
            len(sel_nbcs) > 0,
            len(sel_deptos) > 0,
            len(sel_munis) > 0,
            len(sel_modalidades) > 0,
            len(sel_sectores) > 0,
            len(sel_niveles) > 0,
            len(sel_caracteres) > 0,
            len(sel_estados) > 0,
            len(sel_areas_siet) > 0,
            len(sel_deptos_siet) > 0,
            len(sel_estados_siet) > 0,
            len(sel_modalidades_siet) > 0
        ])
        
        col_info, col_clear = st.columns([2, 1])
        with col_info:
            st.caption(f"{n_filtros} filtros activos" if n_filtros else "Sin filtros — mostrando todos los datos")
        with col_clear:
            if st.button("Limpiar", width='stretch', disabled=(n_filtros == 0)):
                st.rerun()
        
        # =====================================================================
        # SECCION INFERIOR: METODOLOGIA Y LOGOUT
        # =====================================================================
        st.markdown("---")
        
        # Boton para ver metodologia
        if st.button("Ver Metodologia", width='stretch', help="Documentacion de metricas y formulas"):
            mostrar_metodologia_callback()
        
        # Botón de cerrar sesión
        if st.button("Cerrar Sesión", width='stretch', type="secondary"):
            logout()
    
    # =========================================================================
    # Guardar filtros en session_state para uso en queries
    # =========================================================================
    filtros_seleccionados = {
        'campos_amplios': sel_campos_amplios,
        'areas': sel_areas,
        'nbcs': sel_nbcs,
        'deptos': sel_deptos,
        'municipios': sel_munis,
        'modalidades': sel_modalidades,
        'sectores': sel_sectores,
        'niveles': sel_niveles,
        'caracteres': sel_caracteres,
        'estados': sel_estados,
        'busqueda_nombre': busqueda_programa,  # Búsqueda por nombre de programa
        'cod_snies_programas': sel_cod_snies_programas  # Programas específicos por código SNIES
    }
    
    # Filtros SIET (disyuntivos)
    filtros_siet_seleccionados = {
        'areas_desempeno': sel_areas_siet,
        'deptos_siet': sel_deptos_siet,
        'estados_siet': sel_estados_siet,
        'modalidades_siet': sel_modalidades_siet,
        'busqueda_nombre': busqueda_programa,  # Mismo filtro de búsqueda aplica a SIET
        'mostrar': mostrar_siet
    }
    
    return filtros_seleccionados, filtros_siet_seleccionados
