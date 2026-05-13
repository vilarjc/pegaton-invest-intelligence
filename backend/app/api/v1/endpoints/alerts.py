"""
Alerts API — CRUD de reglas de alertas e historial.
P0-03: Alert System | EP-FR-001

Endpoints:
  POST   /api/v1/alerts              — crear regla
  GET    /api/v1/alerts              — listar reglas
  GET    /api/v1/alerts/{id}         — detalle
  PUT    /api/v1/alerts/{id}         — actualizar
  DELETE /api/v1/alerts/{id}         — eliminar
  GET    /api/v1/alerts/history      — historial de alertas disparadas
"""
import os, sys, json
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Query, HTTPException

import sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.core.alerts.rule_engine import RuleEngine, Rule
from backend.app.core.alerts.dispatcher import AlertDispatcher, get_dispatcher
from backend.app.core.pegaton_config import get_db_path

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _get_dispatcher() -> AlertDispatcher:
    """Obtiene el dispatcher singleton."""
    return get_dispatcher()


def _get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


# ── Migración automática ─────────────────────────────────────

def _ensure_tables():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            conditions_json TEXT NOT NULL DEFAULT '[]',
            actions_json TEXT NOT NULL DEFAULT '[]',
            cooldown_minutes INTEGER DEFAULT 60,
            last_triggered TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            condition_met TEXT NOT NULL,
            actual_value REAL,
            message TEXT,
            channel TEXT,
            sent INTEGER DEFAULT 0,
            FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_history_rule
        ON alert_history(rule_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_history_time
        ON alert_history(triggered_at DESC)
    """)
    conn.commit()
    conn.close()


@router.on_event("startup")
async def startup():
    _ensure_tables()


# ── Helpers ───────────────────────────────────────────────────

def _row_to_rule(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "enabled": bool(row["enabled"]),
        "conditions": json.loads(row["conditions_json"] or "[]"),
        "actions": json.loads(row["actions_json"] or "[]"),
        "cooldown_minutes": row["cooldown_minutes"],
        "last_triggered": row["last_triggered"],
        "created_at": row["created_at"],
    }


# ── Endpoints ────────────────────────────────────────────────

@router.post("/alerts")
async def create_alert(
    name: str = Query(..., description="Nombre de la regla"),
    conditions: str = Query(..., description="JSON array de condiciones"),
    actions: str = Query(..., description="JSON array de acciones"),
    cooldown_minutes: int = Query(default=60, description="Cooldown en minutos"),
    enabled: bool = Query(default=True, description="Habilitada al crear"),
):
    """Crea una nueva regla de alerta."""
    rule_id = f"alert_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    try:
        conditions_json = json.loads(conditions)
        actions_json = json.loads(actions)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="conditions y actions deben ser JSON válido")

    conn = _get_db()
    conn.execute("""
        INSERT INTO alert_rules (id, name, enabled, conditions_json, actions_json, cooldown_minutes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (rule_id, name, int(enabled), json.dumps(conditions_json), json.dumps(actions_json), cooldown_minutes, now, now))
    conn.commit()
    conn.close()

    # Registrar en el motor de reglas
    engine = _get_rule_engine()
    rule = Rule(
        rule_id=rule_id,
        name=name,
        enabled=enabled,
        conditions=conditions_json,
        actions=actions_json,
        cooldown_minutes=cooldown_minutes,
    )
    engine.add_rule(rule)

    return {"status": "created", "id": rule_id}


@router.get("/alerts")
async def list_alerts(
    enabled: Optional[bool] = Query(None, description="Filtrar por habilitada"),
):
    """Lista todas las reglas de alerta."""
    conn = _get_db()
    query = "SELECT * FROM alert_rules"
    params = []
    if enabled is not None:
        query += " WHERE enabled = ?"
        params.append(int(enabled))
    rows = conn.execute(query, params).fetchall()
    conn.close()

    rules = [_row_to_rule(row) for row in rows]

    # Enriquecer con estado del motor
    engine = _get_rule_engine()
    for rule in rules:
        engine_rule = engine.get_rule(rule["id"])
        rule["engine_enabled"] = engine_rule.enabled if engine_rule else False

    return {"count": len(rules), "rules": rules}


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Detalle de una regla de alerta."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM alert_rules WHERE id = ?", (alert_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Regla {alert_id} no encontrada")

    rule_dict = _row_to_rule(row)

    # Agregar historial reciente
    hist_conn = _get_db()
    hist_rows = hist_conn.execute(
        "SELECT * FROM alert_history WHERE rule_id = ? ORDER BY triggered_at DESC LIMIT 20",
        (alert_id,),
    ).fetchall()
    hist_conn.close()

    rule_dict["recent_triggers"] = [
        {
            "triggered_at": r["triggered_at"],
            "condition_met": r["condition_met"],
            "actual_value": r["actual_value"],
            "message": r["message"],
            "channel": r["channel"],
        }
        for r in hist_rows
    ]

    return {"rule": rule_dict}


@router.put("/alerts/{alert_id}")
async def update_alert(
    alert_id: str,
    name: Optional[str] = Query(None, description="Nombre nuevo"),
    enabled: Optional[bool] = Query(None, description="Habilitar/deshabilitar"),
    conditions: Optional[str] = Query(None, description="Nuevas condiciones JSON"),
    actions: Optional[str] = Query(None, description="Nuevas acciones JSON"),
    cooldown_minutes: Optional[int] = Query(None, description="Nuevo cooldown"),
):
    """Actualiza una regla de alerta."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM alert_rules WHERE id = ?", (alert_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Regla {alert_id} no encontrada")

    updates = {}
    params = []

    if name is not None:
        updates["name"] = name
    if enabled is not None:
        updates["enabled"] = int(enabled)
    if conditions is not None:
        updates["conditions_json"] = conditions
    if actions is not None:
        updates["actions_json"] = actions
    if cooldown_minutes is not None:
        updates["cooldown_minutes"] = cooldown_minutes

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [datetime.now(timezone.utc).isoformat()] + [alert_id]
    query = f"UPDATE alert_rules SET {set_clause}, updated_at = ? WHERE id = ?"
    conn.execute(query, values)
    conn.commit()
    conn.close()

    # Actualizar en el motor de reglas
    engine = _get_rule_engine()
    if name is not None:
        engine_rule = engine.get_rule(alert_id)
        if engine_rule:
            engine_rule.name = name
    if enabled is not None:
        if enabled:
            engine.enable_rule(alert_id)
        else:
            engine.disable_rule(alert_id)
    if conditions is not None:
        engine_rule = engine.get_rule(alert_id)
        if engine_rule:
            engine_rule.conditions = json.loads(conditions)
    if cooldown_minutes is not None:
        engine_rule = engine.get_rule(alert_id)
        if engine_rule:
            engine_rule.cooldown_minutes = cooldown_minutes

    return {"status": "updated", "id": alert_id}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Elimina una regla de alerta."""
    conn = _get_db()
    cursor = conn.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Regla {alert_id} no encontrada")

    # Eliminar del motor
    engine = _get_rule_engine()
    engine.remove_rule(alert_id)

    return {"status": "deleted", "id": alert_id}


@router.get("/alerts/{alert_id}/history")
async def get_alert_history(
    alert_id: str,
    limit: int = Query(default=50, le=500, description="Máximo de registros"),
):
    """Historial de disparos de una regla."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM alert_history WHERE rule_id = ? ORDER BY triggered_at DESC LIMIT ?",
        (alert_id, limit),
    ).fetchall()
    conn.close()

    history = [
        {
            "id": r["id"],
            "triggered_at": r["triggered_at"],
            "condition_met": r["condition_met"],
            "actual_value": r["actual_value"],
            "message": r["message"],
            "channel": r["channel"],
            "sent": bool(r["sent"]),
        }
        for r in rows
    ]
    return {"rule_id": alert_id, "count": len(history), "history": history}


@router.get("/alerts/history")
async def get_all_alert_history(
    rule_id: Optional[str] = Query(None, description="Filtrar por regla"),
    limit: int = Query(default=100, le=1000, description="Máximo de registros"),
):
    """Historial de todas las alertas disparadas."""
    conn = _get_db()
    query = "SELECT * FROM alert_history"
    params = []
    if rule_id:
        query += " WHERE rule_id = ?"
        params.append(rule_id)
    query += " ORDER BY triggered_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    history = [
        {
            "id": r["id"],
            "rule_id": r["rule_id"],
            "triggered_at": r["triggered_at"],
            "condition_met": r["condition_met"],
            "actual_value": r["actual_value"],
            "message": r["message"],
            "channel": r["channel"],
            "sent": bool(r["sent"]),
        }
        for r in rows
    ]
    return {"count": len(history), "history": history}


# ── Rule Engine singleton ──────────────────────────────────────

_engine: Optional[RuleEngine] = None


def _get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        _engine = RuleEngine()
        # Cargar reglas desde DB
        conn = _get_db()
        rows = conn.execute("SELECT * FROM alert_rules").fetchall()
        for row in rows:
            rule = Rule(
                rule_id=row["id"],
                name=row["name"],
                enabled=bool(row["enabled"]),
                conditions=json.loads(row["conditions_json"] or "[]"),
                actions=json.loads(row["actions_json"] or "[]"),
                cooldown_minutes=row["cooldown_minutes"],
                last_triggered=row["last_triggered"],
            )
            _engine.add_rule(rule)
        conn.close()
        if rows:
            _logger.info(f"RuleEngine cargó {len(rows)} reglas desde DB")
    return _engine


_logger = logging.getLogger(__name__)