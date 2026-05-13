# Plan Ejecutivo: Indicador Fear & Greed Mejorado

## 1. Stack Técnico (100% gratuito)
- **Backend**: Python + FastAPI (ya operativo en puerto 8000)
- **Datos VIX**: `yfinance` (gratis, sin API key)
- **Datos Macro**: FRED API (ya configurada, 120 req/min)
- **Sentimiento noticias**: RSS feeds (Reuters, CNBC) + análisis básico de palabras clave (sin API externa)
- **Frontend**: HTML/CSS/JS autónomo con Canvas 2D (velocímetro) — 1 solo archivo
- **Actualización**: Cron job cada hora → endpoint cachea resultado
- **Coste total**: $0/mes

## 2. Arquitectura
```
[CRON cada hora]
  ├─ yfinance → VIX actual
  ├─ FRED API → IPC, empleo, PMI
  └─ RSS parser → conteo palabras positivas/negativas
        ↓
  [FearGreedEngine.py] → score 0-100 + factores
        ↓
  [FastAPI: /api/v1/fear-greed] → JSON cacheado
        ↓
  [Widget HTML] → iframe/Web Component en web existente
```

## 3. Tareas

| Tarea | Responsable | Horas | Sprint |
|-------|-------------|-------|--------|
| Endpoint `/api/v1/fear-greed` + algoritmo scoring | Dev | 4h | 1 |
| Módulo ingesta VIX (yfinance) | Dev | 2h | 1 |
| Módulo sentimiento noticias (RSS + keywords) | Dev | 4h | 1 |
| Widget velocímetro (Canvas 2D, 0-100) | Dev | 5h | 2 |
| Desglose interactivo (clic → factores) | Dev | 3h | 2 |
| Integración en web existente (iframe snippet) | Dev | 1h | 2 |
| Cron job hourly + pruebas | Dev | 2h | 2 |
| **Total** | | **21h** | 2 sprints |

## 4. Limitaciones Free Tier
- VIX vía yfinance: ~15min retraso (no es tiempo real)
- FRED: algunos indicadores tienen 1-2 meses de retraso (IPC, empleo)
- Sentimiento noticias: análisis por keywords es básico (sin NLP real). Opcional: upgrade a NewsAPI free (500 req/día)
- Sin redundancia: si una fuente falla, el score se degrada

## 5. Código de Integración

```html
<!-- Opción A: iframe (más simple) -->
<iframe src="http://localhost:8000/widget/fear-greed"
  width="320" height="400" frameborder="0"
  style="border-radius:12px;background:#0a0e17">
</iframe>

<!-- Opción B: Web Component (más ligero) -->
<script src="http://localhost:8000/widget/fear-greed.js"></script>
<fear-greed-widget></fear-greed-widget>
```

El widget se actualiza solo cada 60s. Al hacer clic en el velocímetro, se expande mostrando: VIX actual, sentimiento noticias, IPC, empleo, PMI y su contribución al score.

---

*Plan generado para asignar a Equipo A (Gemini 2.5 Flash + HY3) o Equipo B (Nemotron 3 + Owl Alpha). ¿Confirmas cuál equipo lo aborda?*
