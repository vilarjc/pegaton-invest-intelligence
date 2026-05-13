"""
Value at Risk — Cálculos paramétrico, histórico y condicional (CVaR).
P0-04: Risk Management | EP-FR-001
"""
import math
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def returns_from_prices(prices: List[float]) -> List[float]:
    """
    Calcula retornos logarítmicos a partir de precios.

    Args:
        prices: Lista de precios en orden temporal

    Returns:
        Lista de retornos logarítmicos
    """
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            returns.append(math.log(prices[i] / prices[i - 1]))
        else:
            returns.append(0.0)
    return returns


def _mean(returns: List[float]) -> float:
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def _std(returns: List[float]) -> float:
    if len(returns) < 2:
        return 0.0
    m = _mean(returns)
    variance = sum((r - m) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)


def calculate_parametric_var(
    returns: List[float],
    confidence_level: float = 0.95,
    portfolio_value: float = 100_000,
) -> Dict[str, Any]:
    """
    Calcula VaR paramétrico (asumiendo distribución normal).

    Args:
        returns: Lista de retornos
        confidence_level: Nivel de confianza (default 95%)
        portfolio_value: Valor del portafolio

    Returns:
        Dict con VaR, media, std, z-score y detalles
    """
    from math import sqrt, erfc

    if not returns:
        return {"error": "No returns provided", "var": 0, "portfolio_exposure": 0}

    mu = _mean(returns)
    sigma = _std(returns)
    n = len(returns)

    # Z-score para el nivel de confianza
    # Aproximación de la inversa de la CDF normal usando erfc
    alpha = 1 - confidence_level
    # Usar aproximación de Beasley-Springer-Moro para la inversa de la normal
    z = _norm_ppf(1 - alpha)

    # VaR paramétrico
    var = -(mu - z * sigma) * portfolio_value
    var_pct = -(mu - z * sigma) * 100

    # VaR diario (1 día horizonte)
    var_daily = -(mu / n + z * sigma / sqrt(n)) * portfolio_value if n > 0 else var

    return {
        "var": round(var, 2),
        "var_pct": round(var_pct, 4),
        "var_daily_approx": round(var_daily, 2),
        "mean_return": round(mu, 6),
        "std_return": round(sigma, 6),
        "z_score": round(z, 4),
        "confidence_level": confidence_level,
        "n_observations": n,
        "portfolio_value": portfolio_value,
        "method": "parametric_normal",
    }


def calculate_historical_var(
    returns: List[float],
    confidence_level: float = 0.95,
    portfolio_value: float = 100_000,
) -> Dict[str, Any]:
    """
    Calcula VaR histórico (percentil directo de los retornos).

    Args:
        returns: Lista de retornos
        confidence_level: Nivel de confianza (default 95%)
        portfolio_value: Valor del portafolio

    Returns:
        Dict con VaR histórico y detalles
    """
    if not returns:
        return {"error": "No returns provided", "var": 0, "portfolio_exposure": 0}

    sorted_returns = sorted(returns)
    n = len(sorted_returns)

    # Índice del percentil
    alpha = 1 - confidence_level
    k = int(alpha * n)
    k = max(0, min(k, n - 1))

    var_return = sorted_returns[k]
    var = -var_return * portfolio_value

    # Interpolación si k no es exacto
    if k + 1 < n:
        frac = alpha * n - k
        interpolated = sorted_returns[k] * (1 - frac) + sorted_returns[k + 1] * frac
        var_interp = -interpolated * portfolio_value
    else:
        var_interp = var

    return {
        "var": round(var, 2),
        "var_interpolated": round(var_interp, 2),
        "var_pct": round(-var_return * 100, 4),
        "confidence_level": confidence_level,
        "n_observations": n,
        "portfolio_value": portfolio_value,
        "worst_return": round(var_return, 6),
        "method": "historical",
    }


