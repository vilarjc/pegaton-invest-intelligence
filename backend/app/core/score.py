"""Pegaton Score: combined macro + technical score (0-100).
SDD Nivel 2: Parameters defined in pegaton_config.py — Spec #4.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from backend.app.core.macro import macro_score
from backend.app.core.technical import technical_score
from backend.app.core.technical_ondemand import ondemand_technical_score
from backend.app.core.pegaton_config import MACRO_WEIGHT, TECHNICAL_WEIGHT, ACTIONS

# Default tracked symbols
SYMBOLS = {
    'SPY': 'SPY',
    'EUR/USD': 'EUR/USD',
    'BTC/USD': 'BTC/USD',
}


def _determine_action(score: float) -> tuple[str, str]:
    """Return (action_name, emoji_color) from config thresholds."""
    for lo, hi, name, color in ACTIONS:
        if lo <= score <= hi:
            return name, color
    return 'EVITAR', '🔴'  # fallback


def pegaton_score(symbol: str) -> dict:
    """
    Compute the Pegaton Score for a given symbol.
    Supports any symbol via on-demand Twelve Data fetch.
    """
    macro = macro_score()

    # Try local DB first, fall back to on-demand fetch
    if symbol in SYMBOLS:
        tech = technical_score(symbol)
    else:
        tech = ondemand_technical_score(symbol)

    combined = (
        MACRO_WEIGHT * macro['macro_score'] +
        TECHNICAL_WEIGHT * tech['technical_score']
    )

    action, color = _determine_action(combined)

    # Build factors summary
    macro_factors = macro.get('factors', [])
    tech_factors = tech.get('factors', [])
    all_factors = macro_factors + tech_factors

    alcistas = [f['name'] for f in all_factors if f['direction'] == 'alcista']
    bajistas = [f['name'] for f in all_factors if f['direction'] == 'bajista']

    dominante = max(all_factors, key=lambda f: abs(f['contribution'])) if all_factors else None

    return {
        'symbol': symbol,
        'pegaton_score': round(combined, 1),
        'action': f'{color} {action}',
        'macro_score': macro['macro_score'],
        'technical_score': tech['technical_score'],
        'factors': {
            'macro': macro_factors,
            'technical': tech_factors,
            'summary': {
                'factores_alcistas': len(alcistas),
                'factores_bajistas': len(bajistas),
                'factor_dominante': {
                    'name': dominante['name'],
                    'direction': dominante['direction'],
                    'contribution': dominante['contribution'],
                } if dominante else None,
            },
        },
        'macro_details': macro.get('details', {}),
        'technical_details': tech.get('details', {}),
    }


def all_scores() -> dict:
    """Get Pegaton Scores for all tracked symbols."""
    return {symbol: pegaton_score(symbol) for symbol in SYMBOLS}
