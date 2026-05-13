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
│  [INIT]     Verificar entorno (init.sh)          │
├─────────────────────────────────────────────────┤
│  [SPEC]     Recuperar especificación de la tarea │
├─────────────────────────────────────────────────┤
│  [ACT]      Implementar / Revisar / Investigar   │
├─────────────────────────────────────────────────┤
│  [LOG]      Persistir en DB (agente_logs)        │
├─────────────────────────────────────────────────┤
│  [VERIFY]   Validar contra criteria de la spec   │
├─────────────────────────────────────────────────┤
│  [CLOSE]    Cerrar sesión, resumir en DB          │
└─────────────────────────────────────────────────┘
```

### 2.1 SYNC
```python
from harness.harness_db import HarnessDB
db = HarnessDB()
task = db.get_next_task()          # ← prioridad más alta
last_session = db.get_last_session()  # ← qué pasó antes
logs = db.get_recent_logs(task_id=task['id'])  # ← contexto previo
```

### 2.2 INIT
```bash
bash harness/init.sh
```
Si falla (exit code 2), **detente** y reporta el error.
Si da warnings (exit code 1), revisa pero puedes continuar.

### 2.3 SPEC
```python
spec = db.get_task_spec(task['id'])
# Si no hay spec, créala primero (SDD Nivel 2)
```

### 2.4 ACT
Implementa según la spec. Usa herramientas atómicas Unix.
**No edites archivos marcados con:** `// Generated from spec - do not edit`

### 2.5 LOG
```python
db.log_activity(
    session_id=SESSION_ID,
    agent_name="Hermes Agent",
    task_id=task['id'],
    action="implement",
    summary="Implementé el endpoint /api/v1/score con desglose de factores",
    files_changed=["backend/app/main.py", "backend/score_engine.py"],
    context_usage_pct=35,  # ← Regla 20-40%
)
```

### 2.6 VERIFY
Verifica contra los `acceptance_criteria` de la tarea.
Si falla → log con status='failed', no marques como 'done'.

### 2.7 CLOSE
```python
db.update_task_status(task['id'], 'done' if success else 'blocked')
db.close_session(SESSION_ID, summary="...", context_usage_end=current_pct)
```

---

## 🧠 3. GESTIÓN DE CONTEXTO — Regla 20-40%

> *BettaTech: la IA pierde precisión mucho antes de que el contexto esté lleno.*

### Regla
- **20-40% de capacidad de contexto**: es el momento de limpiar o reiniciar.
- **Recomendación**: si tu contexto actual supera el 40%, haz un `log_activity()` con resumen y sugiere reiniciar sesión.

### Cómo mantener el contexto limpio
1. **Memoria externa**: No guardes logs largos en el contexto. Usa `db.log_activity()`.
2. **Resúmenes**: Antes de saturarte, escribe un resumen en `agent_logs`.
3. **Contextos pequeños**: Cada sub-agente debe tener contexto pequeño y tarea específica.
4. **Sesiones nuevas**: Si estás en 40%+, cierra la sesión y abre una nueva.

---

## 📜 4. SPEC-DRIVEN DEVELOPMENT (SDD)

### Niveles
| Nivel | Descripción | Cuándo usarlo |
|-------|-------------|---------------|
| **1 — Spec First** | Escribir spec → Implementar | Features claras, bien entendidas |
| **2 — Spec Anchor** | Spec evoluciona con el código | Features complejas con iteración |
| **3 — Spec as Source** | Solo editas la spec. IA genera código. Código bloqueado 🚫 | Features maduras, estables |

### Flujo SDD Nivel 2 (nuestro default)
1. Escribe la spec en `HarnessDB.create_spec()`
2. Implementa contra la spec
3. Si el código revela algo que la spec no cubría → **actualiza la spec** (nunca solo el código)
4. Registra archivos generados como artefactos
5. Si es SDD Nivel 3, añade `// Generated from spec - do not edit` a los archivos

### Estructura de una Spec
```markdown
## Spec: [Código de Tarea] — [Título]

### Contexto
¿Por qué existe esta feature? ¿Qué problema resuelve?

### Interfaz / Contrato
¿Qué inputs recibe? ¿Qué outputs produce?

### Reglas de Negocio
- Regla 1: ...
- Regla 2: ...

### Criterios de Aceptación
- [ ] CA-1: ...
- [ ] CA-2: ...

### Archivos Generados
- `ruta/al/archivo.py`  // Generated from spec - do not edit

### Notas Técnicas
Implementación, consideraciones, advertencias.
```

---

## 👥 5. ARQUITECTURA MULTI-AGENTE

> *Anthropic: Agente Orquestador + Sub-agentes con contextos pequeños*

