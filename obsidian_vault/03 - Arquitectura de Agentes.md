# Arquitectura de Agentes: Sistema de Inteligencia Colaborativa

## 🧠 Visión General
Un equipo de agentes especializados que trabajan coordinadamente bajo la supervisión del Project Manager Orquestador (yo) para construir, mantener y mejorar PEGATON INVEST INTELLIGENCE. Cada agente tiene un rol definido, acceso a herramientas específicas y utiliza modelos de IA optimizados para su tarea.

## 🏗️ Jerarquía y Roles

### 1. **Project Manager Orquestador** (Rol actual: Hermes Agent)
- **Responsabilidades**:
  - Definir visión, alcance y prioridades del proyecto
  - Desglosar epics en historias de usuario y tareas técnicas
  - Asignar trabajo a agentes especializados según sus capacidades
  - Revisar entregables, asegurar calidad y alineación con visión
  - Gestionar el backlog y planificar sprints iterativos
  - Comunicar avances y bloqueos al usuario (Juan Carlos)
  - Mantener actualizado el conocimiento en Obsidian
- **Modelo Predeterminado**: deepseek-v4-flash (actual) para coordinación y comunicación
- **Herramientas**: Todas las disponibles (terminal, file, web, session_search, etc.)
- **Interfaz Principal**: Telegram (para ti) + Obsidian (base de conocimiento)

### 2. **Agentes Expertos Especializados** (Uno por dominio)
#### a) Agente Experto en Macroeconomía
- **Responsabilidades**:
  - Identificar, evaluar y recomendar fuentes de datos macro confiables
  - Monitorear calendarios económicos y eventos de alto impacto
  - Interpretar indicadores macro en contexto de mercados financieros
  - Sugerir ponderaciones y relaciones entre variables macro y precios de activos
  - Generar informes de régimen económico (expansión, recesión, stagflación, etc.)
- **Fuentes Primarias**: FRED, Twelve Data (macro endpoints), World Bank, OECD, calendarios de investing.com/bloomberg
- **Modelo Recomendado**: 
  - Tareas complejas (análisis de relaciones, interpretación de datos): **DeepSeek razonador** (si se paga) o alternativa gratuita potente
  - Tareas básicas (búsqueda web, extracción de datos): **modelo gratuito actual** (deepseek-v4-flash)
- **Entrega**: Notas en Obsidian bajo `/04 - Fuentes de Datos` y análisis específicos

#### b) Agente Experto en Análisis Técnico
- **Responsabilidades**:
  - Investigar y validar indicadores técnicos óptimos para diferentes timeframes y activos
  - Detectar patrones de gráfico, divergencias y señales de alta probabilidad
  - Evaluar efectividad de combinaciones de indicadores (ej: RSI + MACD + volumen)
  - Sugerir umbrales y reglas para generación de señales técnicas
  - Backtesting rápido de hipótesis técnicas
- **Fuentes Primarias**: Datos de precios (Twelve Data, Alpha Vantage), libros técnicos clásicos, papers cuantitativos
- **Modelo Recomendado**: 
  - Desarrollo de nuevas fórmulas/indicadores: **DeepSeek razonador**
  - Análisis de datos existentes, visualización: **modelo gratuito o intermedio**
- **Entrega**: Documentación de indicadores, reglas de señal, resultados de backtesting

#### c) Agente Experto en Criptomonedas
- **Responsabilidades**:
  - Monitorear métricas on-chain hashrate, active addresses, exchange inflows/outflows
  - Analizar correlaciones entre cripto y activos tradicionales (risk-on/risk-off)
  - Evaluar impacto de actualizaciones de protocolo (halvings, forks, upgrades)
  - Seguir desarrollos regulatorios y adopción institucional
  - Identificar señales específicas del mercado cripto (sentimiento social, dominancia BTC)
- **Fuentes Primarias**: Blockchain explorers (Glassnode, CryptoQuant gratuitos), Twitter/X sentiment, datos de precios
- **Modelo Recomendado**: Similar al experto técnico - equilibrio entre razonamiento y eficiencia
- **Entrega**: Notas específicas de cripto, métrons on-chain a seguir

#### d) (Opcional futuro) Agente Experto en Sentimiento y Noticias
- Para análisis de noticias en tiempo real, detección de eventos de alto impacto, análisis de redes sociales

### 3. **Agentes Programadores**
- **Responsabilidades**:
  - Escribir, revisar y depurar código según especificaciones técnicas
  - Implementar APIs, algoritmos de score, pipelines de ingesta de datos
  - Crear y mantener pruebas unitarias/integración
  - Optimizar rendimiento y manejar errores
  - Documentar código y decisiones técnicas
- **Especialización**: 
  - Backend (Python/FastAPI, bases de datos)
  - Frontend (HTML/CSS/JS, eventualmente Flutter/React Native)
  - DevOps (despliegue, monitoreo, escalado)
- **Modelo Recomendado**:
  - Lógica compleja (algoritmos de score, integración de datos): **DeepSeek razonador o flash** (dependiendo de disponibilidad y presupuesto)
  - Código estándar (CRUD, configuración): **modelos gratuitos eficientes** (como CodeLlama, StarCoder2, o el gratuito actual si es suficiente)
  - Depuración y testing: **modelo gratuito con buenas capacidades de razonamiento**
- **Integración de OpenCode**: 
  - Si tienes OpenCode CLI configurado y accesible, puede usarse como **agente programador especializado** para tareas de código específico
  - Ideal para: generar componentes frontend complejos, escribir scripts de backend detallados, refactorización
  - Flujo: El PM asigna tarea → OpenCode ejecuta en tu entorno local → devuelve código para revisión → PM lo integra o solicita ajustes
  - Requisito: Necesitaría acceso a tu entorno (posiblemente mediante instrucciones para que lo ejecutes tú o mediante un canal de comunicación establecido)

