"""Construye contexto en markdown para analisis LLM a partir de datos del dashboard."""

import pandas as pd


def generar_contexto_analisis(nbc, depto, stats_snies, stats_siet, score_final, veredicto,
                               df_market=None, df_tendencia=None, df_graduados=None, 
                               desglose=None, desglose_siet=None, hhi_data=None, cagr_data=None,
                               df_vacantes=None, df_conocimientos=None, df_destrezas=None,
                               df_salarios=None, df_actividades=None, tipo_oferta_data=None,
                               filtros_activos=None, skills_bridge=None):
    """
    Genera contexto completo para el analisis LLM incorporando datos de SNIES,
    SIET, APE, CUOC, GEIH-DANE y filtros activos del usuario.
    """
    
    # Preparar datos de market share
    top_ies = ""
    if df_market is not None and not df_market.empty:
        top5 = df_market.head(5)
        top_ies = "\n".join([f"   - {row['institucion']}: {row['matriculados']:,} matriculados ({row['share']:.1f}%)" 
                            for _, row in top5.iterrows()])
    
    # Preparar tendencia historica
    tendencia_historica = ""
    if df_tendencia is not None and not df_tendencia.empty:
        tendencia_historica = "\n".join([f"   - {int(row['anio'])}: {int(row['matriculados']):,} matriculados" 
                                         for _, row in df_tendencia.iterrows()])
    
    # Preparar graduados historicos
    graduados_historico = ""
    if df_graduados is not None and not df_graduados.empty:
        graduados_historico = "\n".join([f"   - {int(row['anio'])}: {int(row['graduados']):,} graduados" 
                                         for _, row in df_graduados.tail(5).iterrows()])
    
    # Preparar desgloses SNIES
    desglose_modalidad = ""
    desglose_sector = ""
    desglose_nivel = ""
    desglose_caracter = ""
    if desglose and isinstance(desglose, dict):
        if 'modalidad' in desglose and not desglose['modalidad'].empty:
            desglose_modalidad = "\n".join([f"   - {row['categoria']}: {row['cantidad']} programas" 
                                           for _, row in desglose['modalidad'].iterrows()])
        if 'sector' in desglose and not desglose['sector'].empty:
            desglose_sector = "\n".join([f"   - {row['categoria']}: {row['cantidad']} programas" 
                                        for _, row in desglose['sector'].iterrows()])
        if 'nivel_formacion' in desglose and not desglose['nivel_formacion'].empty:
            desglose_nivel = "\n".join([f"   - {row['categoria']}: {row['cantidad']} programas" 
                                       for _, row in desglose['nivel_formacion'].iterrows()])
        if 'caracter_academico' in desglose and not desglose['caracter_academico'].empty:
            desglose_caracter = "\n".join([f"   - {row['categoria']}: {row['cantidad']} programas" 
                                          for _, row in desglose['caracter_academico'].iterrows()])
    
    # Preparar desgloses SIET
    siet_por_area = ""
    siet_por_depto = ""
    if desglose_siet and isinstance(desglose_siet, dict):
        if 'por_area' in desglose_siet and not desglose_siet['por_area'].empty:
            siet_por_area = "\n".join([f"   - {row['area']}: {row['programas']} programas" 
                                      for _, row in desglose_siet['por_area'].head(8).iterrows()])
        if 'por_depto' in desglose_siet and not desglose_siet['por_depto'].empty:
            siet_por_depto = "\n".join([f"   - {row['departamento']}: {row['programas']} programas" 
                                       for _, row in desglose_siet['por_depto'].head(8).iterrows()])
    
    # Interpretaciones HHI y CAGR
    hhi_valor = stats_snies.get('hhi', 'N/A')
    hhi_interpretacion = ""
    if isinstance(hhi_valor, (int, float)):
        if hhi_valor < 1000:
            hhi_interpretacion = "MERCADO COMPETITIVO - Baja concentracion, muchos oferentes. Oportunidad de diferenciacion."
        elif hhi_valor < 2500:
            hhi_interpretacion = "MERCADO MODERADAMENTE CONCENTRADO - Competencia media, algunos lideres dominantes."
        else:
            hhi_interpretacion = "MERCADO ALTAMENTE CONCENTRADO - Pocos actores dominan. Dificil entrada sin diferenciacion."
    
    cagr_valor = stats_snies.get('cagr', 'N/A')
    cagr_interpretacion = ""
    if isinstance(cagr_valor, (int, float)):
        if cagr_valor > 5:
            cagr_interpretacion = "CRECIMIENTO FUERTE - Demanda en expansion sostenida. Mercado atractivo."
        elif cagr_valor > 0:
            cagr_interpretacion = "CRECIMIENTO MODERADO - Mercado estable con demanda sostenida."
        elif cagr_valor > -3:
            cagr_interpretacion = "ESTANCAMIENTO - Sin crecimiento significativo. Evaluar diferenciacion."
        else:
            cagr_interpretacion = "DECRECIMIENTO - Demanda en descenso. Alto riesgo de mercado."
    
    # Calcular metricas adicionales
    ratio_graduados_matriculados = 0
    if stats_snies.get('matriculados') and stats_snies.get('graduados_anual'):
        try:
            ratio_graduados_matriculados = round(stats_snies['graduados_anual'] / stats_snies['matriculados'] * 100, 2)
        except:
            pass
    
    # =========================================================================
    # NUEVOS DATOS: MERCADO LABORAL (APE, CUOC, GEIH-DANE)
    # =========================================================================
    
    # Preparar datos de vacantes APE
    vacantes_info = ""
    total_vacantes_2024 = 0
    crecimiento_vacantes = ""
    if df_vacantes is not None and not df_vacantes.empty:
        total_vacantes_2024 = int(df_vacantes['vacantes_2024'].sum())
        total_vacantes_2023 = int(df_vacantes['vacantes_2023'].sum()) if 'vacantes_2023' in df_vacantes.columns else 0
        top_ocupaciones = df_vacantes.nlargest(10, 'vacantes_2024')
        # La columna puede llamarse 'ocupacion' o 'nombre_ocupacion' dependiendo del flujo
        col_nombre = 'ocupacion' if 'ocupacion' in df_vacantes.columns else 'nombre_ocupacion'
        vacantes_info = "\n".join([
            f"   - [{row.get('codigo_cuoc', 'N/A')}] {row[col_nombre]}: {int(row['vacantes_2024']):,} vacantes 2024"
            for _, row in top_ocupaciones.iterrows()
        ])
        if total_vacantes_2023 > 0:
            pct_cambio = ((total_vacantes_2024 - total_vacantes_2023) / total_vacantes_2023) * 100
            crecimiento_vacantes = f"   - Variacion 2023-2024: {pct_cambio:+.1f}%"
    
    # Preparar datos de conocimientos CUOC
    conocimientos_info = ""
    total_conocimientos = 0
    if df_conocimientos is not None and not df_conocimientos.empty:
        total_conocimientos = len(df_conocimientos)
        top_conocimientos = df_conocimientos.head(15)
        conocimientos_info = "\n".join([
            f"   - {row['conocimiento']} (similitud: {row.get('similitud_ml', row.get('similitud', 0))*100:.0f}%)"
            for _, row in top_conocimientos.iterrows()
        ])
    
    # Preparar datos de destrezas CUOC
    destrezas_info = ""
    total_destrezas = 0
    if df_destrezas is not None and not df_destrezas.empty:
        total_destrezas = len(df_destrezas)
        top_destrezas = df_destrezas.head(15)
        destrezas_info = "\n".join([
            f"   - {row['destreza']} (similitud: {row.get('similitud_ml', row.get('similitud', 0))*100:.0f}%)"
            for _, row in top_destrezas.iterrows()
        ])
    
    # Preparar datos de salarios reales (SIGEP/OLE)
    salarios_info = ""
    salario_promedio = 0
    if df_salarios is not None and not df_salarios.empty:
        if 'salario_promedio' in df_salarios.columns:
            salario_promedio = df_salarios['salario_promedio'].mean()
            salarios_info = "\n".join([
                f"   - {row.get('nivel_educativo', row.get('nombre_ocupacion', 'N/A'))}: ${int(row.get('salario_promedio', 0)):,} COP/mes"
                for _, row in df_salarios.iterrows()
            ])
    
    # Preparar datos de actividades y tareas ocupacionales
    actividades_info = ""
    total_perfiles = 0
    if df_actividades is not None and not df_actividades.empty:
        total_perfiles = len(df_actividades)
        top_actividades = df_actividades.head(8)
        actividades_info = "\n".join([
            f"   - [{row.get('codigo_cuoc', 'N/A')}] {row.get('titulo_ocupacion', 'N/A')}"
            for _, row in top_actividades.iterrows()
        ])
    
    # Preparar datos de tipo de oferta recomendada
    tipo_oferta_info = ""
    if tipo_oferta_data and isinstance(tipo_oferta_data, dict):
        tipo_oferta_info = f"""
   - TIPO DE OFERTA RECOMENDADA: {tipo_oferta_data.get('tipo', 'N/A')}
   - JUSTIFICACION: {tipo_oferta_data.get('justificacion', 'N/A')}
"""
    
    contexto = f"""
================================================================================
                    INFORME DE PERTINENCIA EDUCATIVA
               SISTEMA DE ANÃLISIS PARA ESTUDIO DE CONTEXTO
================================================================================

FECHA DE GENERACION: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}
NBC ANALIZADO: {nbc or 'No especificado'}
COBERTURA GEOGRAFICA: {depto or 'Nacional (Colombia)'}

================================================================================
                         SECCION 1: DATOS DUROS SNIES
            (Sistema Nacional de Informacion de Educacion Superior)
================================================================================

1.1 METRICAS AGREGADAS DE OFERTA EDUCATIVA:
   - Total programas activos en el NBC: {stats_snies.get('total_programas', 'N/A'):,}
   - Instituciones de Educacion Superior (IES) oferentes: {stats_snies.get('total_instituciones', 'N/A'):,}
   - Matricula total acumulada: {stats_snies.get('matriculados', 'N/A'):,} estudiantes
   - Graduados anuales (ultimo periodo): {stats_snies.get('graduados_anual', 'N/A'):,}
   - Ratio graduados/matriculados: {ratio_graduados_matriculados}%

1.2 INDICADORES DE CONCENTRACION Y CRECIMIENTO:
   - Indice Herfindahl-Hirschman (HHI): {hhi_valor}
     >> INTERPRETACION: {hhi_interpretacion}
   - Tasa de Crecimiento Anual Compuesta (CAGR): {cagr_valor}%
     >> INTERPRETACION: {cagr_interpretacion}

1.3 RANKING DE INSTITUCIONES POR PARTICIPACION DE MERCADO:
{top_ies if top_ies else '   (Datos no disponibles)'}

1.4 SERIE HISTORICA DE MATRICULA (ultimos periodos):
{tendencia_historica if tendencia_historica else '   (Datos no disponibles)'}

1.5 SERIE HISTORICA DE GRADUADOS:
{graduados_historico if graduados_historico else '   (Datos no disponibles)'}

1.6 DISTRIBUCION POR MODALIDAD:
{desglose_modalidad if desglose_modalidad else '   (Datos no disponibles)'}

1.7 DISTRIBUCION POR SECTOR (Oficial/Privado):
{desglose_sector if desglose_sector else '   (Datos no disponibles)'}

1.8 DISTRIBUCION POR NIVEL DE FORMACION:
{desglose_nivel if desglose_nivel else '   (Datos no disponibles)'}

1.9 DISTRIBUCION POR CARACTER ACADEMICO DE IES:
{desglose_caracter if desglose_caracter else '   (Datos no disponibles)'}

================================================================================
                         SECCION 2: DATOS SIET/ETDH
       (Sistema de Informacion de Educacion para el Trabajo y Desarrollo Humano)
================================================================================

2.1 METRICAS AGREGADAS ETDH:
   - Total programas de formacion para el trabajo: {stats_siet.get('total_programas', 'N/A'):,}
   - Instituciones de formacion ETDH: {stats_siet.get('total_instituciones', 'N/A'):,}
   - Certificados emitidos (2023): {stats_siet.get('total_certificados', 'N/A'):,}
   - Duracion promedio de programas: {stats_siet.get('duracion_promedio', 'N/A')} horas
   - Matricula ETDH: {stats_siet.get('total_matriculados', 'N/A'):,}

2.2 DISTRIBUCION POR AREA DE DESEMPENO SIET:
{siet_por_area if siet_por_area else '   (Datos no disponibles)'}

2.3 DISTRIBUCION GEOGRAFICA ETDH:
{siet_por_depto if siet_por_depto else '   (Datos no disponibles)'}

================================================================================
                    SECCION 3: EVALUACION ALGORITMICA DEL SISTEMA
================================================================================

3.1 RESULTADO DEL MODELO DE DECISION:
   - SCORE FINAL DE PERTINENCIA: {score_final}/100
   - VEREDICTO DEL SISTEMA: {veredicto}

3.2 ESCALA DE INTERPRETACION:
   - 90-100: EXCELENTE OPORTUNIDAD - Alta pertinencia demostrada
   - 75-89: BUENA OPORTUNIDAD - Pertinencia favorable con consideraciones
   - 60-74: OPORTUNIDAD MODERADA - Requiere diferenciacion estrategica
   - 45-59: OPORTUNIDAD LIMITADA - Alto riesgo, mercado dificil
   - 0-44: NO RECOMENDADO - Saturacion o ausencia de demanda

================================================================================
                    SECCION 4: MARCO NORMATIVO COLOMBIANO
================================================================================

NORMATIVIDAD APLICABLE:
- Ley 30 de 1992: Organizacion del servicio publico de educacion superior
- Ley 1188 de 2008: Registro calificado de programas academicos
- Decreto 1330 de 2019: Condiciones de calidad para programas de educacion superior
- Decreto 1075 de 2015: Decreto Unico Reglamentario del Sector Educacion
- Marco Nacional de Cualificaciones (MNC): Niveles 1-8 de cualificacion
- Sistema de Aseguramiento de la Calidad: CNA, CONACES

CLASIFICACIONES OFICIALES:
- SNIES: Nucleos Basicos del Conocimiento (NBC)
- CUOC: Clasificacion Unica de Ocupaciones para Colombia
- CIIU Rev. 4: Clasificacion Industrial Internacional Uniforme
- CINE-F 2013: Clasificacion Internacional Normalizada de la Educacion

================================================================================
              SECCION 5: DEMANDA LABORAL REAL (APE - Agencia Publica de Empleo)
================================================================================

5.1 VACANTES REGISTRADAS EN EL SERVICIO PUBLICO DE EMPLEO:
   - Total vacantes 2024 en ocupaciones relacionadas: {total_vacantes_2024:,}
{crecimiento_vacantes if 'crecimiento_vacantes' in dir() and crecimiento_vacantes else ''}

5.2 OCUPACIONES CON MAYOR DEMANDA (Top 10):
{vacantes_info if vacantes_info else '   (Datos no disponibles)'}

   >> FUENTE: Agencia Publica de Empleo (APE) - Ministerio del Trabajo Colombia, 2024

================================================================================
         SECCION 6: COMPETENCIAS OCUPACIONALES (CUOC - MinTrabajo/DANE)
================================================================================

6.1 CONOCIMIENTOS REQUERIDOS EN EL MERCADO LABORAL:
   - Total conocimientos identificados: {total_conocimientos}
   - Top conocimientos relevantes:
{conocimientos_info if conocimientos_info else '   (Datos no disponibles)'}

6.2 DESTREZAS Y HABILIDADES DEMANDADAS:
   - Total destrezas identificadas: {total_destrezas}
   - Top destrezas relevantes:
{destrezas_info if destrezas_info else '   (Datos no disponibles)'}

6.3 PERFILES OCUPACIONALES RELACIONADOS (CUOC):
   - Total perfiles ocupacionales vinculados al NBC: {total_perfiles}
   - Ocupaciones principales:
{actividades_info if actividades_info else '   (Datos no disponibles)'}

   >> FUENTE: Clasificacion Unica de Ocupaciones para Colombia (CUOC) - MinTrabajo/DANE, 2024

================================================================================
     SECCION 6B: PUENTE DE COMPETENCIAS SNIES â†” SIET/ETDH (ML Cross-Education)
================================================================================

{_format_skills_bridge(skills_bridge) if skills_bridge else '   (Analisis de puente no disponible - requiere ML SNIES-ETDH)'}

   >> FUENTE: AnÃ¡lisis ML - sentence-transformers + CUOC como taxonomÃ­a puente

================================================================================
                SECCION 7: SALARIOS DE REFERENCIA (GEIH-DANE)
================================================================================

7.1 SALARIOS PROMEDIO POR OCUPACION RELACIONADA:
   - Salario promedio general: ${int(salario_promedio):,} COP/mes
   - Detalle por ocupacion:
{salarios_info if salarios_info else '   (Datos no disponibles)'}

   >> FUENTE: Gran Encuesta Integrada de Hogares (GEIH) - DANE Colombia, 2023-2024

================================================================================
            SECCION 8: RECOMENDACION DE TIPO DE OFERTA EDUCATIVA
================================================================================

{tipo_oferta_info if tipo_oferta_info else '   (Analisis no disponible)'}

   >> FUENTE: Sistema de anÃ¡lisis para estudio de contexto - Basado en sÃ­ntesis evaluativas

================================================================================
                   CATALOGO DE FUENTES DE DATOS UTILIZADAS
================================================================================

PARA CITAR EN EL INFORME, USA ESTAS REFERENCIAS:

| DATO                      | FUENTE A CITAR                                    |
|---------------------------|---------------------------------------------------|
| Programas/IES/Matricula   | SNIES - MEN Colombia 2024                         |
| Graduados                 | SNIES Graduados - MEN Colombia 2014-2024          |
| Tendencia matricula       | SNIES Matriculados - MEN Colombia 2014-2024       |
| HHI/Concentracion         | Calculo Sistema sobre datos SNIES 2024            |
| CAGR/Crecimiento          | Calculo Sistema sobre SNIES 2014-2024             |
| Educacion ETDH            | SIET - MEN Colombia 2023                          |
| Vacantes laborales        | APE - MinTrabajo Colombia 2024                    |
| Competencias/Conocimientos| CUOC - MinTrabajo/DANE 2024                       |
| Destrezas ocupacionales   | CUOC - MinTrabajo/DANE 2024                       |
| Salarios                  | GEIH - DANE Colombia 2023-2024                    |
| Perfiles ocupacionales    | CUOC Perfiles - MinTrabajo 2025                   |
| Score de pertinencia      | Sistema de anÃ¡lisis para estudio de contexto 2024 |

================================================================================
                         FILTROS ACTIVOS DEL ANALISIS
================================================================================

CONTEXTO DE ANALISIS - FILTROS APLICADOS POR EL USUARIO:

FILTROS PRINCIPALES:
  - NBC Principal para anÃ¡lisis: {nbc or 'Todos los NBCs'}
  - Departamento Principal: {depto or 'Todos (Nacional)'}

{_format_filtros(filtros_activos) if filtros_activos else 'Sin filtros adicionales'}

NOTA METODOLOGICA IMPORTANTE:
Los datos presentados en este informe han sido filtrados segÃºn TODOS los criterios
especificados arriba. El anÃ¡lisis debe:
1. Considerar el alcance geogrÃ¡fico segÃºn departamentos/municipios filtrados
2. Tener en cuenta las modalidades, niveles y sectores seleccionados
3. Ajustar conclusiones al contexto especÃ­fico de los filtros aplicados

================================================================================
                         FIN DE DATOS DE ENTRADA
================================================================================
"""
    return contexto

