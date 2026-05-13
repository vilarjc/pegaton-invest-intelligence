# Widget MACRO — Especificación Técnica

**ID:** `macro`
**Nombre:** Indicadores Macroeconómicos
**Experto:** Experto en Macroeconomía
**PM:** PM Macro
**Programador:** Agente Programador
**Estado:** `spec`
**Versión:** 1.0 — 2026-05-07

---

## 📐 1. ENDPOINT DE DATOS

### 1.1 Ubicación

Archivo: `/root/pegaton_invest_intelligence/olympiad_server.py`

### 1.2 Ruta

`GET /api/widgets/macro/data`

### 1.3 Comportamiento

1. Obtener el registro del widget `macro` de la DB (widget_get("macro"))
2. Leer el HTML de `frontend/widgets/macro.html`
3. Fetchear datos desde `http://100.64.64.58:18081/api/macro/history` (timeout 10s)
4. Procesar los datos: extraer el registro más reciente, calcular cambios porcentuales contra registro anterior, asignar colores semáforo
5. Devolver JSON con: widget info, html, y data procesada

Si el fetch externo falla, devolver `data: null` y un mensaje de error — el JS del widget debe mostrar "Sin datos" gracefulmente.

### 1.4 Formato JSON de respuesta EXACTO

```json
{
  "widget": {
    "id": "macro",
    "name": "Indicadores Macroeconómicos",
    "status": "ready"
  },
  "html": "<div class=\"widget-macro\">... HTML del widget ...</div>",
  "data": {
    "timestamp": "2026-05-01T06:32:04",
    "summary": "📊 VIX en 16.9 — volatilidad moderada. Neutral. | 💵 Dólar débil — favorable para oro, BTC y emergentes.",
    "diagnosis": {
      "text": "Entorno de riesgo moderado. VIX bajo señal de calma. Dólar débil impulsa commodities.",
      "level": "normal",
      "level_label": "🟢 Normal"
    },
    "bands": {
      "riesgo": {
        "label": "Riesgo",
        "indicators": [
          {
            "id": "vix",
            "name": "VIX",
            "value": 16.9,
            "unit": "",
            "change_pct": 2.5,
            "change_label": "+2.5%",
            "change_direction": "up",
            "level": "green",
            "level_label": "🟢",
            "threshold": "normal (<20)"
          },
          {
            "id": "yield_10y",
            "name": "Treasury 10Y",
            "value": null,
            "unit": "%",
            "change_pct": null,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray",
            "level_label": "⚪",
            "threshold": "sin datos"
          },
          {
            "id": "spread_2y10y",
            "name": "Spread 2Y-10Y",
            "value": null,
            "unit": "pb",
            "change_pct": null,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray",
            "level_label": "⚪",
            "threshold": "sin datos"
          }
        ]
      },
      "ciclo": {
        "label": "Ciclo",
        "indicators": [
          {
            "id": "pmi_manufacturing",
            "name": "PMI Manufacturero",
            "value": 49.8,
            "unit": "",
            "change_pct": -0.2,
            "change_label": "-0.2%",
            "change_direction": "down",
            "level": "yellow",
            "level_label": "🟡",
            "threshold": "contracción (<50)"
          },
          {
            "id": "pmi_services",
            "name": "PMI Servicios",
            "value": 52.3,
            "unit": "",
            "change_pct": 0.5,
            "change_label": "+0.5%",
            "change_direction": "up",
            "level": "green",
            "level_label": "🟢",
            "threshold": "expansión (>50)"
          },
          {
            "id": "inflation",
            "name": "Inflación",
            "value": 2.7,
            "unit": "%",
            "change_pct": null,
            "change_label": "est.",
            "change_direction": "neutral",
            "level": "yellow",
            "level_label": "🟡",
            "threshold": "por encima del target"
          },
          {
            "id": "fed_rate",
            "name": "Tasa Fed",
            "value": 3.25,
            "unit": "%",
            "change_pct": null,
            "change_label": "estable",
            "change_direction": "neutral",
            "level": "green",
            "level_label": "🟢",
            "threshold": "pausa"
          },
          {
            "id": "gdp",
            "name": "PIB",
            "value": 2.1,
            "unit": "%",
            "change_pct": null,
            "change_label": "est.",
            "change_direction": "neutral",
            "level": "green",
            "level_label": "🟢",
            "threshold": "crecimiento moderado"
          }
        ]
      },
      "global": {
        "label": "Global",
        "indicators": [
          {
            "id": "sp500",
            "name": "S&P 500",
            "value": 7209.01,
            "unit": "",
            "change_pct": 1.02,
            "change_label": "+1.02%",
            "change_direction": "up",
            "level": "green",
            "level_label": "🟢",
            "threshold": "alcista"
          },
          {
            "id": "dxy",
            "name": "DXY",
            "value": 98.22,
            "unit": "",
            "change_pct": -0.15,
            "change_label": "-0.15%",
            "change_direction": "down",
            "level": "green",
            "level_label": "🟢",
            "threshold": "dólar débil"
          },
          {
            "id": "gold_price",
            "name": "Oro",
            "value": 4611.8,
            "unit": "$",
            "change_pct": 0.4,
            "change_label": "+0.4%",
            "change_direction": "up",
            "level": "green",
            "level_label": "🟢",
            "threshold": "máximos históricos"
          },
          {
            "id": "oil_price",
            "name": "Petróleo",
            "value": null,
            "unit": "$",
            "change_pct": null,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray",
            "level_label": "⚪",
            "threshold": "sin datos"
          },
          {
            "id": "btc_price",
            "name": "Bitcoin",
            "value": null,
            "unit": "$",
            "change_pct": null,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray",
            "level_label": "⚪",
            "threshold": "sin datos"
          }
        ]
      }
    },
    "externo_fetch_ok": true
  }
}
```

