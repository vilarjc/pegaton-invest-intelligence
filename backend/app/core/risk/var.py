"""
Value at Risk — Cálculo de VaR paramétrico, histórico y CVaR.
P0-04: Position Sizing | EP-FR-001
"""
import math
from typing import List, Optional, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_parametric_var(
    returns: List[float],
    confidence: float = 0.95,
    horizon: int = 1,
    portfolio_value: float = 100_000,
) -> float:
    """
    VaR paramétrico (asume distribución normal).

    VaR = portfolio_value × z_score × σ × √horizon

    Args:
        returns: Lista de retornos porcentuales
        confidence: Nivel de confianza (default 0.95)
        horizon: Horizonte en días
        portfolio_value: Valor del portafolio en $

    Returns:
        VaR en dólares (valor absoluto, siempre positivo)
    """
    if len(returns) < 2:
        return 0.0

    arr = np.array(returns, dtype=np.float64)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)

    # z-score para el nivel de confianza
    z = _z_score(confidence)

    # VaR paramétrico
    var = portfolio_value * (z * std * math.sqrt(horizon) - mean * horizon)
    return abs(var)


def calculate_historical_var(
    returns: List[float],
    confidence: float = 0.95,
    portfolio_value: float = 100_000,
) -> float:
    """
    VaR histórico — percentil de la distribución de retornos.

    Args:
        returns: Lista de retornos porcentuales
        confidence: Nivel de confianza (default 0.95)
        portfolio_value: Valor del portafolio en $

    Returns:
        VaR en dólares (valor absoluto, siempre positivo)
    """
    if not returns:
        return 0.0

    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    index = int((1 - confidence) * n)
    index = max(0, min(index, n - 1))

    var_return = sorted_returns[index]
    return abs(portfolio_value * var_return / 100)


def calculate_cvar(
    returns: List[float],
    confidence: float = 0.95,
    portfolio_value: float = 100_000,
) -> float:
    """
    Conditional VaR (Expected Shortfall) — promedio de pérdidas
    más allá del VaR.

    Args:
        returns: Lista de retornos porcentuales
        confidence: Nivel de confianza (default 0.95)
        portfolio_value: Valor del portafolio en $

    Returns:
        CVaR en dólares (valor absoluto, siempre positivo)
    """
    if not returns or len(returns) < 2:
        return 0.0

    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    index = int((1 - confidence) * n)
    index = max(1, min(index, n - 1))

    # Promedio de los retornos en la cola izquierda
    tail_returns = sorted_returns[:index]
    cvar_return = sum(tail_returns) / len(tail_returns)

    return abs(portfolio_value * cvar_return / 100)


def calculate_var_summary(
    returns: List[float],
    portfolio_value: float = 100_000,
) -> Dict[str, float]:
    """
    Resumen completo de VaR con múltiples niveles de confianza.

    Returns:
        Dict con var_95, var_99, cvar_95, cvar_99
    """
    return {
        "var_95_parametric": round(calculate_parametric_var(returns, 0.95, 1, portfolio_value), 2),
        "var_99_parametric": round(calculate_parametric_var(returns, 0.99, 1, portfolio_value), 2),
        "var_95_historical": round(calculate_historical_var(returns, 0.95, portfolio_value), 2),
        "var_99_historical": round(calculate_historical_var(returns, 0.99, portfolio_value), 2),
        "cvar_95": round(calculate_cvar(returns, 0.95, portfolio_value), 2),
        "cvar_99": round(calculate_cvar(returns, 0.99, portfolio_value), 2),
    }


def _z_score(confidence: float) -> float:
    """
    Retorna el z-score para un nivel de confianza dado.
    Valores comunes: 0.95 → 1.645, 0.99 → 2.326, 0.975 → 1.96
    """
    z_table = {
        0.90: 1.282,
        0.95: 1.645,
        0.975: 1.96,
        0.99: 2.326,
        0.995: 2.576,
        0.999: 3.090,
    }
    if confidence in z_table:
        return z_table[confidence]
    # Interpolación lineal simple para valores no tabulados
    return 1.645  # default for unknown confidence


def returns_from_prices(prices: List[float]) -> List[float]:
    """Calcula retornos porcentuales a partir de precios."""
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            returns.append((prices[i] - prices[i - 1]) / prices[i - 1] * 100)
    return returns