# 🏆 Olympiad Widget Factory — Sistema de Desarrollo por Equipos

> **Última actualización:** 8 Mayo 2026
> **Proyecto:** `/root/pegaton_invest_intelligence/`
> **Servidor:** `olympiad_server.py` en puerto **8765**
> **Base de datos:** `harness.db` (SQLite)

---

## 📋 1. ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────────┐
│                   olympiad_server.py                      │
│              Python HTTP Server (puerto 8765)              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Static   │  │  Widget  │  │  Fear &  │  │  Evalu-  │ │
│  │  Files    │  │  Factory │  │  Greed   │  │  ation   │ │
│  │  (HTML)   │  │  API     │  │  Engine  │  │  API     │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────┤
│                    harness.db (SQLite)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────┐ │
│  │  widgets │  │ olympiad_│  │ fear_greed_  │  │macro_│ │
│  │          │  │ ratings  │  │ snapshots    │  │snap  │ │
│  └──────────┘  └──────────┘  └──────────────┘  └──────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.1 Directorios clave

| Ruta | Propósito |
|------|-----------|
| `/root/pegaton_invest_intelligence/` | Raíz del proyecto |
| `olympiad_server.py` | Servidor HTTP (puerto 8765) |
| `harness.db` | Base de datos SQLite |
| `frontend/` | Páginas web estáticas |
| `frontend/widgets/` | HTML de cada widget (auto-contenido) |
| `frontend/coding-olympiad/html/` | Código fuente original de los concursos |
| `backend/scripts/` | Scripts de ingesta de datos |
| `harness/specs/` | Especificaciones de cada widget |

---

## 🗄️ 2. BASE DE DATOS — harness.db

### 2.1 Tabla: `widgets`

Registra cada widget en el sistema, su equipo, estado y evaluación.

```sql
CREATE TABLE widgets (
    id TEXT PRIMARY KEY,              -- 'fear-greed-a', 'macro', 'sentimiento'...
    name TEXT NOT NULL,               -- 'Fear & Greed', 'Indicadores Macroeconómicos'
    description TEXT,
    section TEXT DEFAULT '',           -- 'fear-greed', 'macro', 'sentimiento'...
    team_label TEXT DEFAULT '',        -- 'Equipo A', 'Equipo B', 'Equipo Principal'
    expert TEXT,                      -- 'Organizador', 'Experto en Macroeconomía'
    pm TEXT,                          -- 'Gemini 2.5 Flash', 'PM Macro'
    programmer TEXT,                  -- 'Tencent HY3', 'Equipo Programación'
    endpoint TEXT,                    -- '/api/v1/fear-greed', '/api/widgets/macro/data'
    html_file TEXT,                   -- 'fear-greed-equipo-a.html', 'macro.html'
    rating INTEGER DEFAULT 0,         -- 0-10 puntuación del usuario
    integrated INTEGER DEFAULT 0,     -- 0=no, 1=sí (aparece en dashboard inversor)
    status TEXT DEFAULT 'draft',      -- 'draft', 'spec', 'ready'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Widgets existentes (10 registros):**

| ID | Sección | Equipo | Rating | Integrado |
|----|---------|--------|--------|-----------|
| `fear-greed-a` | fear-greed | Equipo A | 9 | 1 |
| `fear-greed-b` | fear-greed | Equipo B | 10 | 1 |
| `fear-greed-c` | fear-greed | Equipo C | 9 | 0 |
| `macro` | macro | Equipo Principal | 8 | 1 |
| `sentimiento` | sentimiento | Equipo Principal | 8 | 1 |
| `tecnico` | tecnico | — | 0 | 0 |
| `cartera` | cartera | — | 0 | 0 |
| `flujos` | flujos | — | 0 | 0 |
| `regimen` | regimen | — | 0 | 0 |
| `mesaredonda` | mesaredonda | — | 0 | 0 |

### 2.2 Tabla: `fear_greed_snapshots`

Datos históricos del índice Fear & Greed (descargados cada 4h).

```sql
CREATE TABLE fear_greed_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score INTEGER NOT NULL,
    action TEXT DEFAULT 'Neutral',
    vix_value REAL,
    vix_score REAL,
    macro_score REAL,
    macro_details TEXT,         -- JSON
    sent_score REAL,
    sent_details TEXT,          -- JSON
    full_response TEXT,         -- JSON completo del compute (recomendado)
    captured_at TIMESTAMP
);
```

### 2.3 Tabla: `macro_snapshots`

Datos macroeconómicos históricos (descargados cada 4h desde http://100.64.64.58:18081/api/macro/history).

### 2.4 Tabla: `olympiad_ratings`

Ratings del concurso original (modelo → estrellas).

---

## 🛜 3. SERVIDOR — olympiad_server.py

**Puerto:** 8765
**Inicio:** `cd /root/pegaton_invest_intelligence && python3 olympiad_server.py`
**Frontend:** Sirve archivos estáticos desde `frontend/`

### 3.1 Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/widgets` | Lista todos los widgets |
| GET | `/api/widgets/:id` | Widget por ID |
| GET | `/api/widgets/sections` | Widgets agrupados por sección con equipos |
| GET | `/api/widgets/integrated` | Solo widgets integrados |
| GET | `/api/widgets/:id/data` | Datos + HTML del widget (lee html_file) |
| POST | `/api/widgets` | Crear/actualizar widget |
| POST | `/api/widgets/rate` | Puntuar widget `{widget_id, stars}` |
| POST | `/api/widgets/integrate` | Toggle integración `{widget_id}` |
| GET | `/api/v1/fear-greed` | Fear & Greed score desde DB real |
| GET | `/api/fullcode/:model` | Código HTML del concurso original |
| GET | `/api/ratings` | Ratings del concurso original |
| POST | `/api/ratings` | Guardar rating |
| GET | `/api/health` | Health check |

