"""
Alert Conditions — Funciones de evaluación de condiciones.
P0-03: Alert System | EP-FR-001
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def check_threshold(value: float, operator: str, threshold: float) -> bool:
    """Compara un valor contra un umbral."""
    ops = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    check = ops.get(operator)
    if check is None:
        raise ValueError(f"Operador desconocido: {operator}")
    return check(value, threshold)


def check_crossover(series_a: list, series_b: list, lookback: int = 0) -> bool:
    """Detecta si series_a cruza por encima de series_b."""
    if len(series_a) < 2 or len(series_b) < 2:
        return False
    start = max(0, len(series_a) - 2 - lookback)
    prev_a, prev_b = series_a[start], series_b[start]
    curr_a, curr_b = series_a[-1], series_b[-1]
    return prev_a <= prev_b and curr_a > curr_b


def check_crossunder(series_a: list, series_b: list, lookback: int = 0) -> bool:
    """Detecta si series_a cruza por debajo de series_b."""
    if len(series_a) < 2 or len(series_b) < 2:
        return False
    start = max(0, len(series_a) - 2 - lookback)
    prev_a, prev_b = series_a[start], series_b[start]
    curr_a, curr_b = series_a[-1], series_b[-1]
    return prev_a >= prev_b and curr_a < curr_b


def check_fear_greed(value: float, operator: str, threshold: float) -> bool:
    """Evalúa índice Fear & Greed contra umbral."""
    return check_threshold(value, operator, threshold)


def check_volume_spike(current_volume: float, avg_volume: float, multiplier: float = 2.0) -> bool:
    """Detecta pico de volumen: volumen actual > media × multiplicador."""
    if avg_volume == 0:
        return False
    return (current_volume / avg_volume) >= multiplier


def check_price_level(current_price: float, level: float, operator: str) -> bool:
    """Evalúa precio contra un nivel específico."""
    return check_threshold(current_price, operator, level)


def check_macro_change(current_value: float, previous_value: float, operator: str, threshold: float) -> bool:
    """Evalúa cambio porcentual en indicador macro."""
    if previous_value == 0:
        return False
    pct_change = ((current_value - previous_value) / abs(previous_value)) * 100
    return check_threshold(pct_change, operator, threshold)


def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> tuple[bool, str]:
    """
    Evalúa una condición genérica contra un contexto de datos.

    Args:
        condition: Dict con type, field, operator, value, lookback
        context: Dict con los valores de indicadores disponibles

    Returns:
        (resultado: bool, detalle: str)
    """
    cond_type = condition.get("type", "threshold")
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    value = condition.get("value")
    lookback = condition.get("lookback", 0)

    actual = context.get(field)

    try:
        if cond_type == "threshold":
            if actual is None:
                return False, f"{field} no disponible"
            result = check_threshold(actual, operator, float(value))
            return result, f"{field}={actual} {operator} {value}"

        elif cond_type == "crossover":
            series_a = context.get(f"{field}_series")
            series_b = context.get(f"{value}_series")
            if series_a is None or series_b is None:
                return False, f"series {field}/{value} no disponibles"
            result = check_crossover(series_a, series_b, lookback)
            return result, f"{field} cruza {value}"

        elif cond_type == "crossunder":
            series_a = context.get(f"{field}_series")
            series_b = context.get(f"{value}_series")
            if series_a is None or series_b is None:
                return False, f"series {field}/{value} no disponibles"
            result = check_crossunder(series_a, series_b, lookback)
            return result, f"{field} cruza por debajo {value}"

        elif cond_type == "fear_greed":
            fg = context.get("fear_greed_index")
            if fg is None:
                return False, "fear_greed_index no disponible"
            result = check_fear_greed(fg, operator, float(value))
            return result, f"F&G={fg} {operator} {value}"

        elif cond_type == "volume_spike":
            curr = context.get(f"{field}_current")
            avg = context.get(f"{field}_avg")
            if curr is None or avg is None:
                return False, "volumen no disponible"
            result = check_volume_spike(curr, avg, float(value))
            return result, f"vol_spike: {curr/avg if avg else 0:.1f}x >= {value}x"

        elif cond_type == "price_level":
            if actual is None:
                return False, f"precio {field} no disponible"
            result = check_price_level(actual, float(value), operator)
            return result, f"price={actual} {operator} {value}"

        elif cond_type == "macro_change":
            prev = context.get(f"{field}_previous")
            if actual is None or prev is None:
                return False, f"datos macro {field} no disponibles"
            result = check_macro_change(actual, prev, operator, float(value))
            return result, f"{field} cambio={((actual-prev)/abs(prev)*100) if prev else 0:.2f}% {operator} {value}%"

        else:
            return False, f"tipo de condición desconocido: {cond_type}"

    except Exception as e:
        logger.error(f"Error evaluando condición {field}: {e}")
        return False, f"error: {e}"