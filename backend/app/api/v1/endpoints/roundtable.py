"""API endpoints for the Multi-Model Roundtable (Mesa Redonda)."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
from backend.app.core.score import pegaton_score
from backend.app.core.roundtable import run_roundtable
from backend.app.core.providers import get_active_models, get_available_models

router = APIRouter()


@router.get("/models")
async def list_available_models(active_only: bool = False):
    """List all available models for the roundtable."""
    if active_only:
        return {"models": get_active_models()}
    return {"models": get_available_models()}


@router.get("/analyze/{symbol:path}")
async def roundtable_analyze(
    symbol: str,
    models: str = Query(None, description="Comma-separated model IDs to use"),
):
    """
    Run a multi-model roundtable analysis for a symbol.
    
    Each model independently analyzes the same data, then consensus is computed.
    """
    # Normalize symbol (EUR/USD handling)
    symbol = symbol.upper().strip()
    
    # Get base data from Pegaton Score engine
    base_data = pegaton_score(symbol)
    if 'error' in base_data:
        raise HTTPException(status_code=400, detail=base_data['error'])
    
    macro_data = {
        'macro_score': base_data.get('macro_score', 50),
        'details': base_data.get('macro_details', {}),
    }
    technical_data = {
        'technical_score': base_data.get('technical_score', 50),
        'details': base_data.get('technical_details', {}),
    }
    
    # Parse model list if provided
    model_list = None
    if models:
        model_list = [m.strip() for m in models.split(",") if m.strip()]
    
    result = await run_roundtable(
        symbol=symbol,
        macro_data=macro_data,
        technical_data=technical_data,
        models=model_list,
    )
    result["timestamp"] = datetime.utcnow().isoformat()
    
    # Auto-log evaluation data
    try:
        from backend.app.core.model_eval import auto_evaluate_roundtable
        # Run in background to not block response
        import asyncio
        asyncio.ensure_future(auto_evaluate_roundtable(result))
    except Exception:
        pass
    
    return result


@router.get("/default")
async def default_roundtable():
    """Run a quick roundtable with default models on tracked symbols."""
    from backend.app.core.score import all_scores, SYMBOLS
    
    results = {}
    for symbol in SYMBOLS:
        base = all_scores().get(symbol, {})
        if not base:
            continue
        
        macro_data = {
            'macro_score': base.get('macro_score', 50),
            'details': base.get('macro_details', {}),
        }
        technical_data = {
            'technical_score': base.get('technical_score', 50),
            'details': base.get('technical_details', {}),
        }
        
        result = await run_roundtable(
            symbol=symbol,
            macro_data=macro_data,
            technical_data=technical_data,
            models=["deepseek-v4-flash", "deepseek-chat"],
        )
        result["timestamp"] = datetime.utcnow().isoformat()
        results[symbol] = result
    
    return results
