# Widget Fear & Greed — Especificación Técnica — Equipo B

**ID:** `fear-greed-b`
**Nombre:** Fear & Greed
**Sección:** `fear-greed`
**Equipo:** B
**PM:** Nemotron 3 Super
**Programador:** Owl Alpha
**Estado:** `ready`
**Versión:** 1.0 — Concurso Coding Olympiad

---

## 📐 1. ESPECIFICACIÓN

### 1.1 Tipo de Widget
Anillo tipo speedometer circular completo con efecto glow y arco progresivo. Estilo oscuro premium con neón.

### 1.2 Datos
- **Endpoint de datos:** `/api/v1/fear-greed`
- **Formato respuesta:** `{ score: 0-100, action: "Extreme Fear"|"Fear"|"Neutral"|"Greed"|"Extreme Greed", timestamp: "..." }`
- **Actualización:** On load + animación fluida en transiciones

### 1.3 Visualización
- Anillo circular completo (360°) con arco que se llena progresivamente según el score
- Efecto glow en el borde del anillo (color varía con el sentimiento)
- 5 zonas de color en el arco:
  - 0-20: Extreme Fear (rojo neón)
  - 20-40: Fear (naranja)
  - 40-60: Neutral (amarillo)
  - 60-80: Greed (verde lima)
  - 80-100: Extreme Greed (verde neón brillante)
- Score grande centrado en el anillo
- Etiqueta de estado debajo del score
- Líneas de tick/marcas alrededor del anillo

### 1.4 Dimensiones
- Ancho: 330px
- Diámetro del anillo: 230px
- Efecto glow exterior con gradiente radial

### 1.5 Tecnología
- HTML + CSS + Canvas JavaScript
- Sin dependencias externas
- Canvas para el anillo, gradientes y glow

---

## 🧑‍💼 2. ANÁLISIS DEL PM (Nemotron 3 Super)

### 2.1 Brief recibido
> "Desarrolla un widget Fear & Greed visualmente impactante. El dashboard inversor necesita un indicador que capte la atención y transmita la emoción del mercado. Debe verse premium, moderno, con animaciones suaves. Formato compacto ~330px."

### 2.2 Decisión de diseño
Elegí un **anillo circular con glow** porque:
1. El formato circular completo permite un arco más largo y vistoso
2. El efecto glow da una sensación "premium" y tecnológica
3. El círculo completo se siente más dinámico que un semicírculo
4. Las marcas de tick añaden precisión visual

### 2.3 Paleta de colores asignada
| Zona | Rango | Color | Glow |
|------|-------|-------|------|
| Extreme Fear | 0-20 | `#ff1744` | `rgba(255,23,68,0.3)` |
| Fear | 20-40 | `#ff9100` | `rgba(255,145,0,0.3)` |
| Neutral | 40-60 | `#ffd600` | `rgba(255,214,0,0.3)` |
| Greed | 60-80 | `#69f0ae` | `rgba(105,240,174,0.3)` |
| Extreme Greed | 80-100 | `#00e676` | `rgba(0,230,118,0.4)` |

### 2.4 Instrucciones al programador
- Anillo circular con Canvas, no SVG
- El arco debe llenarse con animación al cargar (transición de 0 a score actual)
- Sombra glow exterior que coincida con el color del sentimiento actual
- Tick marks cada 10 unidades alrededor del anillo
- Texto del score en el centro, grande y bold
- Fondo sutil con gradiente radial para profundidad

---

## 💡 3. DECISIONES TÉCNICAS

1. **Canvas con múltiples capas:** Se dibuja primero el anillo base (fondo gris oscuro), luego el arco activo con gradiente, luego el glow con blur.
2. **Glow nativo:** Se usa `shadowBlur` y `shadowColor` de Canvas para el efecto neón sin librerías.
3. **Animación progresiva:** El arco se dibuja incrementalmente usando `requestAnimationFrame` desde ángulo 0 hasta el score actual.
4. **Tick marks:** Se calculan 10 marcas equidistantes alrededor del círculo, cada una rotada con transformaciones canvas.
5. **Auto-refresh:** No incluido por diseño — el usuario recarga manual o se refresca desde el dashboard.