def _format_skills_bridge(bridge: dict) -> str:
    """Formatea el puente de competencias SNIESâ†”SIET para el contexto del LLM."""
    if not bridge or not bridge.get('has_data'):
        return "   (Sin datos de puente de competencias)"
    
    lines = []
    lines.append(f"6B.1 METRICAS DE ALINEACION:")
    lines.append(f"   - AlineaciÃ³n global competencias SNIES-SIET: {bridge.get('alignment_score_global', 0):.0%}")
    lines.append(f"   - Complementariedad SIET (skills Ãºnicos que aporta ETDH): {bridge.get('complementarity_siet', 0):.0%}")
    lines.append(f"   - Conocimientos compartidos SNIES-SIET: {len(bridge.get('shared_conocimientos', []))}")
    lines.append(f"   - Destrezas compartidas SNIES-SIET: {len(bridge.get('shared_destrezas', []))}")
    
    lines.append(f"\n6B.2 OCUPACIONES CUOC POR CAMINO:")
    lines.append(f"   - VÃ­a SNIES (educaciÃ³n formal): {len(bridge.get('snies_ocupaciones', []))} ocupaciones")
    lines.append(f"   - VÃ­a SIET (educaciÃ³n para el trabajo): {len(bridge.get('siet_ocupaciones', []))} ocupaciones")
    lines.append(f"   - Ocupaciones en comÃºn: {len(bridge.get('shared_ocupaciones', []))}")
    
    if bridge.get('shared_conocimientos'):
        lines.append(f"\n6B.3 CONOCIMIENTOS EN COMUN SNIES-SIET:")
        for s in bridge['shared_conocimientos'][:10]:
            lines.append(f"   - {s}")
    
    if bridge.get('shared_destrezas'):
        lines.append(f"\n6B.4 DESTREZAS EN COMUN SNIES-SIET:")
        for s in bridge['shared_destrezas'][:10]:
            lines.append(f"   - {s}")
    
    if bridge.get('ciiu_sectors'):
        lines.append(f"\n6B.5 SECTORES CIIU RELACIONADOS (vÃ­a CUOC):")
        for s in bridge['ciiu_sectors'][:6]:
            lines.append(f"   - SecciÃ³n {s.get('seccion', '?')}: {s.get('nombre', 'N/A')[:60]}")
    
    if bridge.get('notas'):
        lines.append(f"\n   NOTAS: {'; '.join(bridge['notas'])}")
    
    return "\n".join(lines)

