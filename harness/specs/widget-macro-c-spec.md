# Widget MACRO — Brief Básico — Equipo C

**ID:** `macro-c`
**Sección:** `macro`
**Equipo:** C
**PM:** Groq Qwen3
**Programador:** DeepSeek V4 Flash
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
Panorama macroeconómico completo. Tú decides:
- Qué indicadores son más relevantes
- Cómo presentarlos (tabla, tarjetas, gauge, radar...)
- Si incluir diagnóstico de mercado
- Si mostrar cambios vs captura anterior

### Endpoint de datos
`GET /api/widgets/macro/data` → devuelve JSON con los últimos 10 registros de `macro_snapshots`.

### Restricciones
- HTML + CSS + JS auto-contenido (un solo archivo)
- Sin dependencias externas
- Dark mode
- 400px de ancho, alto libre (máximo 500px)
- Los datos deben refrescarse automáticamente cada 60s