### 1.5 Algoritmo de procesamiento (Python en olympiad_server.py)

```python
def _compute_macro_data():
    """Fetch, process, and return macro widget data."""
    import urllib.request, json
    from datetime import datetime
    
    try:
        req = urllib.request.Request(
            "http://100.64.64.58:18081/api/macro/history",
            headers={"User-Agent": "Hermes-Olympiad"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except Exception as e:
        return {"timestamp": datetime.now().isoformat(), "error": str(e), "externo_fetch_ok": False}
    
    records = raw.get("data", [])
    if not records:
        return {"timestamp": datetime.now().isoformat(), "error": "empty_data", "externo_fetch_ok": False}
    
    latest = records[0]
    previous = records[1] if len(records) > 1 else records[0]
    
    def safe_float(v):
        if v is None: return None
        try: return float(str(v).replace("%","").replace(",","").split()[0] if isinstance(v, str) else v)
        except: return None
    
    def pct_change(current, prev):
        c, p = safe_float(current), safe_float(prev)
        if c is None or p is None or p == 0: return None
        return round((c - p) / abs(p) * 100, 2)
    
    def get_change_direction(pct):
        if pct is None: return "neutral"
        if pct > 0: return "up"
        if pct < 0: return "down"
        return "neutral"
    
    def format_change(pct):
        if pct is None: return "N/D"
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct}%"
    
    # VIX thresholds
    def vix_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        if v < 20: return ("green", "🟢", "normal (<20)")
        if v <= 30: return ("yellow", "🟡", "precaución (20-30)")
        return ("red", "🔴", "alarma (>30)")
    
    # Generic level helper: green = good, yellow = warning, red = bad
    def generic_level(current, good_above=None, good_below=None):
        v = safe_float(current)
        if v is None: return ("gray", "⚪", "sin datos")
        if good_above is not None and v >= good_above: return ("green", "🟢", "positivo")
        if good_below is not None and v <= good_below: return ("green", "🟢", "positivo")
        if good_above is not None and v < good_above - 5: return ("red", "🔴", "negativo")
        if good_below is not None and v > good_below + 5: return ("red", "🔴", "negativo")
        return ("yellow", "🟡", "precaución")
    
    # Build indicators for each band
    
    # ── Riesgo ──
    vix_val = safe_float(latest.get("vix"))
    vix_prev = safe_float(previous.get("vix"))
    vix_pct = pct_change(latest.get("vix"), previous.get("vix"))
    vix_lvl, vix_icon, vix_thr = vix_level(latest.get("vix"))
    
    yield_10y_val = safe_float(latest.get("yield_10y"))
    yield_2y_val = safe_float(latest.get("yield_2y"))
    spread_val = (yield_10y_val - yield_2y_val) if (yield_10y_val is not None and yield_2y_val is not None) else None
    
    riesgo_indicators = [
        {
            "id": "vix", "name": "VIX",
            "value": vix_val, "unit": "",
            "change_pct": vix_pct, "change_label": format_change(vix_pct),
            "change_direction": get_change_direction(vix_pct),
            "level": vix_lvl, "level_label": vix_icon, "threshold": vix_thr
        },
        {
            "id": "yield_10y", "name": "Treasury 10Y",
            "value": yield_10y_val, "unit": "%",
            "change_pct": None, "change_label": "N/D" if yield_10y_val is None else f"{yield_10y_val}%",
            "change_direction": "neutral",
            "level": "gray" if yield_10y_val is None else "green",
            "level_label": "⚪" if yield_10y_val is None else "🟢",
            "threshold": "sin datos" if yield_10y_val is None else f"{yield_10y_val}%"
        },
        {
            "id": "spread_2y10y", "name": "Spread 2Y-10Y",
            "value": spread_val, "unit": "pb",
            "change_pct": None, "change_label": "N/D" if spread_val is None else f"{spread_val:.1f}",
            "change_direction": "neutral",
            "level": "gray" if spread_val is None else ("red" if spread_val < 0 else "green"),
            "level_label": "⚪" if spread_val is None else ("🔴" if spread_val < 0 else "🟢"),
            "threshold": "sin datos" if spread_val is None else ("invertida" if spread_val < 0 else "normal")
        }
    ]
    
    # ── Ciclo ──
    def pmi_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        if v >= 50: return ("green", "🟢", "expansión (≥50)")
        return ("red", "🔴", f"contracción (<50)")
    
    def inflation_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        if v <= 2.5: return ("green", "🟢", "bajo control")
        if v <= 4.0: return ("yellow", "🟡", "elevada")
        return ("red", "🔴", "muy elevada")
    
    ciclo_indicators = [
        {
            "id": "pmi_manufacturing", "name": "PMI Manufacturero",
            "value": safe_float(latest.get("pmi_manufacturing")), "unit": "",
            "change_pct": pct_change(latest.get("pmi_manufacturing"), previous.get("pmi_manufacturing")),
            "change_label": format_change(pct_change(latest.get("pmi_manufacturing"), previous.get("pmi_manufacturing"))),
            "change_direction": get_change_direction(pct_change(latest.get("pmi_manufacturing"), previous.get("pmi_manufacturing"))),
            "level": pmi_level(latest.get("pmi_manufacturing"))[0],
            "level_label": pmi_level(latest.get("pmi_manufacturing"))[1],
            "threshold": pmi_level(latest.get("pmi_manufacturing"))[2]
        },
        {
            "id": "pmi_services", "name": "PMI Servicios",
            "value": safe_float(latest.get("pmi_services")), "unit": "",
            "change_pct": pct_change(latest.get("pmi_services"), previous.get("pmi_services")),
            "change_label": format_change(pct_change(latest.get("pmi_services"), previous.get("pmi_services"))),
            "change_direction": get_change_direction(pct_change(latest.get("pmi_services"), previous.get("pmi_services"))),
            "level": pmi_level(latest.get("pmi_services"))[0],
            "level_label": pmi_level(latest.get("pmi_services"))[1],
            "threshold": pmi_level(latest.get("pmi_services"))[2]
        },
        {
            "id": "inflation", "name": "Inflación",
            "value": safe_float(latest.get("inflation")), "unit": "%",
            "change_pct": None,
            "change_label": "est.",
            "change_direction": "neutral",
            "level": inflation_level(latest.get("inflation"))[0],
            "level_label": inflation_level(latest.get("inflation"))[1],
            "threshold": inflation_level(latest.get("inflation"))[2]
        },
        {
            "id": "fed_rate", "name": "Tasa Fed",
            "value": safe_float(latest.get("fed_rate")), "unit": "%",
            "change_pct": None,
            "change_label": "estable",
            "change_direction": "neutral",
            "level": "green",
            "level_label": "🟢",
            "threshold": "pausa"
        },
        {
            "id": "gdp", "name": "PIB",
            "value": safe_float(latest.get("gdp", {}).get("us", {}).get("atlanta_fed_nowcast", "0") if isinstance(latest.get("gdp"), dict) else 2.1),
            "unit": "%",
            "change_pct": None,
            "change_label": "est.",
            "change_direction": "neutral",
            "level": "green", "level_label": "🟢",
            "threshold": "crecimiento moderado"
        }
    ]
    
    # ── Global ──
    def sp500_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        return ("green", "🟢", f"{v:,.0f}")
    
    def dxy_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        if v < 100: return ("green", "🟢", "dólar débil")
        if v < 105: return ("yellow", "🟡", "neutral")
        return ("red", "🔴", "dólar fuerte")
    
    def gold_level(v):
        v = safe_float(v)
        if v is None: return ("gray", "⚪", "sin datos")
        return ("green", "🟢", f"${v:,.0f}")
    
    global_indicators = [
        {
            "id": "sp500", "name": "S&P 500",
            "value": safe_float(latest.get("sp500")), "unit": "",
            "change_pct": pct_change(latest.get("sp500"), previous.get("sp500")),
            "change_label": format_change(pct_change(latest.get("sp500"), previous.get("sp500"))),
            "change_direction": get_change_direction(pct_change(latest.get("sp500"), previous.get("sp500"))),
            "level": sp500_level(latest.get("sp500"))[0],
            "level_label": sp500_level(latest.get("sp500"))[1],
            "threshold": sp500_level(latest.get("sp500"))[2]
        },
        {
            "id": "dxy", "name": "DXY",
            "value": safe_float(latest.get("dxy")), "unit": "",
            "change_pct": pct_change(latest.get("dxy"), previous.get("dxy")),
            "change_label": format_change(pct_change(latest.get("dxy"), previous.get("dxy"))),
            "change_direction": get_change_direction(pct_change(latest.get("dxy"), previous.get("dxy"))),
            "level": dxy_level(latest.get("dxy"))[0],
            "level_label": dxy_level(latest.get("dxy"))[1],
            "threshold": dxy_level(latest.get("dxy"))[2]
        },
        {
            "id": "gold_price", "name": "Oro",
            "value": safe_float(latest.get("gold_price")), "unit": "$",
            "change_pct": pct_change(latest.get("gold_price"), previous.get("gold_price")),
            "change_label": format_change(pct_change(latest.get("gold_price"), previous.get("gold_price"))),
            "change_direction": get_change_direction(pct_change(latest.get("gold_price"), previous.get("gold_price"))),
            "level": gold_level(latest.get("gold_price"))[0],
            "level_label": gold_level(latest.get("gold_price"))[1],
            "threshold": gold_level(latest.get("gold_price"))[2]
        },
        {
            "id": "oil_price", "name": "Petróleo",
            "value": safe_float(latest.get("oil_price")), "unit": "$",
            "change_pct": None,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray", "level_label": "⚪",
            "threshold": "sin datos"
        },
        {
            "id": "btc_price", "name": "Bitcoin",
            "value": safe_float(latest.get("btc_price")), "unit": "$",
            "change_pct": None,
            "change_label": "N/D",
            "change_direction": "neutral",
            "level": "gray", "level_label": "⚪",
            "threshold": "sin datos"
        }
    ]
    
    # ── Diagnosis ──
    # Overall level based on VIX (primary risk indicator)
    diagnosis_level = vix_lvl if vix_lvl != "gray" else "green"
    diagnosis_map = {
        "green": {"text": "Entorno de riesgo controlado. VIX en zona de baja volatilidad.", "level": "normal", "level_label": "🟢 Normal"},
        "yellow": {"text": "Precaución. VIX en zona de volatilidad moderada. Monitorear evolución.", "level": "caution", "level_label": "🟡 Precaución"},
        "red": {"text": "Alarma. VIX en zona de alta volatilidad. Riesgo elevado en mercados.", "level": "alarm", "level_label": "🔴 Alarma"}
    }
    diagnosis = diagnosis_map.get(diagnosis_level, diagnosis_map["green"])
    
    return {
        "timestamp": latest.get("captured_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "summary": latest.get("summary", ""),
        "diagnosis": diagnosis,
        "bands": {
            "riesgo": {"label": "Riesgo", "indicators": riesgo_indicators},
            "ciclo": {"label": "Ciclo", "indicators": ciclo_indicators},
            "global": {"label": "Global", "indicators": global_indicators}
        },
        "externo_fetch_ok": True
    }
```

