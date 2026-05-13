# AGENTS.md — Harness Engineering Protocol

> Protocolo de entrada para todos los agentes del sistema PEGATON INVEST INTELLIGENCE.
> Basado en **Spec-Driven Development (SDD)** + **Harness Engineering**.
> **CADA interacción con el usuario sigue el Pipeline Universal (HU-6.3).**
> Lee esto COMPLETO antes de ejecutar cualquier acción.

---

## ⚡ REGLAS DE ORO

**Regla 1:** Cada input que entra al sistema (video, mensaje, documento, conversación) pasa por el **Pipeline Universal** (`harness/pipeline.py`). No hay excepciones.

**Regla 2:** No confíes en tu memoria interna de chat para el estado de las tareas. Consulta SIEMPRE la base de datos `harness.db`.

**Regla 3:** Si el pipeline no está completo (falla VERIFY), no puedes declarar la tarea como terminada.

---

## 🔄 0. PIPELINE UNIVERSAL — Entry Point Obligatorio

Cada interacción con el usuario SIGUE este pipeline. No puedes saltarte ningún paso.

```
┌─────────────────────────────────────────────────────────────┐
│                     CUALQUIER INPUT                          │
│   (video YouTube • mensaje • documento • conversación)       │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  1/6  📥  INGEST  →  harness/ingest.py                      │
│       Detecta tipo de input, extrae contenido estructurado   │
│       Si es YouTube → transcripción vía Tor proxy           │
│       Si es archivo → lectura                                │
│       Si es texto → procesamiento directo                   │
├──────────────────────────────────────────────────────────────┤
│  2/6  🔍  ANALYZE → ¿Qué significa este input?               │
│       Extraer: tema, puntos clave, entidades, urgencia       │
├──────────────────────────────────────────────────────────────┤
│  3/6  🧠  DECIDE  → ¿Qué acciones tomar?                     │
│       ¿Crear tareas? ¿Escribir specs? ¿Implementar?          │
│       ¿Solo registrar? ¿Loggear decisión?                    │
├──────────────────────────────────────────────────────────────┤
│  4/6  ⚡  ACT     → Ejecutar las acciones decididas           │
│       Implementar, crear tareas en DB, escribir specs, etc.  │
├──────────────────────────────────────────────────────────────┤
│  5/6  💾  LOG    → Persistir TODO en harness.db              │
│       agent_logs, session cerrada, decisiones registradas    │
├──────────────────────────────────────────────────────────────┤
│  6/6  ✅  VERIFY → Validar consistencia post-ejecución       │
│       verify.sh / db_verify.py. 0 errores requerido.        │
└──────────────────────────────────────────────────────────────┘
                          ▼
                  RESPUESTA AL USUARIO
```

### Cómo ejecutar el pipeline

```python
from harness.pipeline import Pipeline

pipe = Pipeline()
result = pipe.run(input_text)

# El pipeline ya registró todo en la DB.
# Usa result para tu respuesta al usuario.
ingested = result['ingested']    # contenido extraído
analysis = result['analysis']    # análisis estructurado
decision = result['decision']    # acciones decididas
results = result['results']      # resultados de acciones
verification = result['verification']  # verificación
```

### Nota importante
El pipeline.py ejecuta las partes **determinísticas** (ingest, log, verify) y delega las partes **razonadas** (analyze, decide) al agente (tú). Las etapas `stage_analyze` y `stage_decide` producen estructuras básicas que **tú debes enriquecer** con tu razonamiento de LLM. La etapa `stage_act` ejecuta acciones mecánicas (crear tareas, specs, loggear decisiones) — las acciones que requieren implementación real las ejecutas tú con tus herramientas.

---

## 🧭 1. INFRAESTRUCTURA — Database-Driven Harness

### 1.1 Memoria Compartida
La base de datos `harness.db` en la raíz del proyecto es **la única fuente de verdad** para:
- Estado de tareas y epics
- Especificaciones técnicas (Specs)
- Logs de actividad de agentes
- Artefactos generados (con checksums)
- Decisiones arquitectónicas

### 1.2 Interfaz de Acceso
Usa `harness/harness_db.py` — NO leas/escribas archivos JSON o Markdown para estado.
- `HarnessDB.get_next_task()` → ¿Qué hago ahora?
- `HarnessDB.get_task_spec(task_id)` → ¿Cuál es la spec?
- `HarnessDB.log_activity(...)` → Registrar lo que hice
- `HarnessDB.register_artifact(...)` → Trackear archivos generados

### 1.3 Herramientas Atómicas Unix
> *BettaTech + Vercel: eliminar el 80% de herramientas hiper-especializadas mejora 3x el rendimiento y reduce 37% los tokens.*

Prefiere: `grep`, `cat`, `ls`, `find`, `python3 script.py`
Evita: wrappers complejos, herramientas propietarias que hacen demasiado.

---

## 🔄 2. OPERATIONAL PROTOCOL — Chain of Action

Cada sesión de agente sigue este flujo EXACTO:

```
┌─────────────────────────────────────────────────┐
│  [SYNC]     Consultar DB → leer estado actual   │
├─────────────────────────────────────────────────┤
│  [INIT]     Verificar entorno (