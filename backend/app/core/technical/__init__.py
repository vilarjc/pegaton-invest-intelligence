"""
Technical Indicators Module — Pegaton Invest Intelligence
50+ indicadores organizados en 6 categorías.

SDD Nivel 2 — P0-05

Importa todo:
    from backend.app.core.technical import (
        registry, scoring, engine,
        RSI, StochasticRSI, MACD, ADX, BollingerBands, OBV, ...
    )
    from backend.app.core.technical.registry import TechnicalIndicator, register_indicator
"""
import logging

logger = logging.getLogger(__name__)

# ─── Compatibilidad legacy ───
DB_PATH = "/root/pegaton_invest_intelligence/data/pegaton.db"

# ─── Registry ───
from .registry import (
    TechnicalIndicator, IndicatorRegistry,
    register_indicator, get_registry
)

# ─── Scoring ───
from .scoring import (
    composite_score, calculate_indicator_score, normalize_score,
    DEFAULT_CATEGORY_WEIGHTS, DEFAULT_INDICATOR_WEIGHTS
)

# ─── Engine ───
from .engine import TechnicalEngine, get_engine


# ─── Shims legacy (compatibilidad con technical_ondemand, score, signal) ───

def _factor_direction(score: float) -> str:
    """Clasifica dirección basada en score (0-100)."""
    if score >= 55:
        return "alcista"
    elif score <= 45:
        return "bajista"
    return "neutral"


def compute_rsi_score(rsi_val: float) -> float:
    """Convert RSI value to 0-100 score. Legacy shim."""
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    if rsi_val <= RSI_OVERSOLD:
        return 100 - (rsi_val / RSI_OVERSOLD) * 20
    elif rsi_val >= RSI_OVERBOUGHT:
        return (100 - rsi_val) / (100 - RSI_OVERBOUGHT) * 20
    else:
        return 80 - (rsi_val - RSI_OVERSOLD) / (RSI_OVERBOUGHT - RSI_OVERSOLD) * 60


def rsi(series, period: int = 14) -> float:
    """Calculate RSI for the last value. Legacy shim."""
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gains = delta.where(delta > 0, 0)
    losses = (-delta.where(delta < 0, 0))
    avg_gain = float(gains.rolling(window=period).mean().iloc[-1])
    avg_loss = float(losses.rolling(window=period).mean().iloc[-1])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def macd(series) -> dict:
    """Calculate MACD. Legacy shim."""
    if len(series) < 26:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'bullish': True}
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1]),
        'bullish': bool(float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]))
    }


def sma_position(series, period: int) -> dict:
    """Check if price is above/below SMA. Legacy shim."""
    if len(series) < period:
        return {'above': True, 'distance_pct': 0.0}
    sma = float(series.rolling(window=period).mean().iloc[-1])
    current = float(series.iloc[-1])
    distance = float(((current - sma) / sma) * 100)
    return {'above': bool(current > sma), 'distance_pct': distance}


def technical_score(symbol: str) -> dict:
    """
    Función de compatibilidad legacy.
    Lee datos OHLCV de la DB y calcula score técnico.
    Si no hay datos → retorna 50 con factores vacíos.
    """
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM precios_ohlcv WHERE simbolo = ? ORDER BY timestamp ASC LIMIT 100",
            (symbol,)
        ).fetchall()
        conn.close()

        if not rows:
            return {
                'technical_score': 50.0,
                'factors': [],
                'details': {
                    'dominant_signal': 'neutral',
                    'signal_strength': 'sin_datos',
                    'top_factor': None,
                    'risk_level': 'medio',
                    'indicators_count': 0,
                },
            }

        import pandas as pd
        import numpy as np
        from datetime import datetime

        df = pd.DataFrame([dict(r) for r in rows])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        engine = get_engine()
        data = df[['open', 'high', 'low', 'close', 'volume']].dropna()

        if len(data) < 30:
            raise ValueError(f"Solo {len(data)} filas OHLCV, mínimo 30")

        results = engine.run_all(data)
        score = results['composite']['composite']
        factors = []
        for key, val in results.get('indicators', {}).items():
            direction = 'alcista' if val['score'] >= 55 else ('bajista' if val['score'] <= 45 else 'neutral')
            factors.append({
                'name': key,
                'direction': direction,
                'contribution': round(val['score'] - 50, 2),
                'value': val['score'],
            })
        top_contrib = max(factors, key=lambda f: abs(f['contribution'])) if factors else None
        return {
            'technical_score': round(score, 1),
            'factors': factors,
            'details': {
                'dominant_signal': results['composite'].get('dominant_signal'),
                'signal_strength': results['composite'].get('signal_strength'),
                'top_factor': {
                    'name': top_contrib['name'],
                    'direction': top_contrib['direction'],
                    'contribution': top_contrib['contribution'],
                } if top_contrib else None,
                'risk_level': results['composite'].get('risk_level'),
                'indicators_count': results['metadata'].get('total_indicators'),
            },
        }
    except Exception as e:
        logger.error(f"technical_score error: {e}", exc_info=True)
        return {
            'technical_score': 50.0,
            'factors': [],
            'details': {'error': str(e)},
        }


# ─── Force-load submodules para que @register_indicator se ejecute ───
try:
    from . import momentum       # noqa: F401  — 10 indicadores
    from . import volatility     # noqa: F401  — 8 indicadores
    from . import trend          # noqa: F401  — 10 indicadores
    from . import volume         # noqa: F401  — 7 indicadores
    from . import cycles         # noqa: F401  — 7 indicadores
    from . import patterns       # noqa: F401  — 8 indicadores
    logger.info("Todos los sub-módulos de indicadores cargados correctamente.")
except ImportError as e:
    logger.error(f"Error cargando sub-módulos de indicadores: {e}")


__all__ = [
    # Core
    'TechnicalIndicator', 'IndicatorRegistry',
    'register_indicator', 'get_registry',
    'composite_score', 'calculate_indicator_score', 'normalize_score',
    'DEFAULT_CATEGORY_WEIGHTS', 'DEFAULT_INDICATOR_WEIGHTS',
    'TechnicalEngine', 'get_engine',
    # Shims legacy
    'technical_score', 'DB_PATH', 'compute_rsi_score',
    '_factor_direction',
    'rsi', 'macd', 'sma_position',
]