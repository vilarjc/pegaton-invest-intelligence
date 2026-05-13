"""
Risk Correlation — Análisis de correlación entre activos.
P0-04: Position Sizing | EP-FR-001
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


def calculate_correlation_matrix(assets_returns: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """
    Calcula la matriz de correlación entre múltiples activos.

    Args:
        assets_returns: Dict {ticker: [returns_list]}

    Returns:
        Matriz de correlación como dict anidado {ticker_a: {ticker_b: corr}}
    """
    if not HAS_DEPS:
        return _fallback_correlation(assets_returns)

    tickers = list(assets_returns.keys())
    if len(tickers) < 2:
        return {}

    # Alinear longitudes
    min_len = min(len(r) for r in assets_returns.values())
    if min_len < 2:
        return {}

    df = pd.DataFrame({t: r[:min_len] for t, r in assets_returns.items()})
    corr = df.corr()

    return {t: {t2: round(corr.loc[t, t2], 4) for t2 in tickers} for t in tickers}


def _fallback_correlation(assets_returns: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    """Correlación sin pandas — cálculo manual con numpy básico."""
    tickers = list(assets_returns.keys())
    if len(tickers) < 2:
        return {}

    def pearson(x, y):
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        x, y = x[:n], y[:n]
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
        dy = sum((yi - my) ** 2 for yi in y) ** 0.5
        if dx * dy == 0:
            return 0.0
        return num / (dx * dy)

    result = {}
    for t1 in tickers:
        result[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                result[t1][t2] = 1.0
            else:
                result[t1][t2] = round(pearson(assets_returns[t1], assets_returns[t2]), 4)
    return result


def diversification_ratio(
    weights: Dict[str, float],
    covariance_matrix: Dict[str, Dict[str, float]],
) -> float:
    """
    Diversification Ratio = Σ(w_i × σ_i) / σ_portfolio

    Un ratio > 1 indica diversificación efectiva.
    """
    tickers = list(weights.keys())
    if len(tickers) < 2:
        return 0.0

    # Varianza del portafolio: w'Σw
    portfolio_var = 0.0
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            w1 = weights.get(t1, 0)
            w2 = weights.get(t2, 0)
            cov = covariance_matrix.get(t1, {}).get(t2, 0)
            portfolio_var += w1 * w2 * cov

    portfolio_std = portfolio_var ** 0.5

    # Σ(w_i × σ_i)
    weighted_stds = 0.0
    for ticker in tickers:
        w = weights.get(ticker, 0)
        std = covariance_matrix.get(ticker, {}).get(ticker, 0) ** 0.5
        weighted_stds += w * std

    if portfolio_std == 0:
        return 0.0

    return round(weighted_stds / portfolio_std, 4)


def max_concentration_risk(
    positions: Dict[str, float],
    threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Detecta concentración excesiva en un solo activo.

    Args:
        positions: Dict {ticker: allocation_pct} (suma a 1.0)
        threshold: Máxima concentración permitida (default 30%)

    Returns:
        Lista de warnings por activo que excede el umbral
    """
    warnings = []
    for ticker, allocation in positions.items():
        if allocation > threshold:
            warnings.append({
                "ticker": ticker,
                "allocation": allocation,
                "threshold": threshold,
                "excess": round(allocation - threshold, 4),
                "severity": "high" if allocation > threshold * 2 else "medium",
            })
    return warnings


def correlation_alert(
    corr_matrix: Dict[str, Dict[str, float]],
    threshold: float = 0.8,
) -> List[Dict[str, Any]]:
    """
    Detecta pares de activos con correlación alta (riesgo de concentración).

    Args:
        corr_matrix: Matriz de correlación
        threshold: Correlación máxima permitida (default 0.8)

    Returns:
        Lista de pares con correlación superior al umbral
    """
    alerts = []
    tickers = list(corr_matrix.keys())

    for i, t1 in enumerate(tickers):
        for t2 in tickers[i + 1:]:
            corr = corr_matrix.get(t1, {}).get(t2, 0)
            if abs(corr) >= threshold:
                alerts.append({
                    "pair": f"{t1}/{t2}",
                    "correlation": corr,
                    "threshold": threshold,
                    "type": "high_positive" if corr > 0 else "high_negative",
                })
    return alerts