# PROMPT PARA MODELO PROGRAMADOR — HU-NEWS-01
## Widget: Sentimiento de Noticias (news-sentimiento.html)

Copiar TODO este prompt y dárselo a un modelo programador (Qwen3-Coder-480B-A35B-Instruct (vía OpenRouter)).
El modelo debe crear/modificar SOLO los archivos indicados. NO tocar nada más.

---

## CONTEXTO

Eres el modelo **Qwen3-Coder-480B-A35B-Instruct**, un programador frontend especializado en widgets financieros HTML/CSS/JS autónomos.
Estás trabajando en el proyecto PEGATON INVEST INTELLIGENCE (frontend/widgets/).

### Tu tarea: HU-NEWS-01 — Reescribir `frontend/widgets/news-sentimiento.html`

El archivo EXISTE actualmente como prototipo básico (121 líneas, HTML estático sin Canvas gauge ni auto-refresh).
Debes REESCRIBIRLO COMPLETAMENTE siguiendo el patrón exacto de `fear-greed-equipo-a.html`.

---

## REFERENCIAS (léelas antes de programar)

### 1. Patrón de widget a seguir
**Archivo:** `/root/pegaton_invest_intelligence/frontend/widgets/fear-greed-equipo-a.html`
(12765 bytes, 434 líneas)

Elementos clave a replicar:
- Gauge circular con Canvas API (semicírculo)
- Multi-color según rango de score
- Aguja animada
- Centro del gauge muestra el número
- Panel desplegable inferior con desglose
- Auto-refresh cada 60 segundos
- Indicador de estado de conexión (live/stale/error)

### 2. Endpoint de datos
**URL:** `GET /api/v1/news-sentiment`
**Response** (el widget debe consumir esto):
```json
{
  "score": 58,
  "delta": 3,
  "delta_pct": "+5%",
  "alert": null,
  "total_articles": 47,
  "sources": {
    "reuters": 12,
    "cnbc": 8,
    "google_news": 15,
    "marketwatch": 7,
    "yahoo_finance": 3,
    "twitter": 2
  },
  "top_keywords": [
    { "word": "tariffs", "count": 8 },
    { "word": "inflation", "count": 5 },
    { "word": "fed", "count": 4 }
  ],
  "distribution": {
    "fear": 12,
    "neutral": 25,
    "greed": 10
  },
  "timestamp": "2026-05-10T20:00:00",
  "status": "ready"
}
```

Notas:
- `alert` puede ser `null`, `"EXTREME_FEAR"`, o `"EXTREME_GREED"`
- `delta` es entero (diferencia vs snapshot anterior)
- `delta_pct` es string con formato `"+5%"` o `"-3%"`
- `sources` tiene solo `count` por fuente (entero)
- `top_keywords` puede ser array vacío si no hay suficientes datos
- `distribution` tiene `fear`, `neutral`, `greed` (enteros)

### 3. Endpoint que el widget YA consume (retrocompatible)
Si el endpoint DEVUELVE el formato antiguo (sin delta, alert, etc.), el widget
debe COMPUTAR esos valores localmente:
- `delta`: calcular diferencia vs score anterior (guardar último score en variable)
- `alert`: si score < 20 → "EXTREME_FEAR", si score > 80 → "EXTREME_GREED"
- `top_keywords`: no disponible → ocultar sección
- `distribution`: no disponible → ocultar sección

---

## ESPECIFICACIONES TÉCNICAS

### Archivo a crear/modificar
**Ruta:** `/root/pegaton_invest_intelligence/frontend/widgets/news-sentimiento.html`
**Tipo:** HTML autónomo (un solo archivo, como fear-greed-equipo-a.html)
**Tamaño objetivo:** 400-500 líneas

### Diseño visual

**Tema:** Dark theme
- Background principal: `#0a0e17`
- Cards/containers: `#0e1520` con borde `#1a2332`
- Colores de texto: `#e2e8f0` (principal), `#64748b` (secundario), `#94a3b8` (terciario)