### 3.2 Rutas frontend

| URL | Archivo | Propósito |
|-----|---------|-----------|
| `/` | `index.html` | Hub principal con navegación |
| `/inversor` | `inversor.html` | Dashboard final con widgets integrados |
| `/widget-auditoria` | `widget-auditoria.html` | Comparación de equipos por sección |
| `/widget-evaluador` | `widget-evaluator.html` | Detalle completo de un widget |
| `/widgets/:file` | `widgets/:file` | Archivo HTML del widget |

---

## 📄 4. PÁGINAS FRONTEND

### 4.1 🧪 Auditoría → `/widget-auditoria`

Compara equipos compitiendo en una misma sección.

**Flujo JS:**
1. `init()` → fetch `/api/widgets/sections`
2. Renderiza tabs de secciones (fear-greed, macro, sentimiento...)
3. Carga sección activa → sub-tabs de equipos (A, B, C...)
4. Carga equipo activo:
   - Intentar fetch desde `w.endpoint` (ej: `/api/v1/fear-greed`)
   - **Si el endpoint no devuelve HTML** → fallback a `/widgets/:html_file` ✅
   - Cargar spec desde `/harness/specs/widget-:id-spec.md`
   - Cargar fullcode desde `/api/fullcode/:model`

**Renderizado:** Grid 3 columnas (Widget preview | Código | PM Spec) + barra de puntuación.

### 4.2 ⭐ Evaluador → `/widget-evaluator?widget=fear-greed-a`

Detalle completo de un widget.

**Secciones:**
- Widget preview en iframe
- Código fuente completo con resaltado
- Requerimiento original (brief)
- Análisis del PM (spec)
- Decisiones técnicas
- Puntuación (1-10) + Integrar
- Botón "Solicitar ajuste" (abre modal)

### 4.3 📊 Inversor → `/inversor`

Dashboard final. Solo muestra widgets con `integrated=1`.

### 4.4 Navegación unificada

```
[HUB] [Inversor] [Auditoría] [Evaluador]
```

