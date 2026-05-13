"""API endpoints for Pegaton Score."""
from fastapi import APIRouter, HTTPException, Query
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from backend.app.core.score import pegaton_score, all_scores, SYMBOLS

router = APIRouter()

@router.get("")
async def get_all_scores():
    return all_scores()

@router.get("/symbols")
async def list_symbols():
    return {'symbols': list(SYMBOLS.keys())}

@router.get("/query")
async def get_score_query(symbol: str = Query(...)):
    """Get score for a symbol using query parameter (handles slashes like EUR/USD)."""
    result = pegaton_score(symbol.upper())
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@router.get("/{symbol}")
async def get_score_path(symbol: str):
    """Get score for a symbol via path parameter (no slashes - use SPY, BTCUSD)."""
    result = pegaton_score(symbol.upper())
    if 'error' in result:
        raise HTTPException(status_code=400, detail=result['error'])
    return result