### 1.6 Parseo especial para campos complejos

El campo `inflation` en el raw data viene como string tipo `"2.7% (estimado)"` — extraer solo el número.
El campo `gdp` viene como string JSON o dict — intentar parsear `gdp['us']['atlanta_fed_nowcast']`.
El campo `fed_rate` viene como `"3.25%"` — extraer solo el número.
El campo `pmi_manufacturing` y `pmi_services` vienen como strings `"49.8"` — convertir a float.

---

## 🧩 2. ESTRUCTURA DEL HTML DEL WIDGET

### 2.1 Ubicación

`/root/pegaton_invest_intelligence/frontend/widgets/macro.html`

### 2.2 Estructura del fragmento HTML

```html
<div class="widget-macro" id="widget-macro-root">
  <div class="macro-header">
    <h3>🌍 Indicadores Macroeconómicos</h3>
    <span class="macro-diagnosis" id="macro-diagnosis">🟢 Normal</span>
    <span class="macro-timestamp" id="macro-timestamp">--</span>
  </div>

  <div class="macro-bands" id="macro-bands">
    <!-- Cada banda se renderiza con JS -->
  </div>

  <div class="macro-summary" id="macro-summary">
    <p class="loading">Cargando datos macro...</p>
  </div>
</div>

<script>
  // JS autónomo (ver sección 3)
</script>
```

