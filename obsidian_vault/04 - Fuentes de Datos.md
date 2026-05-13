# Fuentes de Datos para PEGATON INVEST INTELLIGENCE

## 📊 Resumen de Investigación Completada
*(Basado en análisis previo de agentes de apoyo - ver informe completo en `/root/informe_macro.txt`)*

### 🥇 Fuentes Recomendadas para el MVP

#### 1. **FRED (Federal Reserve Economic Data)** - PRIORIDAD MÁXIMA
- **Tipo**: Indicadores macroeconómicos oficiales de EE.UU.
- **Datos clave para nuestro score**:
  - Tasas de interés: FEDFUNDS (Fed Funds), DGS10 (rendimiento bono 10A)
  - Inflación: CPIAUCSL (IPC urbano), PCEPI (índice de precios PCE)
  - Actividad económica: ISMAN (ISM Manufacturero PMI), ISMSV (ISM Servicios PMI)
  - Empleo: PAYEMS (nóminas no agrícolas), UNRATE (tasa de desempleo)
  - Líderes: UMCSENT (Confianza del Consumidor UMich), INDPRO (Producción Industrial)
- **Frecuencia**: Diario/mensual según serie
- **API**: REST JSON (muy simple)
- **Límite gratuito**: 120 req/min (sin clave) → **ilimitado con registro gratuito** (registro en 2 minutos)
- **Ejemplo llamada**:
  ```
  https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key=TU_KEY&file_type=json&observation_start=2024-01-01
  ```
- **Ventajas**: Datos oficiales, serie histórica larga, metadatos excelentes, sin costo real
- **Desventajas**: Solo EE.UU. (pero cubre nuestros activos iniciales)

#### 2. **Twelve Data** - PRIORIDAD ALTA (Para Precios)
- **Tipo**: Datos de precios en tiempo real y históricos
- **Datos clave**:
  - Precios OHLCV para: SPX (S&P 500), EUR/USD, BTC/USD
  - Algunos indicadores macro básicos (tasas de interés de BCs, CPI EE.UU./Eurozona)
  - Endpoint "economic" para algunos indicadores
- **Frecuencia**: Tiempo real (tick) / 1min / diario
- **API**: REST JSON + **WebSocket** (para streaming de ticks)
- **Límite gratuito**: 800 req/día, 8 req/min (plan gratuito); WebSocket ilimitado para 1 conexión en gratuito
- **Ventajas**: 
  - Precios en tiempo real para nuestros 3 activos base
  - WebSocket ideal para análisis técnico dinámico
  - Cobertura decente de Forex y cripto
  - Fácil de usar
- **Desventajas**: Límite de REST podría requerir caché o WebSocket para alta frecuencia
- **Ejemplo llamada REST**:
  ```
  https://api.twelvedata.com/time_series?symbol=SPX&interval=1day&outputsize=500&apikey=TU_KEY
  ```
- **Ejemplo WebSocket**:
  ```
  wss://ws.twelvedata.com/markets?apikey=TU_KEY
  ```

#### 3. **Alpha Vantage** - PRIORIDAD MEDIA (Como Respaldo)
- **Tipo**: Datos financieros y algunos indicadores macro
- **Datos clave**:
  - Precios OHLCV de acciones/forex/cripto
  - Indicadores macro básicos: inflación (CPI), tipo de cambio
  - Funciones técnicas integradas (SMA, EMA, RSI, MACD, etc.)
- **Frecuencia**: Intradía (1min), diario, semanal, mensual
- **API**: REST JSON/CSV
- **Límite gratuito**: 5 req/min, 500 req/día
- **Ventajas**:
  - Muy fácil de usar
  - Salida CSV útil para pruebas rápidas
  - Algunas funciones técnicas built-in
- **Desventajas**: Límite de rate más estricto que Twelve Data
- **Ejemplo llamada**:
  ```
  https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=SPX&apikey=TU_KEY&datatype=csv
  ```

#### 4. **World Bank / OECD** - PRIORIDAD SUPPLEMENTAL
- **Tipo**: Indicadores macro globales y de líderes internacionales
- **Datos clave para enriquecimiento**:
  - PIB crecimiento (países/regiones)
  - Inflación global
  - PMI manufacturero de UE, Japón, etc.
  - Indicadores líderes OECD
  - Balances comerciales
- **Frecuencia**: Anual/trimestral (según indicador)
- **API**: REST JSON (sin clave requerida)
- **Límite gratuito**: Ilimitado (uso razonable)
- **Ventajas**:
  - Cobertura global excelente
  - Útil para análisis de régimen internacional y líderes
  - Sin costo ni registro
- **Desventajas**: Baja frecuencia (no ideal para señales intradiarias)
- **Ejemplo llamada World Bank**:
  ```
  http://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.KD.ZG?format=json
  ```

