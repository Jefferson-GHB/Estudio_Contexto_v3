"""
Sistema RAG (Retrieval-Augmented Generation) para enriquecer análisis educativos
con datos adicionales de deserción, SABER, tránsito, etc.

Arquitectura:
1. Index Builder: Pre-procesa y crea índices de datos clave
2. SQL Retriever: Ejecuta queries dinámicas según contexto
3. Semantic Search: Búsqueda vectorial para info no estructurada
4. Context Augmenter: Enriquece el prompt del LLM con datos relevantes
"""

import duckdb
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
import hashlib

class EducacionRAG:
    """Sistema RAG para análisis educativo con datos de deserción, SABER, tránsito"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._conectar()
        
        # Cache de consultas frecuentes
        self.cache = {}
        
        # Índice de qué datos están disponibles
        self.data_inventory = self._build_inventory()
    
    def _conectar(self):
        """Conectar a la base de datos"""
        try:
            self.conn = duckdb.connect(self.db_path, read_only=True)
        except Exception as e:
            print(f"Error conectando a BD: {e}")
            raise
    
    def _build_inventory(self) -> Dict[str, List[str]]:
        """Construir inventario de datos disponibles para retrieval"""
        inventory = {
            'desercion': [],
            'saber': [],
            'transito': [],
            'competencias': [],
            'salarios': [],
            'vacantes': []
        }
        
        try:
            # Listar todas las tablas
            tables = self.conn.execute("""
                SELECT schema_name, table_name 
                FROM duckdb_tables()
            """).fetchall()
            
            for schema, table in tables:
                full_name = f"{schema}.{table}"
                
                if 'desercion' in table.lower():
                    inventory['desercion'].append(full_name)
                if 'saber' in table.lower() or 'icfes' in table.lower():
                    inventory['saber'].append(full_name)
                if 'transit' in table.lower() or 'tti' in table.lower() or 'tcb' in table.lower():
                    inventory['transito'].append(full_name)
                if 'competencia' in table.lower():
                    inventory['competencias'].append(full_name)
                if 'salario' in table.lower() or 'ingreso' in table.lower():
                    inventory['salarios'].append(full_name)
                if 'vacant' in table.lower():
                    inventory['vacantes'].append(full_name)
            
        except Exception as e:
            print(f"Error construyendo inventario: {e}")
        
        return inventory
    
    def get_desercion_data(self, nbc_codigo: str = None, departamento: str = None, 
                          nivel: str = None) -> Optional[Dict]:
        """
        Recuperar datos de deserción académica
        
        Args:
            nbc_codigo: Código NBC para filtrar
            departamento: Departamento para filtrar
            nivel: Nivel educativo (Pregrado, Posgrado, etc.)
        
        Returns:
            Dict con estadísticas de deserción o None
        """
        try:
            # Consultar tabla principal de deserción ES
            query = """
            SELECT 
                nivel_formacion,
                periodo,
                AVG(tasa_desercion_cohorte) as desercion_promedio,
                AVG(tasa_desercion_periodo) as desercion_periodo,
                COUNT(*) as programas_analizados
            FROM estadisticas_es.es_desercion_nivel
            WHERE 1=1
            """
            
            params = []
            
            if nivel:
                query += " AND nivel_formacion = ?"
                params.append(nivel)
            
            query += " GROUP BY nivel_formacion, periodo ORDER BY periodo DESC LIMIT 10"
            
            result = self.conn.execute(query, params if params else []).fetchdf()
            
            if result.empty:
                return None
            
            return {
                'disponible': True,
                'niveles': result['nivel_formacion'].unique().tolist(),
                'desercion_promedio': float(result['desercion_promedio'].mean()) if 'desercion_promedio' in result.columns else None,
                'ultimo_periodo': result['periodo'].max() if 'periodo' in result.columns else None,
                'programas_base': int(result['programas_analizados'].sum()) if 'programas_analizados' in result.columns else 0,
                'detalle': result.to_dict('records')[:5]  # Top 5 más recientes
            }
            
        except Exception as e:
            print(f"Error recuperando deserción: {e}")
            return None
    
    def get_saber_data(self, nbc_codigo: str = None, departamento: str = None,
                      ano: int = None) -> Optional[Dict]:
        """
        Recuperar datos de pruebas SABER 11 y SABER PRO
        
        Args:
            nbc_codigo: Código NBC para relacionar con programas
            departamento: Departamento para filtrar
            ano: Año de la prueba
        
        Returns:
            Dict con estadísticas de pruebas SABER
        """
        try:
            # Consultar SABER 11 (agregado)
            query_saber11 = """
            SELECT 
                COUNT(*) as estudiantes,
                AVG(punt_global) as puntaje_promedio_global,
                AVG(punt_matematicas) as puntaje_matematicas,
                AVG(punt_lectura_critica) as puntaje_lectura
            FROM men.resultados_nicos_saber_11
            WHERE 1=1
            """
            
            params11 = []
            
            if departamento:
                query_saber11 += " AND estu_depto_presentacion = ?"
                params11.append(departamento.upper())
            
            if ano:
                query_saber11 += " AND estu_ano = ?"
                params11.append(ano)
            
            saber11_result = self.conn.execute(query_saber11, params11 if params11 else []).fetchone()
            
            # Consultar SABER PRO (agregado)
            query_saberpro = """
            SELECT 
                COUNT(*) as estudiantes,
                AVG(mod_comuni_esc_desem) as comunicacion_escrita,
                AVG(mod_razona_cuantitat_desem) as razonamiento_cuantitativo,
                AVG(mod_lectura_crit_desem) as lectura_critica
            FROM men.resultados_nicos_saber_pro
            WHERE 1=1
            """
            
            paramspro = []
            
            if departamento:
                query_saberpro += " AND estu_depto_reside = ?"
                paramspro.append(departamento.upper())
            
            saberpro_result = self.conn.execute(query_saberpro, paramspro if paramspro else []).fetchone()
            
            return {
                'disponible': True,
                'saber_11': {
                    'estudiantes': int(saber11_result[0]) if saber11_result and saber11_result[0] else 0,
                    'puntaje_global': float(saber11_result[1]) if saber11_result and saber11_result[1] else None,
                    'puntaje_matematicas': float(saber11_result[2]) if saber11_result and saber11_result[2] else None,
                    'puntaje_lectura': float(saber11_result[3]) if saber11_result and saber11_result[3] else None
                },
                'saber_pro': {
                    'estudiantes': int(saberpro_result[0]) if saberpro_result and saberpro_result[0] else 0,
                    'comunicacion_escrita': float(saberpro_result[1]) if saberpro_result and saberpro_result[1] else None,
                    'razonamiento_cuantitativo': float(saberpro_result[2]) if saberpro_result and saberpro_result[2] else None,
                    'lectura_critica': float(saberpro_result[3]) if saberpro_result and saberpro_result[3] else None
                }
            }
            
        except Exception as e:
            print(f"Error recuperando SABER: {e}")
            return None
    
    def get_transito_data(self, departamento: str = None) -> Optional[Dict]:
        """
        Recuperar datos de tránsito inmediato (TCB/TTI)
        
        Args:
            departamento: Departamento para filtrar
        
        Returns:
            Dict con tasas de tránsito
        """
        try:
            # Tasa de Cobertura Bruta (TCB)
            query_tcb = f"""
            SELECT 
                AVG(tcb) as tcb_promedio,
                MIN(tcb) as tcb_min,
                MAX(tcb) as tcb_max
            FROM estadisticas_es.es_tcb_departamento
            WHERE 1=1
            {" AND departamento = ?" if departamento else ""}
            """
            
            tcb_result = self.conn.execute(query_tcb, [departamento] if departamento else []).fetchone()
            
            # Tasa de Tránsito Inmediato (TTI)
            query_tti = f"""
            SELECT 
                AVG(tti) as tti_promedio,
                MIN(tti) as tti_min,
                MAX(tti) as tti_max
            FROM estadisticas_es.es_tti_departamento
            WHERE 1=1
            {" AND departamento = ?" if departamento else ""}
            """
            
            tti_result = self.conn.execute(query_tti, [departamento] if departamento else []).fetchone()
            
            return {
                'disponible': True,
                'tcb': {
                    'promedio': float(tcb_result[0]) if tcb_result and tcb_result[0] else None,
                    'min': float(tcb_result[1]) if tcb_result and tcb_result[1] else None,
                    'max': float(tcb_result[2]) if tcb_result and tcb_result[2] else None
                },
                'tti': {
                    'promedio': float(tti_result[0]) if tti_result and tti_result[0] else None,
                    'min': float(tti_result[1]) if tti_result and tti_result[1] else None,
                    'max': float(tti_result[2]) if tti_result and tti_result[2] else None
                },
                'departamento': departamento or 'Nacional'
            }
            
        except Exception as e:
            print(f"Error recuperando tránsito: {e}")
            return None
    
    def augment_context(self, nbc_codigo: str, departamento: str, 
                       base_context: str, filtros_activos: dict = None) -> str:
        """
        Enriquecer el contexto base con datos adicionales recuperados vía RAG
        
        Args:
            nbc_codigo: Código NBC del programa
            departamento: Departamento para contextualizar
            base_context: Contexto original del sistema
            filtros_activos: Dict con todos los filtros aplicados por el usuario
        
        Returns:
            Contexto enriquecido con datos de RAG
        """
        # Recuperar datos adicionales
        desercion = self.get_desercion_data(nbc_codigo=nbc_codigo, departamento=departamento)
        saber = self.get_saber_data(nbc_codigo=nbc_codigo, departamento=departamento)
        transito = self.get_transito_data(departamento=departamento)
        
        # Construir sección adicional de contexto
        additional_context = "\n\n"
        additional_context += "="*80 + "\n"
        additional_context += "         DATOS ADICIONALES RECUPERADOS (Sistema RAG)\n"
        additional_context += "="*80 + "\n\n"
        
        # Deserción
        if desercion and desercion.get('disponible'):
            additional_context += "DESERCION ACADEMICA:\n"
            additional_context += f"- Tasa promedio de deserción: {desercion.get('desercion_promedio', 'N/A'):.1f}%\n"
            additional_context += f"- Último periodo analizado: {desercion.get('ultimo_periodo', 'N/A')}\n"
            additional_context += f"- Programas analizados: {desercion.get('programas_base', 0):,}\n"
            additional_context += f"- Niveles educativos con datos: {', '.join(desercion.get('niveles', []))}\n"
            additional_context += "  >> FUENTE: ES Deserción - MEN Colombia\n\n"
        
        # SABER
        if saber and saber.get('disponible'):
            s11 = saber.get('saber_11', {})
            spro = saber.get('saber_pro', {})
            
            additional_context += "RESULTADOS PRUEBAS SABER:\n"
            if s11.get('estudiantes', 0) > 0:
                additional_context += f"- SABER 11: {s11['estudiantes']:,} estudiantes evaluados\n"
                if s11.get('puntaje_global'):
                    additional_context += f"  * Puntaje global promedio: {s11['puntaje_global']:.1f}/500\n"
                if s11.get('puntaje_matematicas'):
                    additional_context += f"  * Matemáticas: {s11['puntaje_matematicas']:.1f}/100\n"
                if s11.get('puntaje_lectura'):
                    additional_context += f"  * Lectura crítica: {s11['puntaje_lectura']:.1f}/100\n"
            
            if spro.get('estudiantes', 0) > 0:
                additional_context += f"- SABER PRO: {spro['estudiantes']:,} estudiantes evaluados\n"
                if spro.get('razonamiento_cuantitativo'):
                    additional_context += f"  * Razonamiento cuantitativo: {spro['razonamiento_cuantitativo']:.1f}\n"
                if spro.get('lectura_critica'):
                    additional_context += f"  * Lectura crítica: {spro['lectura_critica']:.1f}\n"
            
            additional_context += "  >> FUENTE: ICFES - MEN Colombia (Resultados únicos)\n\n"
        
        # Tránsito
        if transito and transito.get('disponible'):
            tcb = transito.get('tcb', {})
            tti = transito.get('tti', {})
            
            additional_context += "TRANSITO INMEDIATO Y COBERTURA:\n"
            additional_context += f"- Contexto: {transito.get('departamento', 'Nacional')}\n"
            if tcb.get('promedio'):
                additional_context += f"- Tasa de Cobertura Bruta (TCB): {tcb['promedio']:.1f}%\n"
                additional_context += f"  * Rango: {tcb.get('min', 0):.1f}% - {tcb.get('max', 0):.1f}%\n"
            if tti.get('promedio'):
                additional_context += f"- Tasa de Tránsito Inmediato (TTI): {tti['promedio']:.1f}%\n"
                additional_context += f"  * Rango: {tti.get('min', 0):.1f}% - {tti.get('max', 0):.1f}%\n"
            additional_context += "  >> FUENTE: Estadísticas ES - MEN Colombia\n\n"
        
        additional_context += "="*80 + "\n"
        additional_context += "NOTA: Estos datos enriquecen el análisis con información de deserción,\n"
        additional_context += "calidad educativa (SABER) y tránsito del sistema. Úsalos para argumentar\n"
        additional_context += "sobre riesgos, oportunidades de mejora y benchmark de calidad.\n"
        additional_context += "="*80 + "\n"
        
        # Retornar contexto combinado
        return base_context + additional_context
    
    def close(self):
        """Cerrar conexión a la base de datos"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Destructor para asegurar cierre de conexión"""
        self.close()
