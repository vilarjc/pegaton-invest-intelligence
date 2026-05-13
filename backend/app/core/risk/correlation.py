"""
Correlation Engine — Matriz de correlación y métricas de diversificación.
P0-04: Risk Management | EP-FR-001
"""
import math
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def calculate_correlation_matrix(
    assets: Dict[str, List[float]],
) -> Dict[str, Dict[str, float]]:
    """
    Calcula la matriz de correlación entre activos.

    Args:
        assets: Dict {ticker: [retornos...]}

    Returns:
        Dict {ticker1: {ticker2: correlación, ...}, ...}
    """
    if len(assets) < 2:
        return {}

    # Validar que todos tengan la misma longitud
    lengths = {k: len(v) for k, v in assets.items()}
    min_len = min(lengths.values())
    if min_len < 2:
        logger.warning("Se necesitan al menos 2 retornos por activo")
        return {}

    # Recortar al mínimo común
    trimmed = {k: v[:min_len] for k, v in assets.items()}

    tickers = list(trimmed.keys())
    matrix: Dict[str, Dict[str, float]] = {}

    for t1 in tickers:
        matrix[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                matrix[t1][t2] = 1.0
            else:
                corr = _pearson(trimmed[t1], trimmed[t2])
                matrix[t1][t2] = round(corr, 6)

    return matrix


def _pearson(x: List[float], y: List[float]) -> float:
    """Calcula el coeficiente de correlación de Pearson."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

    den_x = sum((xi - mean_x) ** 2 for xi in x)
    den_y = sum((yi - mean_y) ** 2 for yi in y)

    den = math.sqrt(den_x * den_y)
    if den == 0:
        return 0.0

    return num / den


def diversification_ratio(
    weights: Dict[str, float],
    cov_matrix: Dict[str, Dict[str, float]],
) -> float:
    """
    Calcula el ratio de diversificación (Herfindahl-Hirschman inverso).

    Args:
        weights: {ticker: peso} (deben sumar 1.0)
        cov_matrix: Matriz de covarianza

    Returns:
        Ratio de diversificación (1 = máxima, 0 = mínima)
    """
    if not weights:
        return 0.0

    tickers = list(weights.keys())
    n = len(tickers)

    # Suma ponderada de varianzas
    weighted_var = 0.0
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            w_i = weights.get(t1, 0)
            w_j = weights.get(t2, 0)
            cov_ij = cov_matrix.get(t1, {}).get(t2, 0)
            weighted_var += w_i * w_j * cov_ij

    # Varianza media de los activos individuales
    avg_individual_var = 0.0
    for t in tickers:
        w = weights.get(t, 0)
        var = cov_matrix.get(t, {}).get(t, 0)
        avg_individual_var += w * var

    if avg_individual_var == 0:
        return 0.0

    return round(weighted_var / avg_individual_var, 6)


def max_concentration_risk(weights: Dict[str, float]) -> float:
    """
    Calcula el riesgo de concentración máximo (peso del activo más grande).

    Args:
        weights: {ticker: peso}

    Returns:
        Peso máximo como fracción (0-1)
    """
    if not weights:
        return 0.0
    return max(weights.values())


def correlation_alert(
    corr_matrix: Dict[str, Dict[str, float]],
    threshold: float = 0.8,
) -> List[Dict[str, Any]]:
    """
    Genera alertas por correlaciones altas entre activos.

    Args:
        corr_matrix: Matriz de correlación
        threshold: Umbral de correlación para alerta (default 0.8)

    Returns:
        Lista de alertas
    """
    alerts = []
    tickers = list(corr_matrix.keys())
    seen = set()

    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i >= j:
                continue
            pair = tuple(sorted([t1, t2]))
            if pair in seen:
                continue
            seen.add(pair)

            corr = abs(corr_matrix[t1][t2])
            if corr >= threshold:
                alerts.append({
                    "pair": pair,
                    "correlation": round(corr_matrix[t1][t2], 4),
                    "abs_correlation": round(corr, 4),
                    "threshold": threshold,
                    "message": f"Correlación {pair[0]}/{pair[1]} = {corr_matrix[t1][t2]:.4f} (≥ {threshold})",
                    "severity": "high" if corr >= 0.95 else "medium",
                })

    return alerts