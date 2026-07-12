"""Decision engine — determines recommended educational offer type based on scores."""


def determinar_tipo_oferta(score_academico: float, score_laboral: float,
                           score_territorial: float, n_competencias: int = 0) -> tuple:
    """Determine the most pertinent educational offer type based on weighted scores.

    Args:
        score_academico: Academic synthesis score (0-100)
        score_laboral: Labor market synthesis score (0-100)
        score_territorial: Territorial synthesis score (0-100)
        n_competencias: Number of competency gaps identified

    Returns:
        tuple: (offer_type, justification, icon_name)
        Types: PROGRAMA_COMPLETO, RUTA_FORMATIVA, MICROCREDENCIAL,
               EDUCACION_CONTINUA, EVALUAR_VIABILIDAD, NO_RECOMENDADO
    """
    if score_academico >= 70 and score_laboral >= 70:
        if score_territorial >= 60:
            return (
                "PROGRAMA_COMPLETO",
                "Alta viabilidad para programa formal. Demanda academica y laboral sustentadas con buen contexto territorial.",
                "graduation-cap"
            )
        else:
            return (
                "RUTA_FORMATIVA",
                "Demanda existe pero hay restricciones territoriales. Considerar modalidad virtual/hibrida o rutas flexibles.",
                "signs-post"
            )

    if score_laboral >= 70 and score_academico < 50:
        return (
            "MICROCREDENCIAL",
            "Demanda laboral alta justifica certificaciones rapidas. Baja demanda academica sugiere preferencia por formacion corta y aplicada.",
            "check-circle"
        )

    if score_laboral >= 60 and 50 <= score_academico < 70:
        return (
            "RUTA_FORMATIVA",
            "Demanda moderada en ambas sintesis. Considerar diplomados, especializaciones o rutas de formacion escalonada.",
            "signs-post"
        )

    if score_academico >= 70 and score_laboral < 50:
        return (
            "PROGRAMA_COMPLETO",
            "Alta demanda academica pero mercado laboral limitado. Evaluar nichos especificos, modalidad investigativa o vocacion de servicio publico.",
            "exclamation-triangle"
        )

    if n_competencias > 8:
        return (
            "EDUCACION_CONTINUA",
            f"Se identificaron multiples competencias demandadas. Priorizar actualizacion gradual de profesionales existentes.",
            "sync"
        )

    if score_academico < 40 and score_laboral < 40:
        return (
            "NO_RECOMENDADO",
            "Baja demanda academica y laboral. Evaluar si existe nicho especifico antes de ofertar.",
            "times-circle"
        )

    return (
        "EVALUAR_VIABILIDAD",
        "Scores mixtos requieren analisis mas detallado. Considerar estudio de mercado especifico.",
        "question-circle"
    )
