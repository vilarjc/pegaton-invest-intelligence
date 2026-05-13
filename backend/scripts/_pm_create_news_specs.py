#!/usr/bin/env python3
"""
PM Script — Crea specs y tareas para el modulo de Noticias en harness.db
Ejecutado por el Orquestador (Hermes Agent) siguiendo Harness Engineering SDD Nivel 2.

Correcciones aplicadas:
  - create_task() NO acepta 'status' (se ignora o da error)
  - create_spec() NO acepta 'spec_id' (se autogenera)
  - assign_task() se usa DESPUES de crear la tarea (se requiere id entero)
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from harness.harness_db import HarnessDB
from datetime import datetime

db = HarnessDB()

# ═══════════════════════════════════════════════════════════════
# SYNC — Verificar estado actual
# ═══════════════════════════════════════════════════════════════
print("=== SYNC: Verificando estado de la DB ===")

epics = db.get_epics()
print(f"Epics existentes: {len(epics)}")
for e in epics:
    print(f"  id={e['id']} code={e['code']}: {e['title'][:60]}")

# Buscar epic "NOTICIAS" existente
epic_existente = None
for e in epics:
    if e['code'] == 'EP-NEWS':
        epic_existente = e
        break

# ═══════════════════════════════════════════════════════════════
# EPIC: Modulo Noticias
# ═══════════════════════════════════════════════════════════════
print("\n=== EPIC del modulo Noticias ===")

epic_desc = """Modulo de Noticias y Sentimiento para PEGATON INVEST INTELLIGENCE.
Analisis de sentimiento de mercado basado en noticias financieras en tiempo real.
Entrada: RSS feeds (Reuters, CNBC, MarketWatch, Google News, Yahoo Finance)
Procesamiento: VADER sentiment analysis (0 LLM tokens)
Salida: Score 0-100, desglose por fuente, tendencia, alertas"""

if epic_existente:
    epic_id = epic_existente['id']
    print(f"  ℹ️ EP-NEWS ya existe (id={epic_id})")
else:
    epic_id = db.create_epic(
        code="EP-NEWS",
        title="Modulo de Noticias y Sentimiento de Mercado",
        description=epic_desc,
        priority=1
    )
    print(f"  ✅ EP-NEWS creado con id={epic_id}")

# ═══════════════════════════════════════════════════════════════
# TASK 1: Widget de sentimiento de noticias
# ═══════════════════════════════════════════════════════════════
print("\n=== Tarea HU-NEWS-01 — Widget Sentimiento Noticias ===")

task1_desc = """Widget frontend de Sentimiento de Noticias para el inversor.
- Consume /api/v1/news-sentiment
- Gauge circular Canvas 0-100 (estilo fear-greed-equipo-a)
- Desglose por fuente (Reuters, CNBC, Google News, MarketWatch, Yahoo Finance)
- Tendencia (delta vs snapshot anterior)
- Alertas extremos (<20 panico, >80 euforia)
- Top keywords/temas en titulares
- Auto-refresh 60 segundos
- Dark theme consistente"""

task1 = db.create_task(
    code="HU-NEWS-01",
    title="Widget de Sentimiento de Noticias",
    epic_id=epic_id,
    description=task1_desc,
    priority=1,
    acceptance_criteria=[
        "Widget HTML autonomo en frontend/widgets/news-sentimiento.html",
        "Consume /api/v1/news-sentiment correctamente",
        "Gauge circular con Canvas (estilo fear-greed-equipo-a)",
        "Colores: rojo <20, naranja <45, amarillo <55, verde <75, morado >75",
        "Panel desplegable con desglose por fuente",
        "Indicador de tendencia delta visible junto al score",
        "Top keywords como badges/etiquetas",
        "Alerta visual EXTREME_FEAR (<20) y EXTREME_GREED (>80)",
        "Auto-refresh cada 60s",
        "Compatible con iframe sin scrollbars",
        "Dark theme #0a0e17, bordes #1a2332"
    ]
)
print(f"  ✅ HU-NEWS-01 creada con id={task1}")

# ═══════════════════════════════════════════════════════════════
# TASK 2: Endpoint extendido
# ═══════════════════════════════════════════════════════════════
print("\n=== Tarea HU-NEWS-02 — Endpoint Extendido ===")

task2_desc = """Extender /api/v1/news-sentiment con datos adicionales para el inversor.
Actualmente devuelve: {score, total_articles, sources, timestamp, status}
Agregar: delta, alert, top_keywords, distribution"""

task2 = db.create_task(
    code="HU-NEWS-02",
    title="Endpoint extendido de sentimiento de noticias",
    epic_id=epic_id,
    description=task2_desc,
    priority=1,
    acceptance_criteria=[
        "Endpoint devuelve campos nuevos: delta (int), alert (string|null), top_keywords (array), distribution (object)",
        "Delta = score_actual - score_snapshot_anterior",
        "Alerta EXTREME_FEAR si score < 20",
        "Alerta EXTREME_GREED si score > 80",
        "top_keywords: extraer de titulos, filtrar stopwords EN+ES, min 3 apariciones, top 10",
        "distribution: fear 0-24, neutral 25-74, greed 75-100",
        "Retrocompatible: campos existentes no cambian",
        "Responde en <200ms"
    ]
)
print(f"  ✅ HU-NEWS-02 creada con id={task2}")

# ═══════════════════════════════════════════════════════════════
# TASK 3: Crontab de ingesta
# ═══════════════════════════════════════════════════════════════
print("\n=== Tarea HU-NEWS-03 — Crontab Ingesta ===")

task3_desc = """Configurar crontab del sistema para ingesta cada 4h sin tokens LLM.
REGLA CRITICA: USAR crontab del sistema (crontab -e), NO Hermes cron.
Hermes cron SIEMPRE lanza sesion LLM y consume tokens."""

task3 = db.create_task(
    code="HU-NEWS-03",
    title="Crontab de ingesta de noticias (0 LLM tokens)",
    epic_id=epic_id,
    description=task3_desc,
    priority=2,
    acceptance_criteria=[
        "Crontab configurado: 0 */4 * * *",
        "Ejecuta scripts/ingest_news_sentiment.py",
        "Log en /var/log/ingesta_news.log",
        "0 tokens LLM consumidos",
        "Verificable con: crontab -l"
    ]
)
print(f"  ✅ HU-NEWS-03 creada con id={task3}")

# ═══════════════════════════════════════════════════════════════
# TASK 4: Integración en dashboards
# ═══════════════════════════════════════════════════════════════
print("\n=== Tarea HU-NEWS-04 — Integración Dashboards ===")

task4_desc = """Integrar widget de noticias en paginas existentes:
1. auditoria-completa.html: pestaña 'Noticias' junto a Fear & Greed
2. auditoria-real.html: widget news-sentimiento en panel de equipos
3. dashboard-inversor.html: sección de sentimiento de noticias"""

task4 = db.create_task(
    code="HU-NEWS-04",
    title="Integracion del widget en dashboards",
    epic_id=epic_id,
    description=task4_desc,
    priority=2,
    acceptance_criteria=[
        "auditoria-completa.html incluye pestaña Noticias con widget",
        "auditoria-real.html incluye news-sentimiento en panel equipos",
        "dashboard-inversor.html incluye seccion sentimiento noticias",
        "Todas usan iframe -> /widgets/news-sentimiento.html",
        "Layout responsive y consistente"
    ]
)
print(f"  ✅ HU-NEWS-04 creada con id={task4}")

# ═══════════════════════════════════════════════════════════════
# SPECS
# ═══════════════════════════════════════════════════════════════
print("\n=== Creando Specs Técnicas ===")

spec_widget = """# Spec: Widget de Sentimiento de Noticias (SDD Nivel 2 - Spec Anchor)

