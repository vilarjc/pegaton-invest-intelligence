# Backlog MVP (Producto Mínimo Viable)

## 🎯 Objetivo del MVP
Entregar un sistema funcional que muestre un **Pegaton Score (0-100)** para tres activos base (S&P 500, EUR/USD, BTC/USD) combinando análisis macro (40%) y técnico (60%), con capacidad de watchlist editable y matriz de acción básica.

## 📋 Historias de Usuario (Priorizadas)

### Épica 1: Motor de Señales Pegaton (Core)
- **HU-1.1**: Como usuario, quiero ver un Pegaton Score (0-100) para cada activo en mi watchlist para evaluar rápidamente la convicción alcista/bajista.
  - Tareas:
    - [ ] Crear endpoint API `/score/{symbol}` que devuelve score y timestamp
    - [ ] Implementar función de ingesta macro diaria desde FRED (Fed Funds, CPI, PMI, etc.)
    - [ ] Implementar ingesta de precios en tiempo real/cercano a real-time desde Twelve Data (SPX, EUR/USD, BTC/USD)
    - [ ] Diseñar algoritmo de normalización (z-score sobre ventana 60d) para indicadores macro
    - [ ] Diseñar algoritmo de señal técnica (combinación ponderada de RSI, MACD, posición vs SMA50/200)
    - [ ] Combinar macro (40%) + técnico (60%) en score final 0-100
    - [ ] Almacenar cálculos en base SQLite para historial y consistencia

- **HU-1.2**: Como usuario, necesito entender qué factores están impulsando el score para confiar en la señal.
  - Tareas:
    - [ ] Extender endpoint `/score/{symbol}` para incluir desglose de factores alcistas/bajistas con peso %
    - [ ] Ejemplo de factores: "+25% por caída en rendimiento 10Y, -15% por RSI >70"
    - [ ] Almacenar historial de factores para análisis de drift

### Épica 2: Análisis Macro-Técnico Básico
- **HU-2.1**: Como usuario, quiero ver indicadores macro clave actualizados para contextualizar las señales.
  - Tareas:
    - [ ] Endpoint `/macro` que devuelve últimos valores de 3-5 indicadores macro (Fed Funds rate, CPI YoY, ISM Manufacturero PMI, etc.)
    - [ ] Mostrar valor actual, cambio diario, tendencia (subiendo/bajando/estable)
    - [ ] Actualización automática cada 24h (cron job)

- **HU-2.2**: Como usuario, necesito análisis técnico estándar para validar las señales.
  - Tareas:
    - [ ] Endpoint `/technical/{symbol}` que devuelve RSI(14), MACD, señal, histograma, precio vs SMA50/SMA200
    - [ ] Usar librería `ta` o `pandas-ta` para cálculos consistentes
    - [ ] Actualización cada vez que llegan nuevos datos de precio (o cada 5min si polling)

### Épica 3: Interfaz y Experiencia de Usuario (Webapp Simple)
- **HU-3.1**: Como usuario, quiero una watchlist editable donde pueda añadir activos y ver su Pegaton Score.
  - Tareas:
    - [ ] Frontend HTML/JS con input para añadir/quitar ticker (ej: SPX, EUR/USD, BTC/USD)
    - [ ] Mostrar lista de activos con su score actual (actualizado cada 60s vía polling o WebSocket)
    - [ ] Persistir watchlist en localStorage del navegador

- **HU-3.2**: Como usuario, necesito una matriz de acción clara que me diga qué hacer hoy.
  - Tareas:
    - [ ] Definir umbrales de score para acciones:
        - 80-100: 🔵 COMPRAR (fuerte alcista)
        - 60-79: 🔵 ACUMULAR (alcista moderado)
        - 40-59: 🟡 MANTENER (neutral)
        - 20-39: 🟠 REDUCIR (bajista moderado)
        - 0-19: 🔴 EVITAR (fuerte bajista)
    - [ ] Mostrar botón grande con color y texto de acción recomendada por activo
    - [ ] Incluir tooltip breve con razón principal (ej: "Score 82: fuerte impulso macro alcista")

### Épica 4: Gestión de Portfolio (Versión Manual)
- **HU-4.1**: Como usuario, quiero tracking básico de mi portfolio para ver P&L en relación con las señales.
  - Tareas:
    - [ ] Formulario simple para ingresar posición: activo, cantidad, precio de entrada, fecha
    - [ ] Cálculo automático de valor actual (precio actual * cantidad), P&L no realizado, % cambio
    - [ ] Mostrar distribución por activo (valor y %)
    - [ ] Persistir en localStorage o SQLite (si usuario prefiere)

## 📏 Métricas de Éxito para el MVP
- [ ] Score actualizado cada 60s para al menos 3 activos
- [ ] Desglose de factores disponible y legible
- [ ] Watchlist funcional (añadir/quitar, persistir)
- [ ] Matriz de acción con colores y texto correcto
- [ ] Portfolio manual muestra P&L correcto
- [ ] Webapp accesible en localhost:8000 (o similar) con diseño limpio y usable
- [ ] Documentación en Obsidian actualizada con decisiones técnicas

## ⏱️ Estimación de Esfuerzo (Rough)
- Backend API y lógica de score: 8-12 hrs
- Ingesta de datos (FRED + Twelve Data): 4-6 hrs
- Algoritmos de señal (macro + técnico): 6-8 hrs
- Frontend básico (HTML/JS + interacción): 6-8 hrs
- Integración y testing: 4-6 hrs
- Documentación y setup inicial: 2-4 hrs
- **Total estimado: 30-44 horas** (puede distribuirse en varios días)

## 🔄 Flujo de Trabajo Sugerido
1. Configurar entorno de backend y obtener API keys (FRED, Twelve Data)
2. Implementar ingesta macro y crear tabla en SQLite
3. Implementar ingesta de precios y cálculo de indicadores técnicos
4. Construir algoritmo de score y endpoint
5. Crear frontend simple que consume los endpoints
6. Añadir watchlist y matriz de acción
7. Implementar portfolio manual básico
8. Testing, ajuste de umbrales, documentación

---
*Generado por: Hermes Agent (Project Manager Orquestador)*  
*Fecha: $(date)*  
*Próxima revisión: Después de completar HU-1.1 y HU-1.2 para validar el core*