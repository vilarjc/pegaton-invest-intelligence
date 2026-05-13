# Informe de Indicadores Macroeconómicos — HU-FIN-1

> **Proyecto:** Pegaton Invest Intelligence
> **Tarea:** HU-FIN-1 — Especialista Financiero: Definir indicadores macro y reglas de scoring
> **Fecha de generación:** 2026-05-12
> **Fuente de datos:** FRED (Federal Reserve Economic Data) vía tabla `macro_indicators` en `pegaton.db`

---

## 1. Resumen de Indicadores Macro

| # | Código FRED | Nombre | Peso | Dirección actual |
|---|-------------|--------|------|-------------------|
| 1 | `FEDFUNDS`  | Fed Funds Rate | 0.20 | bajista |
| 2 | `CPIAUCSL`  | CPI (Consumer Price Index) | 0.10 | neutral |
| 3 | `PCEPI`     | PCE Price Index | 0.10 | neutral |
| 4 | `PAYEMS`    | Nonfarm Payrolls | 0.15 | alcista |
| 5 | `UNRATE`    | Unemployment Rate | 0.15 | alcista |
| 6 | `UMCSENT`   | Consumer Sentiment (UMICH) | 0.10 | bajista |
| 7 | `INDPRO`    | Industrial Production | 0.10 | alcista |
| 8 | `DGS10`     | 10-Year Treasury Yield | 0.10 | bajista |

**Suma de pesos: 1.000 ✅**  
**Total de indicadores: 8 (≥ 5 requeridos) ✅**

---

## 2. Fuentes de Datos

Todos los indicadores provienen de **FRED (Federal Reserve Economic Data)** del Banco de la Reserva Federal de St. Louis:

| Código FRED | Serie FRED | URL |
|-------------|------------|-----|
| `FEDFUNDS`  | Federal Funds Effective Rate | https://fred.stlouisfed.org/series/FEDFUNDS |
| `CPIAUCSL`  | CPI for All Urban Consumers: All Items | https://fred.stlouisfed.org/series/CPIAUCSL |
| `PCEPI`     | PCE Price Index (All Items) | https://fred.stlouisfed.org/series/PCEPI |
| `PAYEMS`    | All Employees: Total Nonfarm Payrolls | https://fred.stlouisfed.org/series/PAYEMS |
| `UNRATE`    | Unemployment Rate | https://fred.stlouisfed.org/series/UNRATE |
| `UMCSENT`   | University of Michigan: Consumer Sentiment | https://fred.stlouisfed.org/series/UMCSENT |
| `INDPRO`    | Industrial Production Index | https://fred.stlouisfed.org/series/INDPRO |
| `DGS10`     | 10-Year Treasury Constant Maturity Rate | https://fred.stlouisfed.org/series/DGS10 |

---

## 3. Reglas de Conversión Valor → Puntuación (0–100)

Cada indicador tiene reglas definidas como `(operador, umbral, puntuación)`. Se evalúan en orden; la primera coincidencia determina la puntuación. Si ninguna coincide, se aplica la regla `default`.

### 3.1 Fed Funds Rate (`FEDFUNDS`) — Peso: 0.20

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| ≤ | 1.5% | 80 | Muy expansivo → alcista |
| ≤ | 2.5% | 65 | Expansivo moderado |
| ≤ | 3.5% | 50 | Neutral |
| ≤ | 5.0% | 35 | Restrictivo moderado |
| default | — | 20 | Muy restrictivo → bajista |

### 3.2 CPI (`CPIAUCSL`) — Peso: 0.10

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| default | — | 50 | Neutral (MVP: sin desviación YoY) |

### 3.3 PCE Price Index (`PCEPI`) — Peso: 0.10

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| default | — | 50 | Neutral (MVP: sin desviación YoY) |

### 3.4 Nonfarm Payrolls (`PAYEMS`) — Peso: 0.15

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| > | 160,000 | 70 | Muy fuerte → alcista |
| > | 150,000 | 60 | Fuerte |
| > | 130,000 | 50 | Moderado |
| > | 100,000 | 40 | Débil |
| default | — | 30 | Muy débil → bajista |

### 3.5 Unemployment Rate (`UNRATE`) — Peso: 0.15

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| < | 3.5% | 80 | Muy ajustado → alcista |
| < | 4.0% | 70 | Ajustado |
| < | 4.5% | 60 | Moderado |
| < | 5.0% | 50 | Neutral |
| < | 6.0% | 35 | Elevado |
| default | — | 20 | Muy elevado → bajista |

### 3.6 Consumer Sentiment (`UMCSENT`) — Peso: 0.10

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| ≥ | 100 | 80 | Muy optimista → alcista |
| ≥ | 80 | 65 | Optimista |
| ≥ | 65 | 50 | Neutral |
| ≥ | 50 | 35 | Pesimista |
| default | — | 20 | Muy pesimista → bajista |

### 3.7 Industrial Production (`INDPRO`) — Peso: 0.10

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| ≥ | 105 | 70 | Expansión fuerte → alcista |
| ≥ | 100 | 60 | Expansión moderada |
| ≥ | 95 | 50 | Neutral |
| default | — | 40 | Contracción |

### 3.8 10-Year Treasury Yield (`DGS10`) — Peso: 0.10

| Condición | Umbral | Puntuación | Interpretación |
|-----------|--------|------------|----------------|
| < | 2.0% | 30 | Flight to safety → bajista |
| < | 3.0% | 45 | Bajo |
| < | 4.0% | 55 | Moderado |
| < | 5.0% | 45 | Elevado (inflación) |
| < | 6.0% | 35 | Muy elevado |
| default | — | 25 | Extremo |