Todas las páginas incluyen la misma `<nav>` con enlaces activos.

---

## 📦 5. WIDGETS EXISTENTES

### 5.1 Fear & Greed — 3 equipos (concurso original)

| Equipo | PM | Programador | Archivo | Estilo |
|--------|-----|------------|---------|--------|
| **A** 🏆 | Gemini 2.5 Flash | Tencent HY3 | `fear-greed-equipo-a.html` (434 líneas) | Velocímetro semicircular Canvas |
| **B** | Nemotron 3 Super | Owl Alpha | `fear-greed-equipo-b.html` (791 líneas) | Anillo glow circular Canvas |
| **C** | DeepSeek V4 Flash | DeepSeek V4 Flash | `fear-greed-equipo-c.html` (626 líneas) | Barra termómetro DOM |

**Fuente de datos:** `/api/v1/fear-greed` → desde `fear_greed_snapshots` (DB real)
**Campos que espera el widget:**
```json
{
  "score": 85,
  "action": "Codicia extrema",
  "action_emoji": "🔵",
  "timestamp": "...",
  "cacheado": true,
  "factores": {
    "vix": {"value": 17.1, "score": 71, "peso": "40%"},
    "macro": {"score": null, "peso": "35%", "detalles": {...}},
    "sentimiento": {"score": 100, "peso": "25%", "detalles": {
      "total_articles": 2,
      "positive": 2,
      "negative": 0
    }}
  }
}
```

### 5.2 Widgets funcionales (no concurso)

| Widget | Archivo | Endpoint datos | Estado |
|--------|---------|---------------|--------|
| **Macro** | `macro.html` | `/api/widgets/macro/data` → `macro_snapshots` | Ready ✅ |
| **Sentimiento** | `sentimiento.html` | `/api/widgets/sentimiento/data` | Ready ✅ |

### 5.3 Widgets en spec (pendientes de desarrollo)

| Sección | Descripción |
|---------|-------------|
| Análisis Técnico | Velas, RSI, MACD, medias móviles |
| Cartera | Distribución de activos, riesgo, rebalanceo |
| Flujos de Capital | Institucionales, ETFs, money market |
| Régimen de Mercado | Volatilidad, correlaciones, regime change |
| Mesa Redonda | Consenso entre modelos AI |

---

## 🔄 6. PIPELINE DE DATOS (Crons, 0 LLM)

Ambos crons se ejecutan **cada 4 horas** y NO usan modelos de IA.

### 6.1 Fear & Greed

```
0 */4 * * * → backend/scripts/download_fear_greed.py → fear_greed_snapshots
```

**Qué descarga:**
- VIX desde Yahoo Finance (vía `yfinance`)
- RSS de noticias financieras (MarketWatch, CNBC)
- Macro desde FRED (si `FRED_API_KEY` está configurada)

**Script:** `/root/pegaton_invest_intelligence/backend/scripts/download_fear_greed.py`
**Log:** `/var/log/fear_greed_cron.log`

### 6.2 Macro

```
0 */4 * * * → backend/scripts/ingest_macro.py → macro_snapshots
```

**Qué descarga:**
- VIX, DXY, S&P 500, Oro, Petróleo, PMIs, Inflación, Tasa Fed

**Fuente:** `http://100.64.64.58:18081/api/macro/history`
**Log:** `/var/log/ingest_macro.log`

---

## 📁 7. ARCHIVOS DE ESPECIFICACIÓN (Specs)

Ubicación: `harness/specs/`

| Archivo | Widget | Creado |
|---------|--------|--------|
| `widget-fear-greed-a-spec.md` | Fear & Greed Equipo A | 8 Mayo |
| `widget-fear-greed-b-spec.md` | Fear & Greed Equipo B | 8 Mayo |
| `widget-fear-greed-c-spec.md` | Fear & Greed Equipo C | 8 Mayo |
| `widget-macro-spec.md` | Indicadores Macro | 7 Mayo |
| `HU-1.2.md` | Spec técnica del score | Previo |

