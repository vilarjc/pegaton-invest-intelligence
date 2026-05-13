# Spec-HU-FR-P0-01: Integración de Datos en Tiempo Real (WebSockets)
## Epic: EP-FR-001 | Prioridad: P0 (Crítico) | Estado: Spec

---

## 1. Descripción

Sistema de integración de datos financieros en tiempo real mediante WebSockets. Proporciona precios tick-by-tick, volumen intradía y order book depth con actualización < 1s.

## 2. Fuentes de Datos

| Fuente | Endpoint WSS | Mercado | Fallback |
|--------|-------------|---------|----------|
| Yahoo Finance WebSocket | wss://stream.finance.yahoo.com | US equities | Finnhub WS |
| Finnhub WebSocket | wss://ws.finnhub.io | US/global | Polygon |
| Polygon.io | wss://socket.polygon.io/stocks | US equities | Yahoo |

## 3. Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ WS Client   │────▶│  Message     │────▶│  DB Writer   │
│ (asyncio)   │     │  Handler     │     │  (SQLite/PG) │
└─────────────┘     └──────────────┘     └──────────────┘
       │                   │                    │
       │              ┌──────────┐              │
       └─────────────▶│ Cache    │◀─────────────┘
                      │ (Redis)  │
                      └──────────┘
```

## 4. Módulos Python

### 4.1 `backend/app/core/realtime/ws_manager.py`
- Clase `WebSocketManager` — gestiona conexiones, reconnection, backoff
- Métodos: `connect()`, `disconnect()`, `subscribe(tickers)`, `unsubscribe(tickers)`, `reconnect()`
- Exponential backoff: base=1s, max=60s, jitter=0.1

### 4.2 `backend/app/core/realtime/handler.py`
- Clase `MessageHandler` — parsea mensajes WS según fuente
- Normaliza datos a schema unificado:
```python
{
    "ticker": "AAPL",
    "timestamp": "2026-05-13T20:30:00.000Z",
    "price": 189.42,
    "volume": 15234,
    "bid": 189.40,
    "ask": 189.44,
    "source": "yahoo|finnhub|polygon"
}
```

### 4.3 `backend/app/core/realtime/db_writer.py`
- Escribe ticks en `realtime_ticks` table
- TTL: 30 días rolling window
- Batch insert cada 100ms o 50 mensajes (lo primero que ocurra)

### 4.4 `backend/app/api/v1/endpoints/realtime.py`
- `GET /api/v1/realtime/{ticker}` — último tick disponible
- `WS /ws/ticker/{ticker}` — stream WebSocket al cliente
- `GET /api/v1/realtime/{ticker}/history` — últimos N ticks

## 5. Tablas de Base de Datos

```sql
CREATE TABLE realtime_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    volume INTEGER,
    bid REAL,
    ask REAL,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_rt_ticker_ts ON realtime_ticks(ticker, timestamp DESC);
CREATE INDEX idx_rt_source ON realtime_ticks(source);
```

## 6. Endpoints API

### GET `/api/v1/realtime/{ticker}`
- Response 200: `{ ticker, price, volume, bid, ask, timestamp, source }`
- Response 404: si no hay datos en las últimas 24h

### GET `/api/v1/realtime/{ticker}/history?limit=100`
- Response 200: `{ ticker, ticks: [{price, volume, timestamp}, ...] }`
- Query params: `limit` (default 100, max 1000), `from`, `to`

### WS `/ws/ticker/{ticker}`
- Conexión WebSocket persistente
- Envía JSON por tick nuevo: `{ ticker, price, volume, timestamp }`
- Auto-reconnect del lado del servidor

## 7. Criterios de Aceptación

1. [ ] WebSocket conectado y recibiendo datos de al menos 1 fuente
2. [ ] Precio, volumen y order book actualizados < 1s en DB
3. [ ] Reconnection automática con exponential backoff
4. [ ] Endpoint GET `/api/v1/realtime/{ticker}` funcional
5. [ ] 54 tests existentes + nuevos tests para WS module pasan

## 8. Restricciones

- Sin API keys de pago — solo fuentes gratuitas (Yahoo, Finnhub free tier)
- Manejar rate limits con graceful degradation
- Si WS cae, fallback a polling HTTP cada 5s
- Memory limit: buffer máximo 10000 ticks en RAM

---

**Spec creada:** 2026-05-13 | **SDD Nivel:** 2 (Spec Anchor)