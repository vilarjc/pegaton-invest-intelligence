# Informe Técnico — HU-TEC-1: Especialista Técnico

**Fecha:** 2026-05-12  
**Autor:** Hermes Agent  
**Tarea:** HU-TEC-1 — Especialista Técnico  
**Estado:** ✅ Completado  

---

## 1. Verificación de Indicadores Técnicos

Se verificaron los **4 indicadores técnicos** implementados en `backend/app/core/technical.py`:

| # | Indicador | Fórmula / Método | Archivo |
|---|-----------|------------------|---------|
| 1 | **RSI(14)** | Media móvil exponencial de ganancias y pérdidas sobre 14 períodos. `RSI = 100 - (100 / (1 + RS))` donde `RS = avg_gain / avg_loss` | `technical.py:rsi()` |
| 2 | **MACD** | Línea MACD = EMA(12) − EMA(26). Señal = EMA(9) del MACD. Histograma = MACD − Señal. Criterio bullish: MACD > Señal | `technical.py:macd()` |
| 3 | **SMA50** | Media móvil simple de 50 períodos. Criterio: precio actual > SMA50 → alcista | `technical.py:sma_position()` |
| 4 | **SMA200** | Media móvil simple de 200 períodos. Criterio: precio actual > SMA200 → alcista | `technical.py:sma_position()` |

**Scoring de cada indicador (0–100):**

- **RSI:** Zona oversold (≤30) → score alto (80–100). Zona overbought (≥70) → score bajo (0–20). Entre 30–70: interpolación lineal.
- **MACD:** Bullish → 65, Bearish → 35
- **SMA50:** Precio arriba → 70, Precio abajo → 30
- **SMA200:** Precio arriba → 70, Precio abajo → 30

---

## 2. Verificación de Pesos Técnicos

Definidos en `backend/app/core/pegaton_config.py` → `TECHNICAL_WEIGHTS`:

| Indicador | Peso |
|-----------|------|
| RSI(14)   | 0.30 |
| MACD      | 0.25 |
| SMA50     | 0.25 |
| SMA200    | 0.20 |
| **Suma**  | **1.00** ✅ |

---

## 3. Regla de Combinación Macro/Técnica

Definidos en `pegaton_config.py` → `Spec C`:

| Componente | Peso | Fuente |
|------------|------|--------|
| **MACRO**  | 0.40 (40%) | `macro_score()` — 8 indicadores FRED |
| **TÉCNICO** | 0.60 (60%) | `technical_score()` — 4 indicadores de precio |

**Fórmula:**
```
pegaton_score = MACRO_WEIGHT × macro_score + TECHNICAL_WEIGHT × technical_score
             = 0.40 × macro_score + 0.60 × technical_score
```

**Pesos macro (sub-componentes):**

| Indicador FRED | Peso |
|----------------|------|
| FEDFUNDS       | 0.20 |
| PAYEMS         | 0.15 |
| UNRATE         | 0.15 |
| CPIAUCSL       | 0.10 |
| PCEPI          | 0.10 |
| UMCSENT        | 0.10 |
| INDPRO         | 0.10 |
| DGS10          | 0.10 |
| **Suma**       | **1.00** ✅ |

---

## 4. Umbrales de Decisión (Compra/Venta/Neutral)

Definidos en `pegaton_config.py` → `ACTIONS`:

| Rango de Score | Acción | Emoji |
|----------------|--------|-------|
| 80 – 100       | **COMPRAR** | 🔵 |
| 60 – 79        | **ACUMULAR** | 🔵 |
| 40 – 59        | **MANTENER** | 🟡 |
| 20 – 39        | **REDUCIR**  | 🟠 |
| 0 – 19         | **EVITAR**   | 🔴 |

**Umbrales de factor direction (HU-1.2):**
- `FACTOR_ALCISTA` = 55 (score ≥ 55 → alcista)
- `FACTOR_BAJISTA` = 45 (score ≤ 45 → bajista)
- Entre 45–55 → neutral

---