### 2.3 Layout de tarjetas (renderizado por JS)

**CONTENEDOR PRINCIPAL:**
- `.macro-bands` — contenedor flex con scroll horizontal (`overflow-x: auto`)
- 3 franjas (bandas): Riesgo, Ciclo, Global
- Cada banda es un `.macro-band` con `min-width` fijo y título

**CADA BANDA:**
```html
<div class="macro-band">
  <div class="macro-band-title">⚠️ Riesgo</div>
  <div class="macro-band-cards">
    <!-- tarjetas -->
  </div>
</div>
```

**CADA TARJETA:**
```html
<div class="macro-card" data-level="green">
  <div class="card-semaphore">🟢</div>
  <div class="card-body">
    <div class="card-name">VIX</div>
    <div class="card-value">16.9</div>
    <div class="card-change up">+2.5%</div>
  </div>
</div>
```

### 2.4 Sistema de colores por indicador

| Nivel | Clase CSS | Color Semáforo | Fondo tarjeta | Significado |
|-------|-----------|----------------|---------------|-------------|
| `green` | `.level-green` | 🟢 `#22c55e` | `rgba(34,197,94,0.08)` | Normal / Positivo |
| `yellow` | `.level-yellow` | 🟡 `#eab308` | `rgba(234,179,8,0.08)` | Precaución / Atención |
| `red` | `.level-red` | 🔴 `#ef4444` | `rgba(239,68,68,0.08)` | Alarma / Negativo |
| `gray` | `.level-gray` | ⚪ `#6b7280` | `rgba(107,114,128,0.05)` | Sin datos |

