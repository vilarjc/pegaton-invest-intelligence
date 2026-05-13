"""
Technical Analysis API — Pegaton Invest Intelligence
Endpoints: POST /analyze, GET /indicators, GET /categories
SDD Nivel 2 — P0-05
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

import pandas as pd

from backend.app.core.technical.engine import TechnicalEngine, get_engine
from backend.app.core.technical.registry import get_registry


router = APIRouter(prefix="/technical", tags=["technical"])


class MarketDataRequest(BaseModel):
    """Request body para análisis técnico."""
    symbol: str = "test"
    data: List[Dict[str, Any]]
    indicators: Optional[List[str]] = None  # None = todos
    categories: Optional[List[str]] = None
    min_periods: int = 20


class IndicatorListResponse(BaseModel):
    """Respuesta de listado de indicadores."""
    categories: Dict[str, List[Dict[str, Any]]]
    total: int


class TechnicalAnalysisResponse(BaseModel):
    """Respuesta de análisis técnico."""
    symbol: str
    timestamp: str
    composite: Dict[str, Any]
    indicators: Dict[str, Any]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


@router.post("/analyze", response_model=TechnicalAnalysisResponse)
async def analyze_technical(data: MarketDataRequest):
    """
    Analiza datos de mercado con todos los indicadores técnicos.

    Body:
    - data: array de OHLCV [{open, high, low, close, volume, date}, ...]
    - indicators: lista opcional de indicadores específicos
    - categories: lista opcional de categorías
    """
    if not data.data or len(data.data) < data.min_periods:
        raise HTTPException(
            status_code=422,
            detail=f"Mínimo {data.min_periods} datos OHLCV requeridos"
        )

    try:
        df = pd.DataFrame(data.data)

        # Ensure proper types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].ffill().fillna(0)

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

        engine = get_engine()
        results = engine.run_all(df, min_periods=data.min_periods)

        if 'error' in results:
            raise HTTPException(status_code=422, detail=results['error'])

        return TechnicalAnalysisResponse(
            symbol=data.symbol,
            timestamp=datetime.utcnow().isoformat(),
            composite=results.get('composite', {}),
            indicators=results.get('indicators', {}),
            summary=results.get('summary', {}),
            metadata=results.get('metadata', {}),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators", response_model=IndicatorListResponse)
async def list_indicators(category: Optional[str] = Query(None)):
    """Lista todos los indicadores registrados, opcionalmente por categoría."""
    registry = get_registry()
    categories = {}

    cats = [category] if category else registry.categories()
    for cat in cats:
        indicators = registry.list_all(cat)
        categories[cat] = [
            {'name': i['name'], 'requires_periods': i['requires_periods']}
            for i in indicators
        ]

    return IndicatorListResponse(
        categories=categories,
        total=registry.count()
    )


@router.get("/categories")
async def list_categories():
    """Lista todas las categorías de indicadores disponibles."""
    registry = get_registry()
    counts = {}
    for cat in registry.categories():
        counts[cat] = registry.count(cat)
    return {
        'categories': counts,
        'total': registry.count()
    }


@router.get("/health")
async def technical_health():
    """Health check del motor técnico."""
    engine = get_engine()
    counts = engine.get_indicator_count()
    return {
        'status': 'ok',
        'indicators_loaded': sum(counts.values()),
        'categories': engine.get_categories(),
        'last_run': engine._last_run.isoformat() if engine._last_run else None,
    }