**Gauge circular (Canvas):**
- Semicírculo (igual que fear-greed-equipo-a)
- **5 bandas de color:**
  - 0-19: Rojo pánico `#ff3b30` (EXTREME_FEAR)
  - 20-39: Naranja `#ff9500` (miedo)
  - 40-59: Amarillo `#ffcc02` (neutral)
  - 60-79: Verde `#34c759` (optimista)
  - 80-100: Morado `#af52de` (euforia/greed)
- Aguja blanca con sombra
- Centro del gauge: score numérico grande + label de acción
- Animación suave al cambiar de score (lerp/easing)

**Mapeo score → gauge:**
- Score del API es 0-100 (ya viene mapeado, NO necesitas transformar VADER)
- Si el API devuelve score -1 a +1 (formato VADER raw): mapear como `(score + 1) * 50`

**Alert banner:**
- Si `alert === "EXTREME_FEAR"`: banner rojo pulsante con texto "⚠️ PÁNICO EXTREMO"
- Si `alert === "EXTREME_GREED"`: banner morado pulsante con texto "🚀 EUFORIA EXTREMA"
- Si `alert === null`: banner oculto
- Animación CSS `@keyframes pulse` (opacity alternando)

**Badge de delta:**
- Mostrar delta numérico (+3, -2, 0)
- Color: verde para positivo, rojo para negativo, gris para neutro
- Si viene `delta_pct` del API, mostrarlo entre paréntesis: "+3 (+5%)"

**Panel desplegable (breakdown):**
- Al hacer clic en el gauge o botón "Ver desglose", expandir panel
- Contenido del panel:
  1. **Fuentes RSS** — una barra por fuente con count y % del total
  2. **Top keywords** — badges/chips con palabra y count
  3. **Distribución** — mini-barras para fear/neutral/greed con counts

**Auto-refresh:**
- `setInterval(fetchData, 60000)` — refresco cada 60 segundos
- Indicador visual de estado:
  - Punto verde con glow = datos frescos (live)
  - Punto naranja = datos de cache
  - Punto rojo = error de conexión
- Al hacer fetch, punto temporalmente en estado "loading"

### Respetar el contrato del widget
```
- Compatible con iframe (sin scrollbars, overscroll-behavior: contain)
- Sin dependencias externas (CDN, librerías)
- Sin credenciales/API keys hardcodeadas
- Width: 100% del contenedor (responsive)
- Altura máxima: ~400px
```

## CRITERIOS DE ACEPTACIÓN

- [ ] El widget se carga y muestra datos del endpoint `/api/v1/news-sentiment`
- [ ] Gauge circular Canvas con 5 colores funciona correctamente
- [ ] Animación de transición entre scores (lerp suave)
- [ ] Alert banner aparece en EXTREME_FEAR (<20) y EXTREME_GREED (>80)
- [ ] Delta se muestra con badge de color correcto
- [ ] Panel desplegable muestra fuentes, keywords, distribución
- [ ] Auto-refresh cada 60s con indicador de estado
- [ ] Compatible con iframe (sin scrollbars)
- [ ] Funciona con formato nuevo Y antiguo del endpoint (retrocompatible)
- [ ] Dark theme consistente con el resto de widgets
- [ ] 0 dependencias externas
- [ ] Código limpio, comentado en secciones clave

## NO HACER

- NO usar librerías externas (jQuery, Chart.js, etc.)
- NO hardcodear credenciales
- NO modificar ningún otro archivo
- NO usar Canvas para texto (usar HTML/CSS superpuesto)
- NO romper el patrón visual de fear-greed-equipo-a.html

## ARCHIVOS QUE DEBES LEER PARA CONTEXTO

1. `/root/pegaton_invest_intelligence/frontend/widgets/fear-greed-equipo-a.html` ← PATRÓN
2. El endpoint `/api/v1/news-sentiment` (probar con `curl localhost:8765/api/v1/news-sentiment`)
3. `/root/pegaton_invest_intelligence/frontend/widgets/news-sentimiento.html` ← PROTOTIPO ACTUAL (reemplazar)

---

Cuando termines, responde con:
1. El contenido COMPLETO del archivo `news-sentimiento.html` generado
2. Qué criterios de aceptación cumplen
3. Si encontraste algún problema con el endpoint o datos