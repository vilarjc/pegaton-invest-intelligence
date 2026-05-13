# Spec-HU-FR-P0-05: Indicadores Técnicos Avanzados (50+)
## Epic: EP-FR-001 | Prioridad: P0 (Crítico) | Estado: Spec

---

## 1. Descripción

Ampliar el módulo de indicadores técnicos de 2 (MACD, SMA) a 50+ indicadores organizados en 6 categorías. Cada indicador es un módulo independiente con tests unitarios y contribuye al scoring general con peso configurable.

## 2. Categorías e Indicadores

### 2.1 Momentum (10 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | RSI (Relative Strength Index) | momentum/rsi.py |
| 2 | StochRSI (Stochastic RSI) | momentum/stoch_rsi.py |
| 3 | Williams %R | momentum/williams.py |
| 4 | CCI (Commodity Channel Index) | momentum/cci.py |
| 5 | ROC (Rate of Change) | momentum/roc.py |
| 6 | MFI (Money Flow Index) | momentum/mfi.py |
| 7 | PPO (Percentage Price Oscillator) | momentum/ppo.py |
| 8 | TSI (True Strength Index) | momentum/tsi.py |
| 9 | UO (Ultimate Oscillator) | momentum/ultimate_osc.py |
| 10 | AO (Awesome Oscillator) | momentum/awesome_osc.py |

### 2.2 Volatilidad (8 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | Bollinger Bands | volatility/bollinger.py |
| 2 | ATR (Average True Range) | volatility/atr.py |
| 3 | Keltner Channels | volatility/keltner.py |
| 4 | Donchian Channels | volatility/donchian.py |
| 5 | Standard Deviation | volatility/std_dev.py |
| 6 | Historical Volatility | volatility/hist_vol.py |
| 7 | Chaikin Volatility | volatility/chaikin_vol.py |
| 8 | Normalized Average True Range | volatility/natr.py |

### 2.3 Tendencia (10 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | SMA (Simple Moving Average) | trend/sma.py |
| 2 | EMA (Exponential MA) | trend/ema.py |
| 3 | WMA (Weighted MA) | trend/wma.py |
| 4 | MACD | trend/macd.py |
| 5 | ADX (Average Directional Index) | trend/adx.py |
| 6 | Ichimoku Kinko Hyo | trend/ichimoku.py |
| 7 | Supertrend | trend/supertrend.py |
| 8 | Parabolic SAR | trend/parabolic_sar.py |
| 9 | AMA (Adaptive Moving Avg) | trend/ama.py |
| 10 | Vortex Indicator | trend/vortex.py |

### 2.4 Volumen (7 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | OBV (On Balance Volume) | volume/obv.py |
| 2 | VWAP (Volume Weighted Avg Price) | volume/vwap.py |
| 3 | Accumulation/Distribution | volume/ad.py |
| 4 | Volume SMA | volume/volume_sma.py |
| 5 | Price Volume Trend | volume/pvt.py |
| 6 | Force Index | volume/force_index.py |
| 7 | Elder's Force | volume/elders_force.py |

### 2.5 Ciclos (8 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | Hilbert Transform (HT) | cycles/hilbert.py |
| 2 | Dominant Cycle Period | cycles/dominant_cycle.py |
| 3 | SineWave | cycles/sine_wave.py |
| 4 | Trend vs Cycle Mode | cycles/trend_cycle.py |
| 5 | MESA Adaptive MA | cycles/mama.py |
| 6 | FAMA (Following AMA) | cycles/fama.py |
| 7 | Ehlers Roofing Filter | cycles/roofing_filter.py |
| 8 | Autocorrelation Period | cycles/autocorrelation.py |

### 2.6 Patrones de Chart (7 indicadores)
| # | Indicador | Archivo |
|---|-----------|---------|
| 1 | Double Top/Bottom | patterns/double_top_bottom.py |
| 2 | Head & Shoulders | patterns/head_shoulders.py |
| 3 | Triangle Pattern | patterns/triangle.py |
| 4 | Flag/Pennant | patterns/flag_pennant.py |
| 5 | Wedge Pattern | patterns/wedge.py |
| 6 | Gap Detection | patterns/gap.py |
| 7 | Support/Resistance levels | patterns/support_resistance.py |

**Total: 50 indicadores**

## 3. Interfaz Base

```python
class TechnicalIndicator:
    """Interfaz base para todos los indicadores."""
    name: str
    category: str
    requires_periods: int
    
    def calculate(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        """Añade columna(s) al DataFrame con el resultado."""
        raise NotImplementedError
    
    def score(self, df: pd.DataFrame) -> float:
        """Retorna score de señalización (0-100)."""
        raise NotImplementedError
```

## 4. Sistema de Scoring

Cada indicador contribuye al `pegaton_score` con peso configurable:

```python
INDICATOR_WEIGHTS = {
    'momentum': 0.20,    # 5 indicadores clave * weight
    'volatility': 0.15,
    'trend': 0.25,
    'volume': 0.15,
    'cycles': 0.10,
    'patterns': 0.15,
}
```

La función `composite_score()` en `scoring.py` combina:
```
composite = Σ(indicator_score_i × weight_i × category_weight)
```

## 5. Módulo Central

### `backend/app/core/technical/registry.py`
- Decorador `@register_indicator(category, name)` para auto-registro
- `IndicatorRegistry` — catálogo de indicadores disponibles
- `list_indicators(category=None) → list`

### `backend/app/core/technical/scoring.py`
- `calculate_composite_score(indicators_results, weights) → float`
- `generate_technical_report(df, indicators) → dict`

## 6. Endpoints API

### GET `/api/v1/technical/indicators`
- Response: `{ indicators: [{name, category, requires_periods}, ...] }`

### GET `/api/v1/technical/{category}`
- Response: `{ category_indicators: [{..., score, signal}, ...] }`

### GET `/api/v1/technical/{indicator}/{ticker}`
- Query params: `period=14`, `from=...`, `to=...`
- Response: `{ ticker, indicator, values: [{date, value}, ...] }`

## 7. Criterios de Aceptación

1. [ ] 6 categorías implementadas: Momentum, Volatilidad, Tendencia, Volumen, Ciclos, Patrones
2. [ ] Cada indicador como módulo independiente en `technical/`
3. [ ] Al menos 50 indicadores disponibles
4. [ ] Contribuyen al scoring general con peso configurable
5. [ ] Tests unitarios para cada indicador

## 8. Restricciones

- Usar numpy/pandas del entorno existente (venv)
- Cada indicador debe tener tests en `tests/technical/`
- Documentación del indicador como docstring en el módulo
- Rendimiento: indicador simple < 5ms, compuesto < 20ms

---

**Spec creada:** 2026-05-13 | **SDD Nivel:** 2