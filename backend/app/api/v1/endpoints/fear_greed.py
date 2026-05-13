"""
Fear & Greed API endpoint — Equipo A
GET /api/v1/fear-greed → {score, action, action_emoji, timestamp, factores, cacheado}
"""

from fastapi import APIRouter, Query
from backend.app.core.fear_greed_engine import FearGreedEngine

router = APIRouter()
engine = FearGreedEngine()


@router.get("")
async def get_fear_greed(force_refresh: bool = Query(False, alias="force")):
    """
    Return the current Fear & Greed composite score (0-100).
    
    Args:
        force_refresh: If True, bypass cache and recompute.
    
    Returns:
        JSON dict with score, action, action_emoji, timestamp, factores, cacheado
    """
    result = engine.get_score(force_refresh=force_refresh)
    return result
