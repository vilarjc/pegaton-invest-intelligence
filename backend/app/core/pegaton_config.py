"""
PEGATON CONFIG — Centralized Algorithm Parameters

SDD Nivel 2: Esta configuración ES la spec en código.
Los valores aquí deben coincidir EXACTAMENTE con las specs en harness.db.
Si necesitas cambiar un parámetro, actualiza la spec PRIMERO, luego este archivo.

See specs:
  - Spec #2: Algoritmo Macro
  - Spec #3: Algoritmo Técnico
  - Spec #4: Combinación y Umbrales

YAML Override: Si existen archivos en config/, se cargan desde ahí.
Si no existen o fallan, se usan los valores hardcoded como fallback.
"""
import os
import sys
import yaml

# ── YAML Config Loader (override layer) ──────────────────────────

def _load_yaml_config():
    """
    Intenta cargar configuración desde archivos YAML en config/.
    Retorna dict con valores parseados o None si no se encuentran.
    """
    config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
    if not os.path.isdir(config_dir):
        return None

    config = {}

    # Macro indicators
    macro_yaml = os.path.join(config_dir, 'macro_indicators.yaml')
    if os.path.isfile(macro_yaml):
        try:
            with open(macro_yaml) as f:
                data = yaml.safe_load(f)
            if data and 'indicators' in data and 'weights' in data:
                config['MACRO_WEIGHTS'] = data['weights']
                scoring = {}
                for ind_name, ind_cfg in data['indicators'].items():
                    scoring[ind_name] = {
                        'name': ind_cfg.get('name', ind_name),
                        'description': ind_cfg.get('description', ''),
                        'rules': [
                            (r['operator'], r['threshold'], r['score'])
                            for r in ind_cfg.get('rules', [])
                        ],
                        'weight': data['weights'].get(ind_name, 0),
                    }
                config['MACRO_SCORING'] = scoring
        except Exception:
            pass  # Fallback to hardcoded

    # Technical indicators
    tech_yaml = os.path.join(config_dir, 'technical_indicators.yaml')
    if os.path.isfile(tech_yaml):
        try:
            with open(tech_yaml) as f:
                data = yaml.safe_load(f)
            if data:
                config['TECHNICAL_WEIGHTS'] = data.get('weights', {})
                rsi_cfg = data.get('rsi', {})
                config['RSI_OVERSOLD'] = rsi_cfg.get('oversold', 30)
                config['RSI_OVERBOUGHT'] = rsi_cfg.get('overbought', 70)
                macd_cfg = data.get('macd', {})
                config['MACD_BULLISH_SCORE'] = macd_cfg.get('bullish_score', 65)
                config['MACD_BEARISH_SCORE'] = macd_cfg.get('bearish_score', 35)
                sma_cfg = data.get('sma', {})
                config['SMA_ABOVE_SCORE'] = sma_cfg.get('sma50', {}).get('above_score', 70)
                config['SMA_BELOW_SCORE'] = sma_cfg.get('sma50', {}).get('below_score', 30)
                dir_cfg = data.get('factor_direction', {})
                config['FACTOR_ALCISTA'] = dir_cfg.get('alcista_threshold', 55)
                config['FACTOR_BAJISTA'] = dir_cfg.get('bajista_threshold', 45)
        except Exception:
            pass  # Fallback to hardcoded

    # System / blend config
    sys_yaml = os.path.join(config_dir, 'system.yaml')
    if os.path.isfile(sys_yaml):
        try:
            with open(sys_yaml) as f:
                data = yaml.safe_load(f)
            if data:
                blend = data.get('blend', {})
                config['MACRO_WEIGHT'] = blend.get('macro_weight', 0.40)
                config['TECHNICAL_WEIGHT'] = blend.get('technical_weight', 0.60)
                actions_raw = data.get('actions', [])
                config['ACTIONS'] = [
                    (a['min'], a['max'], a['name'], a['emoji'])
                    for a in actions_raw
                ]
        except Exception:
            pass  # Fallback to hardcoded

    return config if config else None


# ── Load YAML overrides (if available) ───────────────────────────
_YAML_CONFIG = _load_yaml_config()


def _get(key, default):
    """Get value from YAML config first, then fallback to hardcoded default."""
    if _YAML_CONFIG and key in _YAML_CONFIG:
        return _YAML_CONFIG[key]
    return default

# ============================================================================
# SPEC A — ALGORITMO MACRO
# ============================================================================

# These scoring functions map FRED indicator values → 0-100 scores
# Each is a list of (condition, score) pairs evaluated in order.
# condition: (operator, threshold) where operator is '<', '<=', '>=', '>'
# If no condition matches, the last score is the default.

