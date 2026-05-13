# Widget Fear & Greed — Especificación Técnica — Equipo C

**ID:** `fear-greed-c`
**Nombre:** Fear & Greed
**Sección:** `fear-greed`
**Equipo:** C
**PM:** DeepSeek V4 Flash
**Programador:** DeepSeek V4 Flash (autónomo)
**Estado:** `ready`
**Versión:** 1.0 — Concurso Coding Olympiad

---

## 📐 1. ESPECIFICACIÓN

### 1.1 Tipo de Widget
Barra termómetro horizontal con indicador de posición deslizante. Estilo oscuro, diseño limpio minimalista.

### 1.2 Datos
- **Endpoint de datos:** `/api/v1/fear-greed`
- **Formato respuesta:** `{ score: 0-100, action: "Extreme Fear"|"Fear"|"Neutral"|"Greed"|"Extreme Greed", timestamp: "..." }`
- **Actualización:** On load + interacción click para refrescar

### 1.3 Visualización
- Barra horizontal con degradado de 5 colores (rojo → naranja → amarillo → verde claro → verde)
- Marcador deslizante que indica la posición exacta del score
- Score numérico grande sobre el marcador
- Etiqueta de estado (Fear, Greed, etc.) con icono
- Flecha direccional indicando tendencia
- Interactivo: click cambia entre vista compacta y detallada

### 1.4 Dimensiones
- Ancho: 320px
- Alto: ~200px (modo detallado), ~80px (modo compacto)
- Barra: 280px × 16px

### 1.5 Tecnología
- HTML + CSS + JavaScript vanilla
- Sin Canvas, todo basado en DOM + CSS
- `clip-path` para la barra de degradado
- `requestAnimationFrame` para animación del marcador

---

## 🧑‍💼 2. ANÁLISIS DEL PM (DeepSeek V4 Flash)

### 2.1 Brief recibido
> "Desarrolla un widget Fear & Greed que sea informativo y usable. Debe ser compacto pero legible. El dashboard inversor necesita datos rápidos de interpretar. Dark mode. ~320px de ancho."

### 2.2 Decisión de diseño
Opté por una **barra tipo termómetro horizontal** porque:
1. Es el formato más universal y fácil de leer
2. Una barra horizontal encaja mejor en layouts de dashboard junto a otros widgets
3. El marcador deslizante es intuitivo — cualquiera entiende "dónde estamos"
4. Menos "adorno" visual, más datos
5. Modo interactivo: click para expandir/contraer

### 2.3 Paleta de colores asignada
| Zona | Rango | Color CSS |
|------|-------|-----------|
| Extreme Fear | 0-20 | `#d32f2f` |
| Fear | 20-40 | `#f57c00` |
| Neutral | 40-60 | `#fbc02d` |
| Greed | 60-80 | `#7cb342` |
| Extreme Greed | 80-100 | `#2e7d32` |

### 2.4 Instrucciones (auto-programación)
- Implementar como componente DOM puro (sin canvas)
- Barra con `linear-gradient` de 5 stops
- Marcador triangular (▾) sobre la barra en la posición del score
- Tooltip con score exacto sobre el marcador
- Animación ease-out al cargar: el marcador se desliza desde 0 hasta su posición
- Al hacer click en el widget, expandir/contraer para mostrar detalles adicionales

---

## 💡 3. DECISIONES TÉCNICAS

1. **DOM vs Canvas:** Todo DOM — más fácil de inspeccionar, depurar y modificar. La animación se maneja con CSS transitions.
2. **Degradado CSS:** `linear-gradient(to right, ...)` con 5 stops. No necesita redibujado en canvas.
3. **Interactividad:** Click toggle entre vista compacta (solo barra + score) y detallada (con etiquetas de zona, flecha tendencia, última actualización).
4. **Accesibilidad:** La barra y el marcador son elementos DOM reales, accesibles y seleccionables.
5. **Auto-contenido:** Widget completo en un solo HTML, sin dependencias, compatible con iframe.
