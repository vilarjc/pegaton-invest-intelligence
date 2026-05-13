# Widget Fear & Greed — Especificación Técnica — Equipo A

**ID:** `fear-greed-a`
**Nombre:** Fear & Greed
**Sección:** `fear-greed`
**Equipo:** A
**PM:** Gemini 2.5 Flash
**Programador:** Tencent HY3
**Estado:** `ready`
**Versión:** 1.0 — Concurso Coding Olympiad

---

## 📐 1. ESPECIFICACIÓN

### 1.1 Tipo de Widget
Velocímetro semicircular tipo gauge con aguja (180°). Estilo oscuro premium con degradados en el arco.

### 1.2 Datos
- **Endpoint de datos:** `/api/v1/fear-greed`
- **Formato respuesta:** `{ score: 0-100, action: "Extreme Fear"|"Fear"|"Neutral"|"Greed"|"Extreme Greed", timestamp: "..." }`
- **Actualización:** On load + botón recargar manual

### 1.3 Visualización
- Arco semicircular de 180° con 5 zonas de color:
  - 0-20: Extreme Fear (rojo intenso)
  - 20-40: Fear (naranja/rojo)
  - 40-60: Neutral (amarillo)
  - 60-80: Greed (verde claro)
  - 80-100: Extreme Greed (verde intenso)
- Aguja rotatoria indicando el score actual
- Número grande centrado con el score
- Etiqueta textual del estado (Fear, Greed, etc.)
- Animación suave de entrada

### 1.4 Dimensiones
- Ancho: 340px
- Alto: ~280px incluyendo etiquetas
- Arco: 280px de diámetro, 160px de alto

### 1.5 Tecnología
- HTML + CSS + Canvas JavaScript
- Sin dependencias externas
- Canvas para el dibujo del gauge y la aguja

---

## 🧑‍💼 2. ANÁLISIS DEL PM (Gemini 2.5 Flash)

### 2.1 Brief recibido
> "Desarrolla un widget Fear & Greed para el dashboard de inversión. Debe mostrar un indicador visual claro del sentimiento de mercado en tiempo real. El widget debe ser auto-contenido (HTML + CSS + JS inline), estilo dark mode, tamaño compacto ~340px de ancho. Fuente de datos: endpoint interno /api/v1/fear-greed."

### 2.2 Decisión de diseño
Opté por un **velocímetro semicircular** porque:
1. Es el formato más reconocible para indicadores Fear & Greed
2. Permite ver instantáneamente la posición en el espectro
3. Ocupa poco espacio vertical (~160px el arco)
4. La aguja da una sensación de movimiento y datos vivos

### 2.3 Paleta de colores asignada
| Zona | Rango | Color |
|------|-------|-------|
| Extreme Fear | 0-20 | `#ff1744` |
| Fear | 20-40 | `#ff6d00` |
| Neutral | 40-60 | `#ffd600` |
| Greed | 60-80 | `#00e676` |
| Extreme Greed | 80-100 | `#00c853` |

### 2.4 Instrucciones al programador
- Usar Canvas API para dibujar arco y aguja
- Gradiente lineal en el arco (rojo → verde)
- Animación de la aguja al cargar (ease-out)
- Score como número grande centrado
- Actualizar cada 60s (opcional, mantener simple)

---

## 💡 3. DECISIONES TÉCNICAS

1. **Canvas vs SVG:** Canvas elegido por rendimiento en animación de aguja y facilidad para dibujar arcos graduales.
2. **Sin librerías externas:** Todo nativo para mantener el widget auto-contenido.
3. **Offset de mapeo:** El score 0-100 se mapea al ángulo 0-180° del semicírculo.
4. **Color dinámico:** El color del score se determina interpolando entre los 5 colores de zona según el valor.
5. **Dark mode fijo:** El fondo del widget es `#0e1520`, consistente con el dashboard.