Los bordes de tarjeta usan el color del nivel con opacidad 0.3.

### 2.5 Diagnóstico resumen

Debajo de las tarjetas, un bloque `.macro-summary` con:
- Texto del diagnosis (generado por Python)
- El summary original (raw) del endpoint externo
- Timestamp de captura de datos
- Badge de "cache" o "fresh"

---

## 💻 3. LÓGICA JS

### 3.1 Funciones específicas

```javascript
// ── 1. FETCH ──
async function fetchMacroData() { ... }

// ── 2. RENDER ──
function renderWidget(data) { ... }
function renderBand(bandId, bandData) { ... }
function renderCard(indicator) { ... }
function renderSummary(data) { ... }

// ── 3. UPDATE DIAGNOSIS ──
function updateDiagnosis(diagnosis) { ... }

// ── 4. ERROR ──
function showError(msg) { ... }
```

### 3.2 Flujo de ejecución

```
1. Inmediatamente: mostrar "Cargando datos macro..."
2. fetch(`/api/widgets/macro/data`)
3. .then(resp => resp.json())
4. Extraer data.data (los datos procesados)
5. Llamar renderWidget(data.data)
6. Si error: showError("Error al cargar datos macro")
7. Auto-refresh cada 60s con setInterval
```

### 3.3 Lógica de semáforo (cliente)

El nivel de color viene pre-calculado del backend en `indicator.level`.
El JS solo aplica las clases CSS correspondientes:

```javascript
function getCardClass(level) {
  return 'macro-card level-' + level;
}
```

### 3.4 Comportamiento responsive

- **Desktop (>900px):** Las 3 bandas visibles, scroll horizontal si no caben
- **Tablet (600-900px):** 2 bandas visibles, scroll horizontal
- **Mobile (<600px):** 1 banda visible, scroll horizontal con snap
- Altura máxima del contenedor: 320px
- Tarjetas: min-width 130px, max-width 160px
- Banda: min-width 200px

