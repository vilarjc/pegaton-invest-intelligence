#!/usr/bin/env python3
"""
============================================================================
HARNESS MIGRATION — Import existing PEGATON state into harness.db
============================================================================
Takes the backlog from Obsidian vault and current project state,
and populates the harness database with epics, tasks, specs, artifacts.
============================================================================
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.harness_db import HarnessDB

db = HarnessDB()

SESSION = "migration-01-05-2026"
AGENT = "Hermes Agent (PM Orquestador)"

def create_epic(code, title, desc, priority):
    existing = db.get_epics()
    for e in existing:
        if e['code'] == code:
            print(f"  Epic {code} already exists (id={e['id']})")
            return e['id']
    eid = db.create_epic(code, title, desc, priority)
    print(f"  Created epic {code}: {title} (id={eid})")
    return eid

def create_task(code, title, epic_id, desc, criteria, priority, status, tags=None):
    existing = db.get_task_by_code(code)
    if existing:
        print(f"  Task {code} already exists (id={existing['id']}, status={existing['status']})")
        return existing['id']
    tid = db.create_task(code, title, epic_id, desc, criteria, priority, tags or [])
    if status != 'pending':
        db.update_task_status(tid, status)
    print(f"  Created task {code}: {title} (id={tid}, status={status})")
    return tid

def register_file_artifact(task_id, file_path, desc, is_generated=False):
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_path)
    if os.path.exists(full_path):
        db.register_artifact(task_id, full_path, desc, is_generated)
        print(f"    → Artifact: {file_path}")

print("=" * 60)
print("  HARNESS MIGRATION — PEGATON State Import")
print("=" * 60)

# Open migration session
db.open_session(SESSION, AGENT, context_usage_start=5)

# ============================================================================
# EPICS
# ============================================================================
print("\n📦 Importing Epics...")

ep1 = create_epic("EP-01", "Motor de Señales Pegaton (Core)",
    "Score engine que combina análisis macro (40%) + técnico (60%) para generar "
    "Pegaton Score 0-100 con desglose de factores.", priority=1)

ep2 = create_epic("EP-02", "Análisis Macro-Técnico",
    "Indicadores macro clave actualizados + análisis técnico estándar (RSI, MACD, SMA) "
    "para contextualizar las señales.", priority=2)

ep3 = create_epic("EP-03", "Interfaz y Experiencia de Usuario",
    "Webapp HTML/JS con watchlist editable, matriz de acción, y visualización de scores.", priority=3)

ep4 = create_epic("EP-04", "Gestión de Portfolio",
    "Tracking básico de portfolio con P&L en relación a las señales.", priority=4)

ep5 = create_epic("EP-05", "Infraestructura y Automatización",
    "Cron jobs, deploy, monitorización, y mantenimiento del sistema.", priority=5)

ep6 = create_epic("EP-06", "Harness Engineering & SDD",
    "El arnés mismo: base de datos compartida, especificaciones, protocolo multi-agente, "
    "y gestión de contexto.", priority=0)

# ============================================================================
# TASKS
# ============================================================================
print("\n📋 Importing Tasks...")

# --- EP-01: Motor de Señales ---
t_1_1_scores = create_task(
    "HU-1.1", "Endpoint Score + Pegaton Score Engine",
    ep1,
    "Endpoint /score/{symbol} que devuelve score 0-100 + timestamp. "
    "Implementar ingesta macro diaria (FRED) y de precios (Twelve Data). "
    "Algoritmo de normalización z-score + combinación macro/técnico.",
    [
        "Endpoint /api/v1/score/{symbol} devuelve score y timestamp",
        "Ingesta macro diaria desde FRED (Fed Funds, CPI, PMI, etc.)",
        "Ingesta precios en tiempo real desde Twelve Data (SPY, EUR/USD, BTC/USD)",
        "Algoritmo de normalización z-score sobre ventana 60d",
        "Combinación macro (40%) + técnico (60%) en score 0-100",
        "Almacenar en SQLite para consistencia histórica"
    ],
    priority=1,
    status="done",
    tags=["backend", "core", "api"]
)

t_1_2_factores = create_task(
    "HU-1.2", "Desglose de Factores del Score",
    ep1,
    "Extender endpoint /score/{symbol} para incluir desglose de factores "
    "alcistas/bajistas con peso %. Ej: '+25% por caída en rendimiento 10Y'.",
    [
        "Endpoint devuelve desglose de factores con nombre, peso %, dirección",
        "Factores dinámicos según datos disponibles",
        "Historial de factores para análisis de drift"
    ],
    priority=2,
    status="pending",
    tags=["backend", "core", "api"]
)

t_1_3_specs = create_task(
    "HU-1.3", "Refinar Algoritmo de Score con Especificaciones SDD",
    ep1,
    "Reescribir el motor de score siguiendo SDD Nivel 2: "
    "especificar la lógica de puntuación macro y técnica como specs, "
    "luego implementar contra esas specs.",
    [
        "Cada sub-algoritmo (macro, técnico, combinación) tiene su spec",
        "Los parámetros (pesos, umbrales) están documentados en la spec",
        "El código implementa exactamente lo que la spec dice"
    ],
    priority=3,
    status="pending",
    tags=["backend", "core", "sdd"]
)

# --- EP-02: Análisis Macro-Técnico ---
t_2_1 = create_task(
    "HU-2.1", "Indicadores Macro Clave",
    ep2,
    "Endpoint /macro con últimos valores de indicadores macro: "
    "Fed Funds rate, CPI YoY, ISM Manufacturing PMI, etc.",
    [
        "Endpoint /macro devuelve 3-5 indicadores con valor actual",
        "Mostrar cambio diario y tendencia",
        "Actualización automática cada 24h"
    ],
    priority=2,
    status="done",
    tags=["backend", "macro", "api"]
)

t_2_2 = create_task(
    "HU-2.2", "Análisis Técnico Estándar",
    ep2,
    "Endpoint /technical/{symbol} con RSI(14), MACD, señal, histograma, "
    "precio vs SMA50/SMA200.",
    [
        "Endpoint /technical/{symbol} funcional",
        "Usar librería ta o pandas-ta",
        "Actualización con nuevos datos de precio"
    ],
    priority=2,
    status="done",
    tags=["backend", "technical", "api"]
)

# --- EP-03: Interfaz ---
t_3_1 = create_task(
    "HU-3.1", "Watchlist Editable",
    ep3,
    "Frontend HTML/JS con input para añadir/quitar ticker, "
    "mostrar scores actualizados cada 60s, persistir watchlist.",
    [
        "Input para añadir/quitar ticker",
        "Lista de activos con score actual",
        "Auto-refresh cada 60s",
        "Persistir en localStorage"
    ],
    priority=3,
    status="pending",
    tags=["frontend", "ux"]
)

t_3_2 = create_task(
    "HU-3.2", "Matriz de Acción Clara",
    ep3,
    "Definir umbrales de score para acciones: COMPRAR, ACUMULAR, "
    "MANTENER, REDUCIR, EVITAR. Mostrar botón grande con color y acción.",
    [
        "Umbrales definidos: 80-100 COMPRAR, 60-79 ACUMULAR, etc.",
        "Botón grande con color y texto por activo",
        "Tooltip con razón principal"
    ],
    priority=3,
    status="pending",
    tags=["frontend", "ux"]
)

t_3_3 = create_task(
    "HU-3.3", "Dashboard Mesa Redonda (Multi-Modelo)",
    ep3,
    "Frontend que consume el endpoint de Mesa Redonda para mostrar "
    "análisis multi-modelo con scores de consenso, discrepancias y acciones.",
    [
        "Dashboard con resultados de modelos múltiples",
        "Gráfico de consenso y discrepancias",
        "Selección de activo a analizar"
    ],
    priority=4,
    status="done",
    tags=["frontend", "roundtable", "eval"]
)

t_3_4 = create_task(
    "HU-3.4", "Dashboard de Evaluación de Agentes (RISE)",
    ep3,
    "Frontend con 4 tabs: Rankings, OKRs, Auto-Assignment, Events. "
    "Muestra métricas de rendimiento de modelos.",
    [
        "Tabla de rankings con 3 modelos",
        "OKRs con targets y gaps",
        "Auto-asignación de tareas",
        "Eventos de promoción/degradación"
    ],
    priority=4,
    status="done",
    tags=["frontend", "eval"]
)

# --- EP-04: Portfolio ---
t_4_1 = create_task(
    "HU-4.1", "Portfolio Tracker Manual",
    ep4,
    "Formulario para ingresar posición (activo, cantidad, precio de entrada, fecha). "
    "Cálculo automático de valor actual, P&L, % cambio.",
    [
        "Formulario para ingresar posición",
        "Cálculo automático P&L y % cambio",
        "Distribución por activo (valor y %)",
        "Persistir en SQLite"
    ],
    priority=5,
    status="pending",
    tags=["frontend", "portfolio"]
)

# --- EP-05: Infraestructura ---
t_5_1 = create_task(
    "HU-5.1", "Server FastAPI + Deploy",
    ep5,
    "Servidor FastAPI corriendo en puerto 8000 con systemd. "
    "Scripts start/stop, health check endpoint.",
    [
        "Servidor corriendo como servicio",
        "start.sh y stop.sh funcionales",
        "Health endpoint responde 200",
        "Accesible vía Tailscale (100.64.64.58:8000)"
    ],
    priority=3,
    status="done",
    tags=["infra", "devops"]
)

t_5_2 = create_task(
    "HU-5.2", "Cron Jobs Automatizados",
    ep5,
    "Cron job diario para ingesta macro. "
    "Cron jobs periódicos para evaluaciones RISE.",
    [
        "Ingesta macro diaria a las 05:00 UTC",
        "Evaluaciones periódicas de modelos",
        "Logging de ejecución en DB"
    ],
    priority=4,
    status="in_progress",
    tags=["infra", "automation"]
)

t_5_3 = create_task(
    "HU-5.3", "Budget Tracker DeepSeek",
    ep5,
    "Seguimiento de costos de API DeepSeek en tiempo real. "
    "Alertas cuando el balance está bajo.",
    [
        "Tracking de tokens y costo por llamada",
        "Dashboard de presupuesto",
        "Alertas de balance bajo"
    ],
    priority=3,
    status="done",
    tags=["infra", "cost"]
)

# --- EP-06: Harness Engineering ---
t_6_1 = create_task(
    "HU-6.1", "Base de Datos Compartida (Harness DB)",
    ep6,
    "Crear la base de datos SQLite como memoria compartida para todos los agentes. "
    "Tablas: tasks, specs, agent_logs, artifacts, sessions, decisions, epics.",
    [
        "Schema SQL con todas las tablas e índices",
        "harness_db.py con interfaz completa",
        "db_verify.py para validación de entorno",
        "init.sh como entry point de verificación",
        "AGENTS.md con el protocolo completo"
    ],
    priority=0,
    status="done",
    tags=["harness", "core", "sdd"]
)

t_6_2 = create_task(
    "HU-6.2", "Migrar Backlog a la DB (SDD Nivel 2)",
    ep6,
    "Migrar todas las historias de usuario, epics y estado actual "
    "desde Obsidian vault a la base de datos.",
    [
        "Todas las epics están en la tabla epics",
        "Todas las HU están en la tabla tasks",
        "El estado refleja el progreso real",
        "Logs de migración registrados"
    ],
    priority=0,
    status="in_progress",
    tags=["harness", "migration"]
)

t_6_3 = create_task(
    "HU-6.3", "Crear Spec para el Vivero (Seedling System)",
    ep6,
    "Basado en los 2 videos de BettaTech, crear la spec completa del "
    "'vivero de agentes' — el sistema que permite spawnear agentes bebés, "
    "entrenarlos, evaluarlos y cuando superan el umbral, integrarlos al sistema principal. "
    "Primera feature real sobre el arnés SDD.",
    [
        "Spec completa del sistema de vivero (seedling -> adulto -> integración)",
        "Ciclo de vida del agente: semilla, plántula, crecimiento, madurez",
        "Evaluación progresiva con umbrales de promoción",
        "Integración automática al alcanzar madurez",
        "Log de todo el ciclo en harness.db"
    ],
    priority=0,
    status="pending",
    tags=["harness", "sdd", "vivero"]
)

# ============================================================================
# REGISTER ARTIFACTS (existing files)
# ============================================================================
print("\n📦 Registering existing artifacts...")

artifacts_map = {
    "HU-1.1": [
        ("backend/app/main.py", "FastAPI app principal con endpoints"),
        ("backend/static.py", "Archivos estáticos del frontend"),
        ("backend/scripts/ingest_macro.py", "Script de ingesta macro FRED"),
        ("backend/scripts/ingest_precios.py", "Script de ingesta de precios"),
    ],
    "HU-2.1": [
        ("backend/scripts/ingest_macro.py", "Ingesta macro"),
    ],
    "HU-2.2": [
        ("backend/scripts/ingest_precios_historico.py", "Ingesta precios histórica"),
        ("backend/scripts/ingest_precios_incremental.py", "Ingesta precios incremental"),
    ],
    "HU-3.3": [
        ("frontend/roundtable.html", "Dashboard Mesa Redonda"),
        ("backend/roundtable/engine.py", "Motor de consenso multi-modelo"),
        ("backend/roundtable/models.py", "Modelos de datos Roundtable"),
        ("backend/providers/__init__.py", "Providers de modelos"),
    ],
    "HU-3.4": [
        ("frontend/eval.html", "Dashboard de evaluación RISE"),
        ("backend/evaluation/evaluator.py", "Evaluador de modelos"),
        ("backend/evaluation/models.py", "Modelos de datos evaluación"),
    ],
    "HU-5.1": [
        ("start.sh", "Script de inicio del servidor"),
        ("stop.sh", "Script de parada"),
        ("deploy/pegaton.service", "Servicio systemd"),
    ],
    "HU-5.3": [
        ("backend/scripts/budget_tracker.py", "Tracker de presupuesto DeepSeek"),
        ("backend/scripts/check_deepseek_balance.py", "Verificador de balance"),
        ("frontend/budget.html", "Dashboard de presupuesto"),
    ],
    "HU-6.1": [
        ("harness/harness_db.py", "Interfaz DB para agentes"),
        ("harness/db_verify.py", "Script de validación de entorno"),
        ("harness/schema.sql", "Esquema SQL de la DB"),
        ("harness/init.sh", "Entry point de verificación"),
        ("AGENTS.md", "Protocolo maestro del arnés"),
    ],
}

for task_code, files in artifacts_map.items():
    task = db.get_task_by_code(task_code)
    if task:
        for file_path, desc in files:
            register_file_artifact(task['id'], file_path, desc)

# ============================================================================
# LOG THE MIGRATION
# ============================================================================
print("\n📝 Logging migration activity...")

summary_lines = []
for epic in db.get_epics():
    tasks_in_epic = db.get_all_tasks(epic_id=epic['id'])
    done = sum(1 for t in tasks_in_epic if t['status'] == 'done')
    total = len(tasks_in_epic)
    summary_lines.append(f"  {epic['code']}: {done}/{total} done")
    for t in tasks_in_epic:
        db.log_activity(
            session_id=SESSION,
            agent_name=AGENT,
            task_id=t['id'],
            action="migrate",
            summary=f"Importada desde backlog Obsidian. Estado: {t['status']}",
            files_changed=None,
            context_usage_pct=10,
            status="completed"
        )

db.log_activity(
    session_id=SESSION,
    agent_name=AGENT,
    task_id=t_6_2,
    action="migrate",
    summary="Migración completa del backlog PEGATON a harness.db. "
            f"Epics: {len(db.get_epics())}, Tasks: {len(db.get_all_tasks())}",
    files_changed=["harness.db"],
    context_usage_pct=15,
    status="completed"
)

# Close session
db.close_session(SESSION, summary=f"Migración inicial completada.\n" + "\n".join(summary_lines))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print(f"\n{'='*60}")
summary = db.get_project_summary()
print(f"  ✅ MIGRATION COMPLETE")
print(f"  Epics: {summary['epics']}")
print(f"  Tasks: {summary['tasks']['total']} total")
print(f"    - Pending: {summary['tasks']['pending']}")
print(f"    - In Progress: {summary['tasks']['in_progress']}")
print(f"    - Done: {summary['tasks']['done']}")
print(f"    - Blocked: {summary['tasks']['blocked']}")
print(f"{'='*60}")

# Mark HU-6.2 as done since migration is complete
db.update_task_status(t_6_2, 'done')
print(f"\n  ✓ HU-6.2 marcada como 'done'")
print(f"  → Siguiente: HU-6.3 — Crear Spec del Vivero")
