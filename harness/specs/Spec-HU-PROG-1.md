# Especificaciones de Implementación — HU-PROG-1 (Programador)

> **Proyecto:** Pegaton Invest Intelligence  
> **Tarea:** HU-PROG-1 — Implementación del Sistema de Señalización  
> **Fecha:** 2026-05-12  
> **Dependencias:** HU-FIN-1 ✅, HU-TEC-1 ✅, HU-PM-1 ✅  

---

## Subtarea 6.1: `scripts/macro_ingest.py`

**Descripción:** Script de ingesta de datos macroeconómicos desde FRED. Lee la configuración de `config/macro_indicators.yaml`, obtiene datos vía yfinance/FRED API y los guarda en `data/pegaton.db` (tabla `macro_indicators`).

**Entrada:** Ninguna (usa config de YAML + FRED API)  
**Salida:** Datos insertados en `pegaton.db.macro_indicators`  

**Criterios de Aceptación:**
- [ ] Lee config de `config/macro_indicators.yaml`
- [ ] Obtiene datos para los 8 indicadores FRED definidos
- [ ] Guarda en tabla `macro_indicators` con columnas: `date`, `indicator`, `value`
- [ ] Ejecutable sin LLM: `python scripts/macro_ingest.py`
- [ ] Manejo de errores de red/API con retry

---

## Subtarea 6.2: `scripts/macro_scoring.py`

**Descripción:** Script que calcula la señal macro (0-100) a partir de los datos en DB. Usa las reglas definidas en `pegaton_config.py` → `MACRO_SCORING`.

**Entrada:** Datos de `macro_indicators` en pegaton.db  
**Salida:** `dict` con `{'macro_score': float, 'factors': [...], 'details': {...}}`  

**Criterios de Aceptación:**
- [ ] Implementa `macro_score()` que lee de DB y aplica `apply_scoring_rules()`
- [ ] Retorna score 0-100 combinación ponderada
- [ ] Incluye dirección por factor (alcista/bajista/neutral)
- [ ] Módulo testeable: `if __name__ == '__main__': print(macro_score())`

---

## Subtarea 6.3: `scripts/price_ingest.py`

**Descripción:** Script de ingesta de datos OHLCV para símbolos trackeados.

**Entrada:** `config/system.yaml` → lista de symbols  
**Salida:** Datos insertados en `pegaton.db.precios_ohlcv`  

**Criterios de Aceptación:**
- [ ] Obtiene OHLCV vía yfinance para SPY, EUR/USD, BTC/USD
- [ ] Almacena mínimo 200 días de datos
- [ ] Tabla con columnas: `timestamp`, `symbol`, `open`, `high`, `low`, `close`, `volume`
- [ ] Ejecutable sin LLM vía crontab

---

## Subtarea 6.4: `scripts/technical_scoring.py`

**Descripción:** Script que calcula indicadores técnicos y su score combinado.

**Entrada:** Datos de `precios_ohlcv` + config de `config/technical_indicators.yaml`  
**Salida:** `dict` con `{'technical_score': float, 'factors': [...], 'details': {...}}`  

**Criterios de Aceptación:**
- [ ] Calcula RSI(14), MACD, SMA50, SMA200
- [ ] Aplica scoring según pesos TECHNICAL_WEIGHTS
- [ ] Retorna score 0-100 con desglose por factor
- [ ] Consiste con `technical.py` existente

---

## Subtarea 6.5: `scripts/signal_combiner.py`

**Descripción:** Script que combina señal macro + técnica en la señal final PEGATON.

**Entrada:** `macro_score()` + `technical_score()`  
**Salida:** `dict` con score final, acción y desglose  

**Criterios de Aceptación:**
- [ ] Implementa: `pegaton_score = 0.40 × macro + 0.60 × technical`
- [ ] Determina acción según ACTIONS thresholds
- [ ] Identifica factor dominante (mayor contribución absoluta)
- [ ] Retorna formato JSON compatible con API

---

## Subtarea 6.6: `api/signal_api.py` (ENDPOINT FALTANTE)

**Descripción:** Endpoint FastAPI GET `/api/v1/signal` y GET `/api/v1/signals`. **BUG: No está registrado en `main.py` — ya fue arreglado, pero el archivo necesita ser creado/refactorizado como módulo standalone.**

**Entrada (query params):**
- `symbol` (string, default: "SPY")
- `include_details` (bool, default: true)

**Response 200:**
```json
{
  "symbol": "SPY",
  "timestamp": "2026-05-12T19:30:00Z",
  "pegaton_score": 67.4,
  "action": "🔵 ACUMULAR",
  "macro_score": 62.5,
  "technical_score": 70.2,
  "blend": { "macro_weight": 0.40, "technical_weight": 0.60 },
  "factors": { "macro": [...], "technical": [...], "summary": {...} },
  "details": { "macro": {...}, "technical": {...} }
}
```

**Criterios de Aceptación:**
- [ ] GET /api/v1/signal?symbol=X retorna JSON correcto
- [ ] GET /api/v1/signals retorna todos los símbolos trackeados
- [ ] Códigos de error: 404 (sin datos), 503 (macro unavailable), 500 (internal)
- [ ] Registrado en `main.py` ✅ (YA ARREGLADO)

---

## Subtarea 6.7: Test Suite

**Descripción:** Suite de pruebas unitarias para todos los módulos.

**Archivos a crear:** `tests/test_macro.py`, `tests/test_technical.py`, `tests/test_score.py`, `tests/test_api.py`, `tests/test_config.py`

**Criterios de Aceptación:**
- [ ] test_macro.py — 4 tests (score range, all indicators, rules matching, default fallback)
- [ ] test_technical.py — 3 tests (RSI range, MACD bullish, SMA position)
- [ ] test_score.py — 3 tests (pegaton_score range, action mapping, weights sum)
- [ ] test_api.py — 3 tests (signal 200, unknown symbol 404, missing macro 503)
- [ ] test_config.py — 3 tests (macro weights sum, tech weights sum, blend weights sum)
- [ ] `pytest tests/` pasa con éxito

---

## Prioridad de Ejecución

1. 6.2 (`macro_scoring.py`) — ya existe como macro.py, refactorizar
2. 6.4 (`technical_scoring.py`) — ya existe como technical.py, refactorizar
3. 6.5 (`signal_combiner.py`) — ya existe como score.py, refactorizar
4. 6.6 (`signal_api.py`) — ELIMINAR duplicado con score.py endpoint
5. 6.1 (`macro_ingest.py`) — nuevo script
6. 6.3 (`price_ingest.py`) — nuevo script
7. 6.7 (Test suite) — último

---

*Generado por Hermes Agent — PM/Arquitecto para HU-PROG-1*