Cada spec contiene: especificación técnica, análisis del PM (decisiones de diseño), y decisiones técnicas del programador.

---

## 🧠 8. MAPA DE MODELOS (Fullcode)

Los archivos en `frontend/coding-olympiad/html/` contienen el código completo de cada modelo participante en el concurso original. Symlinks para acceso por equipo:

| Symlink | Apunta a | Modelo |
|---------|----------|--------|
| `equipo-a.html` → | `tencent-hy3.html` | Tencent HY3 (programador Equipo A) |
| `equipo-b.html` → | `owl-alpha.html` | Owl Alpha (programador Equipo B) |
| `equipo-c.html` → | `deepseek-v4pro.html` | DeepSeek V4 Pro (programador Equipo C) |

Endpoint: `/api/fullcode/:model` → sirve el HTML del archivo correspondiente.

---

## 🚀 9. PARA EMPEZAR DESPUÉS DE RESET

```bash
# 1. Ir al directorio
cd /root/pegaton_invest_intelligence

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Iniciar servidor
python3 olympiad_server.py &
# Servidor en http://0.0.0.0:8765

# 4. Verificar health
curl -s http://localhost:8765/api/health
# → {"status": "ok", "db": true}

# 5. Verificar DB
sqlite3 harness.db "SELECT COUNT(*) FROM widgets"
# → 10

# 6. Verificar datos Fear & Greed
sqlite3 harness.db "SELECT id, score, action FROM fear_greed_snapshots ORDER BY id DESC LIMIT 1"
# → debe mostrar score real

# 7. Si la DB está vacía, los seeds se ejecutan automáticamente
#    al iniciar el servidor (seed_widgets())

# 8. Si no hay datos de fear-greed, ejecutar descarga manual:
python3 backend/scripts/download_fear_greed.py
```

### 9.1 Recuperar crons perdidos

```bash
# Macro (cada 4h)
echo "0 */4 * * * cd /root/pegaton_invest_intelligence && python3 backend/scripts/ingest_macro.py >> /var/log/ingest_macro.log 2>&1" | crontab -

# Fear & Greed (cada 4h)
echo "0 */4 * * * cd /root/pegaton_invest_intelligence && /root/pegaton_invest_intelligence/venv/bin/python3 backend/scripts/download_fear_greed.py >> /var/log/fear_greed_cron.log 2>&1" | crontab -
```

### 9.2 Acceso vía navegador

```bash
# Si el servidor está en una máquina remota con Tailscale:
# http://pegaton:8765/widget-auditoria
# http://pegaton:8765/widget-evaluator?widget=fear-greed-a
# http://pegaton:8765/inversor
```

---

## ⚠️ 10. NOTAS CRÍTICAS

- **NUNCA re-desarrollar el widget Fear & Greed** — los 3 equipos ya existen y funcionan
- **Los widgets fear-greed esperan `data.factores` en el endpoint** — no aplanar nunca
- **Si el HTML del widget no se muestra en auditoría**, es porque el endpoint devuelve datos pero sin campo `html`. El fallback (cargar desde `widgets/:html_file`) debería resolverlo
- **Specs se sirven desde symlink**: `frontend/harness` → `../harness`
- **Si un widget está "cargando" infinito**, refrescar la página o verificar que el archivo HTML existe en `frontend/widgets/`
- **Agregar un nuevo equipo**: INSERT en `widgets` con mismo `section` y diferente `team_label`
- **Agregar nueva sección**: INSERT con nuevo `section`; aparecerá automáticamente en la auditoría
- **Para puntuar**: POST `/api/widgets/rate` con `{widget_id, stars}`
- **Para integrar**: POST `/api/widgets/integrate` con `{widget_id}`
- Los archivos de fullcode están en `frontend/coding-olympiad/html/` — añadir symlinks si se mapean nuevos equipos
