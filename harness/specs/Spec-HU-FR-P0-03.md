# Spec-HU-FR-P0-03: Sistema de Alertas Configurable
## Epic: EP-FR-001 | Prioridad: P0 (Crítico) | Estado: Spec

---

## 1. Descripción

Motor de alertas basado en reglas que permite crear condiciones de vigilancia sobre indicadores técnicos, macro y Fear & Greed. Canales de notificación: Telegram bot, email, webhook, in-app.

## 2. Arquitectura

```
┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│  Data Feed   │───▶│  Rule Engine │───▶│  Dispatcher    │
│  (ticks/DB)  │    │  (eval loop) │    │  (notificación)│
└──────────────┘    └──────────────┘    └───────┬────────┘
                                                │
                           ┌──────────┬──────────┼──────────┐
                           ▼          ▼          ▼          ▼
                      Telegram    Email     Webhook     In-App
```

## 3. Motor de Reglas

### 3.1 Estructura de Regla
```python
Rule = {
    id: str,
    name: str,
    enabled: bool,
    conditions: [Condition],       # AND/OR logic tree
    actions: [Action],             # qué hacer cuando se dispara
    cooldown_minutes: int,         # evitar spam
    last_triggered: datetime | None
}

Condition = {
    type: str,                     # "indicator", "threshold", "crossover", "fear_greed"
    field: str,                    # "rsi", "macd", "price", "fear_greed_index"
    operator: str,                 # ">", "<", ">=", "<=", "==", "crosses_above", "crosses_below"
    value: float | str,            # umbral o ticker referencia
    lookback: int = 0              # número de periodos para comparar
}

Action = {
    type: str,                     # "telegram", "email", "webhook", "in_app"
    target: str,                   # chat_id, email, url, user_id
    message_template: str          # "Alerta: {ticker} RSI={value} cruzó {threshold}"
}
```

### 3.2 Tipos de Condición

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `threshold` | Valor cruza umbral | RSI < 30 |
| `crossover` | Indicador cruza otro | MACD cruza signal |
| `fear_greed` | Umbral de Fear & Greed | F&G < 25 (Extreme Fear) |
| `volume_spike` | Volumen anómalo | Volume > 2× media 20d |
| `price_level` | Nivel de precio | Precio cruza SMA 50 |
| `macro_change` | Cambio macro | PMI < 50, yield_curve inversion |

## 4. Módulos Python

### 4.1 `backend/app/core/alerts/rule_engine.py`
- `RuleEngine` — evalúa reglas cada tick/minuto
- `evaluate_rule(rule, data) → bool`
- Soporta AND/OR combinados en conditions

### 4.2 `backend/app/core/alerts/dispatcher.py`
- `AlertDispatcher` — envía alertas por canal
- Canales: Telegram (bot), SMTP (email), HTTP POST (webhook), DB (in-app)
- Rate limiting: cooldown por regla configurable

### 4.3 `backend/app/core/alerts/conditions.py`
- Funciones de evaluación de condición
- `check_threshold(value, operator, threshold) → bool`
- `check_crossover(series_a, series_b) → bool`
- `check_volume_spike(current, historical_avg, multiplier) → bool`

### 4.4 `backend/app/api/v1/endpoints/alerts.py`
- CRUD completo de reglas
- `POST /api/v1/alerts` — crear regla
- `GET /api/v1/alerts` — listar reglas
- `GET /api/v1/alerts/{id}` — detalle
- `PUT /api/v1/alerts/{id}` — actualizar
- `DELETE /api/v1/alerts/{id}` — eliminar
- `GET /api/v1/alerts/history` — historial de alertas disparadas

## 5. Tablas de Base de Datos

```sql
CREATE TABLE alert_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    conditions_json TEXT NOT NULL,
    actions_json TEXT NOT NULL,
    cooldown_minutes INTEGER DEFAULT 60,
    last_triggered TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    condition_met TEXT NOT NULL,
    actual_value REAL,
    message TEXT,
    channel TEXT,
    sent INTEGER DEFAULT 0,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
);

CREATE INDEX idx_alert_history_rule ON alert_history(rule_id);
CREATE INDEX idx_alert_history_time ON alert_history(triggered_at DESC);
```

## 6. Endpoints API

### POST `/api/v1/alerts`
- Body: `{ name, conditions: [...], actions: [...], cooldown_minutes }`
- Response 201: `{ id, status: "created" }`

### GET `/api/v1/alerts`
- Response 200: `{ rules: [{id, name, enabled, conditions, actions, cooldown}] }`

### PUT `/api/v1/alerts/{id}`
- Body: `{ name, enabled, conditions, actions, cooldown_minutes }`
- Response 200: `{ status: "updated" }`

### DELETE `/api/v1/alerts/{id}`
- Response 200: `{ status: "deleted" }`

### GET `/api/v1/alerts/history?rule_id=xxx&limit=50`
- Response 200: `{ history: [{rule_id, triggered_at, condition_met, message, channel}] }`

## 7. Criterios de Aceptación

1. [ ] CRUD de reglas de alerta desde API/DB
2. [ ] Al menos 6 tipos de condición implementados
3. [ ] Canales: Telegram bot, email, webhook
4. [ ] Historial de alertas disparadas consultable
5. [ ] Usuario puede crear regla desde UI del dashboard

## 8. Restricciones

- Almacenamiento de reglas en harness.db (no pegaton.db)
- Evaluación en loop: cada 60s evalúa reglas activas
- Cooldown mínimo entre alertas de la misma regla: 1 minuto
- Soporte mínimo: 50 reglas activas simultáneamente

---

**Spec creada:** 2026-05-13 | **SDD Nivel:** 2