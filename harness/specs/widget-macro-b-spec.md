# Widget MACRO — Brief Básico — Equipo B

**ID:** `macro-b`
**Sección:** `macro`
**Equipo:** B
**PM:** DeepSeek V4 Flash
**Programador:** Qwen3 Coder
**Tamaño widget:** 400px de ancho

---

## 📐 Brief

### Información disponible
Tienes acceso a la tabla `macro_snapshots` en `harness.db` con datos históricos cada 4h:
- VIX, DXY, S&P 500, Oro, Petróleo
- PMI Manufacturero, PMI Servicios
- Inflación, Tasa Fed
- Timestamp de cada captura

También puedes descargar datos de fuentes gratuitas si lo prefieres.

### Qué visualizar
Indicadores macroeconómicos clave para un inversor. Tú decides:
- Qué indicadores destacar
- Cómo organizarlos (bandas, semáforos, gráficos, score compuesto...)
- Si incluir histórico/tendencia
- El estilo visual (dentro del dark mode del dashboard)

### Endpoint de datos
`GET /api/widgets/macro/data` → devuelve JSON con los últimos 10 registros de `macro_snapshots`.

### Restricciones
- HTML + CSS + JS auto-contenido (un solo archivo)
- Sin dependencias externas
- Dark mode
- 400px de ancho, alto libre (máximo 500px)
- Los datos deben refrescarse automáticamente cada 60s
