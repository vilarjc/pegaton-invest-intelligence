# Spec-HU-FR-P0-02: Motor de Backtesting Completo
## Epic: EP-FR-001 | Prioridad: P0 (Crítico) | Estado: Spec

---

## 1. Descripción

Framework de backtesting que permite ejecutar cualquier estrategia del sistema contra datos históricos con walk-forward analysis, simulación Monte Carlo y métricas de rendimiento completas.

## 2. Arquitectura

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Strategy    │───▶│ Backtester   │───▶│ Metrics Engine  │
│ Interface   │    │ Core Engine  │    │ (Sharpe/Sortino/│
└─────────────┘    └──────────────┘    │  Drawdown/...)  │
                                        └────────┬────────┘
                                                 │
                                        ┌────────▼────────┐
                                        │ Monte Carlo     │
                                        │ Simulator       │
                                        └────────┬────────┘
                                                 │
                                        ┌────────▼────────┐
                                        │ Equity Curve    │
                                        │ Generator       │
                                        └─────────────────┘
```

## 3. Módulos Python

### 3.1 `backend/app/core/backtester/strategy.py`
- Clase base `Strategy` abstracta
- Métodos: `initialize(params)`, `on_tick(tick)`, `on_bar(bar)`, `get_signals()`
- Ejemplo strategy: `MACrossoverStrategy`, `RSIReversalStrategy`

### 3.2 `backend/app/core/backtester/engine.py`
- Clase `BacktestEngine` — ejecuta el backtest
- Métodos: `run(strategy, data, start_date, end_date)`, `walk_forward(window, step)`
- Soporta vectorized (pandas) y event-driven (tick-by-tick)

### 3.3 `backend/app/core/backtester/monte_carlo.py`
- Clase `MonteCarloSimulator`
- Genera 1000+ escenarios basados en distribución de retornos
- Método: `simulate(returns, n_scenarios=1000, horizon=252)`
- Output: percentiles de retorno, probabilidad de ruina

### 3.4 `backend/app/core/backtester/metrics.py`
- Función `calculate_metrics(returns)` → dict con:
  - `sharpe_ratio`, `sortino_ratio`, `max_drawdown`
  - `win_rate`, `profit_factor`, `expectancy`
  - `calmar_ratio`, `omega_ratio`
  - `var_95`, `cvar_95`

### 3.5 `backend/app/api/v1/endpoints/backtest.py`
- POST `/api/v1/backtest/run` — ejecuta backtest
- GET `/api/v1/backtest/{id}` — resultado de un backtest
- GET `/api/v1/backtest/{id}/equity_curve` — curva de equity

## 4. Tablas de Base de Datos

```sql
CREATE TABLE backtest_results (
    id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    metrics JSON NOT NULL DEFAULT '{}',
    equity_curve JSON,
    monte_carlo_results JSON,
    created_at TEXT DEFAULT (datetime('now'))
);
```

## 5. Endpoints API

### POST `/api/v1/backtest/run`
- Body: `{ strategy: "MACross", ticker: "AAPL", start: "...", end: "...", params: {...} }`
- Response 200: `{ backtest_id, status, metrics }`

### GET `/api/v1/backtest/{id}`
- Response 200: `{ backtest_id, strategy, ticker, dates, metrics }`

### GET `/api/v1/backtest/{id}/equity_curve`
- Response 200: `{ points: [{date, value}, ...] }`

## 6. Criterios de Aceptación

1. [ ] Se puede ejecutar cualquier estrategia contra datos históricos
2. [ ] Walk-forward analysis con ventana configurable
3. [ ] Simulación Monte Carlo con 1000+ escenarios
4. [ ] Métricas: Sharpe, Sortino, max drawdown, win rate, expectancy, profit factor
5. [ ] Curva de equity generada y almacenada
6. [ ] Resultados almacenados en pegaton.db

## 7. Restricciones

- Usar datos de `data/` o `pegaton.db` — sin llamadas API en backtest
- Vectorized mode para velocidad (>1000 backtests/min)
- Memory limit: datasets >100K puntos deben chunked

---

**Spec creada:** 2026-05-13 | **SDD Nivel:** 2