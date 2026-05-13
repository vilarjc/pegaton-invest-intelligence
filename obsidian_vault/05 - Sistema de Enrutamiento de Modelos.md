# 🤖 Sistema de Enrutamiento Inteligente de Modelos

## Visión General
Un sistema que **clasifica cada tarea** (simple/media/compleja/crítica) y la **enruta al modelo de IA óptimo** según su complejidad, respetando límites de presupuesto configurables.

## 🧠 Cómo Funciona
```
Tarea entrante → Clasificador de complejidad → Consulta de presupuesto → Modelo óptimo
                                                        ↓
                                             Budget Tracker (registro)
```

## 📊 Niveles de Tarea y Modelos

| Nivel | Modelo Preferido | Costo/uso | ¿Qué incluye? |
|-------|-----------------|-----------|---------------|
| 🟢 Simple | deepseek-v4-flash (gratuito) | $0 | Búsquedas web, extracción, scraping, comandos estándar |
| 🟡 Media | deepseek-v4-flash o DeepSeek Flash | ~$0.003 | Programación media, análisis de datos, debugging |
| 🔴 Compleja | DeepSeek V4 Flash (razonador) | ~$0.03 | Algoritmos de señales, arquitectura, análisis macro |
| ⚠️ Crítica | DeepSeek V4 Flash + revisión humana | ~$0.08 | Decisiones que afectan señales de trading |

## 💰 Límites de Presupuesto
- **Diario**: $2.00
- **Semanal**: $10.00  
- **Mensual**: $30.00
- *Gasto actual*: **$0.00** (aún no se ha usado ningún modelo de pago)

## 🔧 Uso desde el PM (Hermes Agent)
Cuando el usuario solicita una tarea:
1. Clasificar en Simple/Media/Compleja/Crítica
2. Ejecutar `check_budget(nivel)` antes de usar modelo de pago
3. Registrar tareas de pago con `register_task()`
4. Informar al usuario si se acerca al límite (>90%)

## 📁 Archivos del Sistema
- **Script principal**: `backend/scripts/budget_tracker.py`
- **Registro de gastos**: `data/budget_tracker.json`
- **Skill de Hermes**: `mlops/model-router` (con documentación completa)

---
*Este sistema es la columna vertebral para gestionar costos a medida que crecen los agentes especializados.*