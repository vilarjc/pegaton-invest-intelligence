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
import logging
import os, sys, json
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

import sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter

from backend.app.core.alerts.rule_engine import RuleEngine, Rule
from backend.app.core.alerts.dispatcher import AlertDispatcher, get_dispatcher
from backend.app.core.pegaton_config import get_db_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Dependencies ─────────────────────────────────────────────

def _get_dispatcher() -> AlertDispatcher:
    return get_dispatcher()


def _get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1, conditions_json TEXT NOT NULL DEFAULT '[]',
            actions_json TEXT NOT NULL DEFAULT '[]', cooldown_minutes INTEGER DEFAULT 60,
            last_triggered TEXT, created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rule_id TEXT NOT NULL,
            triggered_at TEXT NOT NULL, condition_met TEXT NOT NULL,
            actual_value REAL, message TEXT, channel TEXT, sent INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_hist_rule ON alert_history(rule_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_hist_time ON alert_history(triggered_at DESC)")
    conn.commit()
    conn.close()


def _row_to_rule(row) -> dict:
    return {
        "id": row["id"], "name": row["name"],
        "enabled": bool(row["enabled"]),
        "conditions": json.loads(row["conditions_json"] or "[]"),
        "actions": json.loads(row["actions_json"] or "[]"),
        "cooldown_minutes": row["cooldown_minutes"],
        "last_triggered": row["last_triggered"],
        "created_at": row["created_at"],
    }


# ── Engine singleton ──────────────────────────────────────────

_engine = None

def _get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        _engine = RuleEngine()
        conn = _get_db()
        for row in conn.execute("SELECT * FROM alert_rules").fetchall():
            _engine.add_rule(Rule(
                rule_id=row["id"], name=row["name"],
                enabled=bool(row["enabled"]),
                conditions=json.loads(row["conditions_json"] or "[]"),
                actions=json.loads(row["actions_json"] or "[]"),
                cooldown_minutes=row["cooldown_minutes"],
                last_triggered=row["last_triggered"],
            ))
        conn.close()
    return _engine


# ── Startup ──────────────────────────────────────────────────

@router.on_event("startup")
def startup():
    _ensure_tables()


# ── Endpoints ────────────────────────────────────────────────

@router.post("/alerts")
async def create_alert(
    name: str, conditions: str, actions: str,
    cooldown_minutes: int = 60, enabled: bool = True,
):
    rule_id = f"alert_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    try:
        conditions_json = json.loads(conditions)
        actions_json = json.loads(actions)
    except (json.JSONDecodeError, TypeError):
        return {"error": "conditions y actions deben ser JSON válido"}

    conn = _get_db()
    conn.execute(
        "INSERT INTO alert_rules (id, name, enabled, conditions_json, actions_json, cooldown_minutes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (rule_id, name, int(enabled), json.dumps(conditions_json), json.dumps(actions_json), cooldown_minutes, now, now),
    )
    conn.commit()
    conn.close()

    engine = _get_rule_engine()
    engine.add_rule(Rule(rule_id=rule_id, name=name, enabled=enabled,
        conditions=conditions_json, actions=actions_json, cooldown_minutes=cooldown_minutes))
    return {"status": "created", "id": rule_id}


@router.get("/alerts")
async def list_alerts(enabled: Optional[bool] = None):
    conn = _get_db()
    q = "SELECT * FROM alert_rules"
    p = []
    if enabled is not None:
        q += " WHERE enabled = ?"; p.append(int(enabled))
    rows = conn.execute(q, p).fetchall(); conn.close()
    rules = [_row_to_rule(r) for r in rows]
    engine = _get_rule_engine()
    for r in rules:
        er = engine.get_rule(r["id"])
        r["engine_enabled"] = er.enabled if er else False
    return {"count": len(rules), "rules": rules}


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    conn = _get_db()
    row = conn.execute("SELECT * FROM alert_rules WHERE id = ?", (alert_id,)).fetchone()
    conn.close()
    if not row:
        return {"error": f"Regla {alert_id} no encontrada"}
    d = _row_to_rule(row)
    hc = _get_db()
    for h in hc.execute("SELECT * FROM alert_history WHERE rule_id=? ORDER BY triggered_at DESC LIMIT 20", (alert_id,)).fetchall():
        d.setdefault("recent_triggers", []).append({
            "triggered_at": h["triggered_at"], "condition_met": h["condition_met"],
            "actual_value": h["actual_value"], "message": h["message"], "channel": h["channel"],
        })
    hc.close()
    return {"rule": d}


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, name: Optional[str] = None, enabled: Optional[bool] = None,
                       conditions: Optional[str] = None, actions: Optional[str] = None,
                       cooldown_minutes: Optional[int] = None):
    conn = _get_db()
    if not conn.execute("SELECT 1 FROM alert_rules WHERE id = ?", (alert_id,)).fetchone():
        conn.close()
        return {"error": f"Regla {alert_id} no encontrada"}
    u, v = {}, []
    if name is not None: u["name"] = name
    if enabled is not None: u["enabled"] = int(enabled)
    if conditions is not None: u["conditions_json"] = conditions
    if actions is not None: u["actions_json"] = actions
    if cooldown_minutes is not None: u["cooldown_minutes"] = cooldown_minutes
    if not u:
        conn.close()
        return {"error": "Sin campos para actualizar"}
    sc = ", ".join(f"{k}=?" for k in u)
    v = list(u.values()) + [datetime.now(timezone.utc).isoformat(), alert_id]
    conn.execute(f"UPDATE alert_rules SET {sc}, updated_at=? WHERE id=?", v)
    conn.commit(); conn.close()

    engine = _get_rule_engine()
    er = engine.get_rule(alert_id)
    if er:
        if name is not None: er.name = name
        if enabled is not None: (engine.enable_rule if enabled else engine.disable_rule)(alert_id)
        if conditions is not None: er.conditions = json.loads(conditions)
        if cooldown_minutes is not None: er.cooldown_minutes = cooldown_minutes
    return {"status": "updated", "id": alert_id}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    conn = _get_db()
    cur = conn.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
    conn.commit(); conn.close()
    if cur.rowcount == 0:
        return {"error": f"Regla {alert_id} no encontrada"}
    _get_rule_engine().remove_rule(alert_id)
    return {"status": "deleted", "id": alert_id}


