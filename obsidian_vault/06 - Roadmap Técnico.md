# Roadmap Técnico y Estado Actual

## 🚀 MVP — Estado Actual (1 de Mayo 2026)

### ✅ Completado

#### Infraestructura
- [x] Estructura del proyecto creada
- [x] Entorno virtual Python con dependencias
- [x] API Keys configuradas (FRED + Twelve Data)
- [x] Base de datos SQLite operativa

#### Backend (Python/FastAPI)
- [x] Script de ingesta macro (10 indicadores FRED, diario)
- [x] Script de ingesta de precios (200 días históricos SPY/EURUSD/BTC)
- [x] Módulo de análisis macro (scoring con 8 indicadores ponderados)
- [x] Módulo de análisis técnico (RSI, MACD, SMA50, SMA200)
- [x] Motor de Señales: Pegaton Score (40% macro + 60% técnico)
- [x] API REST completa (FastAPI en puerto 8000)
- [x] Endpoint `/api/v1/score/` (todos los activos)
- [x] Endpoint `/api/v1/score/{symbol}` (por activo)
- [x] Endpoint `/api/v1/score/query?symbol=X` (para símbolos con /)
- [x] Endpoint `/api/v1/score/symbols` (lista de activos)
- [x] Endpoint `/health`

#### Frontend
- [x] Webapp HTML/JS simple con:
  - Panel macro con indicadores e interpretación
  - Tarjetas de activos con score circular y acción
  - Detalles técnicos (RSI, MACD, SMA)
  - Auto-refresh cada 30 segundos
  - Diseño oscuro "dark theme"

#### Automatización
- [x] Cron job diario 05:00 UTC para ingesta macro automática

#### Conocimiento (Obsidian Vault)
- [x] 00 - Índice
- [x] 01 - Visión del Proyecto
- [x] 02 - Backlog MVP
- [x] 03 - Arquitectura de Agentes
- [x] 04 - Fuentes de Datos
- [x] 06 - Roadmap Técnico (este documento)
- [x] 99 - Recursos y Enlaces

### 📊 Scores Actuales (1 Mayo 2026)

| Activo | Score | Acción | RSI | MACD | SMA50 | SMA200 |
|--------|-------|--------|-----|------|-------|--------|
| **SPY** | 50.7 | 🟡 MANTENER | 79.1 (sobrecompra) | 🟢 alcista | +5.95% | +7.36% |
| **EUR/USD** | 54.5 | 🟡 MANTENER | 43.5 (neutral) | 🔴 bajista | +0.78% | +0.40% |
| **BTC/USD** | 46.9 | 🟡 MANTENER | 53.8 (neutral) | 🔴 bajista | +8.15% | -6.86% |

### 🎯 Pendiente para MVP Completo
- [ ] Pulir frontend (estilos, animaciones)
- [ ] Añadir watchlist editable
- [ ] Añadir matrix de acciones (¿Qué hacer hoy?)
- [ ] Añadir portfolio tracker manual
- [ ] Mejorar algoritmo de score (ajustar umbrales)
- [ ] Añadir más indicadores macro (ISM, NFP actual)
- [ ] Backtesting rápido de señales históricas

### 🗺️ Roadmap a Futuro
1. **Fase 2: Acceso Remoto** → VPS básico ($5-10/mes)
2. **Fase 3: App Móvil** → APK Android (Flutter)
3. **Fase 4: Comercialización** → App Store (freemium/pago)

---
*Actualizado: 1 Mayo 2026*  
*Próximo hito: Frontend pulido + Watchlist editable*