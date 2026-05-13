# Spec-HU-FR-P0-04: Position Sizing y Risk Management
## Epic: EP-FR-001 | Prioridad: P0 (Crítico) | Estado: Spec

---

## 1. Descripción

Calculadora de tamaño de posición que determina cuántas unidades/comprar basándose en el riesgo configurado por el usuario, distancia al stop loss, correlación entre posiciones y VaR del portafolio.

## 2. Fórmulas Centrales

### 2.1 Tamaño de Posición (Fijo % Riesgo)
```
position_size = (account_balance × risk_pct) / (entry_price × stop_loss_pct)
```

Ejemplo: Cuenta=$100,000, Riesgo=1%, Entrada=$100, Stop=2%
→ position_size = ($100,000 × 0.01) / ($100 × 0.02) = 500 unidades

### 2.2 VaR Paramétrico (95%)
```
VaR_95 = portfolio_value × z_95 × σ_portfolio × √holding_period
```
Donde z_95 = 1.645, σ = volatilidad diaria anualizada / √252

### 2.3 VaR Histórico
```
VaR_95 = percentile(returns_distribution, 5) × portfolio_value
```

### 2.4 Correlación de Portafolio
```
ρ_ij = corr(returns_i, returns_j)
Diversification benefit = Σ(w_i × σ_i) - σ_portfolio
```

## 3. Arquitectura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Market Data     │───▶│ Risk Calculator  │───▶│ Position Manager│
│ (realtime DB)   │    │ (position sizing)│    │ (open positions)│
└─────────────────┘    └──────────────────┘    └────────┬────────┘
                                                        │
                                              ┌─────────▼──────────┐
                                              │ Drawdown Monitor   │
                                              │ + Alert Engine     │
                                              └────────────────────┘
```

## 4. Módulos Python

### 4.1 `backend/app/core/risk/sizing.py`
- `PositionSizer` — calcula tamaño de posición
  - `calculate_fixed_risk(account, risk_pct, entry, stop_loss) → {shares, risk_amount, rr_ratio}`
  - `calculate_kelly(wins, losses, avg_win, avg_loss) → fraction`
  - `calculate_volatility_adjusted(asset_vol, benchmark_vol, base_size) → adjusted_size`

### 4.2 `backend/app/core/risk/var.py`
- `calculate_parametric_var(portfolio_returns, confidence=0.95, horizon=1) → float`
- `calculate_historical_var(portfolio_returns, confidence=0.95, horizon=1) → float`
- `calculate_cvar(portfolio_returns, confidence=0.95) → float` (Expected Shortfall)

### 4.3 `backend/app/core/risk/correlation.py`
- `calculate_correlation_matrix(assets_returns) → DataFrame`
- `diversification_ratio(weights, covariance_matrix) → float`
- `max_concentration_risk(positions, threshold=0.3) → list warnings`

### 4.4 `backend/app/core/risk/drawdown.py`
- `calculate_max_drawdown(equity_curve) → {max_dd, duration, recovery}`
- `current_drawdown(current_value, peak_value) → float`
- `drawdown_alert(current_dd, max_allowed_dd) → bool`

### 4.5 `backend/app/api/v1/endpoints/risk.py`
- `POST /api/v1/risk/size` — calcular tamaño de posición
- `GET /api/v1/risk/var` — VaR actual del portafolio
- `GET /api/v1/risk/drawdown` — drawdown actual y máximo
- `GET /api/v1/risk/correlation` — matriz de correlación

## 5. Tablas de Base de Datos

```sql
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL,
    quantity REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    risk_pct REAL DEFAULT 0.01,
    account_allocation REAL,
    correlation_group TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now')),
    closed_at TEXT
);

CREATE TABLE risk_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    portfolio_var_95 REAL,
    portfolio_var_99 REAL,
    portfolio_cvar REAL,
    max_drawdown REAL,
    current_drawdown REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    total_positions INTEGER,
    concentration_risk REAL,
    FOREIGN KEY (snapshot_date) REFERENCES snapshots(date)
);

CREATE TABLE risk_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    triggered_at TEXT DEFAULT (datetime('now')),
    dismissed INTEGER DEFAULT 0
);
```

## 6. Endpoints API

### POST `/api/v1/risk/size`
- Body: `{ ticker, account_balance, risk_pct, entry_price, stop_loss_pct, strategy_type }`
- Response 200:
```json
{
    "ticker": "AAPL",
    "suggested_shares": 500,
    "risk_amount": 1000,
    "rr_ratio": 2.5,
    "max_position_value": 25000,
    "portfolio_impact_pct": 2.5
}
```

### GET `/api/v1/risk/var`
- Response 200: `{ parametric_var_95, historical_var_95, cvar_95, horizon, portfolio_value }`

### GET `/api/v1/risk/drawdown`
- Response 200: `{ current_dd, max_dd, duration_days, recovery_days, near_limit }`

## 7. Criterios de Aceptación

1. [ ] Calculadora muestra tamaño sugerido antes de cada señal
2. [ ] Riesgo $ calculado basado en % configurable (default 1-2%)
3. [ ] VaR paramétrico e histórico calculado
4. [ ] Correlación entre posiciones abiertas monitorizada
5. [ ] Max drawdown limit enforced con alerta

## 8. Restricciones

- No permitir position size > 20% del portafolio en un solo activo
- Máximo drawdown permitido default: 10% (configurable)
- Si correlación > 0.8 entre posiciones, alertar concentración
- Cálculos deben ejecutarse en < 100ms

---

**Spec creada:** 2026-05-13 | **SDD Nivel:** 2