def _format_filtros(filtros: dict) -> str:
    """
    Formatear TODOS los filtros activos para el contexto del LLM.
    Incluye: campos amplios, Ã¡reas, NBCs, departamentos, municipios,
    modalidades, sectores, niveles, carÃ¡cter acadÃ©mico y estados.
    """
    if not filtros:
        return "  - Sin filtros adicionales"
    
    lineas = []
    
    # Filtros de clasificaciÃ³n acadÃ©mica (jerarquÃ­a SNIES)
    if filtros.get('campos_amplios'):
        vals = filtros['campos_amplios']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - Campos amplios CINE: {', '.join(vals)}")
    
    if filtros.get('areas'):
        vals = filtros['areas']
        if isinstance(vals, list) and len(vals) > 0:
            display = vals[:5] if len(vals) > 5 else vals
            suffix = f" (+{len(vals)-5} mÃ¡s)" if len(vals) > 5 else ""
            lineas.append(f"  - Ãreas de conocimiento: {', '.join(display)}{suffix}")
    
    if filtros.get('nbcs'):
        vals = filtros['nbcs']
        if isinstance(vals, list) and len(vals) > 0:
            display = vals[:5] if len(vals) > 5 else vals
            suffix = f" (+{len(vals)-5} mÃ¡s)" if len(vals) > 5 else ""
            lineas.append(f"  - NBCs seleccionados: {', '.join(display)}{suffix}")
    
    # Filtros geogrÃ¡ficos
    if filtros.get('deptos'):
        vals = filtros['deptos']
        if isinstance(vals, list) and len(vals) > 0:
            display = vals[:5] if len(vals) > 5 else vals
            suffix = f" (+{len(vals)-5} mÃ¡s)" if len(vals) > 5 else ""
            lineas.append(f"  - Departamentos: {', '.join(display)}{suffix}")
    
    if filtros.get('municipios'):
        vals = filtros['municipios']
        if isinstance(vals, list) and len(vals) > 0:
            display = vals[:5] if len(vals) > 5 else vals
            suffix = f" (+{len(vals)-5} mÃ¡s)" if len(vals) > 5 else ""
            lineas.append(f"  - Municipios: {', '.join(display)}{suffix}")
    
    # Filtros de programa
    if filtros.get('modalidades'):
        vals = filtros['modalidades']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - Modalidades: {', '.join(vals)}")
    
    if filtros.get('niveles'):
        vals = filtros['niveles']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - Niveles de formaciÃ³n: {', '.join(vals)}")
    
    if filtros.get('sectores'):
        vals = filtros['sectores']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - Sectores (Oficial/Privado): {', '.join(vals)}")
    
    # Filtros institucionales
    if filtros.get('caracteres'):
        vals = filtros['caracteres']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - CarÃ¡cter acadÃ©mico IES: {', '.join(vals)}")
    
    if filtros.get('estados'):
        vals = filtros['estados']
        if isinstance(vals, list) and len(vals) > 0:
            lineas.append(f"  - Estados de programa: {', '.join(vals)}")
    
    # Resumen de filtros activos
    if lineas:
        num_filtros = len(lineas)
        return f"Total de filtros aplicados: {num_filtros}\n" + "\n".join(lineas)
    else:
        return "  - Sin filtros especÃ­ficos (datos a nivel nacional)"
