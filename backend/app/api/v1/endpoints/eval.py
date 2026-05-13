"""API endpoints for Model Evaluation System (RISE-style)."""
from fastapi import APIRouter, Query
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from backend.app.core.model_eval import compute_performance_scores, compute_model_metrics, get_model_task_logs

router = APIRouter()


@router.get("/rankings")
async def model_rankings(days: int = Query(7, description="Evaluation period in days")):
    """Get ranked model evaluations with bell curve distribution."""
    return compute_performance_scores(days=days)


@router.get("/metrics")
async def model_metrics(days: int = Query(7, description="Period in days")):
    """Get raw metrics for all models without normalization."""
    return {"metrics": compute_model_metrics(days=days), "period_days": days}


@router.get("/logs")
async def task_logs(days: int = Query(30, description="Days of history")):
    """Get detailed task execution logs."""
    return {"logs": get_model_task_logs(days=days), "count": len(get_model_task_logs(days=days))}


@router.get("/budge")
async def budget_with_eval_data():
    """Budget data enriched with model evaluation insights."""
    from backend.app.api.v1.endpoints.system import budget_status
    budget_data = await budget_status()
    
    eval_data = compute_performance_scores(days=7)
    
    return {
        "budget": budget_data,
        "evaluation": eval_data,
    }
