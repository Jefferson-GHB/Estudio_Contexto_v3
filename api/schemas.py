"""
Schemas Pydantic para el Backend DSS v2.0
Define los modelos de datos para validación y serialización.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS
# ============================================================
class EstadoVariable(str, Enum):
    DISPONIBLE = " DISPONIBLE"
    PROXY = " PROXY"
    PARCIAL = " PARCIAL"
    LLM = " LLM"
    CALC = " CALC"


class TipoConsulta(str, Enum):
    VARIABLE = "variable"
    DOMINIO = "dominio"
    EJE = "eje"
    NBC = "nbc"
    DEPARTAMENTO = "departamento"


# ============================================================
# MODELOS BASE
# ============================================================
class Variable(BaseModel):
    """Representa una variable del mapeo DSS."""
    id: str = Field(..., description="ID único de la variable (ej: campo_amplio)")
    nombre: str = Field(..., description="Nombre descriptivo")
    eje: str = Field(..., description="Eje al que pertenece")
    dominio: str = Field(..., description="Dominio al que pertenece")
    schema_db: Optional[str] = Field(None, alias="schema", description="Schema en DuckDB")
    tabla: Optional[str] = Field(None, description="Tabla en DuckDB")
    columna_principal: Optional[str] = Field(None, description="Columna principal")
    registros: Optional[int] = Field(None, description="Número de registros disponibles")
    estado: EstadoVariable = Field(..., description="Estado de disponibilidad")
    nota: Optional[str] = Field(None, description="Notas adicionales")
    es_consultable: bool = Field(default=True, description="Si tiene datos en DuckDB")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "nbc",
                "nombre": "Núcleo básico del conocimiento",
                "eje": "EJE_1_PERTINENCIA_ACADEMICA",
                "dominio": "D1_ACADEMICO_FORMATIVO",
                "schema": "snies",
                "tabla": "snies_programas",
                "columna_principal": "NBC",
                "registros": 30660,
                "estado": " DISPONIBLE",
                "nota": "Join catalogo_nbc_snies",
                "es_consultable": True
            }
        }


class Dominio(BaseModel):
    """Representa un dominio DSS."""
    id: str = Field(..., description="ID del dominio (ej: D1_ACADEMICO_FORMATIVO)")
    numero: int = Field(..., description="Número del dominio (1-8)")
    nombre: str = Field(..., description="Nombre corto")
    eje: str = Field(..., description="Eje padre")
    descripcion: str = Field(..., description="Descripción del dominio")
    num_variables: int = Field(default=0, description="Cantidad de variables")
    variables_ids: List[str] = Field(default_factory=list, description="IDs de variables")


class Eje(BaseModel):
    """Representa un eje DSS."""
    id: str = Field(..., description="ID del eje")
    numero: int = Field(..., description="Número del eje (1-4)")
    nombre: str = Field(..., description="Nombre del eje")
    descripcion: str = Field(..., description="Descripción del eje")
    dominios: List[str] = Field(default_factory=list, description="IDs de dominios")
    num_variables: int = Field(default=0, description="Total de variables en este eje")


# ============================================================
# MODELOS DE DATOS
# ============================================================
class VariableData(BaseModel):
    """Datos consultados de una variable."""
    variable_id: str
    variable_nombre: str
    dominio: str
    eje: str
    query_ejecutado: str
    registros_obtenidos: int
    columnas: List[str]
    datos: List[Dict[str, Any]]
    tiempo_ejecucion_ms: float
    error: Optional[str] = None


class DominioCompleto(BaseModel):
    """Dominio con todas sus variables y datos."""
    dominio: Dominio
    variables: List[Variable]
    datos_por_variable: Dict[str, VariableData] = Field(default_factory=dict)


# ============================================================
# REQUEST/RESPONSE
# ============================================================
class FiltrosConsulta(BaseModel):
    """Filtros para consultas personalizadas."""
    nbc_id: Optional[int] = Field(None, description="ID del NBC a filtrar")
    nbc_nombre: Optional[str] = Field(None, description="Nombre del NBC")
    departamento: Optional[str] = Field(None, description="Departamento a filtrar")
    municipio: Optional[str] = Field(None, description="Municipio a filtrar")
    nivel_formacion: Optional[str] = Field(None, description="Nivel de formación")
    modalidad: Optional[str] = Field(None, description="Modalidad")
    año_inicio: Optional[int] = Field(None, description="Año inicio rango")
    año_fin: Optional[int] = Field(None, description="Año fin rango")
    limite: int = Field(default=100, ge=1, le=10000, description="Límite de registros")


class ConsultaRequest(BaseModel):
    """Request para consulta flexible."""
    tipo: TipoConsulta = Field(..., description="Tipo de consulta")
    target_id: Optional[str] = Field(None, description="ID del target (variable, dominio, eje)")
    filtros: FiltrosConsulta = Field(default_factory=FiltrosConsulta)
    incluir_datos: bool = Field(default=True, description="Si incluir datos en respuesta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tipo": "dominio",
                "target_id": "D1_ACADEMICO_FORMATIVO",
                "filtros": {
                    "nbc_id": 1,
                    "departamento": "CUNDINAMARCA",
                    "limite": 100
                },
                "incluir_datos": True
            }
        }


class ConsultaResponse(BaseModel):
    """Response de consulta."""
    exito: bool
    tipo_consulta: str
    target_id: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.now)
    tiempo_total_ms: float
    num_variables_consultadas: int
    num_registros_totales: int
    datos: Dict[str, Any] = Field(default_factory=dict)
    errores: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================
# HEALTH & METADATA
# ============================================================
class HealthResponse(BaseModel):
    """Response del health check."""
    status: str = Field(..., description="Estado del servicio")
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    duckdb_conectado: bool
    mapeo_cargado: bool
    total_variables: int
    total_ejes: int
    total_dominios: int
    variables_disponibles: int
    variables_llm: int
    configuracion: Dict[str, Any] = Field(default_factory=dict)


class MapeoStats(BaseModel):
    """Estadísticas del mapeo DSS."""
    total_variables: int
    por_estado: Dict[str, int]
    por_eje: Dict[str, int]
    por_dominio: Dict[str, int]
    schemas_unicos: List[str]
    tablas_unicas: List[str]


# ============================================================
# CATALOGOS DROPDOWN
# ============================================================
class NbcItem(BaseModel):
    """Item para dropdown de NBC."""
    id_nbc: int
    nombre_nbc: str
    area_conocimiento: Optional[str] = None
    campo_amplio: Optional[str] = None


class DepartamentoItem(BaseModel):
    """Item para dropdown de departamentos."""
    codigo: str
    nombre: str
    region: Optional[str] = None


class CatalogoResponse(BaseModel):
    """Response para catálogos dropdown."""
    tipo: str
    total: int
    items: List[Any]
