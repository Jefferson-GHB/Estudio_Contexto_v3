# ENTREGABLE FINAL: MAPEO DSS CON CRUCES VALIDADOS

## Sistema de Análisis de Pertinencia Educativa

**Fecha:** 2025-01-21  
**Estado:** CRUCES VERIFICADOS EN DUCKDB

---

## RESUMEN EJECUTIVO

El sistema DSS cuenta con **63 variables verificadas** con **nombres de columna REALES** validados contra DuckDB. Todos los **8 cruces principales** fueron probados con consultas SQL exitosas.

---

## CRUCES VALIDADOS (8/8)

| #   | Cruce                     | Registros | Estado |
| --- | ------------------------- | --------- | ------ |
| 1   | Programas → Graduados     | 215,390   |  OK     |
| 2   | Programas → Matriculados  | 589,360   |  OK     |
| 3   | Programas → Instituciones | 30,660    |  OK     |
| 4   | Programas → Catálogo NBC  | 30,798    |  OK     |
| 5   | NBC → CUOC                | 56        |  OK     |
| 6   | SIET → Instituciones      | 25,040    |  OK     |
| 7   | Graduados → NBC (directo) | 307,586   |  OK     |
| 8   | CUOC → Conocimientos      | 79,575    |  OK     |

---

## LLAVES DE CRUCE VERIFICADAS

### Cruce 1: SNIES Programas ↔ Graduados/Matriculados

```sql
CAST(p."CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) = CAST(g."COD_SNIES_PROGRAMA" AS VARCHAR)
```

### Cruce 2: SNIES Programas ↔ Instituciones

```sql
CAST(p."CÓDIGO_INSTITUCIÓN" AS VARCHAR) = CAST(i."CÓDIGO_INSTITUCIÓN" AS VARCHAR)
```

### Cruce 3: NBC → Catálogo NBC

```sql
TRIM(p."NÚCLEO_BÁSICO_DEL_CONOCIMIENTO") = TRIM(c."NBC")
```

### Cruce 4: SIET Programas ↔ Instituciones

```sql
CAST(p."Código Institución" AS VARCHAR) = CAST(i."Código Institución" AS VARCHAR)
```

### Cruce 5: CUOC ↔ Competencias

```sql
c."COD_OCUPACION" = k."codigo_ocupacion"
```

---

## IMPORTANTE: NOMBRES DE COLUMNAS

Los nombres de columnas en DuckDB incluyen **caracteres especiales** (tildes, ñ, espacios):

| INCORRECTO                   | CORRECTO                     |
| ------------------------------ | ------------------------------ |
| CODIGO_SNIES_DEL_PROGRAMA      | CÓDIGO_SNIES_DEL_PROGRAMA      |
| CODIGO_INSTITUCION             | CÓDIGO_INSTITUCIÓN             |
| NUCLEO_BASICO_DEL_CONOCIMIENTO | NÚCLEO_BÁSICO_DEL_CONOCIMIENTO |
| AREA_DE_CONOCIMIENTO           | ÁREA_DE_CONOCIMIENTO           |
| NIVEL_DE_FORMACION             | NIVEL_DE_FORMACIÓN             |
| "Codigo Institucion"           | "Código Institución"           |
| "Duracion Horas"               | "Duración Horas"               |

---

## ESTADISTICAS POR EJE

| Eje                            | Dominios | Variables | Estado |
| ------------------------------ | -------- | --------- | ------ |
| EJE 1: Pertinencia Académica   | 3        | 38        |  OK     |
| EJE 2: Pertinencia Laboral     | 2        | 13        |  OK     |
| EJE 3: Pertinencia Territorial | 1        | 6         |  OK     |
| EJE 4: Pertinencia Tecnológica | 2        | 6         |  OK     |
| **TOTAL**                      | **8**    | **63**    | **OK** |

---

## ARCHIVOS GENERADOS

| Archivo                           | Descripción                        |
| --------------------------------- | ---------------------------------- |
| `MAPEO_DSS_VERIFICADO_V2.csv`     | Mapeo con 63 variables verificadas |
| `CRUCES_VALIDADOS_FINAL.json`     | JSON con detalles de cruces        |
| `validacion_definitiva_cruces.py` | Script de prueba                   |

---

## EJEMPLO DE CONSULTA FUNCIONAL

```sql
SELECT
    p."ÁREA_DE_CONOCIMIENTO" as area,
    COUNT(DISTINCT p."CÓDIGO_SNIES_DEL_PROGRAMA") as total_programas,
    COUNT(DISTINCT g."COD_SNIES_PROGRAMA") as programas_con_graduados
FROM snies.snies_programas p
LEFT JOIN snies.snies_graduados g
    ON CAST(p."CÓDIGO_SNIES_DEL_PROGRAMA" AS VARCHAR) = CAST(g."COD_SNIES_PROGRAMA" AS VARCHAR)
WHERE p."ESTADO_PROGRAMA" = 'Activo'
GROUP BY 1
ORDER BY total_programas DESC;

-- Resultado: 8 áreas de conocimiento con conteos válidos
```

---

## CONCLUSION

El mapeo DSS está **LISTO PARA PRODUCCIÓN** con:

1. OK **63 variables** con nombres reales de columna
2. OK **8 cruces** validados con SQL real
3. OK **Documentacion** de tipos de JOIN necesarios
4. OK **Scripts** de validacion reproducibles

**Generado:** 2025-01-21
