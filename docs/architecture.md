# Arquitectura del Sistema de Señalización PEGATON

> **Proyecto:** Pegaton Invest Intelligence  
> **Tarea:** HU-PM-1 — PM/Arquitecto  
> **Fecha:** 2026-05-12  
> **SDD Nivel:** 2  

---

## 1. Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                     │
│                     puerto 8000                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ /api/v1/     │  │ /api/v1/     │  │ /api/v1/          │  │
│  │ score/*      │  │ news-sent-   │  │ signal*           │  │
│  │ /system/*    │  │   iment      │  │ /signals          │  │
│  │ /roundtable/ │  │ /fear-greed  │  │                   │  │
│  │ /eval/       │  │ /macro       │  │                   │  │
│  │ /objectives/ │  │ /technical   │  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬─────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE NEGOCIO                            │
│                                                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐  │
│  │  MacroEngine    │  │  TechEngine      │  │ SignalAPI  │  │
│  │  (macro.py)     │  │  (technical.py)  │  │ (signal.py)│  │
│  │                 │  │                  │  │            │  │
│  │ • 8 indicadores │  │ • RSI(14)        │  │ • Combina  │  │
│  │   FRED          │  │ • MACD           │  │   macro+tec│  │
│  │ • Scoring rules │  │ • SMA50          │  │ • Action   │  │
│  │ • Peso: varies  │  │ • SMA200         │  │   mapping  │  │
│  │ • Output: 0-100 │  │ • Peso: varies   │  │ • Output   │  │
│  └────────┬────────┘  │ • Output: 0-100  │  │   JSON     │  │
│           │           └────────┬─────────┘  └─────┬──────┘  │
│           │                     │                  │        │
│           ▼                     ▼                  ▼        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Score Combiner (score.py)                │    │
│  │  pegaton_score = 0.40 × macro + 0.60 × technical  │    │
│  │  + Action determination (ACTIONS thresholds)       │    │
│  └───────────────────────┬───────────────────────────┘    │
│                          │                                 │
└──────────────────────────┼─────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              pegaton.db (SQLite)                     │   │
│  │                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────────┐      │   │
│  │  │ macro_indicators │  │ precios_ohlcv        │      │   │
│  │  │ (FRED data)      │  │ (OHLCV por símbolo)  │      │   │
│  │  └──────────────────┘  └──────────────────────┘      │   │
│  │                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────────┐      │   │
│  │  │ news_sentiment   │  │ news_sentiment_      │      │   │
│  │  │ (artículos raw)  │  │ snapshots (resumen)  │      │   │
│  │  └──────────────────┘  └──────────────────────┘      │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │ olympiad_ratings | widget_adjustments | etc. │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────────┐   │
│  │ config/*.yaml         │    │ harness.db (gestión)    │   │
│  │ • macro_indicators.yml│    │ Tareas, Specs, Logs     │   │
│  │ • technical_indicato. │    │ Epics, Artifacts        │   │
│  │ • system.yaml         │    │ Decisiones              │   │
│  └──────────────────────┘    └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Frontend (widgets/)                     │   │
│  │                                                      │   │
│  │  • fear-greed-equipo-a.html  (Canvas gauge)         │   │
│  │  • fear-greed-equipo-b.html                          │   │
│  │  • fear-greed-equipo-c.html                          │   │
│  │  • news-sentimiento.html     (NEW — HU-NEWS-01)     │   │
│  │  → Todos: iframe-compatible, dark theme              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Flujo de Datos

### 2.1 Ingesta de Datos Macro (→ crontab, sin LLM)
```
FRED API → yfinance/fredapi → pegaton.db (macro_indicators)
         ↓
    macro_ingest.py (scripts/)
         ↓
    Crontab: cada 24h
```

### 2.2 Ingesta de Datos de Precio (→ crontab, sin LLM)
```
yfinance/TwelveData → pegaton.db (precios_ohlcv)
         ↓
    price_ingest.py (scripts/)
         ↓
    Crontab: cada 6h (diario) o on-demand
```

### 2.3 Flujo de Señalización Completo
```
1. Request: GET /api/v1/signal?symbol=SPY
2. FastAPI → signal.py (router)
3. signal.py llama a:
   a. macro_score()    → lee de pegaton.db → aplica reglas MACRO_SCORING
   b. technical_score() → lee OHLCV de pegaton.db → calcula RSI/MACD/SMA
4. score.py combina:
   pegaton_score = 0.40 × macro_score + 0.60 × technical_score
5. Aplica ACTIONS thresholds → determina acción (COMPRAR/ACUMULAR/MANTENER/REDUCIR/EVITAR)
6. Response JSON con:
   - symbol, timestamp, pegaton_score, action
   - macro_score, technical_score
   - factors (desglose macro + técnico con dirección)
   - details (valores crudos de indicadores)
```

### 2.4 Flujo de Sentimiento de Noticias
```
1. Ingesta crontab (cada 4h): ingest_news_sentiment.py
   → Google News RSS → VADER sentiment → news_sentiment table
   → Snapshot → news_sentiment_snapshots
2. Request: GET /api/v1/news-sentiment
   → Lee snapshot, calcula delta, keywords, distribution
   → Auto-refresh si snapshot > 4h viejo
3. Frontend: news-sentimiento.html → fetch('/api/v1/news-sentiment') → gauge Canvas
```

---

## 3. Interfaces entre Módulos

### 3.1 MacroEngine → Score Combiner
```json
{
  "macro_score": 49.0,
  "factors": [
    {"name": "FEDFUNDS", "score": 35.0, "weight": 0.20, "direction": "bajista"},
    {"name": "PAYEMS",   "score": 60.0, "weight": 0.15, "direction": "alcista"},
    ...
  ]
}
```

### 3.2 TechEngine → Score Combiner
```json
{
  "technical_score": 52.6,
  "factors": [
    {"name": "RSI(14)",  "score": 16.1, "weight": 0.30, "direction": "bajista"},
    {"name": "MACD",     "score": 65.0, "weight": 0.25, "direction": "alcista"},
    ...
  ]
}
```

### 3.3 Score Combiner → API Response
```json
{
  "symbol": "SPY",
  "timestamp": "2026-05-12T19:30:00Z",
  "pegaton_score": 51.2,
  "action": "🟡 MANTENER",
  "macro_score": 49.0,
  "technical_score": 52.6,
  "blend": { "macro_weight": 0.40, "technical_weight": 0.60 },
  "factors": { "macro": [...], "technical": [...], "summary": {...} },
  "details": { "macro": {...}, "technical": {...} }
}
```

---

## 4. Especificación del Endpoint `/signal`

### GET `/api/v1/signal`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `symbol` | string | `"SPY"` | Símbolo financiero |
| `include_details` | bool | `true` | Incluir desglose completo de factores |

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
  "factors": {
    "macro": [...],
    "technical": [...],
    "summary": {
      "factores_alcistas": 6,
      "factores_bajistas": 4,
      "factor_dominante": { "name": "SMA50", "direction": "alcista", "contribution": 17.5 }
    }
  },
  "details": {
    "macro": { "FEDFUNDS": {...}, ... },
    "technical": { "rsi": 75.8, ... }
  }
}
```

**Códigos de error:**
- `404` → Símbolo no encontrado / sin datos
- `503` → Datos macro no disponibles
- `500` → Error interno

### GET `/api/v1/signals` (multi-símbolo)
```json
{
  "timestamp": "2026-05-12T19:30:00Z",
  "count": 3,
  "signals": {
    "SPY":    { "pegaton_score": 51.2, "action": "🟡 MANTENER", ... },
    "EUR/USD": { "pegaton_score": 67.4, "action": "🔵 ACUMULAR", ... },
    "BTC/USD": { "pegaton_score": 42.1, "action": "🟡 MANTENER", ... }
  }
}
```

---

## 5. Configuración Centralizada (YAML + Python)

| Archivo | Contenido | Ubicación |
|---------|-----------|-----------|
| `config/macro_indicators.yaml` | Indicadores FRED, pesos, reglas | `config/` |
| `config/technical_indicators.yaml` | Pesos RSI/MACD/SMA, params | `config/` |
| `config/system.yaml` | Blend weights, thresholds, symbols, API config | `config/` |
| `pegaton_config.py` | Carga los YAML como constantes Python | `backend/app/core/` |

**Regla:** Si se cambia un parámetro → actualizar YAML PRIMERO → luego `pegaton_config.py`.

---

## 6. Tareas para el Programador (HU-PROG-1)

Cada subtarea tiene spec + criterios de aceptación:

| # | Tarea | Spec | Criterios de Aceptación |
|---|-------|------|------------------------|
| 1 | `scripts/macro_ingest.py` | Lee `config/macro_indicators.yaml`, obtiene datos FRED, guarda en `pegaton.db` | Ingesta ≥8 indicadores, ejecutable vía crontab sin LLM |
| 2 | `scripts/macro_scoring.py` | Lee datos de DB, aplica reglas de scoring, devuelve `macro_score()` | Score 0-100, ejemplo test con datos de muestra |
| 3 | `scripts/price_ingest.py` | Obtiene OHLCV vía yfinance/TwelveData, guarda en `precios_ohlcv` | Al menos 200 días de datos por símbolo |
| 4 | `scripts/technical_scoring.py` | Calcula RSI, MACD, SMA50, SMA200, devuelve `technical_score()` | Score 0-100 con desglose por factor |
| 5 | `scripts/signal_combiner.py` | Combina macro+técnico según `system.yaml`, devuelve señal final | Fórmula 0.40×macro + 0.60×técnico, acción correcta |
| 6 | `api/signal_api.py` | Endpoint GET /signal + /signals (FastAPI) | JSON correcto, códigos de error, docs |

**NOTA:** Los módulos `macro_scoring`, `technical_scoring` y `signal_combiner` ya están parcialmente implementados como funciones dentro de `macro.py`, `technical.py` y `score.py`. La tarea del programador incluye refactorizarlos en scripts independientes + exponer la API faltante.

---

## 7. Plan de Pruebas Unitarias

### 7.1 Test `test_macro.py`
```python
def test_macro_score_returns_dict():
    result = macro_score()
    assert 'macro_score' in result
    assert 0 <= result['macro_score'] <= 100

def test_macro_score_all_indicators_present():
    result = macro_score()
    details = result.get('details', {}).get('indicators', {})
    expected = {'FEDFUNDS', 'CPIAUCSL', 'PCEPI', 'PAYEMS', 'UNRATE', 'UMCSENT', 'INDPRO', 'DGS10'}
    assert set(details.keys()) == expected

def test_apply_scoring_rules_match():
    # Regla: <= 1.5 → score 80
    assert apply_scoring_rules(1.0, MACRO_SCORING['FEDFUNDS']['rules']) == 80.0

def test_apply_scoring_rules_default():
    # Valor muy alto, cae en default
    assert apply_scoring_rules(99.0, MACRO_SCORING['FEDFUNDS']['rules']) == 20.0
```

### 7.2 Test `test_technical.py`
```python
def test_rsi_calculation():
    series = pd.Series([100, 101, 102, 101, 100, 99, 98, 99, 100, 101, 102, 103, 104, 105, 104])
    r = rsi(series, 14)
    assert 0 <= r <= 100

def test_macd_bullish():
    series = pd.Series(range(50, 70, 1))  # uptrend
    m = macd(series)
    assert m['bullish'] == True

def test_sma_position_above():
    series = pd.Series([50] * 49 + [55])
    pos = sma_position(series, 50)
    assert pos['above'] == True
```

### 7.3 Test `test_score.py`
```python
def test_pegaton_score_range():
    result = pegaton_score('SPY')
    assert 0 <= result['pegaton_score'] <= 100

def test_pegaton_score_action():
    result = pegaton_score('SPY')
    assert 'action' in result
    assert any(result['pegaton_score'] in range(lo, hi+1) for lo, hi, *_ in ACTIONS)

def test_blend_weights_sum():
    assert MACRO_WEIGHT + TECHNICAL_WEIGHT == 1.0
```

### 7.4 Test `test_signal_api.py`
```python
def test_signal_endpoint_200():
    response = client.get("/api/v1/signal?symbol=SPY")
    assert response.status_code == 200
    data = response.json()
    assert 'pegaton_score' in data
    assert 'action' in data

def test_signal_endpoint_unknown_symbol():
    response = client.get("/api/v1/signal?symbol=NONEXISTENT")
    assert response.status_code == 404

def test_signal_missing_macro():
    # Simulate empty macro data
    response = client.get("/api/v1/signal?symbol=SPY")
    # If macro unavailable → 503
    assert response.status_code in [200, 503]
```

### 7.5 Test `test_config.py`
```python
def test_macro_weights_sum():
    total = sum(v['weight'] for v in MACRO_SCORING.values())
    assert abs(total - 1.0) < 0.001

def test_technical_weights_sum():
    total = sum(TECHNICAL_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_blend_weights_sum():
    assert MACRO_WEIGHT + TECHNICAL_WEIGHT == 1.0
```

---

## 8. Notas Técnicas

1. **Bug detectado:** El router `/signal` (`signal.py`) NO está registrado en `main.py`. Fix: agregar `app.include_router(signal_router, ...)`.

2. **Rutas faltantes en main.py:**
   - `/api/v1/macro` → futuro, comentado
   - `/api/v1/technical` → futuro, comentado
   - `/api/v1/signal` → **EXISTE en signal.py pero NO registrado → FIX REQUERIDO**

3. **Crontab recomendado:**
   ```
   # Ingesta macro diaria
   0 6 * * * /root/pegaton_invest_intelligence/venv/bin/python scripts/macro_ingest.py
   # Ingesta precios diaria
   0 7 * * * /root/pegaton_invest_intelligence/venv/bin/python scripts/price_ingest.py
   # Ingesta noticias cada 4h
   0 */4 * * * /root/pegaton_invest_intelligence/venv/bin/python scripts/ingest_news_sentiment.py
   ```