---

## ✅ 4. CRITERIOS DE ACEPTACIÓN

- [ ] El endpoint `GET /api/widgets/macro/data` responde con 200 y formato JSON válido
- [ ] Los datos devueltos incluyen: widget, html, y data con bands, diagnosis, timestamp
- [ ] Los campos `value` son floats (no strings con %), los campos `change_pct` son floats o null
- [ ] El campo `level` es siempre uno de: "green", "yellow", "red", "gray"
- [ ] El HTML en `frontend/widgets/macro.html` es un fragmento autónomo (sin `<html><body>`)
- [ ] El JS del widget se ejecuta sin errores en la consola del navegador
- [ ] Las tarjetas se renderizan con el color de semáforo correcto según `indicator.level`
- [ ] Los indicadores sin datos muestran ⚪ y "N/D"
- [ ] El diagnóstico resume el estado general del VIX
- [ ] El widget tiene scroll horizontal y es responsive
- [ ] Si el fetch externo falla, el widget muestra "Sin datos" sin romperse
- [ ] El auto-refresh funciona cada 60s
- [ ] No hay dependencias externas rotas (CDNs, etc.)
- [ ] El widget cabe en el grid del dashboard (responsive)

---

## 📋 5. TAREAS ASIGNADAS AL PROGRAMADOR

### Tarea 1: Endpoint de datos en olympiad_server.py ⏱ 30min
**Archivo:** `/root/pegaton_invest_intelligence/olympiad_server.py`

- Agregar función `_compute_macro_data()` (copiar el código de la sección 1.5)
- Modificar el handler de `GET /api/widgets/macro/data` para que:
  1. Obtenga widget de DB (widget_get("macro"))
  2. Lea HTML de `frontend/widgets/macro.html`
  3. Llame a `_compute_macro_data()`
  4. Devuelva `{"widget": w, "html": html, "data": macro_data}`
- NO crear un endpoint separado — usar el handler existente en `/api/widgets/{id}/data`
- Agregar manejo de error: si `_compute_macro_data` falla, devolver `data: null` y `data_error: mensaje`

### Tarea 2: HTML del widget en frontend/widgets/macro.html ⏱ 45min
**Archivo:** `/root/pegaton_invest_intelligence/frontend/widgets/macro.html`

- Crear el fragmento HTML autónomo descrito en la sección 2
- **NO** incluir `<html>`, `<head>`, `<body>` — solo el div raíz `.widget-macro` y el script
- Incluir estilos INLINE en una etiqueta `<style>` dentro del fragmento (ver sección 6)
- No usar CDNs externas — todo el CSS/JS debe ser autónomo
- Usar la función `fetchMacroData` que fetchea `/api/widgets/macro/data`
- Implementar `renderWidget` que itera sobre `data.bands` y renderiza cada banda con sus tarjetas
- Implementar auto-refresh cada 60s
- Animaciones: transiciones suaves en color y opacidad (0.3s ease)

### Tarea 3: Verificar integración ⏱ 15min
- Iniciar el servidor: `python3 /root/pegaton_invest_intelligence/olympiad_server.py`
- Verificar que `curl http://localhost:8765/api/widgets/macro/data` devuelve JSON válido con `data` poblado
- Verificar que `curl http://localhost:8765/api/widgets/macro/data | python3 -m json.tool` no da errores
- Verificar que el HTML existe en `frontend/widgets/macro.html`
- Verificar que no hay errores de sintaxis en el HTML

---

## 🎨 6. ESTILOS CSS EXACTOS

