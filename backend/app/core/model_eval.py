"""Model Evaluation System — RISE-style performance tracking for AI models.
Evaluates models on: cost, speed, quality, reliability, consensus alignment.
Produces bell curve ranking with task allocation recommendations."""

import os
import json
import math
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from .providers import get_active_models


# === DATA STORAGE ===
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pegaton.db')
TRACKER_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'budget_tracker.json')


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Create eval tables if not exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS model_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            task_count INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            avg_cost_per_task REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            total_tokens_in INTEGER DEFAULT 0,
            total_tokens_out INTEGER DEFAULT 0,
            json_compliance_rate REAL DEFAULT 0,
            task_completion_rate REAL DEFAULT 100,
            error_count INTEGER DEFAULT 0,
            consensus_alignment REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS model_task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            task_type TEXT DEFAULT 'analysis',
            response_time REAL DEFAULT 0,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            cost REAL DEFAULT 0,
            json_valid INTEGER DEFAULT 1,
            completed INTEGER DEFAULT 1,
            had_error INTEGER DEFAULT 0,
            consensus_match INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


# === METRICS AGGREGATION ===

def get_model_task_logs(days: int = 30) -> list:
    """Get task logs from the last N days."""
    conn = _get_db()
    c = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = c.execute(
        "SELECT * FROM model_task_logs WHERE created_at >= ? ORDER BY created_at",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tracker_tasks() -> list:
    """Get tasks from the budget tracker JSON."""
    if not os.path.exists(TRACKER_PATH):
        return []
    try:
        with open(TRACKER_PATH) as f:
            data = json.load(f)
        # Try both paths: flat (d.tracker.tasks) and nested (projects.pegaton.tasks)
        tasks = data.get("tasks", [])
        if not tasks:
            for proj in data.get("projects", {}).values():
                tasks.extend(proj.get("tasks", []))
        return tasks
    except:
        return []


# === EVALUATION ENGINE ===

METRIC_WEIGHTS = {
    "cost_efficiency": 0.20,        # How cheap per task
    "speed": 0.15,                   # Response time
    "quality": 0.25,                 # JSON compliance + task completion
    "reliability": 0.20,             # Low error rate
    "consensus_alignment": 0.10,     # How well it agrees with majority
    "token_efficiency": 0.10,        # Tokens per dollar
}


def compute_model_metrics(days: int = 7) -> dict:
    """
    Compute performance metrics for all active models.
    Returns dict of model_id -> {metrics}
    """
    logs = get_model_task_logs(days)
    tracker_tasks = get_tracker_tasks()
    active_models = get_active_models()
    model_ids = set(m["id"] for m in active_models)
    
    # Combine data sources
    all_tasks = list(logs)
    
    # Add tracker tasks as pseudo-logs
    for t in tracker_tasks:
        model = t.get("model", "")
        if model in model_ids or not model_ids:
            all_tasks.append({
                "model_id": model or "unknown",
                "task_type": t.get("level", "analysis"),
                "response_time": t.get("response_time", 0),
                "tokens_in": t.get("tokens_in", 0),
                "tokens_out": t.get("tokens_out", 0),
                "cost": t.get("cost", 0),
                "json_valid": 1,
                "completed": 1,
                "had_error": 0,
                "consensus_match": None,
            })
    
    if not all_tasks:
        return {}
    
    # Group by model
    by_model = {}
    for task in all_tasks:
        mid = task.get("model_id", "unknown")
        if mid not in by_model:
            by_model[mid] = []
        by_model[mid].append(task)
    
    results = {}
    for mid, tasks in by_model.items():
        total = len(tasks)
        if total == 0:
            continue
        
        total_cost = sum(t.get("cost", 0) for t in tasks)
        total_tokens_in = sum(t.get("tokens_in", 0) for t in tasks)
        total_tokens_out = sum(t.get("tokens_out", 0) for t in tasks)
        total_tokens = total_tokens_in + total_tokens_out
        
        response_times = [t.get("response_time", 0) for t in tasks if t.get("response_time", 0) > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        json_valid_count = sum(1 for t in tasks if t.get("json_valid", 1))
        completed_count = sum(1 for t in tasks if t.get("completed", 1))
        error_count = sum(1 for t in tasks if t.get("had_error", 0))
        consensus_matches = [t.get("consensus_match") for t in tasks if t.get("consensus_match") is not None]
        
        json_compliance = (json_valid_count / total) * 100 if total > 0 else 100
        completion_rate = (completed_count / total) * 100 if total > 0 else 100
        error_rate = (error_count / total) * 100 if total > 0 else 0
        avg_cost = total_cost / total if total > 0 else 0
        token_efficiency = total_tokens / total_cost if total_cost > 0 else 0
        consensus_alignment = (sum(consensus_matches) / len(consensus_matches)) * 100 if consensus_matches else 50
        
        # Find model display name
        model_name = mid
        for m in active_models:
            if m["id"] == mid:
                model_name = m["name"]
                break
        
        results[mid] = {
            "model_id": mid,
            "model_name": model_name,
            "task_count": total,
            "avg_response_time": round(avg_response_time, 2),
            "avg_cost_per_task": round(avg_cost, 6),
            "total_cost": round(total_cost, 6),
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_tokens": total_tokens,
            "json_compliance_rate": round(json_compliance, 1),
            "task_completion_rate": round(completion_rate, 1),
            "error_rate": round(error_rate, 1),
            "consensus_alignment": round(consensus_alignment, 1),
            "token_efficiency": round(token_efficiency, 2),
            "cost_efficiency": round(1 / avg_cost, 2) if avg_cost > 0 else 0,
        }
    
    return results


def compute_performance_scores(days: int = 7) -> dict:
    """
    Compute normalized performance scores across all models.
    Produces bell curve distribution.
    """
    metrics = compute_model_metrics(days)
    if not metrics:
        return {"models": [], "distribution": {}, "period_days": days}
    
    model_ids = list(metrics.keys())
    n = len(model_ids)
    
    # Extract raw metric values for z-score normalization
    raw = {
        "cost_efficiency": [metrics[mid]["cost_efficiency"] for mid in model_ids],
        "speed": [metrics[mid]["avg_response_time"] for mid in model_ids],
        "quality": [
            (metrics[mid]["json_compliance_rate"] + metrics[mid]["task_completion_rate"]) / 2
            for mid in model_ids
        ],
        "reliability": [100 - metrics[mid]["error_rate"] for mid in model_ids],
        "consensus_alignment": [metrics[mid]["consensus_alignment"] for mid in model_ids],
        "token_efficiency": [metrics[mid]["token_efficiency"] for mid in model_ids],
    }
    
    def zscore(values):
        """Compute z-scores for a list of values. Higher = better."""
        if len(values) < 2:
            return [0.0] * len(values)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 1
        return [(v - mean) / std if std > 0 else 0.0 for v in values]
    
    def invert_zscore(values):
        """For metrics where lower is better (response time, cost)."""
        zs = zscore(values)
        return [-z for z in zs]
    
    # Compute z-scores per metric
    normalized = {}
    for metric, values in raw.items():
        if metric in ("speed",):  # Lower is better
            normalized[metric] = invert_zscore(values)
        else:  # Higher is better
            normalized[metric] = zscore(values)
    
    # Compute weighted composite score
    scores = {}
    for i, mid in enumerate(model_ids):
        composite = 0.0
        breakdown = {}
        for metric, zs in normalized.items():
            weight = METRIC_WEIGHTS.get(metric, 0.1)
            weighted = zs[i] * weight
            composite += weighted
            breakdown[metric] = {
                "z_score": round(zs[i], 3),
                "weight": weight,
                "contribution": round(weighted, 3),
            }
        
        # Clamp to reasonable range
        composite = max(-3.0, min(3.0, composite))
        
        # Convert to percentile-like score (0-100)
        percentile = round((composite + 3.0) / 6.0 * 100, 1)
        
        # Classification
        if composite >= 1.0:
            classification = "⭐ SOBRESALIENTE"
            level = "outstanding"
            responsibility = "Tareas críticas: orquestación, planificación, programación, decisiones de inversión"
        elif composite >= 0.5:
            classification = "✅ BUENO"
            level = "good"
            responsibility = "Análisis estándar, informes, tareas de responsabilidad media"
        elif composite >= -0.5:
            classification = "📊 MEDIO"
            level = "average"
            responsibility = "Tareas rutinarias, análisis básicos, procesamiento de datos"
        elif composite >= -1.0:
            classification = "⚠️ POR DEBAJO"
            level = "below_average"
            responsibility = "Tareas supervisadas, verificación doble requerida"
        else:
            classification = "❌ DEFICIENTE"
            level = "poor"
            responsibility = "Solo tareas básicas de bajo riesgo o excluir de producción"
        
        scores[mid] = {
            "model_id": mid,
            "model_name": metrics[mid]["model_name"],
            "task_count": metrics[mid]["task_count"],
            "composite_zscore": round(composite, 3),
            "percentile_score": percentile,
            "classification": classification,
            "level": level,
            "recommended_responsibility": responsibility,
            "metrics": metrics[mid],
            "breakdown": breakdown,
        }
    
    # Sort by composite score (descending)
    sorted_models = sorted(scores.values(), key=lambda x: x["composite_zscore"], reverse=True)
    
    # Compute bell curve distribution
    outstanding = [m for m in sorted_models if m["level"] == "outstanding"]
    good = [m for m in sorted_models if m["level"] == "good"]
    average = [m for m in sorted_models if m["level"] == "average"]
    below_avg = [m for m in sorted_models if m["level"] == "below_average"]
    poor = [m for m in sorted_models if m["level"] == "poor"]
    
    distribution = {
        "outstanding": {"count": len(outstanding), "pct": round(len(outstanding)/n*100, 1) if n else 0, "models": [m["model_name"] for m in outstanding]},
        "good": {"count": len(good), "pct": round(len(good)/n*100, 1) if n else 0, "models": [m["model_name"] for m in good]},
        "average": {"count": len(average), "pct": round(len(average)/n*100, 1) if n else 0, "models": [m["model_name"] for m in average]},
        "below_average": {"count": len(below_avg), "pct": round(len(below_avg)/n*100, 1) if n else 0, "models": [m["model_name"] for m in below_avg]},
        "poor": {"count": len(poor), "pct": round(len(poor)/n*100, 1) if n else 0, "models": [m["model_name"] for m in poor]},
    }
    
    return {
        "models": sorted_models,
        "distribution": distribution,
        "total_models": n,
        "period_days": days,
        "evaluated_at": datetime.utcnow().isoformat(),
    }


def log_model_task(
    model_id: str,
    task_type: str = "analysis",
    response_time: float = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost: float = 0,
    json_valid: bool = True,
    completed: bool = True,
    had_error: bool = False,
    consensus_match: Optional[bool] = None,
):
    """Log a single model task execution for evaluation."""
    conn = _get_db()
    conn.execute(
        """INSERT INTO model_task_logs
           (model_id, task_type, response_time, tokens_in, tokens_out,
            cost, json_valid, completed, had_error, consensus_match)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (model_id, task_type, response_time, tokens_in, tokens_out,
         cost, 1 if json_valid else 0, 1 if completed else 0,
         1 if had_error else 0, 1 if consensus_match else 0 if consensus_match is False else None)
    )
    conn.commit()
    conn.close()


async def auto_evaluate_roundtable(roundtable_result: dict):
    """
    Auto-log evaluation data from a roundtable execution.
    Called after each roundtable analysis to build the eval database.
    """
    consensus_score = roundtable_result.get("consensus", {}).get("consensus_score")
    
    for model_data in roundtable_result.get("models", []):
        model_id = model_data.get("model")
        if not model_id or model_data.get("error"):
            continue
        
        raw = model_data.get("_raw", {})
        has_error = bool(model_data.get("error"))
        
        # Check if this model's score matched consensus
        model_score = model_data.get("score")
        consensus_match = None
        if model_score is not None and consensus_score is not None:
            # Within 15 points = matches consensus
            consensus_match = abs(model_score - consensus_score) <= 15
        
        log_model_task(
            model_id=model_id,
            task_type="roundtable_analysis",
            response_time=raw.get("response_time", 0),
            tokens_in=raw.get("tokens_in", 0),
            tokens_out=raw.get("tokens_out", 0),
            cost=raw.get("cost", 0),
            json_valid=not model_data.get("parse_error") and not model_data.get("parse_fallback"),
            completed=not has_error,
            had_error=has_error,
            consensus_match=consensus_match,
        )