## Contexto
El inversor necesita un widget visual que muestre el indice de sentimiento
de noticias financieras para tomar decisiones de inversion.

## Interface/Contract
- Fuente de datos: GET /api/v1/news-sentiment
- Formato respuesta (tras HU-NEWS-02):
```json
{
  "score": 0-100,
  "delta": -100..+100,
  "delta_pct": "+X%" o "-X%",
  "alert": null | "EXTREME_FEAR" | "EXTREME_GREED",
  "total_articles": N,
  "sources": {"reuters": 5, "cnbc": 3, ...},
  "top_keywords": [{"word": "inflation", "count": 12}, ...],
  "distribution": {"fear": N, "neutral": N, "greed": N},
  "timestamp": "ISO8601",
  "status": "ready|pending|error"
}
```
- Auto-refresh: cada 60 segundos
- Dimensiones: ~340px ancho, ~480px expandido

## Business Rules
1. Score 0-24: Panico Extremo (rojo #ff3b30)
2. Score 25-44: Panico (naranja #ff9500)
3. Score 45-54: Neutral (amarillo #ffcc02)
4. Score 55-74: Optimista (verde #34c759)
5. Score 75-80: Euforia (azul #007aff)
6. Score 81-100: Euforia Extrema (morado #af52de)
7. Delta > 0: tendencia alcista (flecha arriba verde)
8. Delta < 0: tendencia bajista (flecha abajo roja)
9. Delta = 0: neutro (flecha derecha gris)
10. Alerta EXTREME_FEAR si score < 20 (banner rojo pulsante)
11. Alerta EXTREME_GREED si score > 80 (banner morado pulsante)
12. Sin datos: estado "pending", score 50 neutro
13. Keywords como badges, max 10
14. Distribucion: mini-barras horizontales (3 colores)
15. Desglose por fuente: nombre + conteo + barra proporcion

## Acceptance Criteria
- Widget HTML autonomo (frontend/widgets/news-sentimiento.html)
- Gauge circular con Canvas
- Panel desplegable con desglose por fuente
- Indicador de tendencia (delta)
- Top keywords como badges
- Alerta visual para extremos (banner pulsante)
- Distribucion por rango (mini-barras)
- Auto-refresh 60s con indicador de estado
- Compatible con iframe
- Dark theme consistente
"""

spec_endpoint = """# Spec: Endpoint Extendido /api/v1/news-sentiment (SDD Nivel 2)

## Contexto
El endpoint actual devuelve score y fuentes. Se extiende con tendencia,
alertas y analisis de palabras clave.

## Nuevos campos en respuesta
```json
{
  "delta": int,
  "delta_pct": "+X%" o "-X%",
  "alert": null | "EXTREME_FEAR" | "EXTREME_GREED",
  "top_keywords": [{"word": "...", "count": N}, ...],
  "distribution": {"fear": N, "neutral": N, "greed": N}
}
```

## Business Rules
1. Delta = score_actual - score_snapshot_anterior
2. delta_pct = "±round(abs(delta))%"
3. Alerta EXTREME_FEAR si score < 20
4. Alerta EXTREME_GREED si score > 80
5. top_keywords: extraer de titulos, filtrar stopwords EN+ES, min 3 apariciones, top 10
6. distribution: fear 0-24, neutral 25-74, greed 75-100
7. Sin snapshot anterior: delta=0, delta_pct="0%"
8. Empate en keywords: ordenar alfabeticamente
9. Max 10 keywords

## Acceptance Criteria
- Endpoint responde con campos nuevos manteniendo los existentes
- Retrocompatible
- Responde en <200ms
- top_keywords filtrado de stopwords correcto
- distribution cuenta correctamente por rango
"""

try:
    s1 = db.create_spec(
        task_id=task1,
        title="Widget Sentimiento Noticias",
        content=spec_widget.strip(),
        sdd_level=2,
        generated_files=["frontend/widgets/news-sentimiento.html"]
    )
    print(f"  ✅ SPEC creado para HU-NEWS-01 (id={s1})")
except Exception as e:
    print(f"  ⚠️ Spec widget error: {e}")

try:
    s2 = db.create_spec(
        task_id=task2,
        title="Endpoint Extendido Noticias",
        content=spec_endpoint.strip(),
        sdd_level=2,
        generated_files=[]
    )
    print(f"  ✅ SPEC creado para HU-NEWS-02 (id={s2})")
except Exception as e:
    print(f"  ⚠️ Spec endpoint error: {e}")

try:
    s3 = db.create_spec(
        task_id=task3,
        title="Crontab Ingesta Noticias",
        content="""# Spec: Crontab de Ingesta de Noticias (SDD Nivel 2)

## Contexto
La ingesta de noticias debe ejecutarse cada 4 horas sin consumir tokens LLM.

## Implementation
- Crontab del sistema: 0 */4 * * *
- Comando: cd /root/pegaton_invest_intelligence && python3 scripts/ingest_news_sentiment.py >> /var/log/ingesta_news.log 2>&1
- NO usar Hermes cron (consume tokens LLM aunque use script:)
- Logs rotativos: max 7 dias

## Acceptance Criteria
- Crontab activo verificable con crontab -l
- Script ejecuta sin errores
- Log en /var/log/ingesta_news.log
- 0 tokens LLM consumidos (Python puro + VADER)
- DB actualizada con nuevos articulos tras cada ejecucion
""",
        sdd_level=2,
        generated_files=[]
    )
    print(f"  ✅ SPEC creado para HU-NEWS-03 (id={s3})")
except Exception as e:
    print(f"  ⚠️ Spec crontab error: {e}")

try:
    s4 = db.create_spec(
        task_id=task4,
        title="Integracion Dashboards Noticias",
        content="""# Spec: Integracion del Widget en Dashboards (SDD Nivel 2)

## Contexto
El widget de noticias debe aparecer en las 3 paginas principales del inversor.

## Changes
1. auditoria-completa.html: Añadir pestaña "Noticias" junto a Fear & Greed
   - Contenido: iframe widget + codigo fuente + decisiones PM
   - Seguir patron exacto de las pestañas existentes

2. auditoria-real.html: Añadir seccion de noticias en panel de equipos
   - Entrada: news-sentimiento-a: { label: 'Noticias', widget: 'news-sentimiento.html' }
   - Seguir patron de carga que fear-greed

3. dashboard-inversor.html: Añadir widget en la pagina del inversor
   - Nueva seccion "Sentimiento de Noticias" con iframe al widget

## Acceptance Criteria
- Widget visible en las 3 paginas
- Carga correcta via iframe
- Responsive y consistente con el diseño
""",
        sdd_level=2,
        generated_files=[]
    )
    print(f"  ✅ SPEC creado para HU-NEWS-04 (id={s4})")
except Exception as e:
    print(f"  ⚠️ Spec dashboards error: {e}")

# ═══════════════════════════════════════════════════════════════
# LOG — Registrar sesión de planificación
# ═══════════════════════════════════════════════════════════════
print("\n=== Registrando actividad ===")
session_id = f"news-plan-{datetime.now().strftime('%Y%m%d%H%M%S')}"
try:
    db.log_activity(
        session_id=session_id,
        agent_name="Hermes Agent (Orquestador)",
        task_id=task1,
        action="plan",
        summary=(
            f"Orquestacion modulo Noticias. EP-NEWS (id={epic_id}). "
            f"4 tareas: HU-NEWS-01(widget,id={task1}), HU-NEWS-02(endpoint,id={task2}), "
            f"HU-NEWS-03(crontab,id={task3}), HU-NEWS-04(dashboards,id={task4}). "
            f"4 specs creados. Experto definio: score, tendencia, keywords, volumén, alertas."
        ),
        tokens_used=0,
        status="completed"
    )
    for tid, name in [(task2, "HU-NEWS-02 endpoint"), (task3, "HU-NEWS-03 crontab"), (task4, "HU-NEWS-04 dashboards")]:
        db.log_activity(
            session_id=session_id,
            agent_name="Hermes Agent (Orquestador)",
            task_id=tid,
            action="plan",
            summary=f"Tarea {name}: specs definidos, pendiente implementación por Programador",
            tokens_used=0,
            status="completed"
        )
    print("  ✅ Actividad logueada")
except Exception as e:
    print(f"  ⚠️ Error al loguear: {e}")

db.close()

print("\n" + "="*60)
print("PLANIFICACION COMPLETA — Modulo de Noticias")
print("="*60)
print(f"""
EPIC: EP-NEWS (id={epic_id}) — Modulo de Noticias y Sentimiento de Mercado
├── HU-NEWS-01 (id={task1}) → Widget Sentimiento Noticias
├── HU-NEWS-02 (id={task2}) → Endpoint Extendido /api/v1/news-sentiment
├── HU-NEWS-03 (id={task3}) → Crontab ingesta 4h (0 LLM tokens)
└── HU-NEWS-04 (id={task4}) → Integracion en dashboards

PRÓXIMO PASO: Delegar tareas al Programador.
""")