```css
/* ── Widget Macro Container ── */
.widget-macro {
  background: #0e1520;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid #1a2332;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #e0e0e0;
  min-width: 320px;
  max-width: 100%;
}

/* ── Header ── */
.macro-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.macro-header h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  flex: 1;
  min-width: 180px;
}
.macro-diagnosis {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(34,197,94,0.12);
  white-space: nowrap;
}
.macro-timestamp {
  font-size: 11px;
  color: #4a5a6e;
  white-space: nowrap;
}

/* ── Bands Container (scroll horizontal) ── */
.macro-bands {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  scroll-snap-type: x mandatory;
}
.macro-bands::-webkit-scrollbar {
  height: 4px;
}
.macro-bands::-webkit-scrollbar-track {
  background: #1a2332;
  border-radius: 2px;
}
.macro-bands::-webkit-scrollbar-thumb {
  background: #2a3a4e;
  border-radius: 2px;
}

/* ── Each Band ── */
.macro-band {
  min-width: 220px;
  max-width: 280px;
  flex-shrink: 0;
  scroll-snap-align: start;
}
.macro-band-title {
  font-size: 13px;
  font-weight: 600;
  color: #6a7a8e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #1a2332;
}

/* ── Cards Container ── */
.macro-band-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ── Individual Card ── */
.macro-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
  transition: all 0.3s ease;
  cursor: default;
}
.macro-card:hover {
  border-color: rgba(255,255,255,0.12);
  transform: translateX(2px);
}
.macro-card.level-green {
  background: rgba(34,197,94,0.06);
  border-color: rgba(34,197,94,0.2);
}
.macro-card.level-yellow {
  background: rgba(234,179,8,0.06);
  border-color: rgba(234,179,8,0.2);
}
.macro-card.level-red {
  background: rgba(239,68,68,0.06);
  border-color: rgba(239,68,68,0.2);
}
.macro-card.level-gray {
  background: rgba(107,114,128,0.04);
  border-color: rgba(107,114,128,0.12);
}

/* ── Card Elements ── */
.card-semaphore {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}
.card-body {
  flex: 1;
  min-width: 0;
}
.card-name {
  font-size: 11px;
  font-weight: 500;
  color: #6a7a8e;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 2px;
}
.card-value {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
}
.card-change {
  font-size: 11px;
  font-weight: 500;
  margin-top: 1px;
}
.card-change.up { color: #22c55e; }
.card-change.down { color: #ef4444; }
.card-change.neutral { color: #6b7280; }

/* ── Summary / Diagnosis ── */
.macro-summary {
  margin-top: 16px;
  padding: 12px 14px;
  background: #111a28;
  border-radius: 10px;
  border: 1px solid #1a2332;
  font-size: 12px;
  line-height: 1.5;
  color: #a0b0c0;
}
.macro-summary .summary-text {
  margin-bottom: 6px;
}
.macro-summary .summary-raw {
  font-size: 11px;
  color: #4a5a6e;
  border-top: 1px solid #1a2332;
  padding-top: 6px;
  margin-top: 6px;
}
.macro-summary .summary-error {
  color: #ef4444;
  font-weight: 500;
}

/* ── Loading / Error ── */
.macro-loading,
.macro-error {
  text-align: center;
  padding: 30px 0;
  font-size: 14px;
  color: #4a5a6e;
}
.macro-error {
  color: #ef4444;
}

/* ── Responsive ── */
@media (max-width: 600px) {
  .widget-macro { padding: 14px; }
  .macro-band { min-width: 180px; max-width: 220px; }
  .macro-card { padding: 8px 10px; }
  .card-value { font-size: 14px; }
}
```

---

## 📊 7. DIAGRAMA DE FLUJO

```
┌───────────────────────────────────────────────────────┐
│                  olympiad_server.py                    │
│                                                       │
│  GET /api/widgets/macro/data                          │
│       │                                               │
│       ├─→ widget_get("macro") → {id, name, ...}       │
│       ├─→ read file: frontend/widgets/macro.html      │
│       ├─→ _compute_macro_data()                       │
│       │      │                                        │
│       │      ├─→ fetch http://100.64.64.58:18081/...  │
│       │      ├─→ parse: safe_float, pct_change        │
│       │      ├─→ assign: levels (green/yellow/red)    │
│       │      ├─→ build bands (riesgo/ciclo/global)    │
│       │      ├─→ generate diagnosis                   │
│       │      └─→ return data dict                     │
│       │                                               │
│       └─→ JSON: {widget, html, data}                  │
│                                                       │
└───────────────────┬───────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────┐
│              frontend/widgets/macro.html               │
│                                                       │
│  JS: fetchMacroData()                                 │
│       │                                               │
│       ├─→ fetch("/api/widgets/macro/data")            │
│       ├─→ renderWidget(data.data)                     │
│       │      │                                        │
│       │      ├─→ renderBand("riesgo", ...)            │
│       │      │      └─→ renderCard(indicator) × N     │
│       │      ├─→ renderBand("ciclo", ...)             │
│       │      ├─→ renderBand("global", ...)            │
│       │      └─→ renderSummary(data)                  │
│       │                                               │
│       └─→ setInterval(fetchMacroData, 60000)          │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## End of Specification
