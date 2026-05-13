"""
Sizing Engine — Cálculo de tamaño de posición.
P0-04: Position Sizing | EP-FR-001
"""
import math
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SizingResult:
    """Resultado de un cálculo de position sizing."""

    def __init__(
        self,
        shares: float = 0.0,
        position_value: float = 0.0,
        risk_amount: float = 0.0,
        stop_loss: Optional[float] = None,
        risk_per_share: Optional[float] = None,
        method: str = "unknown",
        metadata: Optional[Dict] = None,
    ):
        self.shares = shares
        self.position_value = position_value
        self.risk_amount = risk_amount
        self.stop_loss = stop_loss
        self.risk_per_share = risk_per_share
        self.method = method
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return (
            f"SizingResult(method={self.method}, shares={self.shares:.4f}, "
            f"value={self.position_value:.2f}, risk=${self.risk_amount:.2f})"
        )

    @property
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shares": round(self.shares, 6),
            "position_value": round(self.position_value, 2),
            "risk_amount": round(self.risk_amount, 2),
            "stop_loss": self.stop_loss,
            "risk_per_share": self.risk_per_share,
            "method": self.method,
            "metadata": self.metadata,
        }


class PositionSizer:
    """
    Calculadora de tamaño de posición con múltiples métodos.

    Métodos soportados:
      - fixed_risk: Riesgo fijo por operación (% del capital)
      - kelly: Criterio de Kelly para sizing óptimo
      - volatility: Ajustado por volatilidad del activo
      - atr: Basado en ATR (Average True Range)
    """

    def __init__(self, account_balance: float, risk_pct: float = 0.01):
        """
        Args:
            account_balance: Capital total de la cuenta
            risk_pct: Porcentaje del capital a arriesgar por operación (default 1%)
        """
        if account_balance <= 0:
            raise ValueError(f"account_balance debe ser positivo, got {account_balance}")
        if not (0.0 < risk_pct <= 1.0):
            raise ValueError(f"risk_pct debe estar entre 0 y 1, got {risk_pct}")

        self.account_balance = account_balance
        self.risk_pct = risk_pct
        self.max_risk_amount = account_balance * risk_pct

    def calculate_fixed_risk(
        self,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: Optional[float] = None,
    ) -> SizingResult:
        """
        Calcula el tamaño de posición basado en riesgo fijo.

        Args:
            entry_price: Precio de entrada
            stop_loss_price: Precio de stop loss
            risk_pct: Override del riesgo porcentual (opcional)

        Returns:
            SizingResult con el cálculo
        """
        if entry_price <= 0:
            raise ValueError(f"entry_price debe ser positivo, got {entry_price}")
        if stop_loss_price <= 0:
            raise ValueError(f"stop_loss_price debe ser positivo, got {stop_loss_price}")

        risk_amount = self.account_balance * (risk_pct or self.risk_pct)
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            logger.warning("Entry price == stop loss price, riesgo por share = 0")
            shares = 0.0
        else:
            shares = risk_amount / risk_per_share

        position_value = shares * entry_price

        return SizingResult(
            shares=round(shares, 6),
            position_value=round(position_value, 2),
            risk_amount=round(risk_amount, 2),
            stop_loss=stop_loss_price,
            risk_per_share=round(risk_per_share, 6),
            method="fixed_risk",
            metadata={
                "account_balance": self.account_balance,
                "risk_pct": risk_pct or self.risk_pct,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
            },
        )

    def calculate_kelly(
        self,
        wins: int,
        losses: int,
        avg_win: float,
        avg_loss: float,
        max_fraction: float = 0.25,
    ) -> SizingResult:
        """
        Calcula el tamaño de posición usando el Criterio de Kelly.

        Args:
            wins: Número de operaciones ganadoras
            losses: Número de operaciones perdedoras
            avg_win: Ganancia promedio por trade ganador
            avg_loss: Pérdida promedio por trade perdedor (valor positivo)
            max_fraction: Fracción máxima de capital a arriesgar (default 25%)

        Returns:
            SizingResult con el cálculo
        """
        if wins + losses == 0:
            raise ValueError("Se necesitan al menos algunas operaciones (wins + losses > 0)")
        if avg_loss <= 0:
            raise ValueError(f"avg_loss debe ser positivo, got {avg_loss}")

        win_rate = wins / (wins + losses)
        win_loss_ratio = avg_win / avg_loss

        # Kelly formula: f* = (bp - q) / b
        # where b = win/loss ratio, p = win rate, q = loss rate
        kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        kelly_pct = max(0.0, kelly_pct)  # Floor at 0
        kelly_pct = min(kelly_pct, max_fraction)  # Cap at max_fraction

        risk_amount = self.account_balance * kelly_pct
        shares = risk_amount / avg_loss if avg_loss > 0 else 0.0

        return SizingResult(
            shares=round(shares, 6),
            position_value=round(shares * avg_win if avg_win > 0 else risk_amount, 2),
            risk_amount=round(risk_amount, 2),
            method="kelly",
            metadata={
                "account_balance": self.account_balance,
                "win_rate": round(win_rate, 4),
                "win_loss_ratio": round(win_loss_ratio, 4),
                "raw_kelly_pct": round(kelly_pct, 6),
                "capped_kelly_pct": round(kelly_pct, 6),
                "wins": wins,
                "losses": losses,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
            },
        )

    def calculate_volatility_adjusted(
        self,
        asset_volatility: float,
        benchmark_volatility: float,
        base_size_value: float,
    ) -> SizingResult:
        """
        Calcula el tamaño ajustado por volatilidad relativa.

        Args:
            asset_volatility: Volatilidad del activo (std dev de retornos)
            benchmark_volatility: Volatilidad del benchmark de referencia
            base_size_value: Valor base de la posición

        Returns:
            SizingResult con el cálculo
        """
        if benchmark_volatility <= 0:
            raise ValueError(f"benchmark_volatility debe ser positivo, got {benchmark_volatility}")
        if base_size_value <= 0:
            raise ValueError(f"base_size_value debe ser positivo, got {base_size_value}")

        # Ratio de volatilidad: si el activo es más volátil, reducir tamaño
        vol_ratio = asset_volatility / benchmark_volatility if asset_volatility > 0 else 1.0

        # Invertir el ratio: más volatil → posición más pequeña
        vol_adjustment = 1.0 / max(vol_ratio, 0.1)
        adjusted_value = base_size_value * vol_adjustment

        return SizingResult(
            shares=0.0,  # Se necesita precio para calcular shares
            position_value=round(adjusted_value, 2),
            risk_amount=round(base_size_value * self.risk_pct, 2),
            method="volatility",
            metadata={
                "asset_volatility": asset_volatility,
                "benchmark_volatility": benchmark_volatility,
                "vol_ratio": round(vol_ratio, 4),
                "vol_adjustment": round(vol_adjustment, 4),
                "base_size_value": base_size_value,
                "adjusted_value": round(adjusted_value, 2),
            },
        )

    def calculate_atr_position(
        self,
        atr: float,
        entry_price: float,
        risk_pct: Optional[float] = None,
        multiplier: float = 1.5,
    ) -> SizingResult:
        """
        Calcula el tamaño de posición basado en ATR.

        Args:
            atr: Valor actual del ATR
            entry_price: Precio de entrada
            risk_pct: Porcentaje de riesgo (opcional, usa el de la instancia)
            multiplier: Multiplicador del ATR para el stop loss

        Returns:
            SizingResult con el cálculo
        """
        if atr <= 0:
            raise ValueError(f"ATR debe ser positivo, got {atr}")
        if entry_price <= 0:
            raise ValueError(f"entry_price debe ser positivo, got {entry_price}")

        risk_amount = self.account_balance * (risk_pct or self.risk_pct)
        stop_loss_distance = atr * multiplier
        stop_loss_price = entry_price - stop_loss_distance

        if stop_loss_distance == 0:
            shares = 0.0
        else:
            shares = risk_amount / stop_loss_distance

        position_value = shares * entry_price

        return SizingResult(
            shares=round(shares, 6),
            position_value=round(position_value, 2),
            risk_amount=round(risk_amount, 2),
            stop_loss=round(stop_loss_price, 4),
            risk_per_share=round(stop_loss_distance, 6),
            method="atr",
            metadata={
                "atr": atr,
                "entry_price": entry_price,
                "multiplier": multiplier,
                "stop_loss_distance": round(stop_loss_distance, 6),
                "stop_loss_price": round(stop_loss_price, 4),
            },
        )