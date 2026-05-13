"""
Backtest Engine — Ejecuta backtests con modo vectorizado y event-driven.
P0-02: Backtesting Engine | EP-FR-001
"""
import uuid
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from backend.app.core.backtester.strategy import Strategy, get_strategy
from backend.app.core.backtester.metrics import calculate_metrics
from backend.app.core.backtester.monte_carlo import MonteCarloSimulator

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    direction: str  # "long" or "short"


@dataclass
class BacktestResult:
    backtest_id: str
    strategy_name: str
    ticker: str
    start_date: str
    end_date: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    trades: List[Dict] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    monte_carlo: Dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
    error: Optional[str] = None


class BacktestEngine:
    """
    Motor de backtesting que soporta:
    - Modo vectorizado (rápido, para análisis exploratorio)
    - Modo event-driven (tick-by-tick, para simulación realista)
    - Walk-forward analysis
    - Simulación Monte Carlo
    """

    def __init__(self, initial_capital: float = 100_000.0, commission: float = 0.001, slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.results: Dict[str, BacktestResult] = {}

    def run(
        self,
        strategy_name: str,
        data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        mode: str = "vectorized",
        capital: Optional[float] = None,
    ) -> BacktestResult:
        """
        Ejecuta un backtest completo.

        Args:
            strategy_name: Nombre de la estrategia registrada
            data: DataFrame con columnas OHLCV + volume
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)
            params: Parámetros para la estrategia
            mode: "vectorized" o "event_driven"
            capital: Capital inicial (usa default si None)

        Returns:
            BacktestResult con métricas, trades y equity curve
        """
        bt_id = f"bt_{uuid.uuid4().hex[:12]}"
        capital = capital or self.initial_capital

        try:
            # Filtrar datos por fecha
            df = self._filter_data(data, start_date, end_date)
            if len(df) < 30:
                raise ValueError(f"Datos insuficientes: {len(df)} filas (mínimo 30)")

            # Obtener estrategia
            strategy = get_strategy(strategy_name)
            if params:
                strategy.initialize(df, params)

            # Generar señales
            df = strategy.generate_signals(df)

            # Ejecutar backtest según modo
            if mode == "vectorized":
                result = self._run_vectorized(bt_id, strategy_name, df, capital)
            else:
                result = self._run_event_driven(bt_id, strategy_name, df, capital)

            logger.info(f"Backtest {bt_id} completado: {result.metrics.get('total_return', 0):.2f}% return")
            return result

        except Exception as e:
            logger.error(f"Error en backtest {bt_id}: {e}", exc_info=True)
            return BacktestResult(
                backtest_id=bt_id,
                strategy_name=strategy_name,
                ticker="",
                start_date=start_date or "",
                end_date=end_date or "",
                status="error",
                error=str(e),
            )

    def walk_forward(
        self,
        strategy_name: str,
        data: pd.DataFrame,
        window: int = 252,
        step: int = 63,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[BacktestResult]:
        """
        Walk-forward analysis: ejecuta backtests en ventanas deslizantes.

        Args:
            window: Tamaño de ventana en días (default 252 = 1 año)
            step: Paso entre ventanas en días (default 63 = 1 trimestre)
        """
        results = []
        dates = data.index.sort_values()

        for start_idx in range(0, len(dates) - window, step):
            end_idx = min(start_idx + window, len(dates))
            window_data = data.loc[dates[start_idx]:dates[end_idx]]

            if len(window_data) < 30:
                continue

            bt = self.run(strategy_name, window_data, params=params)
            results.append(bt)

        logger.info(f"Walk-forward completado: {len(results)} ventanas analizadas")
        return results

    def _run_vectorized(self, bt_id: str, strategy_name: str, df: pd.DataFrame, capital: float) -> BacktestResult:
        """Ejecuta backtest en modo vectorizado (rápido)."""
        ticker = "N/A"
        if "ticker" in df.columns:
            ticker = df["ticker"].iloc[0] if not df["ticker"].empty else "N/A"

        positions = []
        in_position = False
        entry_price = 0.0
        entry_date = ""
        equity = capital
        equity_curve = [{"date": df.index[0].isoformat(), "value": capital}]
        trades = []

        signals = df[df["signal"] != 0].copy()

        for idx, row in signals.iterrows():
            date_str = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
            price = row["close"]
            signal = row["signal"]

            if signal == 1 and not in_position:  # Compra
                in_position = True
                entry_price = price * (1 + self.slippage)
                entry_date = date_str
                shares = capital / entry_price
                cost = capital * self.commission
                equity -= cost

            elif signal == -1 and in_position:  # Venta
                in_position = False
                exit_price = price * (1 - self.slippage)
                pnl = (exit_price - entry_price) * shares
                pnl_pct = (exit_price / entry_price - 1) * 100
                equity += pnl
                equity -= equity * self.commission

                trades.append(Trade(
                    entry_date=entry_date,
                    exit_date=date_str,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=shares,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    direction="long",
                ))

                entry_price = 0.0
                entry_date = ""

            equity_curve.append({"date": date_str, "value": round(equity, 2)})

        # Cerrar posición abierta al final
        final_equity = equity
        if in_position and entry_price > 0:
            final_price = df["close"].iloc[-1]
            pnl = (final_price - entry_price) * shares
            final_equity += pnl
            trades.append(Trade(
                entry_date=entry_date,
                exit_date=df.index[-1].isoformat() if hasattr(df.index[-1], "isoformat") else str(df.index[-1]),
                entry_price=entry_price,
                exit_price=final_price,
                quantity=shares,
                pnl=pnl,
                pnl_pct=(final_price / entry_price - 1) * 100,
                direction="long",
            ))

        total_return = (final_equity / capital - 1) * 100
        metrics = calculate_metrics([t.pnl_pct for t in trades])
        metrics["total_return"] = total_return
        metrics["final_equity"] = round(final_equity, 2)
        metrics["num_trades"] = len(trades)

        # Monte Carlo
        if trades:
            returns = [t.pnl_pct / 100 for t in trades]
            mc = MonteCarloSimulator().simulate(returns)
        else:
            mc = {"error": "No trades to simulate"}

        return BacktestResult(
            backtest_id=bt_id,
            strategy_name=strategy_name,
            ticker=ticker,
            start_date=str(df.index[0])[:10] if hasattr(df.index[0], "__str__") else str(df.index[0])[:10],
            end_date=str(df.index[-1])[:10] if hasattr(df.index[-1], "__str__") else str(df.index[-1])[:10],
            metrics=metrics,
            trades=[self._trade_to_dict(t) for t in trades],
            equity_curve=equity_curve,
            monte_carlo=mc,
        )

    def _run_event_driven(self, bt_id: str, strategy_name: str, df: pd.DataFrame, capital: float) -> BacktestResult:
        """Ejecuta backtest en modo event-driven (tick-by-tick, más realista)."""
        ticker = "N/A"
        if "ticker" in df.columns:
            ticker = df["ticker"].iloc[0] if not df["ticker"].empty else "N/A"

        df = df.sort_index()
        shares = 0.0
        entry_price = 0.0
        equity = capital
        position = None
        trades = []
        equity_curve = [{"date": df.index[0].isoformat() if hasattr(df.index[0], "isoformat") else str(df.index[0]), "value": capital}]

        prev_signal = 0

        for idx, row in df.iterrows():
            date_str = idx.isoformat() if hasattr(idx, "isoformat") else str(idx)
            price = row["close"]
            signal = int(row.get("signal", 0))

            # Transición de señal
            if signal == 1 and prev_signal != 1 and position is None:
                # Abrir long
                entry_price = price * (1 + self.slippage)
                shares = equity / entry_price
                equity -= equity * self.commission
                position = {"entry": entry_price, "shares": shares, "date": date_str}

            elif signal == -1 and position is not None:
                # Cerrar long
                exit_price = price * (1 - self.slippage)
                pnl = (exit_price - position["entry"]) * position["shares"]
                equity += pnl
                equity -= equity * self.commission
                trades.append(Trade(
                    entry_date=position["date"],
                    exit_date=date_str,
                    entry_price=position["entry"],
                    exit_price=exit_price,
                    quantity=position["shares"],
                    pnl=pnl,
                    pnl_pct=(exit_price / position["entry"] - 1) * 100,
                    direction="long",
                ))
                position = None

            prev_signal = signal

            if len(equity_curve) == 0 or date_str != equity_curve[-1]["date"]:
                equity_curve.append({"date": date_str, "value": round(equity, 2)})

        # Cerrar posición abierta al final
        if position:
            final_price = df["close"].iloc[-1]
            pnl = (final_price - position["entry"]) * position["shares"]
            equity += pnl
            trades.append(Trade(
                entry_date=position["date"],
                exit_date=str(df.index[-1])[:10],
                entry_price=position["entry"],
                exit_price=final_price,
                quantity=position["shares"],
                pnl=pnl,
                pnl_pct=(final_price / position["entry"] - 1) * 100,
                direction="long",
            ))

        total_return = (equity / capital - 1) * 100
        metrics = calculate_metrics([t.pnl_pct for t in trades])
        metrics["total_return"] = total_return
        metrics["final_equity"] = round(equity, 2)
        metrics["num_trades"] = len(trades)

        if trades:
            returns = [t.pnl_pct / 100 for t in trades]
            mc = MonteCarloSimulator().simulate(returns)
        else:
            mc = {"error": "No trades to simulate"}

        return BacktestResult(
            backtest_id=bt_id,
            strategy_name=strategy_name,
            ticker=ticker,
            start_date=str(df.index[0])[:10],
            end_date=str(df.index[-1])[:10],
            metrics=metrics,
            trades=[self._trade_to_dict(t) for t in trades],
            equity_curve=equity_curve,
            monte_carlo=mc,
        )

    def _filter_data(self, data: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
        df = data.copy()
        df.index = pd.to_datetime(df.index)
        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
        return df

    @staticmethod
    def _trade_to_dict(trade: Trade) -> Dict[str, Any]:
        return {
            "entry_date": trade.entry_date,
            "exit_date": trade.exit_date,
            "entry_price": round(trade.entry_price, 4),
            "exit_price": round(trade.exit_price, 4),
            "quantity": round(trade.quantity, 2),
            "pnl": round(trade.pnl, 2),
            "pnl_pct": round(trade.pnl_pct, 2),
            "direction": trade.direction,
        }


# Singleton global
_engine: Optional[BacktestEngine] = None


def get_engine() -> BacktestEngine:
    global _engine
    if _engine is None:
        _engine = BacktestEngine()
    return _engine