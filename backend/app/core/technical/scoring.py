"""
Technical Scoring — Pegaton Invest Intelligence
SDD Nivel 2 — P0-05

Combina scores de 50+ indicadores en un composite score (0-100).
Pesos configurables por categoría.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from backend.app.core.technical.registry import get_registry


# Pesos por categoría (suman 1.0)
DEFAULT_CATEGORY_WEIGHTS = {
    'momentum': 0.20,
    'volatility': 0.15,
    'trend': 0.25,
    'volume': 0.15,
    'cycles': 0.10,
    'patterns': 0.15,
}

DEFAULT_INDICATOR_WEIGHTS = {
    # Momentum
    'rsi': 1.5, 'stoch_rsi': 1.2, 'williams': 1.0, 'cci': 1.0,
    'roc': 0.8, 'mfi': 1.2, 'ppo': 0.8, 'tsi': 0.7, 'uo': 0.8, 'ao': 0.8,
    # Volatility
    'bollinger': 1.5, 'atr': 1.2, 'keltner': 1.0, 'donchian': 0.8,
    'std_dev': 0.7, 'hist_vol': 1.0, 'chaikin_vol': 0.8, 'natr': 0.8,
    # Trend
    'sma': 1.0, 'ema': 1.2, 'wma': 0.8, 'macd': 1.5, 'adx': 1.5,
    'ichimoku': 1.3, 'supertrend': 1.2, 'parabolic_sar': 1.0,
    'ama': 0.8, 'vortex': 0.8,
    # Volume
    'obv': 1.2, 'vwap': 1.3, 'ad': 1.0, 'volume_sma': 0.8,
    'pvt': 0.8, 'force_index': 0.9, 'elders_force': 0.8,
    # Cycles
    'hilbert': 0.8, 'dominant_cycle': 0.9, 'sine_wave': 0.7,
    'trend_cycle': 0.7, 'mama': 0.8, 'fama': 0.7, 'roofing_filter': 0.6,
    'autocorrelation': 0.7,
    # Patterns
    'double_top_bottom': 1.2, 'head_shoulders': 1.2, 'triangle': 1.0,
    'flag_pennant': 1.0, 'wedge': 0.9, 'gap': 0.8, 'support_resistance': 1.2,
}


def calculate_indicator_score(signal: float, neutral_zone: float = 0.1) -> float:
    """
    Convierte una señal normalizada (-1 a +1) en score (0-100).
    signal: valor normalizado del indicador
    neutral_zone: rango alrededor de 0 considerado neutral
    """
    if abs(signal) <= neutral_zone:
        return 50.0  # neutral
    if signal > 0:
        return 50.0 + (signal / (1.0 - neutral_zone)) * 50.0
    else:
        return 50.0 - (abs(signal) / (1.0 - neutral_zone)) * 50.0


def normalize_score(score: float, min_val: float, max_val: float) -> float:
    """Normaliza un valor a rango 0-100."""
    if max_val == min_val:
        return 50.0
    normalized = (score - min_val) / (max_val - min_val)
    return max(0.0, min(100.0, normalized * 100.0))


def composite_score(
    indicator_results: Dict[str, Dict],
    category_weights: Optional[Dict[str, float]] = None,
    indicator_weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Calcula el composite score técnico combinando todos los indicadores.

    Args:
        indicator_results: {indicator_key: {'score': float, 'signal': float}}
        category_weights: pesos por categoría (default DEFAULT_CATEGORY_WEIGHTS)
        indicator_weights: pesos individuales por indicador

    Returns:
        {
            'composite': float (0-100),
            'by_category': {category: score},
            'by_indicator': {indicator: score},
            'dominant_signal': 'bullish'/'bearish'/'neutral',
            'signal_strength': 'strong'/'moderate'/'weak'/'neutral',
            'risk_level': 'low'/'medium'/'high',
        }
    """
    cat_weights = category_weights or DEFAULT_CATEGORY_WEIGHTS
    ind_weights = indicator_weights or DEFAULT_INDICATOR_WEIGHTS

    # Agrupar por categoría
    by_category: Dict[str, List[float]] = {}
    by_indicator: Dict[str, float] = {}
    registry = get_registry()

    for key, result in indicator_results.items():
        # Buscar categoría del indicador en el registry
        reg_entry = registry.get(key)
        if reg_entry:
            cat = reg_entry['category']
        else:
            # Fallback: inferir del key
            cat = key.split('.')[0] if '.' in key else 'momentum'

        score = result.get('score', 50.0)
        weight = ind_weights.get(key, 1.0)

        weighted_score = score * weight

        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(weighted_score)
        by_indicator[key] = score

    # Calcular score por categoría
    cat_scores: Dict[str, float] = {}
    total_weighted = 0.0
    total_cat_weight = 0.0

    for cat, scores in by_category.items():
        cat_avg = np.mean(scores) if scores else 50.0
        cat_weight = cat_weights.get(cat, 0.1)
        cat_scores[cat] = round(cat_avg, 2)
        total_weighted += cat_avg * cat_weight
        total_cat_weight += cat_weight

    composite = round(total_weighted / total_cat_weight, 2) if total_cat_weight > 0 else 50.0

    # Determinar señal dominante
    bullish_count = sum(1 for s in by_indicator.values() if s > 55)
    bearish_count = sum(1 for s in by_indicator.values() if s < 45)
    neutral_count = len(by_indicator) - bullish_count - bearish_count

    if bullish_count > bearish_count and bullish_count > neutral_count:
        dominant = 'bullish'
    elif bearish_count > bullish_count and bearish_count > neutral_count:
        dominant = 'bearish'
    else:
        dominant = 'neutral'

    # Strength
    deviation = abs(composite - 50)
    if deviation > 30:
        strength = 'strong'
    elif deviation > 15:
        strength = 'moderate'
    elif deviation > 5:
        strength = 'weak'
    else:
        strength = 'neutral'

    # Risk level (inverso: score extremo = alto riesgo de dirección equivocada)
    risk = 'medium'
    if 35 <= composite <= 65:
        risk = 'low'
    elif 20 <= composite < 35 or 65 < composite <= 80:
        risk = 'medium'
    else:
        risk = 'high'

    return {
        'composite': round(composite, 1),
        'by_category': cat_scores,
        'by_indicator': {k: round(v, 2) for k, v in by_indicator.items()},
        'dominant_signal': dominant,
        'signal_strength': strength,
        'risk_level': risk,
        'total_indicators': len(by_indicator),
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'neutral_count': neutral_count,
    }