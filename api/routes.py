"""
FastAPI Routes para Backend DSS v3.0
====================================
Endpoints REST para consulta del sistema DSS.

PUNTOS CRÍTICOS:
- PUNTO 10: /punto10/* - Tendencias Globales y LATAM
- PUNTO 11: /punto11/* - Tendencias Nacionales y Regionales
- PUNTO 12: /punto12/* - Transformaciones Sectoriales CIIU
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .engine import get_engine, DSSEngine
from .schemas import (
    Variable,
    Dominio,
    Eje,
    ConsultaRequest,
    ConsultaResponse,
    VariableData,
    HealthResponse,
    MapeoStats,
    FiltrosConsulta,
    NbcItem,
    DepartamentoItem,
    CatalogoResponse
)
from .config import validar_configuracion, API_VERSION

router = APIRouter()


# ================================================================
# HEALTH & METADATA
# ================================================================

@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """
    Health check del sistema.
    
    Verifica:
    - Conexión a DuckDB
    - Carga del mapeo DSS
    - Estadísticas generales
    """
    engine = get_engine()
    config = validar_configuracion()
    
    # Verificar conexión DuckDB
    duckdb_ok, duckdb_msg = engine.verificar_conexion()
    
    stats = engine.get_stats()
    
    return HealthResponse(
        status="healthy" if (engine.inicializado and duckdb_ok) else "unhealthy",
        version=API_VERSION,
        timestamp=datetime.now(),
        duckdb_conectado=duckdb_ok,
        mapeo_cargado=engine.inicializado,
        total_variables=stats.total_variables,
        total_ejes=len(engine.get_ejes()),
        total_dominios=len(engine.get_dominios()),
        variables_disponibles=stats.por_estado.get(" DISPONIBLE", 0),
        variables_llm=stats.por_estado.get(" LLM", 0),
        configuracion=config
    )


@router.get("/stats", response_model=MapeoStats, tags=["Sistema"])
async def obtener_estadisticas():
    """
    Estadísticas detalladas del mapeo DSS.
    
    Retorna conteos por estado, eje, dominio y listado de schemas/tablas únicos.
    """
    engine = get_engine()
    return engine.get_stats()


# ================================================================
# EJES
# ================================================================

@router.get("/ejes", response_model=List[Eje], tags=["Estructura DSS"])
async def listar_ejes():
    """
    Lista los 4 ejes del sistema DSS.
    
    - EJE_1: Pertinencia Académica (D1, D2, D3)
    - EJE_2: Pertinencia Laboral (D4, D5)
    - EJE_3: Pertinencia Territorial (D6, D7)
    - EJE_4: Decisión Virtual (D8)
    """
    engine = get_engine()
    return engine.get_ejes()


@router.get("/ejes/{eje_id}", response_model=Eje, tags=["Estructura DSS"])
async def obtener_eje(
    eje_id: str = Path(..., description="ID del eje (ej: EJE_1_PERTINENCIA_ACADEMICA)")
):
    """
    Obtiene detalle de un eje específico.
    """
    engine = get_engine()
    eje = engine.get_eje(eje_id)
    
    if not eje:
        raise HTTPException(status_code=404, detail=f"Eje '{eje_id}' no encontrado")
    
    return eje


@router.get("/ejes/{eje_id}/variables", response_model=List[Variable], tags=["Estructura DSS"])
async def obtener_variables_eje(
    eje_id: str = Path(..., description="ID del eje")
):
    """
    Lista todas las variables de un eje.
    """
    engine = get_engine()
    variables = engine.get_variables_eje(eje_id)
    
    if not variables:
        raise HTTPException(status_code=404, detail=f"Eje '{eje_id}' no encontrado o sin variables")
    
    return variables


# ================================================================
# DOMINIOS
# ================================================================

@router.get("/dominios", response_model=List[Dominio], tags=["Estructura DSS"])
async def listar_dominios():
    """
    Lista los 8 dominios del sistema DSS.
    """
    engine = get_engine()
    return engine.get_dominios()


@router.get("/dominios/{dom_id}", tags=["Estructura DSS"])
async def obtener_dominio(
    dom_id: str = Path(..., description="ID del dominio (ej: D1_ACADEMICO_FORMATIVO)")
):
    """
    Obtiene detalle de un dominio con resumen de sus variables.
    """
    engine = get_engine()
    resumen = engine.obtener_resumen_dominio(dom_id)
    
    if "error" in resumen:
        raise HTTPException(status_code=404, detail=resumen["error"])
    
    return resumen


@router.get("/dominios/{dom_id}/variables", response_model=List[Variable], tags=["Estructura DSS"])
async def obtener_variables_dominio(
    dom_id: str = Path(..., description="ID del dominio")
):
    """
    Lista todas las variables de un dominio.
    """
    engine = get_engine()
    variables = engine.get_variables_dominio(dom_id)
    
    if not variables:
        raise HTTPException(status_code=404, detail=f"Dominio '{dom_id}' no encontrado o sin variables")
    
    return variables


@router.get("/dominios/{dom_id}/datos", tags=["Consulta Datos"])
async def consultar_datos_dominio(
    dom_id: str = Path(..., description="ID del dominio"),
    nbc_id: Optional[int] = Query(None, description="Filtrar por ID de NBC"),
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    limite: int = Query(100, ge=1, le=1000, description="Límite de registros por variable")
):
    """
    Consulta datos de todas las variables de un dominio.
    
    Retorna los datos reales de DuckDB para cada variable consultable del dominio.
    Las variables con estado LLM/CALC no retornan datos (se generan posteriormente).
    """
    engine = get_engine()
    
    dominio = engine.get_dominio(dom_id)
    if not dominio:
        raise HTTPException(status_code=404, detail=f"Dominio '{dom_id}' no encontrado")
    
    filtros = FiltrosConsulta(
        nbc_id=nbc_id,
        departamento=departamento,
        limite=limite
    )
    
    resultados = engine.consultar_dominio(dom_id, filtros)
    
    # Convertir a dict serializable
    return {
        "dominio": dominio.model_dump(),
        "filtros_aplicados": filtros.model_dump(),
        "variables": {
            var_id: data.model_dump() 
            for var_id, data in resultados.items()
        }
    }


# ================================================================
# VARIABLES
# ================================================================

@router.get("/variables", response_model=List[Variable], tags=["Variables"])
async def listar_variables(
    solo_consultables: bool = Query(False, description="Solo variables con datos en DuckDB"),
    dominio: Optional[str] = Query(None, description="Filtrar por dominio"),
    eje: Optional[str] = Query(None, description="Filtrar por eje")
):
    """
    Lista las 81 variables del mapeo DSS.
    
    Permite filtrar por:
    - solo_consultables: excluye variables LLM/CALC
    - dominio: filtra por dominio específico
    - eje: filtra por eje específico
    """
    engine = get_engine()
    
    if solo_consultables:
        variables = engine.get_variables_consultables()
    else:
        variables = engine.get_variables()
    
    if dominio:
        variables = [v for v in variables if v.dominio == dominio]
    
    if eje:
        variables = [v for v in variables if v.eje == eje]
    
    return variables


@router.get("/variables/{var_id}", response_model=Variable, tags=["Variables"])
async def obtener_variable(
    var_id: str = Path(..., description="ID de la variable (ej: nbc, campo_amplio)")
):
    """
    Obtiene metadata de una variable específica.
    """
    engine = get_engine()
    variable = engine.get_variable(var_id)
    
    if not variable:
        raise HTTPException(status_code=404, detail=f"Variable '{var_id}' no encontrada")
    
    return variable


@router.get("/variables/{var_id}/datos", response_model=VariableData, tags=["Consulta Datos"])
async def consultar_datos_variable(
    var_id: str = Path(..., description="ID de la variable"),
    nbc_id: Optional[int] = Query(None, description="Filtrar por ID de NBC"),
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    nivel_formacion: Optional[str] = Query(None, description="Filtrar por nivel de formación"),
    modalidad: Optional[str] = Query(None, description="Filtrar por modalidad"),
    limite: int = Query(100, ge=1, le=10000, description="Límite de registros"),
    agregado: bool = Query(False, description="Retornar estadísticas agregadas")
):
    """
    Consulta datos de una variable específica.
    
    Ejecuta query dinámico a DuckDB basado en el mapeo de la variable.
    Solo funciona para variables consultables (no LLM/CALC).
    """
    engine = get_engine()
    
    variable = engine.get_variable(var_id)
    if not variable:
        raise HTTPException(status_code=404, detail=f"Variable '{var_id}' no encontrada")
    
    filtros = FiltrosConsulta(
        nbc_id=nbc_id,
        departamento=departamento,
        nivel_formacion=nivel_formacion,
        modalidad=modalidad,
        limite=limite
    )
    
    resultado = engine.consultar_variable(var_id, filtros, modo_agregado=agregado)
    
    return resultado


# ================================================================
# CATÁLOGOS (DROPDOWNS)
# ================================================================

@router.get("/catalogos/nbcs", response_model=CatalogoResponse, tags=["Catálogos"])
async def listar_nbcs():
    """
    Lista NBCs disponibles para dropdown de selección.
    
    Retorna ID, nombre, área de conocimiento y campo amplio.
    """
    engine = get_engine()
    items = engine.get_nbcs_disponibles()
    
    return CatalogoResponse(
        tipo="nbc",
        total=len(items),
        items=[item.model_dump() for item in items]
    )


@router.get("/catalogos/departamentos", response_model=CatalogoResponse, tags=["Catálogos"])
async def listar_departamentos():
    """
    Lista departamentos disponibles para dropdown de selección.
    """
    engine = get_engine()
    items = engine.get_departamentos_disponibles()
    
    return CatalogoResponse(
        tipo="departamento",
        total=len(items),
        items=[item.model_dump() for item in items]
    )


@router.get("/catalogos/niveles-formacion", tags=["Catálogos"])
async def listar_niveles_formacion():
    """
    Lista niveles de formación disponibles.
    """
    engine = get_engine()
    items = engine.get_niveles_formacion()
    
    return CatalogoResponse(
        tipo="nivel_formacion",
        total=len(items),
        items=items
    )


@router.get("/catalogos/modalidades", tags=["Catálogos"])
async def listar_modalidades():
    """
    Lista modalidades disponibles.
    """
    engine = get_engine()
    items = engine.get_modalidades()
    
    return CatalogoResponse(
        tipo="modalidad",
        total=len(items),
        items=items
    )


# ================================================================
# CONSULTA COMPLETA (CONTEXTO PARA ANÁLISIS)
# ================================================================

@router.post("/consulta", response_model=ConsultaResponse, tags=["Análisis"])
async def realizar_consulta(request: ConsultaRequest):
    """
    Realiza una consulta flexible al sistema DSS.
    
    Permite consultar por:
    - variable: datos de una variable específica
    - dominio: datos de todas las variables de un dominio
    - eje: datos de todos los dominios de un eje
    - nbc: contexto completo para un NBC específico
    """
    engine = get_engine()
    inicio = datetime.now()
    
    resultado = ConsultaResponse(
        exito=False,
        tipo_consulta=request.tipo.value,
        target_id=request.target_id,
        tiempo_total_ms=0,
        num_variables_consultadas=0,
        num_registros_totales=0
    )
    
    try:
        if request.tipo.value == "variable":
            if not request.target_id:
                raise HTTPException(status_code=400, detail="target_id requerido para tipo 'variable'")
            
            data = engine.consultar_variable(request.target_id, request.filtros)
            resultado.datos = {"variable": data.model_dump()}
            resultado.num_variables_consultadas = 1
            resultado.num_registros_totales = data.registros_obtenidos
            
        elif request.tipo.value == "dominio":
            if not request.target_id:
                raise HTTPException(status_code=400, detail="target_id requerido para tipo 'dominio'")
            
            data = engine.consultar_dominio(request.target_id, request.filtros)
            resultado.datos = {"dominio": {k: v.model_dump() for k, v in data.items()}}
            resultado.num_variables_consultadas = len(data)
            resultado.num_registros_totales = sum(v.registros_obtenidos for v in data.values())
            
        elif request.tipo.value == "eje":
            if not request.target_id:
                raise HTTPException(status_code=400, detail="target_id requerido para tipo 'eje'")
            
            data = engine.consultar_eje(request.target_id, request.filtros)
            resultado.datos = {
                "eje": {
                    dom_id: {var_id: v.model_dump() for var_id, v in vars_dict.items()}
                    for dom_id, vars_dict in data.items()
                }
            }
            resultado.num_variables_consultadas = sum(len(d) for d in data.values())
            resultado.num_registros_totales = sum(
                v.registros_obtenidos 
                for dom in data.values() 
                for v in dom.values()
            )
            
        elif request.tipo.value == "nbc":
            nbc_id = request.filtros.nbc_id
            if not nbc_id:
                raise HTTPException(status_code=400, detail="filtros.nbc_id requerido para tipo 'nbc'")
            
            data = engine.consultar_contexto_nbc(nbc_id, request.filtros.departamento)
            resultado.datos = data
            # Contar variables y registros
            total_vars = 0
            total_regs = 0
            for eje_data in data.get("ejes", {}).values():
                for dom_data in eje_data.values():
                    total_vars += len(dom_data)
                    for var_data in dom_data.values():
                        total_regs += var_data.registros_obtenidos
            resultado.num_variables_consultadas = total_vars
            resultado.num_registros_totales = total_regs
        
        resultado.exito = True
        
    except HTTPException:
        raise
    except Exception as e:
        resultado.errores.append(str(e))
    
    resultado.tiempo_total_ms = (datetime.now() - inicio).total_seconds() * 1000
    
    return resultado


@router.get("/contexto/{nbc_id}", tags=["Análisis"])
async def obtener_contexto_nbc(
    nbc_id: int = Path(..., description="ID del NBC a analizar"),
    departamento: Optional[str] = Query(None, description="Departamento (opcional)")
):
    """
    Obtiene el contexto completo para análisis de pertinencia de un NBC.
    
    Este es el endpoint principal para alimentar el análisis LLM.
    Retorna datos organizados por eje y dominio.
    """
    engine = get_engine()
    
    resultado = engine.consultar_contexto_nbc(nbc_id, departamento)
    
    return resultado


# ================================================================
# PUNTO 10: TENDENCIAS GLOBALES Y LATAM
# ================================================================

@router.get("/punto10/banco-mundial", tags=["PUNTO 10 - Global"])
async def obtener_indicadores_banco_mundial(
    solo_latam: bool = Query(False, description="Filtrar solo países LATAM")
):
    """
    Indicadores del Banco Mundial: 22 indicadores globales.
    
    PUNTO 10: PIB, desempleo, matrícula terciaria, gasto educación, etc.
    """
    engine = get_engine()
    return engine.consultar_indicadores_banco_mundial(solo_latam=solo_latam)


@router.get("/punto10/oecd", tags=["PUNTO 10 - Global"])
async def obtener_oecd_educacion():
    """
    Estadísticas OECD de educación.
    
    PUNTO 10: 13 países con datos de educación terciaria.
    """
    engine = get_engine()
    return engine.consultar_oecd_educacion()


@router.get("/punto10/oit", tags=["PUNTO 10 - Global"])
async def obtener_oit_empleo():
    """
    Estadísticas OIT (ILO) de empleo global.
    
    PUNTO 10: Tendencias de empleo internacional.
    """
    engine = get_engine()
    return engine.consultar_oit_empleo()


@router.get("/punto10/unesco", tags=["PUNTO 10 - Global"])
async def obtener_unesco_educacion():
    """
    Estadísticas UNESCO de educación.
    
    PUNTO 10: 12,089 registros de educación mundial.
    """
    engine = get_engine()
    return engine.consultar_unesco_educacion()


@router.get("/punto10/tendencias-tech", tags=["PUNTO 10 - Global"])
async def obtener_tendencias_tecnologicas():
    """
    Tendencias tecnológicas: IA, Industria 4.0, habilidades futuro.
    
    PUNTO 10: Adopción IA, microcredenciales, skills emergentes.
    """
    engine = get_engine()
    return engine.consultar_tendencias_tecnologicas()


@router.get("/punto10/completo", tags=["PUNTO 10 - Global"])
async def obtener_punto_10_completo(
    solo_latam: bool = Query(True, description="Filtrar solo países LATAM")
):
    """
    Obtiene TODOS los datos del PUNTO 10: Tendencias Globales y LATAM.
    
    Consolida: Banco Mundial, OECD, OIT, UNESCO, Tendencias Tech.
    """
    engine = get_engine()
    return engine.obtener_punto_10_completo(solo_latam=solo_latam)


# ================================================================
# PUNTO 11: TENDENCIAS NACIONALES Y REGIONALES
# ================================================================

@router.get("/punto11/snies", tags=["PUNTO 11 - Nacional"])
async def obtener_snies_completo(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    nbc_id: Optional[int] = Query(None, description="Filtrar por NBC")
):
    """
    SNIES completo: 2.8M+ registros, 30,660 programas.
    
    PUNTO 11: Oferta educativa nacional por nivel, departamento, NBC.
    """
    engine = get_engine()
    return engine.consultar_snies_completo(departamento, nbc_id)


@router.get("/punto11/tendencias-ocupacionales", tags=["PUNTO 11 - Nacional"])
async def obtener_tendencias_ocupacionales(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento")
):
    """
    Tendencias ocupacionales: 160+ tablas del Observatorio Laboral.
    
    PUNTO 11: Demanda laboral, vacantes, proyecciones.
    """
    engine = get_engine()
    return engine.consultar_tendencias_ocupacionales(departamento)


@router.get("/punto11/dnp", tags=["PUNTO 11 - Nacional"])
async def obtener_dnp_planes_desarrollo(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento")
):
    """
    Planes de desarrollo DNP: 2.9M+ registros.
    
    PUNTO 11: Alineación con políticas públicas y metas de desarrollo.
    """
    engine = get_engine()
    return engine.consultar_dnp_planes_desarrollo(departamento)


@router.get("/punto11/estadisticas-es", tags=["PUNTO 11 - Nacional"])
async def obtener_estadisticas_es():
    """
    Estadísticas de educación superior consolidadas.
    
    PUNTO 11: Series históricas de admitidos, graduados, etc.
    """
    engine = get_engine()
    return engine.consultar_estadisticas_es()


@router.get("/punto11/completo", tags=["PUNTO 11 - Nacional"])
async def obtener_punto_11_completo(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    nbc_id: Optional[int] = Query(None, description="Filtrar por NBC")
):
    """
    Obtiene TODOS los datos del PUNTO 11: Tendencias Nacionales.
    
    Consolida: SNIES, Tendencias Ocupacionales, DNP, Estadísticas ES.
    """
    engine = get_engine()
    return engine.obtener_punto_11_completo(departamento, nbc_id)


# ================================================================
# PUNTO 12: TRANSFORMACIONES SECTORIALES CIIU
# ================================================================

@router.get("/punto12/ciiu", tags=["PUNTO 12 - Sectorial"])
async def obtener_ciiu_sectores(
    codigo_ciiu: Optional[str] = Query(None, description="Código CIIU (ej: 62, J)")
):
    """
    Clasificación CIIU Rev 4: 700 códigos de actividad económica.
    
    PUNTO 12: Base de sectores económicos.
    """
    engine = get_engine()
    return engine.consultar_ciiu_sectores(codigo_ciiu)


@router.get("/punto12/estructura-empresarial", tags=["PUNTO 12 - Sectorial"])
async def obtener_estructura_empresarial(
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    codigo_ciiu: Optional[str] = Query(None, description="Filtrar por código CIIU")
):
    """
    Estructura empresarial RUES: 9.1M de registros.
    
    PUNTO 12: Densidad empresarial por sector y territorio.
    """
    engine = get_engine()
    return engine.consultar_estructura_empresarial(departamento, codigo_ciiu)


@router.get("/punto12/mesas-sectoriales", tags=["PUNTO 12 - Sectorial"])
async def obtener_mesas_sectoriales(
    sector: Optional[str] = Query(None, description="Buscar por sector")
):
    """
    Mesas sectoriales SENA: 84 mesas activas.
    
    PUNTO 12: Articulación sector productivo - formación.
    """
    engine = get_engine()
    return engine.consultar_mesas_sectoriales(sector)


@router.get("/punto12/cuoc", tags=["PUNTO 12 - Sectorial"])
async def obtener_cuoc_ocupaciones(
    nivel_competencia: Optional[int] = Query(None, description="Nivel de competencia (1-5)"),
    busqueda: Optional[str] = Query(None, description="Búsqueda en nombre/descripción")
):
    """
    CUOC: 14,462 ocupaciones clasificadas.
    
    PUNTO 12: Ocupaciones por sector y nivel de competencia.
    """
    engine = get_engine()
    return engine.consultar_cuoc_ocupaciones(nivel_competencia, busqueda)


@router.get("/punto12/mapeos", tags=["PUNTO 12 - Sectorial"])
async def obtener_mapeos_ciiu_cuoc():
    """
    Mapeos CIIU-CUOC-NBC para relacionar sectores con ocupaciones.
    
    PUNTO 12: Cruces estratégicos sector-ocupación-formación.
    """
    engine = get_engine()
    return engine.consultar_mapeo_ciiu_cuoc()


@router.get("/punto12/completo", tags=["PUNTO 12 - Sectorial"])
async def obtener_punto_12_completo(
    codigo_ciiu: Optional[str] = Query(None, description="Código CIIU"),
    departamento: Optional[str] = Query(None, description="Departamento"),
    sector: Optional[str] = Query(None, description="Sector/Mesa sectorial")
):
    """
    Obtiene TODOS los datos del PUNTO 12: Transformaciones Sectoriales.
    
    Consolida: CIIU, RUES, Mesas Sectoriales, CUOC, Mapeos.
    """
    engine = get_engine()
    return engine.obtener_punto_12_completo(codigo_ciiu, departamento, sector)


# ================================================================
# CONTEXTO INTEGRAL: PUNTOS 10 + 11 + 12
# ================================================================

@router.get("/contexto-completo", tags=["Análisis Integral"])
async def obtener_contexto_completo_pertinencia(
    nbc_id: Optional[int] = Query(None, description="ID del NBC"),
    departamento: Optional[str] = Query(None, description="Departamento"),
    codigo_ciiu: Optional[str] = Query(None, description="Código CIIU"),
    incluir_punto_10: bool = Query(True, description="Incluir tendencias globales"),
    incluir_punto_11: bool = Query(True, description="Incluir tendencias nacionales"),
    incluir_punto_12: bool = Query(True, description="Incluir análisis sectorial"),
    solo_latam: bool = Query(True, description="Solo países LATAM en punto 10")
):
    """
    Obtiene el CONTEXTO COMPLETO para análisis de pertinencia.
    
    ENDPOINT PRINCIPAL - Integra los 3 puntos críticos:
    - PUNTO 10: Tendencias Globales y LATAM (BM, OECD, OIT, UNESCO, Tech)
    - PUNTO 11: Tendencias Nacionales y Regionales (SNIES, DNP, Ocupacionales)
    - PUNTO 12: Transformaciones Sectoriales por CIIU (RUES, Empresas, Mesas)
    
    Este es el método PRINCIPAL para alimentar el análisis LLM.
    """
    engine = get_engine()
    return engine.obtener_contexto_completo_pertinencia(
        nbc_id=nbc_id,
        departamento=departamento,
        codigo_ciiu=codigo_ciiu,
        incluir_punto_10=incluir_punto_10,
        incluir_punto_11=incluir_punto_11,
        incluir_punto_12=incluir_punto_12,
        solo_latam=solo_latam
    )