---

## 4. Fórmula de Combinación Ponderada

La puntuación macro final se calcula como **media ponderada** de las puntuaciones individuales:

```
macro_score = Σ (puntuación_i × peso_i) / Σ peso_i
```

Donde `Σ peso_i = 1.0`, por lo que se simplifica a:

```
macro_score = Σ (puntuación_i × peso_i)
```

### Clasificación de dirección por factor:

| Rango de puntuación | Dirección |
|---------------------|-----------|
| ≥ 55 | Alcista 🟢 |
| 46–54 | Neutral 🟡 |
| ≤ 45 | Bajista 🔴 |

### Combinación Macro-Técnica (Spec C):

```
score_final = macro_score × 0.40 + technical_score × 0.60
```

Umbrales de acción:

| Rango | Acción |
|-------|--------|
| 80–100 | 🔵 COMPRAR |
| 60–79  | 🔵 ACUMULAR |
| 40–59  | 🟡 MANTENER |
| 20–39  | 🟠 REDUCIR |
| 0–19   | 🔴 EVITAR |

---

## 5. Ejemplo de Cálculo con Datos Reales

**Datos de entrada (últimos valores disponibles en pegaton.db):**

| Indicador | Valor | Fecha |
|-----------|-------|-------|
| FEDFUNDS | 3.64% | 2026-04-01 |
| CPIAUCSL | 330.293 | 2026-03-01 |
| PCEPI | 130.344 | 2026-03-01 |
| PAYEMS | 158,637 | 2026-03-01 |
| UNRATE | 4.3% | 2026-03-01 |
| UMCSENT | 53.3 | 2026-03-01 |
| INDPRO | 101.790 | 2026-03-01 |
| DGS10 | 4.43% | 2026-05-05 |

### Paso a paso:

1. **FEDFUNDS = 3.64** → regla `<= 3.5` no (3.64 > 3.5), regla `<= 5.0` sí → **puntuación = 35** → dirección: bajista
2. **CPIAUCSL = 330.293** → solo regla default → **puntuación = 50** → dirección: neutral
3. **PCEPI = 130.344** → solo regla default → **puntuación = 50** → dirección: neutral
4. **PAYEMS = 158,637** → regla `> 150,000` sí → **puntuación = 60** → dirección: alcista
5. **UNRATE = 4.3** → regla `< 4.5` sí → **puntuación = 60** → dirección: alcista
6. **UMCSENT = 53.3** → regla `>= 50` sí → **puntuación = 35** → dirección: bajista
7. **INDPRO = 101.790** → regla `>= 100` sí → **puntuación = 60** → dirección: alcista
8. **DGS10 = 4.43** → regla `< 5.0` sí → **puntuación = 45** → dirección: bajista

### Cálculo ponderado:

```
macro_score = (35×0.20) + (50×0.10) + (50×0.10) + (60×0.15) + (60×0.15)
            + (35×0.10) + (60×0.10) + (45×0.10)

macro_score = 7.0 + 5.0 + 5.0 + 9.0 + 9.0 + 3.5 + 6.0 + 4.5

macro_score = 49.0
```

### Resultado:

| Métrica | Valor |
|---------|-------|
| **Macro Score** | **49.0 / 100** |
| Dirección global | **Neutral-Bajista** |
| Acción recomendada | **MANTENER** (siendo conservador) |

### Desglose de contribuciones:

| Indicador | Puntuación | Peso | Contribución |
|-----------|-----------|------|-------------|
| FEDFUNDS | 35.0 | 0.20 | 7.00 |
| CPIAUCSL | 50.0 | 0.10 | 5.00 |
| PCEPI | 50.0 | 0.10 | 5.00 |
| PAYEMS | 60.0 | 0.15 | 9.00 |
| UNRATE | 60.0 | 0.15 | 9.00 |
| UMCSENT | 35.0 | 0.10 | 3.50 |
| INDPRO | 60.0 | 0.10 | 6.00 |
| DGS10 | 45.0 | 0.10 | 4.50 |
| **TOTAL** | — | **1.00** | **49.00** |

---

## 6. Implementación en Código

### Archivos relevantes:

- **`backend/app/core/pegaton_config.py`** — Define `MACRO_SCORING` (diccionario de 8 indicadores con reglas y pesos), `MACRO_WEIGHTS`, `FACTOR_ALCISTA` (55), `FACTOR_BAJISTA` (45)
- **`backend/app/core/macro.py`** — Implementa `apply_scoring_rules()`, `get_latest_values()`, `macro_score()` (combinación ponderada automática)
- **`backend/app/core/technical.py`** — Scoring técnico complementario (RSI, MACD, SMA50, SMA200)

### Verificación de integridad:

- [x] ≥ 5 indicadores macro definidos (hay 8)
- [x] Pesos suman 1.0 (verificado: 0.20+0.10+0.10+0.15+0.15+0.10+0.10+0.10 = 1.0)
- [x] Cada indicador tiene reglas de conversión valor → puntuación 0-100
- [x] Fórmula de combinación ponderada documentada e implementada
- [x] Ejemplo de cálculo con datos reales de FRED incluido
- [x] Fuentes FRED documentadas con URLs

---

*Generado automáticamente por el Especialista Financiero (Hermes Agent) — Tarea HU-FIN-1*