def calculate_cvar(
    returns: List[float],
    confidence_level: float = 0.95,
    portfolio_value: float = 100_000,
) -> Dict[str, Any]:
    """
    Calcula CVaR (Expected Shortfall / Conditional VaR).
    Promedio de las pérdidas que exceden el VaR.

    Args:
        returns: Lista de retornos
        confidence_level: Nivel de confianza (default 95%)
        portfolio_value: Valor del portafolio

    Returns:
        Dict con CVaR y detalles
    """
    if not returns:
        return {"error": "No returns provided", "cvar": 0}

    alpha = 1 - confidence_level
    var_result = calculate_historical_var(returns, confidence_level, portfolio_value)
    var_return = -var_result["worst_return"]

    # Promediar todos los retornos peores o iguales al VaR
    tail_losses = [r for r in returns if r <= var_return]

    if not tail_losses:
        cvar_return = var_return
    else:
        cvar_return = sum(tail_losses) / len(tail_losses)

    cvar = -cvar_return * portfolio_value

    return {
        "cvar": round(cvar, 2),
        "cvar_pct": round(-cvar_return * 100, 4),
        "var_at_threshold": var_result["var"],
        "tail_losses_count": len(tail_losses),
        "total_observations": len(returns),
        "confidence_level": confidence_level,
        "portfolio_value": portfolio_value,
        "tail_avg_return": round(cvar_return, 6),
        "method": "cvar_historical",
    }


def calculate_var_summary(
    returns: List[float],
    portfolio_value: float = 100_000,
    confidence_levels: List[float] = None,
) -> Dict[str, Any]:
    """
    Calcula un resumen completo de VaR y CVaR a múltiples niveles de confianza.

    Args:
        returns: Lista de retornos
        portfolio_value: Valor del portafolio
        confidence_levels: Lista de niveles de confianza (default [0.90, 0.95, 0.99])

    Returns:
        Dict con resumen completo de riesgo
    """
    if confidence_levels is None:
        confidence_levels = [0.90, 0.95, 0.99]

    if not returns:
        return {"error": "No returns provided", "portfolio_value": portfolio_value}

    summary = {
        "portfolio_value": portfolio_value,
        "n_observations": len(returns),
        "mean_return": round(_mean(returns), 6),
        "std_return": round(_std(returns), 6),
        "levels": {},
    }

    for cl in confidence_levels:
        pv = calculate_parametric_var(returns, cl, portfolio_value)
        hv = calculate_historical_var(returns, cl, portfolio_value)
        cv = calculate_cvar(returns, cl, portfolio_value)

        summary["levels"][f"{int(cl * 100)}%"] = {
            "parametric_var": pv["var"],
            "historical_var": hv["var"],
            "cvar": cv["cvar"],
            "var_pct": pv["var_pct"],
            "z_score": pv["z_score"],
        }

    # Clasificación de riesgo
    var_95 = summary["levels"].get("95%", {}).get("parametric_var", 0)
    risk_ratio = abs(var_95) / portfolio_value if portfolio_value > 0 else 0

    if risk_ratio < 0.02:
        risk_grade = "BAJO"
    elif risk_ratio < 0.05:
        risk_grade = "MODERADO"
    elif risk_ratio < 0.10:
        risk_grade = "ALTO"
    else:
        risk_grade = "MUY_ALTO"

    summary["risk_grade"] = risk_grade
    summary["risk_ratio_95"] = round(risk_ratio * 100, 2)

    return summary


def _norm_ppf(p: float) -> float:
    """
    Aproximación de la inversa de la CDF normal estándar (percent point function).
    Algoritmo de Beasley-Springer-Moro.

    Args:
        p: Probabilidad (0 < p < 1)

    Returns:
        Valor z tal que P(Z <= z) = p
    """
    if p <= 0 or p >= 1:
        raise ValueError(f"p debe estar en (0, 1), got {p}")

    # Coeficientes
    a = [
        -3.969683028665376e01, 2.209460984245205e02,
        -2.759285104469687e02, 1.383577518672690e02,
        -3.066479806614716e01, 2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01, 1.615858368580409e02,
        -1.556989798598866e02, 6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e00, -2.549732539343734e00,
        4.374664141464968e00, 2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e00, 3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1))