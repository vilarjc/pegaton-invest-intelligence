"""
Drawdown Monitor — Cálculo y seguimiento de drawdown.
P0-04: Position Sizing | EP-FR-001
"""
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


def calculate_max_drawdown(equity_curve: List[float]) -> Dict[str, float]:
    """
    Calcula el máximo drawdown de una curva de equity.

    Args:
        equity_curve: Lista de valores de equity en orden temporal

    Returns:
        Dict con max_dd (%), duration (periodos), recovery (periodos)
    """
    if not equity_curve or len(equity_curve) < 2:
        return {"max_dd": 0.0, "duration": 0, "recovery": 0}

    peak = equity_curve[0]
    trough = equity_curve[0]
    peak_idx = 0
    trough_idx = 0
    max_dd = 0.0
    max_dd_peak_idx = 0
    max_dd_trough_idx = 0

    for i, value in enumerate(equity_curve):
        if value > peak:
            peak = value
            peak_idx = i
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                max_dd_peak_idx = peak_idx
                max_dd_trough_idx = i

    # Duración (períodos desde peak hasta trough)
    duration = max_dd_trough_idx - max_dd_peak_idx

    # Tiempo de recuperación (desde trough hasta que equity supera el peak anterior)
    recovery = 0
    recovery_peak = equity_curve[max_dd_peak_idx]
    for i in range(max_dd_trough_idx + 1, len(equity_curve)):
        if equity_curve[i] >= recovery_peak:
            recovery = i - max_dd_trough_idx
            break
    else:
        # No se recuperó
        recovery = len(equity_curve) - max_dd_trough_idx

    return {
        "max_dd": round(max_dd * 100, 2),      # En porcentaje
        "duration": duration,                  # En periodos
        "recovery": recovery,                   # En periodos
        "peak_idx": max_dd_peak_idx,
        "trough_idx": max_dd_trough_idx,
    }


def current_drawdown(current_value: float, peak_value: float) -> float:
    """
    Calcula el drawdown actual desde el último máximo.

    Args:
        current_value: Valor actual del equity
        peak_value: Valor máximo previo

    Returns:
        Drawdown como porcentaje (positivo = pérdida)
    """
    if peak_value <= 0:
        return 0.0
    return round((peak_value - current_value) / peak_value * 100, 4)


def drawdown_alert(current_dd: float, max_allowed_dd: float = 10.0) -> bool:
    """
    Verifica si el drawdown actual excede el límite permitido.

    Args:
        current_dd: Drawdown actual en %
        max_allowed_dd: Drawdown máximo permitido (default 10%)

    Returns:
        True si excede el límite
    """
    return current_dd > max_allowed_dd


def calculate_drawdown_series(equity_curve: List[float]) -> List[float]:
    """
    Calcula la serie de drawdown para cada punto de la equity.

    Args:
        equity_curve: Lista de valores de equity

    Returns:
        Lista de drawdown en cada punto (en porcentaje)
    """
    if not equity_curve:
        return []

    peak = equity_curve[0]
    drawdowns = []

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100 if peak > 0 else 0
        drawdowns.append(round(dd, 4))

    return drawdowns


class DrawdownMonitor:
    """
    Monitor de drawdown stateful para seguimiento en tiempo real.
    """

    def __init__(self, max_allowed_dd: float = 10.0, alert_at: float = 8.0):
        self.max_allowed_dd = max_allowed_dd
        self.alert_at = alert_at
        self.peak_value = 0.0
        self.current_value = 0.0
        self.in_alert = False

    def update(self, value: float) -> Dict[str, Any]:
        """
        Actualiza el monitor con un nuevo valor de equity.

        Args:
            value: Nuevo valor de equity

        Returns:
            Dict con estado actual y alertas
        """
        self.current_value = value
        if value > self.peak_value:
            self.peak_value = value

        dd = current_drawdown(value, self.peak_value)
        should_alert = drawdown_alert(dd, self.alert_at)

        if should_alert and not self.in_alert:
            self.in_alert = True
            return {
                "current_dd": dd,
                "alert_triggered": True,
                "message": f"⚠️ Drawdown {dd:.2f}% excede umbral de {self.alert_at}%",
            }
        elif not should_alert and self.in_alert:
            self.in_alert = False

        return {
            "current_dd": dd,
            "peak_value": self.peak_value,
            "alert_triggered": False,
        }

    def reset(self) -> None:
        """Resetea el monitor."""
        self.peak_value = 0.0
        self.current_value = 0.0
        self.in_alert = False