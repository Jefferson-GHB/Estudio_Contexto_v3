"""
Backend DSS v2.0 - FastAPI Application
======================================
Motor de Decisión para Análisis de Pertinencia de Programas Académicos.

Ejecutar con:
    uvicorn api.main:app --reload --port 8000

Documentación automática:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import CORS_ORIGINS, API_PREFIX, validar_configuracion
from .routes import router
from .engine import get_engine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager para inicialización y cleanup.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Iniciando Backend DSS v2.0")
    logger.info("=" * 60)
    
    # Validar configuración
    config = validar_configuracion()
    if not config["valido"]:
        for error in config["errores"]:
            logger.error(f"ERROR CONFIG: {error}")
    else:
        logger.info(" Configuración validada correctamente")
        logger.info(f"   DuckDB: {config['paths']['duckdb']}")
        logger.info(f"   Mapeo DSS: {config['paths']['mapeo_dss']}")
    
    # Inicializar motor DSS
    try:
        engine = get_engine()
        stats = engine.get_stats()
        logger.info(f" Motor DSS inicializado:")
        logger.info(f"   Variables totales: {stats.total_variables}")
        logger.info(f"   Variables disponibles: {stats.por_estado.get(' DISPONIBLE', 0)}")
        logger.info(f"   Schemas únicos: {len(stats.schemas_unicos)}")
        logger.info(f"   Tablas únicas: {len(stats.tablas_unicas)}")
    except Exception as e:
        logger.error(f" Error inicializando motor DSS: {e}")
    
    logger.info("=" * 60)
    logger.info("Backend DSS listo para recibir requests")
    logger.info(f"Documentación: http://localhost:8000/docs")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Cerrando Backend DSS v2.0")


# Crear aplicación FastAPI
app = FastAPI(
    title="Backend DSS v2.0",
    description="""
## Motor de Decisión para Análisis de Pertinencia

Sistema basado en **81 variables** organizadas en **4 ejes** y **8 dominios**.

### Ejes del Sistema:
1. **Pertinencia Académica** - Estructura curricular y normativa
2. **Pertinencia Laboral** - Demanda ocupacional y competencias
3. **Pertinencia Territorial** - Contexto regional y planes de desarrollo
4. **Decisión Virtual** - Integración y recomendaciones

### Fuentes de Datos:
- DuckDB con 748 tablas y 52M+ registros
- SNIES, SIET, CUOC, CIIU, DANE, Banco Mundial, etc.

### Uso Principal:
```python
# Obtener contexto para análisis de un NBC
GET /api/v1/contexto/1  # NBC ID = 1

# Consultar variables de un dominio
GET /api/v1/dominios/D1_ACADEMICO_FORMATIVO/datos?nbc_id=1
```
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas
app.include_router(router, prefix=API_PREFIX)


# Ruta raíz
@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz con información básica del sistema.
    """
    return {
        "nombre": "Backend DSS v2.0",
        "descripcion": "Motor de Decisión para Análisis de Pertinencia",
        "version": "2.0.0",
        "docs": "/docs",
        "health": f"{API_PREFIX}/health",
        "endpoints": {
            "ejes": f"{API_PREFIX}/ejes",
            "dominios": f"{API_PREFIX}/dominios",
            "variables": f"{API_PREFIX}/variables",
            "catalogos": f"{API_PREFIX}/catalogos/nbcs"
        }
    }


# Para ejecutar directamente con python -m api.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