@router.get("/alerts/{alert_id}/history")
async def get_alert_history(alert_id: str, limit: int = 50):
    conn = _get_db()
    rows = conn.execute("SELECT * FROM alert_history WHERE rule_id=? ORDER BY triggered_at DESC LIMIT ?", (alert_id, limit)).fetchall()
    conn.close()
    return {"rule_id": alert_id, "count": len(rows), "history": [
        {"id": r["id"], "triggered_at": r["triggered_at"], "condition_met": r["condition_met"],
         "actual_value": r["actual_value"], "message": r["message"], "channel": r["channel"], "sent": bool(r["sent"])}
        for r in rows
    ]}


@router.get("/alerts/history")
async def get_all_alert_history(rule_id: Optional[str] = None, limit: int = 100):
    conn = _get_db()
    q = "SELECT * FROM alert_history"
    p = []
    if rule_id: q += " WHERE rule_id=?"; p.append(rule_id)
    q += " ORDER BY triggered_at DESC LIMIT ?"; p.append(limit)
    rows = conn.execute(q, p).fetchall(); conn.close()
    return {"count": len(rows), "history": [
        {"id": r["id"], "rule_id": r["rule_id"], "triggered_at": r["triggered_at"],
         "condition_met": r["condition_met"], "actual_value": r["actual_value"],
         "message": r["message"], "channel": r["channel"], "sent": bool(r["sent"])}
        for r in rows
    ]}