### 🏗️ Arquitectura de Ingesta de Datos (MVP)

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   CRON JOB      │───▶│   FRED API       │───▶│  Base SQLite:      │
│  (diario a las  │    │                  │    │  macro_indicators  │
│   00:05 UTC)    │    │  Series:         │    │  (fecha, indicador,│
│                 │    │  - FEDFUNDS      │    │   valor, fuente)   │
└─────────────────┘    │  - CPIAUCSL      │    └────────────────────┘
                       │  - PCEPI         │
                       │  - ISMAN         │
                       │  - ISMSV         │
                       │  - PAYEMS        │
                       │  - UNRATE        │
                       └──────────────────┘
                               │
                               ▼
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│ WEBSOCKET/POLL  │───▶│ Twelve Data API  │───▶│ Base SQLite:       │
│  (cada 5min o   │    │                  │    │  precios_ohlcv     │
│   WebSocket)    │    │  Símbolos:       │    │  (timestamp, símb, │
│                 │    │  - SPX           │    │   open,high,low,   │
└─────────────────┘    │  - EUR/USD       │    │   close,volume)    │
                       │  - BTC/USD       │    └────────────────────┘
                       └──────────────────┘
```

### 📋 Plan de Acción para Ingesta de Datos

#### Fase Inmediata (Día 1-2):
1. **Registrarse en**:
   - [FRED](https://fred.stlouisfed.org/) → obtener API key (gratis, inmediato)
   - [Twelve Data](https://twelvedata.com/) → obtener API key (plan gratuito)
   - (Opcional) [Alpha Vantage](https://www.alphavantage.co/) → API key gratuita

2. **Crear scripts de prueba**:
   - `scripts/test_fred.py`: Obtener último valor de FEDFUNDS, CPIAUCSL, ISMAN
   - `scripts/test_twelvedata.py`: Obtener último precio de SPX, EUR/USD, BTC/USD vía REST
   - (Opcional) `scripts/test_websocket.py`: Conectar a WebSocket de Twelve Data para 1 símbolo

3. **Diseñar tabla SQLite**:
   ```sql
   CREATE TABLE macro_indicators (
       id INTEGER PRIMARY KEY,
       fecha DATE NOT NULL,
       indicador TEXT NOT NULL,
       valor REAL NOT NULL,
       fuente TEXT DEFAULT 'FRED',
       UNIQUE(fecha, indicador)
   );

   CREATE TABLE precios_ohlcv (
       id INTEGER PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,
       simbolo TEXT NOT NULL,
       open REAL,
       high REAL,
       low REAL,
       close REAL,
       volume REAL,
       UNIQUE(timestamp, simbolo)
   );
   ```

4. **Implementar lógica de normalización**:
   - Para cada indicador macro, calcular z-score sobre ventana de 60 días:
     ```
     z = (valor_actual - media_60d) / std_60d
     ```
   - Para precios, calcular indicadores técnicos (RSI, MACD) sobre las velas

### ⚠️ Consideraciones de Límites y Costos

| Fuente | Límite Gratuito | Riesgo de Saturación | Estrategia de Mitigación |
|--------|-----------------|----------------------|--------------------------|
| **FRED** | 120 req/min (sin clave) → **ilimitado con clave** | Muy bajo (solo ~10 indicadores diarios) | Registrar clave; cachear series poco cambiantes |
| **Twelve Data** | 800 req/día, 8 req/min | Medio si se hacen muchos REST; **WS ilimitado en gratuito** | **Preferir WebSocket para precios**; usar REST solo para metadatos históricos; implementar caché de 5min |
| **Alpha Vantage** | 5 req/min, 500 req/día | Medio si se usan muchos endpoints | Limitar a llamadas de respaldo; usar Twelve Data como primario |
| **World Bank/OECD** | Ilimitado (uso justo) | Bajo | Ninguna acción necesaria |
| **Investing.com** (calendario) | 500 req/día (gratuito) | Bajo si solo para eventos del día | Cachear eventos diarios; actualizar cada 6h |

### 💰 Estimación de Costos a Largo Plazo

| Etapa | Servicios | Costo Mensual Estimado | Comentario |
|-------|-----------|------------------------|------------|
| **MVP Local** | Ninguno (APIs gratuitas) | $0 | Todo en máquina local |
| **Etapa de Acceso Remoto** | VPS básico (DigitalOcean/Linode) | $5-10/mes | 1GB RAM, 25GB SSD suficiente para inicio |
| **Etapa de Crecimiento** | VPS medio + posibles APIs premium | $20-50/mes | Si se necesitan más límites o datos especializados |
| **Etapa de Comercialización** | Infraestructura escalable | $50-200+/mes | Dependiendo de usuarios activos; compensado por ingresos |

### 📂 Archivos de Referencia
- **Informe completo de investigación**: `/root/informe_macro.txt`
- **Plantilla para seguimiento de límites**: `docs/limites_api.md` (por crear)
- **Script de ingesta macro**: `backend/scripts/ingest_macro.py` (por crear)
- **Script de ingesta precios**: `backend/scripts/ingest_precios.py` (por crear)

### ✅ Próximos Pasos Confirmados
1. Juan Carlos proporciona API keys de FRED y Twelve Data (o yo guío el registro)
2. Creo los scripts de ingesta inicial y los pruebo
3. Implementamos la lógica de normalización y cálculo de score básico
4. Construimos el endpoint `/score/{symbol}` que combina macro (40%) + técnico (60%)

---
*Nota: Este documento se actualizará a medida que probemos las integraciones y descubramos mejores prácticas o limitaciones inesperadas.*

*Generado por: Hermes Agent (Project Manager Orquestador)*  
*Fecha: $(date)*