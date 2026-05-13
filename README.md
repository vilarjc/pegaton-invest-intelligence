# ⚡ PEGATON INVEST INTELLIGENCE

Sistema de inteligencia de inversión que combina análisis **macroeconómico** (40%) y **técnico** (60%) para generar señales de compra/venta en tiempo real, con arquitectura multi-agente y control inteligente de costos de IA.

## 🚀 Acceso
```
http://100.64.64.58:8000/
```
Via Tailscale. 7 páginas: Panel Central, Inversor, Presupuesto, Procesos, Salud, Agentes, Proyectos.

## 🏗️ Arquitectura

### Backend
- **Python 3.11 + FastAPI** — API REST en puerto 8000
- **SQLite** — Base de datos local (`data/pegaton.db`)
- **FRED API** — 8 indicadores macroeconómicos (Fed Funds, CPI, empleo, etc.)
- **Twelve Data API** — Precios OHLCV en tiempo real (SPY, EUR/USD, BTC/USD + símbolos on-demand)
- **DeepSeek API** — Balance en vivo para control de presupuesto

### Frontend
- **HTML/CSS/JS vanilla** — Sin dependencias, diseño oscuro responsive
- **Auto-refresh 30s** — Datos en vivo sin recargar página
- **localStorage** — Watchlist y portfolio persistente en el navegador

### Agentes
| Rol | Descripción |
|-----|-------------|
| 👑 PM Orquestador | Coordina todos los agentes, planifica, asigna tareas |
| 📊 Agente Inversor | Motor de señales Pegaton Score (macro + técnico) |
| 🌍 Experto Macro | Analiza indicadores económicos y regímenes |
| 📈 Experto Técnico | Patrones, divergencias, RSI/MACD/SMA |
| ₿ Experto Cripto | Métricas on-chain, correlaciones |
| 💻 Programador | Implementa APIs, algoritmos, pipelines |

### Modelos de IA
| Modelo | Costo IN/M | Costo OUT/M | Uso |
|--------|-----------|------------|-----|
| DeepSeek V4 Flash | $0.14 | $0.28 | Tareas simples/medias |
| DeepSeek Reasoner | $0.55 | $2.19 | Tareas complejas/críticas |

## 📊 Scores en Vivo

| Activo | Score | Acción |
|--------|-------|--------|
| SPY (S&P 500) | 50.7 | 🟡 MANTENER |
| EUR/USD | 54.5 | 🟡 MANTENER |
| BTC/USD | 46.9 | 🟡 MANTENER |

## ⏰ Jobs Automáticos
| Job | Horario | Función |
|-----|---------|---------|
| 🌅 Ingesta Macro | 05:00 UTC | FRED indicators |
| 📈 Ingesta Precios | 05:30 UTC | Twelve Data (incremental) |
| 🩺 Health Check | Cada 5min | Reinicio automático |
| 💰 Balance DeepSeek | Cada hora | Snapshot de saldo |

## 📁 Estructura del Proyecto
```
/root/pegaton_invest_intelligence/
├── backend/
│   ├── app/              # FastAPI app
│   │   ├── api/v1/       # Endpoints REST
│   │   └── core/         # Lógica de negocio
│   ├── scripts/          # Scripts de ingesta y utilidades
│   └── data/             # Base SQLite + JSONs
├── frontend/             # Páginas web
├── obsidian_vault/       # Documentación del proyecto
├── deploy/               # Systemd service file
└── .env                  # API keys
```

## 💰 Presupuesto
- Recarga: $6.03 saldo actual en DeepSeek
- Límite proyecto: $3.00 (alerta al 80%)
- Límites: $1/día · $3/semana · $5/mes

## 🗺️ Roadmap
- [x] **Fase 1:** MVP Local (backen + frontend + API)
- [x] **Fase 1b:** Landing page, budget tracker, health dashboard
- [x] **Fase 1c:** Watchlist editable, portfolio tracker, matriz de acción
- [ ] **Fase 2:** Agentes expertos especializados
- [ ] **Fase 3:** App Android (Flutter)
- [ ] **Fase 4:** Comercialización

## 🔧 Mantenimiento
```bash
# Iniciar servidor
./start.sh

# Detener servidor
./stop.sh

# Tracking de tareas (registrar uso de IA)
python backend/scripts/track_task.py pegaton deepseek-v4-flash <tokens_in> <tokens_out> "descripción"

# Ver presupuesto
python backend/scripts/check_deepseek_balance.py
```

---
*Creado: 1 Mayo 2026 · v0.2*

## 🏆 Olympiad Widget Factory

Sistema de desarrollo de widgets por equipos compitiendo. Servidor en puerto **8765**.

**Documentación completa:** [`OLYMPIAD.md`](OLYMPIAD.md)

| Página | URL | Propósito |
|--------|-----|-----------|
| 🧪 Auditoría | `/widget-auditoria` | Comparar equipos por sección |
| ⭐ Evaluador | `/widget-evaluator?widget=:id` | Detalle completo de widget |
| 📊 Inversor | `/inversor` | Dashboard final |

**Cada 4h (0 LLM):** Fear & Greed (`download_fear_greed.py`) + Macro (`ingest_macro.py`)
**Base de datos:** `harness.db` — `widgets`, `fear_greed_snapshots`, `macro_snapshots`
**Recuperación:** Cargar skill `olympiad-widget-factory` y seguir `OLYMPIAD.md`