## 5. Verificación de `technical_ondemand.py`

**Estado:** ✅ Existe y funciona

Archivo: `backend/app/core/technical_ondemand.py` (109 líneas)

- Importa funciones de scoring de `technical.py` (reutilización de código ✅)
- Usa Twelve Data API para fetch on-demand de cualquier símbolo
- Implementa la misma lógica de scoring que `technical.py` (consistencia ✅)
- Incluye manejo de errores (fallback a `technical_score: 50` si no hay datos)
- `score.py` lo importa correctamente como fallback cuando el símbolo no está en la DB local

---

## 6. Ejemplo de Cálculo — SPY

**Ejecución:** `pegaton_score('SPY')`

### Resultados

| Métrica | Valor |
|---------|-------|
| **Pegaton Score** | **51.2** |
| **Acción** | 🟡 MANTENER |
| Macro Score | 49.0 |
| Technical Score | 52.6 |

### Desglose de Factores Técnicos

| Factor | RSI Raw | Score | Peso | Contribución | Dirección |
|--------|---------|-------|------|---------------|-----------|
| RSI(14) | 75.8 | 16.1 | 0.30 | 4.84 | bajista |
| MACD | — | 65.0 | 0.25 | 16.25 | alcista |
| SMA50 | above (+7.5%) | 70.0 | 0.25 | 17.50 | alcista |
| SMA200 | above (+9.1%) | 70.0 | 0.20 | 14.00 | alcista |

**Technical Score ponderado:** (4.84 + 16.25 + 17.50 + 14.00) = **52.59 → 52.6** ✅

### Desglose de Factores Macro

| Factor | Valor | Score | Peso | Contribución | Dirección |
|--------|-------|-------|------|---------------|-----------|
| FEDFUNDS | 3.64% | 35 | 0.20 | 7.00 | bajista |
| UNRATE | 4.3% | 60 | 0.15 | 9.00 | alcista |
| PAYEMS | 158,637K | 60 | 0.15 | 9.00 | alcista |
| INDPRO | 101.79 | 60 | 0.10 | 6.00 | alcista |
| DGS10 | 4.43% | 45 | 0.10 | 4.50 | bajista |
| UMCSENT | 53.3 | 35 | 0.10 | 3.50 | bajista |
| CPIAUCSL | 330.29 | 50 | 0.10 | 5.00 | neutral |
| PCEPI | 130.34 | 50 | 0.10 | 5.00 | neutral |

**Macro Score ponderado:** 49.0 ✅

### Cálculo Final

```
pegaton_score = 0.40 × 49.0 + 0.60 × 52.6
              = 19.6 + 31.56
              = 51.16 → 51.2

Acción: 40 ≤ 51.2 ≤ 59 → MANTENER 🟡
```

### Factores — Resumen

- **Factores alcistas:** 6 (MACD, SMA50, SMA200, PAYEMS, UNRATE, INDPRO)
- **Factores bajistas:** 4 (RSI, FEDFUNDS, DGS10, UMCSENT)
- **Factor dominante:** SMA50 (alcista, contribución = 17.5)

---

## 7. Checklist de Criterios de Aceptación

| # | Criterio | Estado |
|---|----------|--------|
| 1 | ≥3 indicadores técnicos con fórmulas definidas | ✅ 4 indicadores |
| 2 | Pesos que sumen 1.0 | ✅ 0.30+0.25+0.25+0.20=1.0 |
| 3 | Regla de combinación macro/técnica | ✅ 40% macro + 60% técnico |
| 4 | Umbrales compra/venta/neutral | ✅ 5 rangos definidos |
| 5 | Ejemplo de cálculo con datos de muestra | ✅ SPY → score 51.2 → MANTENER |

---

## 8. Artifacts Registrados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `data/pegaton_score_spy_example.json` | JSON | Resultado completo del cálculo SPY |
| `data/technical_indicator_report.md` | Markdown | Este informe |

---

*Generado por Hermes Agent para la tarea HU-TEC-1. Verificado contra spec #12 (aprobada).*