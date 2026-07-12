# ENTREGABLE: MAPEO DSS SISTEMA DE PERTINENCIA

## Estudio Contexto - Enero 2026

---

## ESTADO FINAL

| Métrica                  | Valor         |
| ------------------------ | ------------- |
| **Total Variables**      | 106           |
| **Disponibilidad Real**  | 88 (83%)      |
| **Dominios Cubiertos**   | 8/8 (100%)    |
| **Registros Accesibles** | 16.7 millones |

---

## COBERTURA POR DOMINIO

| Dominio                     | Doc. Formal | Mapeo Final | Estado   |
| --------------------------- | ----------- | ----------- | -------- |
| D1: Académico-Formativo     | 12          | 15          | OK +25%  |
| D2: Normativo Institucional | 9           | 13          | OK +44%  |
| D3: Oferta Comparada        | 12          | 17          | OK +42%  |
| D4: Ocupacional Laboral     | 11          | 14          | OK +27%  |
| D5: Competencias            | 7           | 9           | OK +29%  |
| D6: Territorial Estratégico | 10          | 14          | OK +40%  |
| D7: Global y Tendencias     | 7           | 18          | OK +157% |
| D8: Decisión Integrador     | 6           | 6           | OK 100%  |
| **TOTAL**                   | **74**      | **106**     | **143%** |

---

## FUENTES DE DATOS PRINCIPALES

### Educación Superior

- **SNIES**: 30,660 programas + 1.5M históricos (graduados, admitidos, matriculados)
- **ICFES Saber**: 1.9M resultados (PRO + TyT)
- **Acreditación**: 132 IES acreditadas

### Educación para el Trabajo (ETDH)

- **SIET**: 25,010 programas + 4,385 instituciones
- **Matrícula SIET**: 41,424 registros

### Mercado Laboral

- **CUOC 2025**: 14,462 ocupaciones
- **RUES**: 9.1M registros empresariales
- **APE/Observatorio SENA**: Vacantes y colocaciones

### Territorial

- **DIVIPOLA**: 1,122 municipios, 33 departamentos
- **Conectividad**: 2.7M registros internet + 407K móvil
- **DNP**: 22,020 indicadores desempeño municipal

### Internacional

- **Banco Mundial**: 29,984 indicadores
- **UNESCO**: 12,089 indicadores educativos
- **OECD**: 13 indicadores laborales

---

## ARCHIVOS GENERADOS

| Archivo                            | Descripción                                   |
| ---------------------------------- | --------------------------------------------- |
| `MAPEO_DSS_VARIABLES_COMPLETO.csv` | Versión completa (15 columnas, 106 variables) |
| `MAPEO_DSS_81_VARIABLES.csv`       | Versión compatible con dss_engine.py          |
| `README_MAPEO_DSS.md`              | Documentación técnica completa                |

---

## TIPOS DE VARIABLES

```
DATO (30)         ████████████████████████████████░░░░░░░░ 28%
INDICADOR (35)    ████████████████████████████████████████ 33%
CLASIFICADOR (22) ███████████████████████░░░░░░░░░░░░░░░░░ 21%
LLM (8)           █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  8%
CALCULADO (6)     ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  6%
OTROS (5)         █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  4%
```

---

## MEJORAS RESPECTO A VERSION ANTERIOR

1. **+32 variables nuevas** (de 74 base a 106 implementadas)
2. **ICFES Saber integrado** (1.9M resultados PRO y TyT)
3. **SIET completo** (instituciones, matrícula, certificados)
4. **Indicadores internacionales** (BM, UNESCO, OECD, OIT)
5. **Conectividad digital** (internet fijo y móvil)
6. **Tendencias tecnológicas** (IA, Industria 4.0, EdTech)
7. **Históricos SNIES** (admitidos, matriculados, graduados)

---

## PROXIMOS PASOS

1. [ ] Validar cruces en producción
2. [ ] Implementar variables CALCULADAS
3. [ ] Integrar con motor LLM para variables generadas
4. [ ] Testing end-to-end con casos de uso reales

---

**Generado automáticamente:** 20/01/2026 14:04  
**Script:** `scripts/generar_mapeo_completo.py`