```
Usuario
   │
   ▼
┌─────────────────────────────────────────────────┐
│  AGENTE ORQUESTADOR (Hermes Agent)               │
│  • Recibe la instrucción del usuario             │
│  • Consulta la DB para estado actual             │
│  • Asigna tareas a sub-agentes                   │
│  • Revisa entregables                            │
│  • Reporta al usuario                            │
└─────────────────────────────────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Experto  │ │Program. │ │Revisor  │
│Macro    │ │Backend  │ │(valida) │
└─────────┘ └─────────┘ └─────────┘
```

### Roles
- **Orquestador** (Hermes Agent): Coordina, revisa, reporta. Acceso completo a la DB.
- **Experto**: Investiga, analiza, recomienda. Lee specs, escribe hallazgos en DB.
- **Programador**: Implementa según specs. Lee specs, escribe código.
- **Revisor**: Valida que el código cumpla la spec. Ejecuta tests.

### Comunicación entre agentes
No hay "pasar el contexto" manualmente. Todo queda en la DB:
- `agent_logs` → qué hizo cada agente
- `artifacts` → qué archivos se generaron
- `tasks.status` → dónde quedó cada tarea
- `specs` → el "qué" y "cómo" de cada feature

---

## ✅ 6. VERIFICACIÓN Y AUDITORÍA

> *"No confíes, verifica" — BettaTech*

Cada tarea debe pasar validación antes de marcarse como 'done':
1. **Init check** → `bash harness/init.sh` (entorno sano)
2. **Spec compliance** → El código implementa lo que dice la spec
3. **Tests** → Si hay tests, deben pasar
4. **Artifact integrity** → Los archivos generados no han sido modificados

---

## 📝 7. OUTPUT FORMAT

Al final de cada sesión, asegúrate de que la DB contenga:
- ✅ Log de actividad (`agent_logs`)
- ✅ Estado actualizado de la tarea (`tasks.status`)
- ✅ Session cerrada con resumen (`sessions`)
- ✅ Artefactos registrados si generaste código (`artifacts`)
- ✅ Decisiones documentadas si aplica (`decisions`)

---

## 📚 8. CONTEXT7 — Documentación de Librerías Externas

> *Context7 MCP: documentación actualizada en tiempo real para librerías, SDKs, APIs y frameworks.*

### Regla Context7

Antes de escribir **CUALQUIER código** que use una librería externa, SDK, framework, API o CLI tool:

1. **Resuelve el ID** → `mcp_context7_resolve_library_id(nombre, contexto)`
2. **Consulta docs** → `mcp_context7_query_docs(libraryId, "parámetros/funcionalidad específica")`
3. **Usa la documentación devuelta** para generar el código — no confíes en tus datos de entrenamiento

### Cuándo se activa

| Situación | Ejemplo | Acción |
|-----------|---------|--------|
| Importar una librería | `import pandas as pd` | Query docs antes de escribir |
| Llamar a API/SDK | `stripe.Customer.create()` | Verificar firmas actuales |
| Configurar framework | Express.js middleware | Consultar setup real |
| Usar CLI tool | Docker, gh CLI | Verificar sintaxis |
| Cloud SDK | AWS CDK, Terraform | Obtener ejemplos actuales |

### Excepciones (NO usar Context7)

- Python stdlib puro (`os`, `sys`, `json`, `re`, `pathlib`, etc.)
- Código interno del proyecto (no está en Context7)
- Lógica de negocio / algoritmos
- Misma librería ya consultada en los últimos 5 tool calls (evitar duplicados)

### Integración en el Pipeline Universal

| Fase | Acción Context7 |
|------|----------------|
| **SPEC** | Consultar Context7 para todas las dependencias externas → incrustar firmas reales de API |
| **ACT** | Antes de cada llamada a API externa en código → verificar parámetros actuales |
| **VERIFY** | Cruzar llamadas API del código contra docs de Context7 → marcar discrepancias |

---

## 🚫 9. CONSTRAINT SUMMARY

1. **No confíes en tu memoria de chat** — consulta la DB siempre
2. **No edites código con** `// Generated from spec - do not edit`
3. **Sigue el flujo** SYNC → INIT → SPEC → ACT → LOG → VERIFY → CLOSE
4. **Mantén contexto <40%** — si te acercas, resumir y reiniciar
5. **Prefiere herramientas Unix** sobre wrappers complejos
6. **Cada cambio de código vinculado a un task_id** — trazabilidad total
7. **Si algo no está en la spec, actualiza la spec primero** — nunca solo el código

---

*Protocolo establecido: 1 de Mayo 2026*
*Fuentes: BettaTech — "La Nueva Forma de Programar" + "¿Qué es el Harness Engineering?"*
*Adaptado para: Pegaton Invest Intelligence + Hermes Agent*