MACRO_SCORING = {
    'FEDFUNDS': {
        'name': 'Fed Funds Rate',
        'description': 'Higher rates = tighter policy = bearish. 0-2% accommodative → bullish, 4%+ restrictive → bearish.',
        'rules': [
            ('<=', 1.5, 80),
            ('<=', 2.5, 65),
            ('<=', 3.5, 50),
            ('<=', 5.0, 35),
            ('default', None, 20),
        ],
        'weight': 0.20,
    },
    'CPIAUCSL': {
        'name': 'CPI (Consumer Price Index)',
        'description': 'CPI Level. For MVP: neutral default (need YoY for proper context).',
        'rules': [('default', None, 50)],
        'weight': 0.10,
    },
    'PCEPI': {
        'name': 'PCE Price Index',
        'description': 'PCE Price Index level. Similar to CPI. For MVP: neutral default.',
        'rules': [('default', None, 50)],
        'weight': 0.10,
    },
    'PAYEMS': {
        'name': 'Nonfarm Payrolls',
        'description': 'Higher = strong economy = bullish. Over 150K monthly is typically strong.',
        'rules': [
            ('>', 160000, 70),
            ('>', 150000, 60),
            ('>', 130000, 50),
            ('>', 100000, 40),
            ('default', None, 30),
        ],
        'weight': 0.15,
    },
    'UNRATE': {
        'name': 'Unemployment Rate',
        'description': 'Lower = stronger = bullish. Under 4% = tight labor market = bullish. Over 5% = weakening.',
        'rules': [
            ('<', 3.5, 80),
            ('<', 4.0, 70),
            ('<', 4.5, 60),
            ('<', 5.0, 50),
            ('<', 6.0, 35),
            ('default', None, 20),
        ],
        'weight': 0.15,
    },
    'UMCSENT': {
        'name': 'Consumer Sentiment (UMICH)',
        'description': 'Higher = more confident = bullish. Historical range ~50-110.',
        'rules': [
            ('>=', 100, 80),
            ('>=', 80, 65),
            ('>=', 65, 50),
            ('>=', 50, 35),
            ('default', None, 20),
        ],
        'weight': 0.10,
    },
    'INDPRO': {
        'name': 'Industrial Production',
        'description': 'Higher = stronger production = bullish. Index (100 = 2017 base).',
        'rules': [
            ('>=', 105, 70),
            ('>=', 100, 60),
            ('>=', 95, 50),
            ('default', None, 40),
        ],
        'weight': 0.10,
    },
    'DGS10': {
        'name': '10-Year Treasury Yield',
        'description': 'Very low = flight to safety = bearish. Very high = inflation concerns = bearish. Moderate = normal.',
        'rules': [
            ('<', 2.0, 30),
            ('<', 3.0, 45),
            ('<', 4.0, 55),
            ('<', 5.0, 45),
            ('<', 6.0, 35),
            ('default', None, 25),
        ],
        'weight': 0.10,
    },
}

MACRO_WEIGHTS = {k: v['weight'] for k, v in MACRO_SCORING.items()}

# ============================================================================
# SPEC B — ALGORITMO TÉCNICO
# ============================================================================

# Technical indicator weights (must sum to 1.0)
TECHNICAL_WEIGHTS = {
    'RSI(14)':   0.30,
    'MACD':      0.25,
    'SMA50':     0.25,
    'SMA200':    0.20,
}

# RSI scoring parameters
# RSI <= 30 (oversold) → high score (bullish zone)
# RSI >= 70 (overbought) → low score (bearish zone)
# 30-70: linear interpolation
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# MACD: simplified scoring
MACD_BULLISH_SCORE = 65
MACD_BEARISH_SCORE = 35

# SMA: position-based scoring
SMA_ABOVE_SCORE = 70
SMA_BELOW_SCORE = 30

# ============================================================================
# SPEC C — COMBINACIÓN Y UMBRALES
# ============================================================================

# Macro-Technical blend
MACRO_WEIGHT = 0.40
TECHNICAL_WEIGHT = 0.60

# Action thresholds (score ranges)
ACTIONS = [
    (80, 100, 'COMPRAR', '🔵'),
    (60, 79,  'ACUMULAR', '🔵'),
    (40, 59,  'MANTENER', '🟡'),
    (20, 39,  'REDUCIR',  '🟠'),
    (0,  19,  'EVITAR',   '🔴'),
]

# Factor direction thresholds (for HU-1.2 factor breakdown)
FACTOR_ALCISTA = 55    # score >= 55 → alcista
FACTOR_BAJISTA = 45    # score <= 45 → bajista
                       # between 45-55 → neutral

# ── Central DB Path ──────────────────────────────────────────
def get_db_path() -> str:
    """Retorna la ruta a la base de datos principal de Pegaton."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "pegaton.db")
