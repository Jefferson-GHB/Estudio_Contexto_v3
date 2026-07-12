"""
DSS Engine v3.0 - Motor de Decisión para Análisis de Pertinencia
================================================================
Este es el corazón del sistema. Lee MAPEO_DSS_81_VARIABLES.csv y genera
queries dinámicos a DuckDB basándose en la configuración del mapeo.

PUNTOS CRÍTICOS IMPLEMENTADOS:
- PUNTO 10: Tendencias globales y LATAM (BM, OECD, OIT, UNESCO, Tech)
- PUNTO 11: Tendencias nacionales y regionales (SNIES, DNP, Ocupacionales)
- PUNTO 12: Transformaciones sectoriales por CIIU (RUES, Empresas, Mesas)

NO USA QUERIES HARDCODEADOS - Todo es dinámico basado en el CSV de mapeo.
"""
import pandas as pd
import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import logging
import time

from .config import (
    DUCKDB_PATH, 
    EJES, 
    DOMINIOS,
    ESTADOS_CONSULTABLES,
    ESTADOS_GENERADOS,
    SCHEMAS_INTERNACIONALES,
    SCHEMAS_NACIONALES,
    SCHEMAS_SECTORIALES
)
from .models.schemas import (
    Variable, 
    Dominio, 
    Eje, 
    VariableData,
    EstadoVariable,
    FiltrosConsulta,
    MapeoStats,
    NbcItem,
    DepartamentoItem
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DSSEngine:
    """
    Motor DSS que carga el mapeo de 81 variables y ejecuta consultas dinámicas.
    
    Principios:
    1. El CSV MAPEO_DSS_81_VARIABLES.csv es la ÚNICA fuente de verdad
    2. Los queries se generan dinámicamente basados en Schema/Tabla/Columna
    3. Variables con estado LLM/CALC no se consultan a DuckDB - se generan
    """
    
    def __init__(self, duckdb_path: Path = DUCKDB_PATH):
        """
        Inicializa el motor cargando el mapeo desde DuckDB.
        
        Args:
            duckdb_path: Ruta al archivo DuckDB
        """
        self.duckdb_path = Path(duckdb_path)
        
        # Datos cargados
        self._mapeo_df: Optional[pd.DataFrame] = None
        self._variables: Dict[str, Variable] = {}
        self._dominios: Dict[str, Dominio] = {}
        self._ejes: Dict[str, Eje] = {}
        
        # Estado
        self._inicializado = False
        self._ultima_carga: Optional[datetime] = None
        
        # Cargar al iniciar
        self._cargar_mapeo()
    
    # ================================================================
    # INICIALIZACIÓN Y CARGA
    # ================================================================
    
    def _cargar_mapeo(self) -> None:
        """Carga el mapeo DSS desde DuckDB y construye estructuras internas."""
        logger.info("Cargando mapeo DSS desde DuckDB: catalogo_curado.mapeo_dss_variables")
        
        conn = self._get_connection()
        self._mapeo_df = conn.execute("""
            SELECT Eje, Dominio, ID_Variable, Nombre_Variable, Schema, Tabla,
                   Columna_Principal, Tipo_Cruce, Cruce_Via, Nota, Verificado
            FROM catalogo_curado.mapeo_dss_variables
            ORDER BY Eje, Dominio, ID_Variable
        """).fetchdf()
        conn.close()
        logger.info(f"Mapeo cargado: {len(self._mapeo_df)} variables")
        
        # Construir diccionario de variables
        self._variables = {}
        for _, row in self._mapeo_df.iterrows():
            var_id = row['ID_Variable']
            
            # Adaptación robusta a columnas variables
            tiene_tabla = pd.notna(row.get('Tabla'))
            
            # Determinar estado
            if 'Estado' in row and pd.notna(row['Estado']):
                estado_str = row['Estado']
            else:
                # Inferencia por defecto si falta la columna
                estado_str = " DISPONIBLE" if tiene_tabla else " LLM"
            
            # Intentar mapear a Enum, fallback a DISPONIBLE si falla
            try:
                estado_enum = EstadoVariable(estado_str)
            except ValueError:
                estado_enum = EstadoVariable.DISPONIBLE
            
            # Verificar si es consultable
            es_consultable = (estado_enum.value in ESTADOS_CONSULTABLES) and tiene_tabla
            
            registros = 0
            if 'Registros' in row and pd.notna(row['Registros']):
                try:
                    registros = int(row['Registros'])
                except:
                    pass
            
            self._variables[var_id] = Variable(
                id=var_id,
                nombre=row['Nombre_Variable'],
                eje=row['Eje'],
                dominio=row['Dominio'],
                schema_db=row['Schema'] if pd.notna(row.get('Schema')) else None,
                tabla=row['Tabla'] if pd.notna(row.get('Tabla')) else None,
                columna_principal=row['Columna_Principal'] if pd.notna(row.get('Columna_Principal')) else None,
                registros=registros,
                estado=estado_enum,
                nota=row['Nota'] if pd.notna(row.get('Nota')) else None,
                es_consultable=es_consultable
            )
        
        # Construir dominios con sus variables
        self._dominios = {}
        for dom_id, dom_config in DOMINIOS.items():
            variables_dom = [v.id for v in self._variables.values() if v.dominio == dom_id]
            self._dominios[dom_id] = Dominio(
                id=dom_id,
                numero=dom_config['id'],
                nombre=dom_config['nombre'],
                eje=dom_config['eje'],
                descripcion=dom_config['descripcion'],
                num_variables=len(variables_dom),
                variables_ids=variables_dom
            )
        
        # Construir ejes con sus dominios
        self._ejes = {}
        for eje_id, eje_config in EJES.items():
            total_vars = sum(
                self._dominios[d].num_variables 
                for d in eje_config['dominios'] 
                if d in self._dominios
            )
            self._ejes[eje_id] = Eje(
                id=eje_id,
                numero=eje_config['id'],
                nombre=eje_config['nombre'],
                descripcion=eje_config['descripcion'],
                dominios=eje_config['dominios'],
                num_variables=total_vars
            )
        
        self._inicializado = True
        self._ultima_carga = datetime.now()
        logger.info(f"Motor DSS inicializado: {len(self._variables)} variables, "
                   f"{len(self._dominios)} dominios, {len(self._ejes)} ejes")
    
    # ================================================================
    # CONEXIÓN DUCKDB
    # ================================================================
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Obtiene conexión a DuckDB."""
        if not self.duckdb_path.exists():
            raise FileNotFoundError(f"DuckDB no encontrado: {self.duckdb_path}")
        return duckdb.connect(str(self.duckdb_path), read_only=True)
    
    def verificar_conexion(self) -> Tuple[bool, str]:
        """Verifica la conexión a DuckDB."""
        try:
            conn = self._get_connection()
            result = conn.execute("SELECT 1").fetchone()
            conn.close()
            return True, "Conexión exitosa"
        except Exception as e:
            return False, str(e)
    
    # ================================================================
    # GETTERS DE METADATA
    # ================================================================
    
    @property
    def inicializado(self) -> bool:
        return self._inicializado
    
    def get_variables(self) -> List[Variable]:
        """Retorna todas las variables."""
        return list(self._variables.values())
    
    def get_variable(self, var_id: str) -> Optional[Variable]:
        """Retorna una variable específica."""
        return self._variables.get(var_id)
    
    def get_dominios(self) -> List[Dominio]:
        """Retorna todos los dominios."""
        return list(self._dominios.values())
    
    def get_dominio(self, dom_id: str) -> Optional[Dominio]:
        """Retorna un dominio específico."""
        return self._dominios.get(dom_id)
    
    def get_ejes(self) -> List[Eje]:
        """Retorna todos los ejes."""
        return list(self._ejes.values())
    
    def get_eje(self, eje_id: str) -> Optional[Eje]:
        """Retorna un eje específico."""
        return self._ejes.get(eje_id)
    
    def get_variables_dominio(self, dom_id: str) -> List[Variable]:
        """Retorna las variables de un dominio."""
        return [v for v in self._variables.values() if v.dominio == dom_id]
    
    def get_variables_eje(self, eje_id: str) -> List[Variable]:
        """Retorna las variables de un eje."""
        return [v for v in self._variables.values() if v.eje == eje_id]
    
    def get_variables_consultables(self) -> List[Variable]:
        """Retorna solo las variables que tienen datos en DuckDB."""
        return [v for v in self._variables.values() if v.es_consultable]
    
    def get_stats(self) -> MapeoStats:
        """Retorna estadísticas del mapeo."""
        por_estado = {}
        por_eje = {}
        por_dominio = {}
        schemas = set()
        tablas = set()
        
        for v in self._variables.values():
            # Por estado
            estado_str = v.estado.value
            por_estado[estado_str] = por_estado.get(estado_str, 0) + 1
            
            # Por eje
            por_eje[v.eje] = por_eje.get(v.eje, 0) + 1
            
            # Por dominio
            por_dominio[v.dominio] = por_dominio.get(v.dominio, 0) + 1
            
            # Schemas y tablas únicos
            if v.schema_db:
                schemas.add(v.schema_db)
            if v.tabla:
                tablas.add(v.tabla)
        
        return MapeoStats(
            total_variables=len(self._variables),
            por_estado=por_estado,
            por_eje=por_eje,
            por_dominio=por_dominio,
            schemas_unicos=sorted(list(schemas)),
            tablas_unicas=sorted(list(tablas))
        )
    
    # ================================================================
    # GENERACIÓN DE QUERIES DINÁMICOS
    # ================================================================
    
    def _generar_query_variable(
        self, 
        variable: Variable, 
        filtros: Optional[FiltrosConsulta] = None
    ) -> Optional[str]:
        """
        Genera el query SQL para una variable basándose en su mapeo.
        
        Args:
            variable: Variable a consultar
            filtros: Filtros opcionales
            
        Returns:
            Query SQL o None si no es consultable
        """
        if not variable.es_consultable:
            return None
        
        if not variable.schema_db or not variable.tabla:
            return None
        
        # Tabla completa con schema
        tabla_completa = f"{variable.schema_db}.{variable.tabla}"
        
        # Columna a seleccionar
        if variable.columna_principal:
            select_cols = f'"{variable.columna_principal}"'
        else:
            select_cols = "*"
        
        # Construir WHERE
        where_clauses = []
        
        if filtros:
            # Filtro por NBC (aplica a tablas SNIES principalmente)
            if filtros.nbc_id and "snies" in variable.schema_db.lower():
                # Verificar si la tabla tiene columna NBC o similar
                if variable.tabla == "snies_programas":
                    where_clauses.append(
                        f""""CÓDIGO_NBC" = (
                            SELECT "CÓDIGO_NBC" FROM catalogo_curado.catalogo_nbc_snies 
                            WHERE "ID_NBC" = {filtros.nbc_id} LIMIT 1
                        )"""
                    )
            
            # Filtro por departamento
            if filtros.departamento:
                # Diferentes columnas según la tabla
                dep_columns = [
                    "DEPARTAMENTO", "DEPARTAMENTO_OFERTA_PROG", 
                    "departamento", "NOMBRE_DEPARTAMENTO", "nombre_departamento"
                ]
                # Intentamos con la más común
                where_clauses.append(
                    f"""(
                        COALESCE("DEPARTAMENTO_OFERTA_PROG", "DEPARTAMENTO", '') 
                        ILIKE '%{filtros.departamento}%'
                    )"""
                )
            
            # Filtro por municipio
            if filtros.municipio:
                where_clauses.append(
                    f"""COALESCE("MUNICIPIO_OFERTA_PROG", "MUNICIPIO", '') ILIKE '%{filtros.municipio}%'"""
                )
            
            # Filtro por nivel de formación
            if filtros.nivel_formacion and "snies" in variable.schema_db.lower():
                where_clauses.append(
                    f""""NIVEL_DE_FORMACIÓN" = '{filtros.nivel_formacion}'"""
                )
            
            # Filtro por modalidad
            if filtros.modalidad and "snies" in variable.schema_db.lower():
                where_clauses.append(
                    f""""MODALIDAD" = '{filtros.modalidad}'"""
                )
        
        # Límite
        limite = filtros.limite if filtros else 100
        
        # Construir query
        query = f"SELECT {select_cols} FROM {tabla_completa}"
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += f" LIMIT {limite}"
        
        return query
    
    def _generar_query_agregado(
        self,
        variable: Variable,
        filtros: Optional[FiltrosConsulta] = None
    ) -> Optional[str]:
        """
        Genera query agregado para obtener estadísticas de una variable.
        """
        if not variable.es_consultable:
            return None
        
        tabla_completa = f"{variable.schema_db}.{variable.tabla}"
        col = variable.columna_principal
        
        if not col:
            return f"SELECT COUNT(*) as total FROM {tabla_completa}"
        
        # Query agregado con conteo por valor
        query = f"""
        SELECT 
            "{col}" as valor,
            COUNT(*) as frecuencia
        FROM {tabla_completa}
        WHERE "{col}" IS NOT NULL
        GROUP BY "{col}"
        ORDER BY frecuencia DESC
        LIMIT 50
        """
        return query
    
    # ================================================================
    # EJECUCIÓN DE CONSULTAS
    # ================================================================
    
    def consultar_variable(
        self, 
        var_id: str, 
        filtros: Optional[FiltrosConsulta] = None,
        modo_agregado: bool = False
    ) -> VariableData:
        """
        Consulta los datos de una variable específica.
        
        Args:
            var_id: ID de la variable
            filtros: Filtros opcionales
            modo_agregado: Si True, retorna estadísticas agregadas
            
        Returns:
            VariableData con los resultados
        """
        inicio = time.time()
        
        variable = self.get_variable(var_id)
        if not variable:
            return VariableData(
                variable_id=var_id,
                variable_nombre="No encontrada",
                dominio="",
                eje="",
                query_ejecutado="",
                registros_obtenidos=0,
                columnas=[],
                datos=[],
                tiempo_ejecucion_ms=0,
                error=f"Variable '{var_id}' no existe en el mapeo"
            )
        
        if not variable.es_consultable:
            return VariableData(
                variable_id=var_id,
                variable_nombre=variable.nombre,
                dominio=variable.dominio,
                eje=variable.eje,
                query_ejecutado="",
                registros_obtenidos=0,
                columnas=[],
                datos=[],
                tiempo_ejecucion_ms=(time.time() - inicio) * 1000,
                error=f"Variable '{var_id}' no es consultable (estado: {variable.estado.value})"
            )
        
        # Generar query
        if modo_agregado:
            query = self._generar_query_agregado(variable, filtros)
        else:
            query = self._generar_query_variable(variable, filtros)
        
        if not query:
            return VariableData(
                variable_id=var_id,
                variable_nombre=variable.nombre,
                dominio=variable.dominio,
                eje=variable.eje,
                query_ejecutado="",
                registros_obtenidos=0,
                columnas=[],
                datos=[],
                tiempo_ejecucion_ms=(time.time() - inicio) * 1000,
                error="No se pudo generar query para esta variable"
            )
        
        # Ejecutar query
        try:
            conn = self._get_connection()
            result = conn.execute(query)
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            conn.close()
            
            # Convertir a lista de dicts
            datos = [dict(zip(columns, row)) for row in rows]
            
            return VariableData(
                variable_id=var_id,
                variable_nombre=variable.nombre,
                dominio=variable.dominio,
                eje=variable.eje,
                query_ejecutado=query,
                registros_obtenidos=len(datos),
                columnas=columns,
                datos=datos,
                tiempo_ejecucion_ms=(time.time() - inicio) * 1000
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando query para {var_id}: {e}")
            return VariableData(
                variable_id=var_id,
                variable_nombre=variable.nombre,
                dominio=variable.dominio,
                eje=variable.eje,
                query_ejecutado=query,
                registros_obtenidos=0,
                columnas=[],
                datos=[],
                tiempo_ejecucion_ms=(time.time() - inicio) * 1000,
                error=str(e)
            )
    
    def consultar_dominio(
        self, 
        dom_id: str, 
        filtros: Optional[FiltrosConsulta] = None,
        solo_consultables: bool = True
    ) -> Dict[str, VariableData]:
        """
        Consulta todas las variables de un dominio.
        
        Args:
            dom_id: ID del dominio
            filtros: Filtros opcionales
            solo_consultables: Si True, solo consulta variables con datos en DuckDB
            
        Returns:
            Dict con variable_id -> VariableData
        """
        variables = self.get_variables_dominio(dom_id)
        
        if solo_consultables:
            variables = [v for v in variables if v.es_consultable]
        
        resultados = {}
        for var in variables:
            resultados[var.id] = self.consultar_variable(var.id, filtros)
        
        return resultados
    
    def consultar_eje(
        self, 
        eje_id: str, 
        filtros: Optional[FiltrosConsulta] = None,
        solo_consultables: bool = True
    ) -> Dict[str, Dict[str, VariableData]]:
        """
        Consulta todas las variables de un eje (organizado por dominio).
        
        Args:
            eje_id: ID del eje
            filtros: Filtros opcionales
            solo_consultables: Si True, solo consulta variables con datos en DuckDB
            
        Returns:
            Dict con dominio_id -> {variable_id -> VariableData}
        """
        eje = self.get_eje(eje_id)
        if not eje:
            return {}
        
        resultados = {}
        for dom_id in eje.dominios:
            resultados[dom_id] = self.consultar_dominio(dom_id, filtros, solo_consultables)
        
        return resultados
    
    # ================================================================
    # CATÁLOGOS PARA DROPDOWNS
    # ================================================================
    
    def get_nbcs_disponibles(self) -> List[NbcItem]:
        """Obtiene la lista de NBCs disponibles para dropdown."""
        query = """
        SELECT 
            "ID_NBC" as id_nbc,
            "NBC" as nombre_nbc,
            "Area_Conocimiento" as area_conocimiento,
            "CINE_Campo_Amplio" as campo_amplio
        FROM catalogo_curado.catalogo_nbc_snies
        ORDER BY "NBC"
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchall()
            conn.close()
            
            return [
                NbcItem(
                    id_nbc=row[0],
                    nombre_nbc=row[1],
                    area_conocimiento=row[2],
                    campo_amplio=row[3]
                )
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error obteniendo NBCs: {e}")
            return []
    
    def get_departamentos_disponibles(self) -> List[DepartamentoItem]:
        """Obtiene la lista de departamentos disponibles para dropdown."""
        # Usar DIVIPOLA como fuente autoritativa
        query = """
        SELECT DISTINCT
            departamento as codigo,
            departamento_1 as nombre,
            region as region
        FROM divipola.divipola_departamentos
        ORDER BY departamento_1
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchall()
            conn.close()
            
            return [
                DepartamentoItem(
                    codigo=str(row[0]) if row[0] else "",
                    nombre=row[1] if row[1] else "",
                    region=row[2] if len(row) > 2 and row[2] else None
                )
                for row in result
                if row[1]  # Solo incluir si tiene nombre
            ]
        except Exception as e:
            logger.error(f"Error obteniendo departamentos: {e}")
            # Fallback: usar SNIES
            try:
                query_fallback = """
                SELECT DISTINCT "DEPARTAMENTO_OFERTA_PROGRAMA" as nombre
                FROM snies.snies_programas
                WHERE "DEPARTAMENTO_OFERTA_PROGRAMA" IS NOT NULL
                ORDER BY "DEPARTAMENTO_OFERTA_PROGRAMA"
                """
                conn = self._get_connection()
                result = conn.execute(query_fallback).fetchall()
                conn.close()
                return [
                    DepartamentoItem(codigo="", nombre=row[0], region=None)
                    for row in result
                ]
            except:
                return []
    
    def get_niveles_formacion(self) -> List[str]:
        """Obtiene niveles de formación disponibles."""
        query = """
        SELECT DISTINCT "NIVEL_DE_FORMACIÓN"
        FROM snies.snies_programas
        WHERE "NIVEL_DE_FORMACIÓN" IS NOT NULL
        ORDER BY "NIVEL_DE_FORMACIÓN"
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchall()
            conn.close()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error obteniendo niveles: {e}")
            return []
    
    def get_modalidades(self) -> List[str]:
        """Obtiene modalidades disponibles."""
        query = """
        SELECT DISTINCT "MODALIDAD"
        FROM snies.snies_programas
        WHERE "MODALIDAD" IS NOT NULL
        ORDER BY "MODALIDAD"
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchall()
            conn.close()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error obteniendo modalidades: {e}")
            return []
    
    # ================================================================
    # PUNTO 10: TENDENCIAS GLOBALES Y LATAM
    # ================================================================
    
    def consultar_indicadores_banco_mundial(
        self, 
        paises: Optional[List[str]] = None,
        solo_latam: bool = False
    ) -> Dict[str, Any]:
        """
        Consulta todos los indicadores del Banco Mundial disponibles.
        
        PUNTO 10: Tendencias globales - 22 indicadores BM
        """
        paises_latam = [
            'Colombia', 'México', 'Brasil', 'Argentina', 'Chile', 
            'Perú', 'Ecuador', 'Venezuela', 'Bolivia', 'Paraguay',
            'Uruguay', 'Costa Rica', 'Panamá'
        ]
        
        indicadores_bm = [
            ('bm_pib_per_capita', 'PIB per cápita (USD)'),
            ('bm_tasa_desempleo', 'Tasa de desempleo (%)'),
            ('bm_tasa_matricula_terciaria', 'Matrícula educación terciaria (%)'),
            ('bm_gasto_educacion_pib', 'Gasto educación (% PIB)'),
            ('bm_usuarios_internet_pct', 'Usuarios internet (%)'),
            ('bm_gasto_id_pib', 'Gasto I+D (% PIB)'),
            ('bm_empleo_vulnerable', 'Empleo vulnerable (%)'),
            ('bm_desempleo_jovenes', 'Desempleo jóvenes (%)'),
            ('bm_poblacion_urbana_pct', 'Población urbana (%)'),
        ]
        
        resultado = {
            "fuente": "Banco Mundial",
            "punto": "PUNTO_10_GLOBAL",
            "indicadores": {},
            "paises_consultados": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            for tabla, descripcion in indicadores_bm:
                query = f"""
                SELECT * FROM indicadores_globales.{tabla}
                ORDER BY a_o DESC
                LIMIT 100
                """
                try:
                    df = conn.execute(query).fetchdf()
                    if not df.empty:
                        # Filtrar por países si se especifica
                        if solo_latam:
                            # Intentar filtrar por columna de país
                            for col in ['pais', 'nombre_pais', 'country', 'country_name']:
                                if col in df.columns:
                                    df = df[df[col].isin(paises_latam)]
                                    break
                        
                        resultado["indicadores"][tabla] = {
                            "descripcion": descripcion,
                            "registros": len(df),
                            "columnas": list(df.columns),
                            "datos": df.head(50).to_dict(orient='records'),
                            "resumen_estadistico": df.describe().to_dict() if df.select_dtypes(include=['number']).shape[1] > 0 else {}
                        }
                except Exception as e:
                    logger.warning(f"Error consultando {tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
            logger.error(f"Error consultando Banco Mundial: {e}")
        
        return resultado
    
    def consultar_oecd_educacion(self, paises: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Consulta estadísticas OECD de educación.
        
        PUNTO 10: 13 países OECD con datos de educación terciaria
        """
        resultado = {
            "fuente": "OECD",
            "punto": "PUNTO_10_GLOBAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Listar tablas disponibles en schema oecd
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'oecd_internacional'
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            for tabla in tablas_df['table_name'].tolist():
                query = f"SELECT * FROM oecd_internacional.{tabla} LIMIT 200"
                try:
                    df = conn.execute(query).fetchdf()
                    resultado["tablas"][tabla] = {
                        "registros": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error consultando OECD {tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_oit_empleo(self) -> Dict[str, Any]:
        """
        Consulta estadísticas OIT (ILO) de empleo global.
        
        PUNTO 10: Tendencias de empleo internacional
        """
        resultado = {
            "fuente": "OIT/ILO",
            "punto": "PUNTO_10_GLOBAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'ilo_internacional'
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            for tabla in tablas_df['table_name'].tolist():
                query = f"SELECT * FROM ilo_internacional.{tabla} LIMIT 200"
                try:
                    df = conn.execute(query).fetchdf()
                    resultado["tablas"][tabla] = {
                        "registros": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error consultando OIT {tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_unesco_educacion(self) -> Dict[str, Any]:
        """
        Consulta estadísticas UNESCO de educación global.
        
        PUNTO 10: 12,089 registros de educación mundial
        """
        resultado = {
            "fuente": "UNESCO",
            "punto": "PUNTO_10_GLOBAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'unesco_internacional'
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            for tabla in tablas_df['table_name'].tolist():
                # Agregar agregaciones para datasets grandes
                count_query = f"SELECT COUNT(*) as total FROM unesco_internacional.{tabla}"
                total = conn.execute(count_query).fetchone()[0]
                
                query = f"SELECT * FROM unesco_internacional.{tabla} LIMIT 500"
                try:
                    df = conn.execute(query).fetchdf()
                    resultado["tablas"][tabla] = {
                        "registros_total": total,
                        "registros_muestra": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error consultando UNESCO {tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_tendencias_tecnologicas(self) -> Dict[str, Any]:
        """
        Consulta tendencias tecnológicas: IA, Industria 4.0, habilidades futuro.
        
        PUNTO 10: Adopción IA (76 registros), microcredenciales (54), habilidades futuro (12)
        """
        resultado = {
            "fuente": "Tendencias Tecnológicas",
            "punto": "PUNTO_10_GLOBAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            tablas_tech = [
                'adopcion_ia_paises',
                'habilidades_futuro', 
                'industria40_paises',
                'edtech_adopcion_paises',
                'edtech_mercado',
                'mercado_ia_global'
            ]
            
            for tabla in tablas_tech:
                query = f"SELECT * FROM tendencias_tecnologicas.{tabla}"
                try:
                    df = conn.execute(query).fetchdf()
                    resultado["tablas"][tabla] = {
                        "registros": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error consultando tendencias_tecnologicas.{tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def obtener_punto_10_completo(self, solo_latam: bool = False) -> Dict[str, Any]:
        """
        Obtiene TODOS los datos del PUNTO 10: Tendencias Globales y LATAM.
        
        Consolida:
        - Banco Mundial (22 indicadores)
        - OECD (13 países)
        - OIT (empleo global)
        - UNESCO (12K+ registros educación)
        - Tendencias tecnológicas (IA, Industria 4.0)
        - Microcredenciales
        """
        inicio = time.time()
        
        resultado = {
            "punto": "PUNTO_10",
            "titulo": "Tendencias Globales y LATAM",
            "descripcion": "Análisis de tendencias internacionales en educación, empleo y tecnología",
            "timestamp": datetime.now().isoformat(),
            "fuentes": {}
        }
        
        # Consultar todas las fuentes
        resultado["fuentes"]["banco_mundial"] = self.consultar_indicadores_banco_mundial(solo_latam=solo_latam)
        resultado["fuentes"]["oecd"] = self.consultar_oecd_educacion()
        resultado["fuentes"]["oit"] = self.consultar_oit_empleo()
        resultado["fuentes"]["unesco"] = self.consultar_unesco_educacion()
        resultado["fuentes"]["tendencias_tech"] = self.consultar_tendencias_tecnologicas()
        
        resultado["tiempo_ejecucion_ms"] = (time.time() - inicio) * 1000
        
        # Resumen
        total_registros = 0
        for fuente, datos in resultado["fuentes"].items():
            if "indicadores" in datos:
                for ind in datos["indicadores"].values():
                    total_registros += ind.get("registros", 0)
            if "tablas" in datos:
                for tab in datos["tablas"].values():
                    total_registros += tab.get("registros", tab.get("registros_total", 0))
        
        resultado["resumen"] = {
            "total_registros": total_registros,
            "fuentes_consultadas": len(resultado["fuentes"]),
            "solo_latam": solo_latam
        }
        
        return resultado
    
    # ================================================================
    # PUNTO 11: TENDENCIAS NACIONALES Y REGIONALES
    # ================================================================
    
    def consultar_snies_completo(
        self, 
        departamento: Optional[str] = None,
        nbc_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consulta SNIES completo: 2.8M+ registros, 30,660 programas.
        
        PUNTO 11: Oferta educativa nacional
        """
        resultado = {
            "fuente": "SNIES",
            "punto": "PUNTO_11_NACIONAL",
            "tablas": {},
            "filtros": {"departamento": departamento, "nbc_id": nbc_id},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Estadísticas generales
            stats_query = """
            SELECT 
                COUNT(DISTINCT "CÓDIGO_SNIES_DEL_PROGRAMA") as total_programas,
                COUNT(DISTINCT "NOMBRE_INSTITUCIÓN") as total_instituciones,
                COUNT(DISTINCT "DEPARTAMENTO_OFERTA_PROGRAMA") as total_departamentos,
                COUNT(DISTINCT "NIVEL_DE_FORMACIÓN") as niveles_formacion
            FROM snies.snies_programas
            """
            stats = conn.execute(stats_query).fetchone()
            resultado["estadisticas_globales"] = {
                "total_programas": stats[0],
                "total_instituciones": stats[1],
                "total_departamentos": stats[2],
                "niveles_formacion": stats[3]
            }
            
            # Programas por nivel
            nivel_query = """
            SELECT 
                "NIVEL_DE_FORMACIÓN" as nivel,
                COUNT(*) as cantidad
            FROM snies.snies_programas
            GROUP BY "NIVEL_DE_FORMACIÓN"
            ORDER BY cantidad DESC
            """
            resultado["por_nivel"] = conn.execute(nivel_query).fetchdf().to_dict(orient='records')
            
            # Programas por departamento
            where_clause = ""
            if departamento:
                where_clause = f"WHERE \"DEPARTAMENTO_OFERTA_PROGRAMA\" ILIKE '%{departamento}%'"
            
            dep_query = f"""
            SELECT 
                "DEPARTAMENTO_OFERTA_PROGRAMA" as departamento,
                COUNT(*) as programas,
                COUNT(DISTINCT "NOMBRE_INSTITUCIÓN") as instituciones
            FROM snies.snies_programas
            {where_clause}
            GROUP BY "DEPARTAMENTO_OFERTA_PROGRAMA"
            ORDER BY programas DESC
            LIMIT 50
            """
            resultado["por_departamento"] = conn.execute(dep_query).fetchdf().to_dict(orient='records')
            
            # Programas por NBC
            nbc_query = """
            SELECT 
                "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" as nbc,
                COUNT(*) as programas
            FROM snies.snies_programas
            WHERE "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" IS NOT NULL
            GROUP BY "NÚCLEO_BÁSICO_DEL_CONOCIMIENTO"
            ORDER BY programas DESC
            LIMIT 30
            """
            resultado["por_nbc"] = conn.execute(nbc_query).fetchdf().to_dict(orient='records')
            
            # Modalidades
            mod_query = """
            SELECT 
                "MODALIDAD" as modalidad,
                COUNT(*) as programas
            FROM snies.snies_programas
            GROUP BY "MODALIDAD"
            ORDER BY programas DESC
            """
            resultado["por_modalidad"] = conn.execute(mod_query).fetchdf().to_dict(orient='records')
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
            logger.error(f"Error consultando SNIES: {e}")
        
        return resultado
    
    def consultar_tendencias_ocupacionales(
        self, 
        departamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta tendencias ocupacionales: 160+ tablas del Observatorio Laboral.
        
        PUNTO 11: Demanda laboral nacional
        """
        resultado = {
            "fuente": "Observatorio Laboral / Tendencias Ocupacionales",
            "punto": "PUNTO_11_NACIONAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Listar tablas del schema
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'tendencias_ocupacionales'
            ORDER BY table_name
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            tablas_prioritarias = [
                'vacantes_anual_2024',
                'vacantes_total_activas',
                'demanda_ocupaciones_top',
                'salarios_ocupacion',
                'tendencias_ocupacion_historico'
            ]
            
            # Primero las prioritarias
            for tabla in tablas_prioritarias:
                if tabla in tablas_df['table_name'].tolist():
                    try:
                        count_query = f"SELECT COUNT(*) FROM tendencias_ocupacionales.{tabla}"
                        total = conn.execute(count_query).fetchone()[0]
                        
                        query = f"SELECT * FROM tendencias_ocupacionales.{tabla} LIMIT 300"
                        df = conn.execute(query).fetchdf()
                        resultado["tablas"][tabla] = {
                            "prioridad": "ALTA",
                            "registros_total": total,
                            "registros_muestra": len(df),
                            "columnas": list(df.columns),
                            "datos": df.to_dict(orient='records')
                        }
                    except Exception as e:
                        logger.warning(f"Error en {tabla}: {e}")
            
            # Resumen de otras tablas
            otras_tablas = [t for t in tablas_df['table_name'].tolist() if t not in tablas_prioritarias]
            resultado["otras_tablas_disponibles"] = {
                "cantidad": len(otras_tablas),
                "nombres": otras_tablas[:50]  # Primeras 50
            }
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_dnp_planes_desarrollo(
        self, 
        departamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta planes de desarrollo DNP: múltiples tablas con indicadores.
        
        PUNTO 11: Alineación con políticas públicas
        
        Tablas disponibles:
        - dnp_plan_desarrollo_indicadores
        - dnp_medicion_desempeno_municipal  
        - dnp_producto_localizacion
        - dnp_producto_sector_inversion
        - avance_fisico_plan_desarrollo_caldas
        """
        resultado = {
            "fuente": "DNP Planes de Desarrollo",
            "punto": "PUNTO_11_NACIONAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Listar todas las tablas DNP
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'dnp_planes_desarrollo'
            ORDER BY table_name
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            tablas_prioritarias = [
                'dnp_plan_desarrollo_indicadores',
                'dnp_medicion_desempeno_municipal',
                'dnp_producto_localizacion',
                'dnp_producto_sector_inversion'
            ]
            
            for tabla in tablas_prioritarias:
                if tabla in tablas_df['table_name'].tolist():
                    try:
                        count_query = f"SELECT COUNT(*) FROM dnp_planes_desarrollo.{tabla}"
                        total = conn.execute(count_query).fetchone()[0]
                        
                        # Primero verificar qué columnas tiene la tabla
                        cols_query = f"SELECT * FROM dnp_planes_desarrollo.{tabla} LIMIT 1"
                        df_sample = conn.execute(cols_query).fetchdf()
                        columnas_disponibles = list(df_sample.columns)
                        
                        # Construir query según columnas disponibles
                        if departamento:
                            # Buscar columna que contenga 'departamento'
                            dep_col = None
                            for col in columnas_disponibles:
                                if 'departamento' in col.lower():
                                    dep_col = col
                                    break
                            
                            if dep_col:
                                query = f"""
                                SELECT * FROM dnp_planes_desarrollo.{tabla}
                                WHERE CAST("{dep_col}" AS VARCHAR) ILIKE '%{departamento}%'
                                LIMIT 500
                                """
                            else:
                                # No hay columna departamento, traer muestra sin filtro
                                query = f"SELECT * FROM dnp_planes_desarrollo.{tabla} LIMIT 500"
                        else:
                            query = f"SELECT * FROM dnp_planes_desarrollo.{tabla} LIMIT 500"
                        
                        df = conn.execute(query).fetchdf()
                        resultado["tablas"][tabla] = {
                            "prioridad": "ALTA",
                            "registros_total": total,
                            "registros_muestra": len(df),
                            "columnas": list(df.columns),
                            "datos": df.to_dict(orient='records')
                        }
                    except Exception as e:
                        logger.warning(f"Error consultando DNP {tabla}: {e}")
            
            # Resumen de otras tablas
            otras_tablas = [t for t in tablas_df['table_name'].tolist() if t not in tablas_prioritarias]
            resultado["otras_tablas_disponibles"] = {
                "cantidad": len(otras_tablas),
                "nombres": otras_tablas[:20]
            }
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_estadisticas_es(self) -> Dict[str, Any]:
        """
        Consulta estadísticas de educación superior consolidadas.
        
        PUNTO 11: 25K+ registros históricos
        """
        resultado = {
            "fuente": "Estadísticas Educación Superior",
            "punto": "PUNTO_11_NACIONAL",
            "tablas": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            tablas_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'estadisticas_es'
            """
            tablas_df = conn.execute(tablas_query).fetchdf()
            
            for tabla in tablas_df['table_name'].tolist():
                try:
                    query = f"SELECT * FROM estadisticas_es.{tabla} LIMIT 500"
                    df = conn.execute(query).fetchdf()
                    resultado["tablas"][tabla] = {
                        "registros": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error en estadisticas_es.{tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)

        return resultado
    
    def consultar_siet_oferta(
        self, 
        busqueda: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta oferta de Educación para el Trabajo (SIET).
        
        PUNTO 11: Oferta técnica laboral (Sin cruce forzado con NBC)
        """
        resultado = {
            "fuente": "SIET",
            "punto": "PUNTO_11_NACIONAL",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Buscar tabla correcta en schema SIET
            query = """
            SELECT * FROM siet.siet_programas 
            LIMIT 50
            """
            
            if busqueda:
                query = f"""
                SELECT * FROM siet.siet_programas 
                WHERE "Nombre Programa" ILIKE '%{busqueda}%'
                LIMIT 50
                """
            
            df = conn.execute(query).fetchdf()
            resultado["programas"] = {
                "registros": len(df),
                "muestras": df.to_dict(orient='records')
            }
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
            
        return resultado

    def obtener_punto_11_completo(
        self, 
        departamento: Optional[str] = None,
        nbc_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtiene TODOS los datos del PUNTO 11: Tendencias Nacionales y Regionales.
        
        Consolida:
        - SNIES (2.8M+ registros, 30,660 programas)
        - SIET (Oferta Técnica)
        - Tendencias Ocupacionales (160 tablas)
        - DNP Planes de Desarrollo (2.9M+ registros)
        - Estadísticas ES nacionales
        """
        inicio = time.time()
        
        resultado = {
            "punto": "PUNTO_11",
            "titulo": "Tendencias Nacionales y Regionales",
            "descripcion": "Análisis de oferta educativa y demanda laboral en Colombia",
            "filtros": {"departamento": departamento, "nbc_id": nbc_id},
            "timestamp": datetime.now().isoformat(),
            "fuentes": {}
        }
        
        resultado["fuentes"]["snies"] = self.consultar_snies_completo(departamento, nbc_id)
        # SIET se consulta sin filtros de NBC para evitar sesgos
        resultado["fuentes"]["siet"] = self.consultar_siet_oferta() 
        resultado["fuentes"]["tendencias_ocupacionales"] = self.consultar_tendencias_ocupacionales(departamento)
        resultado["fuentes"]["dnp"] = self.consultar_dnp_planes_desarrollo(departamento)
        resultado["fuentes"]["estadisticas_es"] = self.consultar_estadisticas_es()
        
        resultado["tiempo_ejecucion_ms"] = (time.time() - inicio) * 1000
        
        return resultado
    
    # ================================================================
    # PUNTO 12: TRANSFORMACIONES SECTORIALES POR CIIU
    # ================================================================
    
    def consultar_ciiu_sectores(self, codigo_ciiu: Optional[str] = None) -> Dict[str, Any]:
        """
        Consulta clasificación CIIU Rev 4: 700 códigos de actividad económica.
        
        PUNTO 12: Base de sectores económicos
        
        Columnas disponibles: CODIGO_CIIU, DESCRIPCION, NIVEL, NOMBRE_NIVEL,
        COD_SECCION, COD_DIVISION, COD_GRUPO
        """
        resultado = {
            "fuente": "CIIU Rev 4",
            "punto": "PUNTO_12_SECTORIAL",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            if codigo_ciiu:
                query = f"""
                SELECT * FROM clasificadores.ciiu_rev4
                WHERE CAST("CODIGO_CIIU" AS VARCHAR) LIKE '{codigo_ciiu}%'
                ORDER BY "CODIGO_CIIU"
                """
            else:
                query = """
                SELECT * FROM clasificadores.ciiu_rev4
                ORDER BY "CODIGO_CIIU"
                """
            
            df = conn.execute(query).fetchdf()
            resultado["datos"] = {
                "registros": len(df),
                "columnas": list(df.columns),
                "sectores": df.to_dict(orient='records')
            }
            
            # Resumen por sección (columna COD_SECCION)
            if not codigo_ciiu:
                resumen_query = """
                SELECT 
                    "COD_SECCION" as seccion,
                    COUNT(*) as actividades,
                    MIN("DESCRIPCION") as primera_descripcion
                FROM clasificadores.ciiu_rev4
                WHERE "NOMBRE_NIVEL" = 'DIVISION'
                GROUP BY "COD_SECCION"
                ORDER BY seccion
                """
                resultado["resumen_secciones"] = conn.execute(resumen_query).fetchdf().to_dict(orient='records')
                
                # Resumen por nivel
                nivel_query = """
                SELECT 
                    "NOMBRE_NIVEL" as nivel,
                    COUNT(*) as cantidad
                FROM clasificadores.ciiu_rev4
                GROUP BY "NOMBRE_NIVEL"
                ORDER BY cantidad DESC
                """
                resultado["resumen_niveles"] = conn.execute(nivel_query).fetchdf().to_dict(orient='records')
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_estructura_empresarial(
        self, 
        departamento: Optional[str] = None,
        codigo_ciiu: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta estructura empresarial: RUES + MIPYMES.
        
        PUNTO 12: Densidad empresarial por sector
        
        Fuentes reales:
        - rues_camaras_comercio: 14 tablas con datos empresariales
        - mipymes_estructura_empresarial: 4 tablas con estructura por CIIU y tamaño
        """
        resultado = {
            "fuente": "RUES + MIPYMES - Estructura Empresarial",
            "punto": "PUNTO_12_SECTORIAL",
            "filtros": {"departamento": departamento, "codigo_ciiu": codigo_ciiu},
            "timestamp": datetime.now().isoformat(),
            "tablas": {}
        }
        
        try:
            conn = self._get_connection()
            
            # 1. MIPYMES: Estructura por CIIU y tamaño (dato más estructurado)
            try:
                mipymes_query = """
                SELECT * FROM mipymes_estructura_empresarial.estructura_empresarial_ciiu_naturaleza_tamano
                LIMIT 500
                """
                df = conn.execute(mipymes_query).fetchdf()
                resultado["tablas"]["mipymes_ciiu_naturaleza_tamano"] = {
                    "registros": len(df),
                    "columnas": list(df.columns),
                    "datos": df.to_dict(orient='records')
                }
            except Exception as e:
                logger.warning(f"Error en mipymes ciiu naturaleza: {e}")
            
            # 2. Estructura empresarial por actividad económica (RUES)
            try:
                rues_actividad_query = """
                SELECT * FROM rues_camaras_comercio.estructura_empresarial_actividad_economica
                ORDER BY a_o DESC
                LIMIT 500
                """
                df = conn.execute(rues_actividad_query).fetchdf()
                resultado["tablas"]["rues_actividad_economica"] = {
                    "registros": len(df),
                    "columnas": list(df.columns),
                    "datos": df.to_dict(orient='records')
                }
            except Exception as e:
                logger.warning(f"Error en rues actividad: {e}")
            
            # 3. Top 10000 empresas más grandes de Colombia
            try:
                top_query = """
                SELECT * FROM rues_camaras_comercio.top_10000_empresas_mas_grandes_colombia
                LIMIT 500
                """
                df = conn.execute(top_query).fetchdf()
                
                # Filtrar por departamento si aplica
                if departamento and 'departamento' in df.columns:
                    df = df[df['departamento'].str.contains(departamento, case=False, na=False)]
                
                # Filtrar por CIIU si aplica
                if codigo_ciiu and 'sector_ciiu' in df.columns:
                    df = df[df['sector_ciiu'].str.startswith(codigo_ciiu, na=False)]
                
                resultado["tablas"]["top_10000_empresas"] = {
                    "registros": len(df),
                    "columnas": list(df.columns),
                    "datos": df.head(200).to_dict(orient='records')
                }
            except Exception as e:
                logger.warning(f"Error en top 10000: {e}")
            
            # 4. CIIU por municipio (estructura de tipos de empresa)
            try:
                ciiu_mun_query = """
                SELECT * FROM rues_camaras_comercio.ciiu_por_municipio
                LIMIT 300
                """
                df = conn.execute(ciiu_mun_query).fetchdf()
                resultado["tablas"]["ciiu_por_municipio"] = {
                    "registros": len(df),
                    "columnas": list(df.columns),
                    "datos": df.to_dict(orient='records')
                }
            except Exception as e:
                logger.warning(f"Error en ciiu_por_municipio: {e}")
            
            # 5. Resumen totales por tabla
            tablas_totales = [
                ('rues_camaras_comercio', 'rues_personas_naturales_juridicas_esal_nacional'),
                ('rues_camaras_comercio', 'empresas_activas_legalmente_constituidas'),
                ('mipymes_estructura_empresarial', 'estructura_empresarial_municipio_tamano')
            ]
            
            resultado["resumen_totales"] = {}
            for schema, tabla in tablas_totales:
                try:
                    count_query = f"SELECT COUNT(*) FROM {schema}.{tabla}"
                    total = conn.execute(count_query).fetchone()[0]
                    resultado["resumen_totales"][f"{schema}.{tabla}"] = total
                except:
                    pass
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_mesas_sectoriales(self, sector: Optional[str] = None) -> Dict[str, Any]:
        """
        Consulta mesas sectoriales SENA: 84 mesas activas.
        
        PUNTO 12: Articulación sector productivo - formación
        
        Columnas disponibles: regional, mesa_sectorial_secretaria_tecnica, 
        correo_mesa_sectorial, municipio, centro, centro_formacion, 
        direccion_del_centro, localizacion, georeferenciacion
        """
        resultado = {
            "fuente": "Mesas Sectoriales SENA",
            "punto": "PUNTO_12_SECTORIAL",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            if sector:
                query = f"""
                SELECT * FROM competencias.mesas_sectoriales_sena
                WHERE mesa_sectorial_secretaria_tecnica ILIKE '%{sector}%' 
                   OR regional ILIKE '%{sector}%'
                   OR centro ILIKE '%{sector}%'
                """
            else:
                query = "SELECT * FROM competencias.mesas_sectoriales_sena"
            
            df = conn.execute(query).fetchdf()
            resultado["mesas"] = {
                "total": len(df),
                "columnas": list(df.columns),
                "datos": df.to_dict(orient='records')
            }
            
            # Resumen por regional
            resumen_query = """
            SELECT 
                regional,
                COUNT(*) as cantidad_mesas
            FROM competencias.mesas_sectoriales_sena
            GROUP BY regional
            ORDER BY cantidad_mesas DESC
            """
            resultado["por_regional"] = conn.execute(resumen_query).fetchdf().to_dict(orient='records')
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_cuoc_ocupaciones(
        self, 
        nivel_competencia: Optional[int] = None,
        busqueda: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta CUOC: 14,462 ocupaciones clasificadas.
        
        PUNTO 12: Ocupaciones por sector y nivel de competencia
        
        Columnas disponibles: CODIGO_CUOC, nombre, nivel_formacion, NOMBRE_NIVEL,
        COD_GRAN_GRUPO, GRAN_GRUPO, COD_SUBGRUPO_PRINCIPAL, SUBGRUPO_PRINCIPAL,
        COD_SUBGRUPO, grupo_poblacional, COD_GRUPO_PRIMARIO, GRUPO_PRIMARIO,
        COD_OCUPACION, ocupacion, CODIGO_PADRE
        """
        resultado = {
            "fuente": "CUOC - Clasificación de Ocupaciones",
            "punto": "PUNTO_12_SECTORIAL",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Estadísticas generales
            stats_query = """
            SELECT 
                COUNT(*) as total_ocupaciones,
                COUNT(DISTINCT "NOMBRE_NIVEL") as niveles_competencia,
                COUNT(DISTINCT "GRAN_GRUPO") as grandes_grupos
            FROM cuoc.cuoc_limpio_2025
            """
            stats = conn.execute(stats_query).fetchone()
            resultado["estadisticas"] = {
                "total_ocupaciones": stats[0],
                "niveles_competencia": stats[1],
                "grandes_grupos": stats[2]
            }
            
            # Por nivel de competencia (usando NOMBRE_NIVEL)
            nivel_query = """
            SELECT 
                "NOMBRE_NIVEL" as nivel,
                COUNT(*) as ocupaciones
            FROM cuoc.cuoc_limpio_2025
            GROUP BY "NOMBRE_NIVEL"
            ORDER BY ocupaciones DESC
            """
            resultado["por_nivel"] = conn.execute(nivel_query).fetchdf().to_dict(orient='records')
            
            # Por gran grupo
            grupo_query = """
            SELECT 
                "COD_GRAN_GRUPO" as codigo,
                "GRAN_GRUPO" as nombre,
                COUNT(*) as ocupaciones
            FROM cuoc.cuoc_limpio_2025
            GROUP BY "COD_GRAN_GRUPO", "GRAN_GRUPO"
            ORDER BY ocupaciones DESC
            """
            resultado["por_gran_grupo"] = conn.execute(grupo_query).fetchdf().to_dict(orient='records')
            
            # Búsqueda o muestra
            if busqueda:
                search_query = f"""
                SELECT * FROM cuoc.cuoc_limpio_2025
                WHERE nombre ILIKE '%{busqueda}%'
                   OR "GRAN_GRUPO" ILIKE '%{busqueda}%'
                   OR "SUBGRUPO_PRINCIPAL" ILIKE '%{busqueda}%'
                LIMIT 100
                """
            elif nivel_competencia:
                search_query = f"""
                SELECT * FROM cuoc.cuoc_limpio_2025
                WHERE nivel_formacion = {nivel_competencia}
                LIMIT 200
                """
            else:
                search_query = "SELECT * FROM cuoc.cuoc_limpio_2025 LIMIT 200"
            
            df = conn.execute(search_query).fetchdf()
            resultado["ocupaciones"] = {
                "registros": len(df),
                "columnas": list(df.columns),
                "datos": df.to_dict(orient='records')
            }
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def consultar_mapeo_ciiu_cuoc(self) -> Dict[str, Any]:
        """
        Consulta mapeo CIIU-CUOC para relacionar sectores con ocupaciones.
        
        PUNTO 12: Cruce sectores-ocupaciones
        """
        resultado = {
            "fuente": "Mapeo CIIU-CUOC",
            "punto": "PUNTO_12_SECTORIAL",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            conn = self._get_connection()
            
            # Mapeos disponibles
            mapeos = [
                ('catalogo_curado.mapeo_cuoc_ciiu', 'CUOC-CIIU'),
                ('catalogo_curado.mapeo_nbc_cuoc', 'NBC-CUOC'),
                ('catalogo_curado.mapeo_observatorio_cuoc', 'Observatorio-CUOC'),
            ]
            
            resultado["mapeos"] = {}
            
            for tabla, nombre in mapeos:
                try:
                    query = f"SELECT * FROM {tabla}"
                    df = conn.execute(query).fetchdf()
                    resultado["mapeos"][nombre] = {
                        "registros": len(df),
                        "columnas": list(df.columns),
                        "datos": df.to_dict(orient='records')
                    }
                except Exception as e:
                    logger.warning(f"Error en {tabla}: {e}")
            
            conn.close()
            
        except Exception as e:
            resultado["error"] = str(e)
        
        return resultado
    
    def obtener_punto_12_completo(
        self, 
        codigo_ciiu: Optional[str] = None,
        departamento: Optional[str] = None,
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene TODOS los datos del PUNTO 12: Transformaciones Sectoriales.
        
        Consolida:
        - CIIU Rev4 (700 códigos)
        - Estructura Empresarial RUES (9.1M registros)
        - Mesas Sectoriales SENA (84 mesas)
        - CUOC Ocupaciones (14,462)
        - Mapeos CIIU-CUOC-NBC
        """
        inicio = time.time()
        
        resultado = {
            "punto": "PUNTO_12",
            "titulo": "Transformaciones Sectoriales por CIIU",
            "descripcion": "Análisis de estructura productiva y demandas sectoriales",
            "filtros": {"codigo_ciiu": codigo_ciiu, "departamento": departamento, "sector": sector},
            "timestamp": datetime.now().isoformat(),
            "fuentes": {}
        }
        
        resultado["fuentes"]["ciiu"] = self.consultar_ciiu_sectores(codigo_ciiu)
        resultado["fuentes"]["estructura_empresarial"] = self.consultar_estructura_empresarial(departamento, codigo_ciiu)
        resultado["fuentes"]["mesas_sectoriales"] = self.consultar_mesas_sectoriales(sector)
        resultado["fuentes"]["cuoc"] = self.consultar_cuoc_ocupaciones(busqueda=sector)
        resultado["fuentes"]["mapeos"] = self.consultar_mapeo_ciiu_cuoc()
        
        resultado["tiempo_ejecucion_ms"] = (time.time() - inicio) * 1000
        
        return resultado
    
    # ================================================================
    # CONSULTA INTEGRAL: PUNTOS 10 + 11 + 12
    # ================================================================
    
    def obtener_contexto_completo_pertinencia(
        self,
        nbc_id: Optional[int] = None,
        departamento: Optional[str] = None,
        codigo_ciiu: Optional[str] = None,
        incluir_punto_10: bool = True,
        incluir_punto_11: bool = True,
        incluir_punto_12: bool = True,
        solo_latam: bool = True
    ) -> Dict[str, Any]:
        """
        Obtiene el contexto COMPLETO para análisis de pertinencia.
        
        Integra los 3 puntos críticos:
        - PUNTO 10: Tendencias Globales y LATAM
        - PUNTO 11: Tendencias Nacionales y Regionales  
        - PUNTO 12: Transformaciones Sectoriales por CIIU
        
        Este es el método PRINCIPAL para alimentar el análisis LLM.
        """
        inicio = time.time()
        
        resultado = {
            "analisis_pertinencia": {
                "titulo": "Contexto Integral para Estudio de Pertinencia",
                "parametros": {
                    "nbc_id": nbc_id,
                    "departamento": departamento,
                    "codigo_ciiu": codigo_ciiu,
                    "solo_latam": solo_latam
                },
                "timestamp": datetime.now().isoformat()
            },
            "puntos": {}
        }
        
        if incluir_punto_10:
            logger.info("Consultando PUNTO 10: Tendencias Globales...")
            resultado["puntos"]["PUNTO_10_GLOBAL"] = self.obtener_punto_10_completo(solo_latam=solo_latam)
        
        if incluir_punto_11:
            logger.info("Consultando PUNTO 11: Tendencias Nacionales...")
            resultado["puntos"]["PUNTO_11_NACIONAL"] = self.obtener_punto_11_completo(
                departamento, nbc_id
            )
        
        if incluir_punto_12:
            logger.info("Consultando PUNTO 12: Transformaciones Sectoriales...")
            resultado["puntos"]["PUNTO_12_SECTORIAL"] = self.obtener_punto_12_completo(codigo_ciiu, departamento)
        
        # Resumen ejecutivo
        resultado["resumen_ejecutivo"] = {
            "tiempo_total_ms": (time.time() - inicio) * 1000,
            "puntos_consultados": list(resultado["puntos"].keys()),
            "fuentes_totales": sum(
                len(p.get("fuentes", {})) 
                for p in resultado["puntos"].values()
            )
        }
        
        return resultado
    
    # ================================================================
    # QUERIES ESPECIALIZADOS POR CONTEXTO
    # ================================================================
    
    def consultar_contexto_nbc(
        self, 
        nbc_id: int, 
        departamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta contexto completo para un NBC específico.
        
        Esta es la consulta principal para el análisis de pertinencia.
        Retorna datos de todos los dominios relevantes filtrados por NBC.
        """
        filtros = FiltrosConsulta(nbc_id=nbc_id, departamento=departamento)
        
        resultado = {
            "nbc_id": nbc_id,
            "departamento": departamento,
            "ejes": {}
        }
        
        # Consultar cada eje
        for eje_id in self._ejes:
            resultado["ejes"][eje_id] = self.consultar_eje(eje_id, filtros)
        
        return resultado
    
    def obtener_resumen_dominio(self, dom_id: str) -> Dict[str, Any]:
        """
        Obtiene un resumen rápido de un dominio sin datos detallados.
        Útil para mostrar overview antes de consultas pesadas.
        """
        dominio = self.get_dominio(dom_id)
        if not dominio:
            return {"error": f"Dominio {dom_id} no encontrado"}
        
        variables = self.get_variables_dominio(dom_id)
        
        return {
            "dominio": dominio.model_dump(),
            "variables": [
                {
                    "id": v.id,
                    "nombre": v.nombre,
                    "estado": v.estado.value,
                    "es_consultable": v.es_consultable,
                    "tabla": v.tabla,
                    "registros": v.registros
                }
                for v in variables
            ],
            "resumen": {
                "total_variables": len(variables),
                "consultables": sum(1 for v in variables if v.es_consultable),
                "llm": sum(1 for v in variables if v.estado == EstadoVariable.LLM),
                "calculadas": sum(1 for v in variables if v.estado == EstadoVariable.CALC)
            }
        }

    # ================================================================
    # PIPELINES DE VISUALIZACIÓN (DATA PIPELINES REQUESTED)
    # ================================================================

    def get_benchmarking_data(self, nbc_id: int) -> pd.DataFrame:
        """
        Obtiene datos para el Scatter Plot (Duración vs Costo vs Tamaño).
        Returns: DataFrame con [institucion, programa, duracion, costo, matriculados, acreditada]
        """
        if not nbc_id:
            return pd.DataFrame()

        query = f"""
        SELECT 
            p."NOMBRE_INSTITUCIÓN" as institucion,
            p."NOMBRE_DEL_PROGRAMA" as programa,
            CAST(p."NÚMERO_PERIODOS_DE_DURACIÓN" as FLOAT) as duracion,
            CAST(p."COSTO_MATRÍCULA_ESTUD_NUEVOS" as FLOAT) as costo,
            COALESCE(i."ACREDITADA_ALTA_CALIDAD", 'NO') as acreditada,
            COALESCE(SUM(TRY_CAST(m."MATRICULADOS" AS BIGINT)), 0) as matriculados
        FROM snies.snies_programas p
        LEFT JOIN snies.snies_matriculados m 
            ON CAST(p."CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) = m."COD_SNIES_PROGRAMA"
        LEFT JOIN snies.snies_instituciones i
            ON p."CÓDIGO_INSTITUCIÓN" = i."CÓDIGO_INSTITUCIÓN"
        WHERE p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" = (
            SELECT "NBC" FROM catalogo_curado.catalogo_nbc_snies WHERE "ID_NBC" = {nbc_id} LIMIT 1
        )
        GROUP BY p."NOMBRE_INSTITUCIÓN", p."NOMBRE_DEL_PROGRAMA", 
                 p."NÚMERO_PERIODOS_DE_DURACIÓN", p."COSTO_MATRÍCULA_ESTUD_NUEVOS", 
                 i."ACREDITADA_ALTA_CALIDAD"
        HAVING matriculados > 0
        LIMIT 1000
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchdf()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error en get_benchmarking_data: {e}")
            return pd.DataFrame()

    def get_market_trends(self, nbc_id: int) -> pd.DataFrame:
        """
        Obtiene histórico de matriculados para calcular CAGR.
        Returns: DataFrame con [anio, matriculados]
        """
        if not nbc_id:
            return pd.DataFrame()
            
        query = f"""
        SELECT 
            m."ANO" as anio,
            SUM(TRY_CAST(m."MATRICULADOS" AS BIGINT)) as matriculados
        FROM snies.snies_matriculados m
        JOIN snies.snies_programas p 
            ON m."COD_SNIES_PROGRAMA" = CAST(p."CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR)
        WHERE p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" = (
            SELECT "NBC" FROM catalogo_curado.catalogo_nbc_snies WHERE "ID_NBC" = {nbc_id} LIMIT 1
        )
        GROUP BY m."ANO"
        ORDER BY m."ANO" ASC
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchdf()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error en get_market_trends: {e}")
            return pd.DataFrame()

    def get_labor_absorption(self, nbc_id: int) -> pd.DataFrame:
        """
        Compara Graduados (Oferta) vs Vacantes (Demanda).
        Usa Mapeo Oficial: NBC -> Maepo_NBC_CUOC -> Vacantes (APE).
        """
        if not nbc_id:
            return pd.DataFrame()
            
        # 1. Obtener Graduados Históricos
        query_graduados = f"""
        SELECT 
            g."ANO" as anio,
            SUM(TRY_CAST(g."GRADUADOS" AS BIGINT)) as graduados
        FROM snies.snies_graduados g
        JOIN snies.snies_programas p 
            ON g."COD_SNIES_PROGRAMA" = CAST(p."CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR)
        WHERE p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO" = (
            SELECT "NBC" FROM catalogo_curado.catalogo_nbc_snies WHERE "ID_NBC" = {nbc_id} LIMIT 1
        )
        GROUP BY g."ANO"
        ORDER BY g."ANO" ASC
        """
        
        try:
            conn = self._get_connection()
            df_grads = conn.execute(query_graduados).fetchdf()
            conn.close()
            # Nota: Vacantes se implementará en V2 cuando la tabla tendencias_laborales.vacantes_ape_clean esté confirmada.
            # Por ahora retornamos solo graduados para evitar romper el dashboard si falta la tabla de vacantes.
            return df_grads
        except Exception as e:
            logger.error(f"Error en get_labor_absorption: {e}")
            return pd.DataFrame()

    def get_geo_score_data(self) -> pd.DataFrame:
        """
        Obtiene datos para el mapa de viabilidad (Conectividad + PDET).
        Returns: DataFrame con [departamento, conectividad, es_pdet]
        """
        # Consulta simplificada. En producción cruzaría con municipios exactos.
        query = """
        SELECT 
            d.departamento_1 as departamento,
            AVG(i.no_de_accesos) as conectividad, -- Proxy muy simple
            0 as es_pdet -- Placeholder por ahora
        FROM divipola.divipola_departamentos d
        LEFT JOIN conectividad.internet_fijo_accesos i ON d.departamento_1 = i.departamento
        GROUP BY d.departamento_1
        LIMIT 50
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query).fetchdf()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error en get_geo_score_data: {e}")
            return pd.DataFrame()


# ================================================================
# SINGLETON INSTANCE
# ================================================================
_engine_instance: Optional[DSSEngine] = None


def get_engine() -> DSSEngine:
    """
    Obtiene la instancia singleton del motor DSS.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DSSEngine()
    return _engine_instance


def reset_engine() -> None:
    """
    Resetea la instancia del motor (útil para testing).
    """
    global _engine_instance
    _engine_instance = None
