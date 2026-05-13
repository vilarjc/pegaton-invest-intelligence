"""API endpoints for Model Objectives (OKRs) and Auto-Assignment."""
from fastapi import APIRouter, Query, HTTPException
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from backend.app.core.model_objectives import (
    get_objectives, set_objectives, get_default_targets_for_all,
    compute_objective_gaps, auto_assign_tasks, get_auto_log
)
from backend.app.core.model_eval import compute_performance_scores

router = APIRouter()


@router.get("")
async def list_all_objectives():
    """Get OKRs for all models."""
    return get_objectives()


@router.post("/init-defaults")
async def init_defaults(force: bool = Query(False)):
    """Initialize default OKRs for all active models."""
    return get_default_targets_for_all(force=force)


@router.get("/gaps")
async def objective_gaps(days: int = Query(7)):
    """Compute gap between targets and actual performance for each model."""
    return {"gaps": compute_objective_gaps(days=days)}


@router.get("/auto-assign")
async def auto_assign(days: int = Query(7)):
    """Auto-assign models to task tiers based on evaluation."""
    eval_data = compute_performance_scores(days=days)
    return auto_assign_tasks(eval_data)


@router.get("/auto-log")
async def auto_log(limit: int = Query(20)):
    """Get recent auto-assignment events (promotions, demotions)."""
    return {"events": get_auto_log(limit=limit)}


@router.get("/full-dashboard")
async def full_dashboard(days: int = Query(7)):
    """
    Comprehensive dashboard combining evaluation, OKR gaps, and auto-assignment.
    """
    eval_data = compute_performance_scores(days=days)
    gaps = compute_objective_gaps(days=days, eval_data=eval_data)
    assignments = auto_assign_tasks(eval_data)
    return {
        "evaluation": eval_data,
        "objectives": {
            "gaps": gaps,
            "settings": get_objectives(),
        },
        "auto_assignment": assignments,
        "auto_log": get_auto_log(limit=10),
    }


# These MUST be last (after specific routes) to avoid path conflicts
@router.get("/{model_id}")
async def get_model_objectives(model_id: str):
    """Get OKRs for a specific model."""
    result = get_objectives(model_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"No objectives found for model: {model_id}")
    return result


@router.put("/{model_id}")
async def update_model_objectives(model_id: str, objectives: dict):
    """Set or update OKRs for a model."""
    return set_objectives(model_id, objectives)
