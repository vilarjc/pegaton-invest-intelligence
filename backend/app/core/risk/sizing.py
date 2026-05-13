"""
Risk Sizing — Calculadora de tamaño de posición.
P0-04: Position Sizing | EP-FR-001
"""
import math
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SizingResult:
    suggested_shares: float
    risk_amount: float
    entry_price: float
    stop_loss_price: float
    rr_ratio: float
    max_position_value: float
    portfolio_impact_pct: float
    risk_pct: float
    method: str


class PositionSizer:
    """
    Calculadora de tamaño de posición con múltiples métodos:
    - Fixed % Risk: tamaño basado en % de capital arriesgado
    - Kelly Criterion: f* = (bp - q) / b
    - Volatility Adjusted: ajustado por volatilidad del activo
    """

    def __init__(self, account_balance: float, risk_pct: float = 0.01):
        """
        Args:
            account_balance: Capital total de la cuenta
            risk_pct: Porcentaje de capital a arriesgar por trade (default 1%)
        """
        self.account_balance = account_balance
        self.risk_pct = risk_pct

    def calculate_fixed_risk(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: Optional[float] = None,
    ) -> SizingResult:
        """
        Fixed % Risk method.
        position_size = (account_balance × risk_pct) / (entry_price × stop_loss_pct)

        Args:
            entry_price: Precio de entrada
            stop_loss_price: Precio de stop loss
            risk_pct: Override del riesgo porcentual (opcional)

        Returns:
            SizingResult con todos los parámetros calculados
        """
        risk = risk_pct if risk_pct is not None else self.risk_pct
        risk_amount = self.account_balance * risk
        stop_pct = abs(entry_price - stop_loss_price) / entry_price

        if stop_pct == 0:
            logger.warning("Stop loss al mismo precio que entrada")
            return SizingResult(
                suggested_shares=0,
                risk_amount=0,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                rr_ratio=0,
                max_position_value=0,
                portfolio_impact_pct=0,
                risk_pct=risk,
                method="fixed_risk",
            )

        position_value = risk_amount / stop_pct
        shares = position_value / entry_price
        max_loss = shares * (entry_price - stop_loss_price)

        return SizingResult(
            suggested_shares=round(shares, 2),
            risk_amount=round(risk_amount, 2),
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            rr_ratio=round((entry_price - stop_loss_price) / stop_loss_price * (1 / stop_pct), 2) if stop_pct > 0 else 0,
            max_position_value=round(position_value, 2),
            portfolio_impact_pct=round((position_value / self.account_balance) * 100, 2),
            risk_pct=risk,
            method="fixed_risk",
        )

    def calculate_kelly(
        self,
        wins: int,
        losses: int,
        avg_win: float,
        avg_loss: float,
    ) -> Dict[str, float]:
        """
        Kelly Criterion: f* = (bp - q) / b
        Donde b = avg_win / avg_loss, p = win_rate, q = 1 - p

        Args:
            wins: Número de trades ganadores
            losses: Número de trades perdedores
            avg_win: Ganancia media por trade ganador
            avg_loss: Pérdida media por trade perdedor (valor positivo)

        Returns:
            Dict con kelly_fraction, expected_edge, y recommended_shares
        """
        total = wins + losses
        if total == 0 or avg_loss == 0:
            return {
                "kelly_fraction": 0.0,
                "expected_edge": 0.0,
                "recommended_shares": 0.0,
                "win_rate": 0.0,
                "interpretation": "datos insuficientes",
            }

        win_rate = wins / total
        loss_rate = losses / total
        b = avg_win / avg_loss if avg_loss > 0 else 0

        # Kelly = (bp - q) / b
        kelly = (b * win_rate - loss_rate) / b if b > 0 else 0

        # Cap Kelly a 25% (half-kelly común en práctica)
        kelly_capped = max(0, min(kelly, 0.25))

        recommended_value = self.account_balance * kelly_capped

        interpretation = (
            "agresivo" if kelly > 0.15 else
            "moderado" if kelly > 0.05 else
            "conservador" if kelly > 0 else
            "no apostar"
        )

        return {
            "kelly_fraction": round(kelly, 4),
            "kelly_capped": round(kelly_capped, 4),
            "expected_edge": round(b * win_rate - loss_rate, 4),
            "win_rate": round(win_rate, 4),
            "recommended_value": round(recommended_value, 2),
            "interpretation": interpretation,
        }

    def calculate_volatility_adjusted(
        self,
        asset_volatility: float,
        benchmark_volatility: float,
        base_size_value: float,
    ) -> Dict[str, float]:
        """
        Position sizing ajustado por volatilidad.
        Reduce el tamaño cuando la volatilidad del activo es alta
        y aumenta cuando es baja (inversamente proporcional).

        Args:
            asset_volatility: Volatilidad anualizada del activo (ej: 0.30 = 30%)
            benchmark_volatility: Volatilidad del benchmark (ej: 0.15 = 15%)
            base_size_value: Tamaño base de la posición en $

        Returns:
            Dict con adjusted_size y ratio de ajuste
        """
        if benchmark_volatility == 0:
            return {
                "adjusted_size": base_size_value,
                "adjustment_ratio": 1.0,
                "note": "volatilidad benchmark = 0, sin ajuste",
            }

        ratio = benchmark_volatility / asset_volatility if asset_volatility > 0 else 1.0
        # Cap ratio entre 0.25 y 4.0
        ratio = max(0.25, min(ratio, 4.0))
        adjusted_size = base_size_value * ratio

        return {
            "adjusted_size": round(adjusted_size, 2),
            "adjustment_ratio": round(ratio, 4),
            "original_size": base_size_value,
        }

    def calculate_atr_position(
        self,
        atr: float,
        entry_price: float,
        risk_pct: Optional[float] = None,
        multiplier: float = 1.5,
    ) -> SizingResult:
        """
        ATR-based position sizing.
        Stop loss = entry - (ATR × multiplier)

        Args:
            atr: Average True Range actual
            entry_price: Precio de entrada
            risk_pct: % de capital a arriesgar
            multiplier: Multiplicador del ATR para el stop

        Returns:
            SizingResult con los cálculos
        """
        risk = risk_pct if risk_pct is not None else self.risk_pct
        stop_distance = atr * multiplier
        stop_loss_price = entry_price - stop_distance

        if entry_price == 0:
            return SizingResult(
                suggested_shares=0,
                risk_amount=0,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                rr_ratio=0,
                max_position_value=0,
                portfolio_impact_pct=0,
                risk_pct=risk,
                method="atr",
            )

        return self.calculate_fixed_risk(entry_price, stop_loss_price, risk)