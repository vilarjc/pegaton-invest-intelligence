"""Model Objectives (OKRs) System.
Allows configuring targets per model and auto-assigning responsibility based on performance."""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pegaton.db')
OBJECTIVES_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'model_objectives.json')
ASSIGNMENT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'model_assignments.json')


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS model_objectives (
            model_id TEXT PRIMARY KEY,
            period TEXT DEFAULT 'weekly',
            target_cost_per_task REAL DEFAULT 0.001,
            target_response_time REAL DEFAULT 10.0,
            target_json_compliance REAL DEFAULT 90.0,
            target_reliability REAL DEFAULT 95.0,
            target_consensus_alignment REAL DEFAULT 70.0,
            target_task_count INTEGER DEFAULT 10,
            is_active INTEGER DEFAULT 1,
            auto_promote_threshold REAL DEFAULT 0.8,
            auto_demote_threshold REAL DEFAULT -0.8,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS model_auto_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            event TEXT NOT NULL,
            reason TEXT,
            old_level TEXT,
            new_level TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def get_default_objectives() -> dict:
    return {
        "period": "weekly",
        "target_cost_per_task": 0.001,
        "target_response_time": 10.0,
        "target_json_compliance": 90.0,
        "target_reliability": 95.0,
        "target_consensus_alignment": 70.0,
        "target_task_count": 10,
        "auto_promote_threshold": 0.8,   # z-score above this → promote
        "auto_demote_threshold": -0.8,    # z-score below this → demote
        "is_active": True,
    }


def get_objectives(model_id: Optional[str] = None) -> dict:
    """Get OKRs for a model, or all models if model_id is None."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if model_id:
        rows = c.execute("SELECT * FROM model_objectives WHERE model_id = ?", (model_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM model_objectives").fetchall()
    
    conn.close()
    
    if not rows:
        return {}
    
    result = {}
    for row in rows:
        d = dict(row)
        result[d["model_id"]] = {
            "period": d["period"],
            "target_cost_per_task": d["target_cost_per_task"],
            "target_response_time": d["target_response_time"],
            "target_json_compliance": d["target_json_compliance"],
            "target_reliability": d["target_reliability"],
            "target_consensus_alignment": d["target_consensus_alignment"],
            "target_task_count": d["target_task_count"],
            "auto_promote_threshold": d["auto_promote_threshold"],
            "auto_demote_threshold": d["auto_demote_threshold"],
            "is_active": bool(d["is_active"]),
            "created_at": d["created_at"],
            "updated_at": d["updated_at"],
        }
    
    return result if not model_id else result.get(model_id, {})


def set_objectives(model_id: str, objectives: dict) -> dict:
    """Set or update OKRs for a model."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    defaults = get_default_objectives()
    data = {**defaults, **objectives}
    
    c.execute("""
        INSERT INTO model_objectives (
            model_id, period,
            target_cost_per_task, target_response_time,
            target_json_compliance, target_reliability,
            target_consensus_alignment, target_task_count,
            auto_promote_threshold, auto_demote_threshold,
            is_active, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(model_id) DO UPDATE SET
            period = excluded.period,
            target_cost_per_task = excluded.target_cost_per_task,
            target_response_time = excluded.target_response_time,
            target_json_compliance = excluded.target_json_compliance,
            target_reliability = excluded.target_reliability,
            target_consensus_alignment = excluded.target_consensus_alignment,
            target_task_count = excluded.target_task_count,
            auto_promote_threshold = excluded.auto_promote_threshold,
            auto_demote_threshold = excluded.auto_demote_threshold,
            is_active = excluded.is_active,
            updated_at = datetime('now')
    """, (
        model_id, data["period"],
        data["target_cost_per_task"], data["target_response_time"],
        data["target_json_compliance"], data["target_reliability"],
        data["target_consensus_alignment"], data["target_task_count"],
        data["auto_promote_threshold"], data["auto_demote_threshold"],
        1 if data["is_active"] else 0,
    ))
    conn.commit()
    conn.close()
    return get_objectives(model_id)


def get_default_targets_for_all(force: bool = False) -> dict:
    """Initialize default OKRs for all active models from providers."""
    from .providers import get_active_models
    
    existing = get_objectives()
    models = get_active_models()
    created = []
    
    for m in models:
        mid = m["id"]
        if mid not in existing or force:
            is_free = m["input_price"] == 0
            set_objectives(mid, {
                "target_cost_per_task": 0.0005 if is_free else 0.001,
                "target_response_time": 15.0 if mid == "deepseek-reasoner" else 8.0,
                "target_json_compliance": 85.0,
                "target_reliability": 90.0,
                "target_consensus_alignment": 65.0,
                "target_task_count": 5,
                "auto_promote_threshold": 1.0,
                "auto_demote_threshold": -0.5,
            })
            created.append(mid)
    
    return {"created": created, "total": len(models)}


# === GAP ANALYSIS ===

def compute_objective_gaps(days: int = 7, eval_data: Optional[dict] = None) -> list:
    """For each model with OKRs, compute gap between target and actual performance."""
    from .model_eval import compute_model_metrics, compute_performance_scores

    objectives = get_objectives()
    if not objectives:
        return []

    metrics = compute_model_metrics(days)

    # Get z-scores from eval data if not provided
    if eval_data is None:
        eval_data = compute_performance_scores(days=days)

    # Build lookup: model_id -> z-score
    zscore_lookup = {}
    for m in eval_data.get("models", []):
        zscore_lookup[m["model_id"]] = m.get("composite_zscore", 0)

    objectives = get_objectives()
    if not objectives:
        return []

    gaps = []
    for model_id, obj in objectives.items():
        if not obj.get("is_active"):
            continue
        
        actual = metrics.get(model_id, {})
        if not actual:
            continue
        
        # Compute gap (%) for each KPI
        gap_cost = _pct_gap(actual.get("avg_cost_per_task", 0), obj["target_cost_per_task"], lower_is_better=True)
        gap_speed = _pct_gap(actual.get("avg_response_time", 0), obj["target_response_time"], lower_is_better=True)
        gap_quality = _pct_gap(actual.get("json_compliance_rate", 0), obj["target_json_compliance"])
        gap_reliability = _pct_gap(100 - actual.get("error_rate", 0), obj["target_reliability"])
        gap_consensus = _pct_gap(actual.get("consensus_alignment", 0), obj["target_consensus_alignment"])
        
        # Overall OKR score (average of gap %)
        scores = [gap_cost, gap_speed, gap_quality, gap_reliability, gap_consensus]
        overall = sum(scores) / len(scores)
        
        # Status
        if overall >= 90:
            status = "🏆 Superando"
        elif overall >= 75:
            status = "✅ Cumpliendo"
        elif overall >= 50:
            status = "⚠️ En riesgo"
        else:
            status = "❌ Incumpliendo"
        
        # Auto-assignment check using z-scores from eval data
        z = zscore_lookup.get(model_id, 0)
        auto_action = None
        if z >= obj.get("auto_promote_threshold", 0.8):
            auto_action = "ASCENDER"
        elif z <= obj.get("auto_demote_threshold", -0.8):
            auto_action = "DEGRADAR"
        
        gaps.append({
            "model_id": model_id,
            "model_name": actual.get("model_name", model_id),
            "targets": obj,
            "actual": {
                "avg_cost_per_task": actual.get("avg_cost_per_task", 0),
                "avg_response_time": actual.get("avg_response_time", 0),
                "json_compliance_rate": actual.get("json_compliance_rate", 0),
                "error_rate": actual.get("error_rate", 0),
                "consensus_alignment": actual.get("consensus_alignment", 0),
                "task_count": actual.get("task_count", 0),
            },
            "gaps": {
                "cost": round(gap_cost, 1),
                "speed": round(gap_speed, 1),
                "quality": round(gap_quality, 1),
                "reliability": round(gap_reliability, 1),
                "consensus": round(gap_consensus, 1),
            },
            "overall_score": round(overall, 1),
            "status": status,
            "auto_action": auto_action,
            "task_count": actual.get("task_count", 0),
        })
    
    return sorted(gaps, key=lambda x: x["overall_score"], reverse=True)


def _pct_gap(actual: float, target: float, lower_is_better: bool = False) -> float:
    """Compute % of target achieved (0-100+)."""
    if target == 0:
        return 100.0 if actual == 0 else 0.0
    
    if lower_is_better:
        # Lower is better: e.g. cost — $0.0005 actual vs $0.001 target
        if actual <= target:
            return 100.0  # Exceeding
        ratio = target / actual if actual > 0 else 0
        return min(100, ratio * 100)
    else:
        # Higher is better: e.g. reliability 95% actual vs 90% target
        if actual >= target:
            return 100.0  # Exceeding
        ratio = actual / target if target > 0 else 0
        return min(100, ratio * 100)


# === AUTO-ASSIGNMENT ENGINE ===

def auto_assign_tasks(eval_data: dict) -> dict:
    """
    Given evaluation results, assign optimal models to task types.
    Returns a dict mapping task type -> recommended model.
    """
    from .providers import get_active_models
    
    models = eval_data.get("models", [])
    if not models:
        return {"error": "No evaluation data available"}
    
    objectives = get_objectives()
    gaps = compute_objective_gaps(eval_data=eval_data)
    
    # Task tiers and their requirements
    task_tiers = {
        "critico": {
            "label": "🔴 Tareas Críticas",
            "description": "Orquestación, trading, decisiones de inversión, programación compleja",
            "requirements": {"min_percentile": 70, "max_cost": 0.01},
        },
        "alto": {
            "label": "🟠 Tareas de Alta Responsabilidad",
            "description": "Análisis profundos, informes, backtesting, planificación",
            "requirements": {"min_percentile": 50, "max_cost": 0.005},
        },
        "medio": {
            "label": "🟡 Tareas Estándar",
            "description": "Análisis rutinarios, monitoreo, watchlist",
            "requirements": {"min_percentile": 30, "max_cost": 0.002},
        },
        "basico": {
            "label": "🟢 Tareas Básicas",
            "description": "Data fetching, formateo, logs, tareas repetitivas",
            "requirements": {},  # Any model can do these
        },
    }
    
    # Assign models to tiers
    tier_assignments = {}
    for tier_id, tier_info in task_tiers.items():
        reqs = tier_info["requirements"]
        candidates = []
        
        for m in models:
            if m.get("task_count", 0) == 0:
                continue  # No data yet
            
            # Check requirements
            meets = True
            if "min_percentile" in reqs and m.get("percentile_score", 0) < reqs["min_percentile"]:
                meets = False
            cost = m.get("metrics", {}).get("avg_cost_per_task", 999)
            if "max_cost" in reqs and cost > reqs["max_cost"]:
                meets = False
            
            if meets:
                candidates.append(m)
        
        # Sort by percentile
        candidates.sort(key=lambda x: x.get("percentile_score", 0), reverse=True)
        
        if candidates:
            tier_assignments[tier_id] = {
                "models": [c["model_name"] + f" ({c['percentile_score']}pts)" for c in candidates[:3]],
                "best": candidates[0]["model_name"],
                "best_score": candidates[0]["percentile_score"],
            }
        else:
            # Fallback: assign the best available
            if models:
                best = models[0]
                tier_assignments[tier_id] = {
                    "models": [best["model_name"] + f" ({best['percentile_score']}pts)"],
                    "best": best["model_name"],
                    "best_score": best["percentile_score"],
                    "note": "Ningún modelo cumple requisitos mínimos — usando el mejor disponible",
                }
            else:
                tier_assignments[tier_id] = {"models": [], "best": None, "note": "Sin modelos disponibles"}
    
    return {
        "tiers": task_tiers,
        "assignments": tier_assignments,
        "evaluated_models": len(models),
        "total_models_with_data": sum(1 for m in models if m.get("task_count", 0) > 0),
    }


def log_auto_event(model_id: str, event: str, reason: str, old_level: str = "", new_level: str = ""):
    """Log an auto-assignment event (promotion, demotion, exclusion)."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO model_auto_log (model_id, event, reason, old_level, new_level) VALUES (?, ?, ?, ?, ?)",
        (model_id, event, reason, old_level, new_level)
    )
    conn.commit()
    conn.close()


def get_auto_log(limit: int = 20) -> list:
    """Get recent auto-assignment events."""
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM model_auto_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
