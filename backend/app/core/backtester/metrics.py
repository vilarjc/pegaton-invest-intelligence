"""
Metrics Engine — Cálculo de métricas de rendimiento para backtesting.
P0-02: Backtesting Engine | EP-FR-001
"""
import math
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def calculate_metrics(returns_pct: List[float]) -> Dict[str, Any]:
    """
    Calcula métricas de rendimiento completo a partir de una lista de retornos porcentuales.

    Args:
        returns_pct: Lista de retornos en porcentaje (ej: [1.5, -0.5, 2.0, ...])

    Returns:
        Diccionario con todas las métricas calculadas.
    """
    if not returns_pct:
        return _empty_metrics()

    returns = returns_pct  # Ya en porcentaje
    n = len(returns)

    if n < 2:
        return {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "calmar_ratio": 0.0,
            "omega_ratio": 0.0,
            "var_95": 0.0,
            "cvar_95": 0.0,
            "total_return": 0.0,
            "avg_trade": 0.0,
            "num_trades": n,
        }

    # Retornos acumulados para equity curve
    cumulative = _cumulative_returns(returns)

    return {
        "sharpe_ratio": round(_sharpe_ratio(returns), 4),
        "sortino_ratio": round(_sortino_ratio(returns), 4),
        "max_drawdown": round(_max_drawdown(cumulative), 4),
        "win_rate": round(_win_rate(returns), 4),
        "profit_factor": round(_profit_factor(returns), 4),
        "expectancy": round(_expectancy(returns), 4),
        "calmar_ratio": round(_calmar_ratio(returns, cumulative), 4),
        "omega_ratio": round(_omega_ratio(returns), 4),
        "var_95": round(_var(returns, 0.95), 4),
        "cvar_95": round(_cvar(returns, 0.95), 4),
        "total_return": round(sum(returns), 4),
        "avg_trade": round(sum(returns) / n, 4),
        "num_trades": n,
    }


def _empty_metrics() -> Dict[str, Any]:
    return {
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "calmar_ratio": 0.0,
        "omega_ratio": 0.0,
        "var_95": 0.0,
        "cvar_95": 0.0,
        "total_return": 0.0,
        "avg_trade": 0.0,
        "num_trades": 0,
    }


def _cumulative_returns(returns: List[float]) -> List[float]:
    """Calcula retornos acumulados."""
    cumulative = []
    total = 0.0
    for r in returns:
        total += r
        cumulative.append(total)
    return cumulative


def _sharpe_ratio(returns: List[float], risk_free: float = 0.0) -> float:
    """Sharpe Ratio = (Retorno medio - risk-free) / Desviación estándar."""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean - risk_free) / std * math.sqrt(252)  # Anualizado


def _sortino_ratio(returns: List[float], risk_free: float = 0.0) -> float:
    """Sortino Ratio — solo penaliza volatilidad negativa (downside deviation)."""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    downside_returns = [min(r - risk_free, 0) ** 2 for r in returns]
    downside_variance = sum(downside_returns) / n
    downside_std = math.sqrt(downside_variance)
    if downside_std == 0:
        return 0.0
    return (mean - risk_free) / downside_std * math.sqrt(252)


def _max_drawdown(cumulative: List[float]) -> float:
    """Máximo drawdown (en porcentaje)."""
    if not cumulative:
        return 0.0
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _win_rate(returns: List[float]) -> float:
    """Porcentaje de trades ganadores."""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return wins / len(returns)


def _profit_factor(returns: List[float]) -> float:
    """Profit Factor = Gross Profit / Gross Loss."""
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _expectancy(returns: List[float]) -> float:
    """Expectancy = (Win% × Avg Win) - (Loss% × Avg Loss)."""
    if not returns:
        return 0.0
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    n = len(returns)

    win_pct = len(wins) / n
    loss_pct = len(losses) / n
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

    return win_pct * avg_win - loss_pct * avg_loss


def _calmar_ratio(returns: List[float], cumulative: List[float]) -> float:
    """Calmar Ratio = Retorno anualizado / Max Drawdown."""
    total_return = sum(returns)
    max_dd = _max_drawdown(cumulative)
    if max_dd == 0:
        return 0.0
    return total_return / max_dd


def _omega_ratio(returns: List[float], threshold: float = 0.0) -> float:
    """Omega Ratio = Probabilidad ponderada de retornos positivos / negativos."""
    gains = sum(1 for r in returns if r > threshold)
    losses = sum(1 for r in returns if r < threshold)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _var(returns: List[float], confidence: float) -> float:
    """Value at Risk (VaR) paramétrico — percentil de la distribución."""
    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    index = int((1 - confidence) * n)
    return sorted_returns[max(0, min(index, n - 1))]


def _cvar(returns: List[float], confidence: float) -> float:
    """Conditional VaR (Expected Shortfall) = media de pérdidas beyond VaR."""
    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    index = int((1 - confidence) * n)
    tail_losses = sorted_returns[: max(1, index)]
    return sum(tail_losses) / len(tail_losses)