### 4. **Agentes para Tareas Básicas y de Apoyo**
- **Responsabilidades**:
  - Búsqueda web profunda y síntesis de información
  - Extracción y estructuración de datos de APIs o sitios web
  - Monitoreo de cambios en fuentes (feeds, calendarios)
  - Tareas de limpieza y preprocessing de datos
  - Envío de notificaciones (si se configura)
  - Generación de reportes rutinarios
- **Modelo Recomendado**: Siempre el **modelo más económico disponible** que haga el trabajo bien (actualmente deepseek-v4-flash es excelente para esto)
- **Ejemplos**: 
  - "Busca el último comunicado del FED y extrae las decisiones clave"
  - "Extrae los tickers de la watchlist de esta página de TradingView"
  - "Verifica si el calendario económico de hoy tiene eventos de alto impacto"

## 🔄 Flujo de Trabajo Típico

1. **Definición**: El usuario (tú) da un input de requerimiento o visión de alto nivel
2. **Planificación**: El PM Orquestador:
   - Entiende el requerimiento
   - Consulta al agente experto correspondiente si se necesita conocimiento especializado
   - Desglosa en historias de usuario técnicas
   - Asigna tareas a agentes programadores y/o de apoyo
3. **Ejecución**:
   - Agentes expertos investigan y proveen contexto/conocimiento
   - Agentes programadores escriben el código
   - Agentes de apoyo manejan tareas de búsqueda, extracción, limpieza
4. **Revisión**: El PM revisa entregables, asegura calidad y alineación
5. **Integración**: El trabajo se combina en el sistema principal
6. **Documentación**: Todo se registra en Obsidian como conocimiento permanente
7. **Retroalimentación**: Se muestra al usuario para validación y siguiente iteración

## 💰 Estrategia de Uso de Modelos (Basado en tus indicaciones)

| Tipo de Tarea | Complejidad | Modelo Preferido | Razón |
|---------------|-------------|------------------|-------|
| **Toma de decisiones estratégicas, definición de visión** | Alta | **DeepSeek (modo razonador si disponible, sino flash)** | Necesita profundo entendimiento de contexto y consecuencias |
| **Análisis complejo de datos macro/técnico** | Alta-Media | DeepSeek razonador > flash > gratuito potente | Busca relaciones no obvias y fundamentación sólida |
| **Escribir algoritmos de score o lógica de negocio** | Media-Alta | DeepSeek flash (si pago) > razonador gratuito | Equilibrio entre corrección y velocidad |
| **Código estándar (CRUD, configuración, pruebas)** | Baja-Media | Modelo gratuito eficiente (ej: CodeLlama, o el actual si es suficiente) | Tareas repetitivas, bien definidas |
| **Búsqueda web, extracción de datos, síntesis de información** | Baja | Modelo gratuito actual (deepseek-v4-flash) | Excelente para comprender y resumir información |
| **Depuración, testing, revisiones de código** | Media | Modelo gratuito con buen razonamiento | Necesita entender lógica y encontrar edge cases |
| **Comunicación con el usuario, actualizaciones** | Baja-Media | Modelo actual (deepseek-v4-flash) | Claro, conciso, alineado con tono establecido |

**Nota sobre presupuestos**: Si decides usar DeepSeek de pago, sugiero asignar un presupuesto mensual modesto (ej: $10-20) que permitiría cientos de llamadas al modo flash o docenas al modo razonador, suficiente para el desarrollo activo. El resto se haría con modelos gratuitos.

## 📚 Integración con Obsidian
- Cada agente, al completar una tarea significativa, debe crear o actualizar una nota en el vault
- Estructura sugerida por agente:
  - `/agentes/experto-macro/[fecha] - tema.md`
  - `/agentes/experto-tecnico/[fecha] - indicador-algoritmo.md`
  - `/agentes/programador/[fecha] - feature-nombre.md`
- El PM mantiene notas maestras que resumen el estado actual de cada dominio
- Las notas incluyen: fuentes consultadas, decisiones tomadas, código relevante, pendientes

## 🚀 Próximos Pasos para Implementar Esta Arquitectura

1. **Configurar acceso a OpenCode (si aplica)**:
   - Verificar si tienes OpenCode CLI instalado y funcionando en tu máquina local
   - Si es así, documentar cómo invocarlo para que el PM pueda delegarle tareas de código
   - Si no, decidir si vale la pena instalarlo (es sencillo mediante npm) o esperar a tener necesidad clara

2. **Definir umbrales de uso de modelos pagos**:
   - Acordar contigo cuándo vale la pena usar DeepSeek de pago vs. esperar a usar gratuito
   - Ej: "Usa DeepSeek flash solo para tareas que tomarían >1 hora con gratuito y bloqueen el progreso"

3. **Crear plantillas de notas para agentes**:
   - Estándar para que cada agente sepa qué información registrar al entregar trabajo

4. **Primera asignación de tareas**:
   - Ya tengo la investigación macro completada (agente de apoyo)
   - Próxima: asignar a un agente experto técnico para investigar indicadores óptimos para el score inicial
   - Paralelamente: agente programador comienza a setting up el entorno de desarrollo

---
*Nota: Esta arquitectura está diseñada para empezar simple (solo yo actuando en múltiples roles) y escalar hacia especialización real a medida que el proyecto crece y se validating el valor de cada rol.*

*Generado por: Hermes Agent (Project Manager Orquestador)*  
*Fecha: $(date)*