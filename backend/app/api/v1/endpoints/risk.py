"""
Risk API — Endpoints para position sizing, VaR y drawdown.
P0-04: Position Sizing | EP-FR-001

Endpoints:
  POST /api/v1/risk/size          — calcular tamaño de posición
  GET  /api/v1/risk/var            — VaR paramétrico + histórico + CVaR
  GET  /api/v1/risk/drawdown       — drawdown actual y máximo
  POST /api/v1/risk/correlation    — matriz de correlación
  GET  /api/v1/risk/monitor        — estado del monitor de drawdown
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json

from backend.app.core.risk.sizing import PositionSizer, SizingResult
from backend.app.core.risk.var import (
    calculate_parametric_var,
    calculate_historical_var,
    calculate_cvar,
    calculate_var_summary,
    returns_from_prices,
)
from backend.app.core.risk.correlation import (
    calculate_correlation_matrix,
    diversification_ratio,
    max_concentration_risk,
    correlation_alert,
)
from backend.app.core.risk.drawdown import (
    calculate_max_drawdown,
    current_drawdown,
    drawdown_alert,
    DrawdownMonitor,
)
from backend.app.core.pegaton_config import get_db_path

router = APIRouter(prefix="/risk", tags=["risk"])


# ── Request Models ─────────────────────────────────────────

class SizingRequest(BaseModel):
    account_balance: float = 100_000
    risk_pct: float = 0.01
    entry_price: float
    stop_loss_price: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    atr: Optional[float] = None
    atr_multiplier: float = 1.5
    method: str = "fixed_risk"  # fixed_risk | kelly | volatility | atr
    # Kelly params
    wins: Optional[int] = None
    losses: Optional[int] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    # Volatility adjusted params
    asset_volatility: Optional[float] = None
    benchmark_volatility: Optional[float] = None


class CorrelationRequest(BaseModel):
    assets: Dict[str, List[float]]


# ── DB Helpers ─────────────────────────────────────────────

def _get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            entry_price REAL NOT NULL,
            current_price REAL,
            quantity REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            risk_pct REAL DEFAULT 0.01,
            account_allocation REAL,
            correlation_group TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            portfolio_var_95 REAL,
            portfolio_var_99 REAL,
            portfolio_cvar REAL,
            max_drawdown REAL,
            current_drawdown REAL,
            sharpe_ratio REAL,
            sortino_ratio REAL,
            total_positions INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'warning',
            triggered_at TEXT DEFAULT (datetime('now')),
            dismissed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


# ── Lifecycle ──────────────────────────────────────────────

@router.on_event("startup")
async def startup():
    _ensure_tables()


# ── Endpoints ──────────────────────────────────────────────

@router.post("/size")
async def calculate_position_size(req: SizingRequest):
    """Calcula el tamaño óptimo de posición según el método elegido."""
    try:
        sizer = PositionSizer(
            account_balance=req.account_balance,
            risk_pct=req.risk_pct,
        )

        if req.method == "fixed_risk":
            if req.stop_loss_price is None and req.stop_loss_pct is None:
                raise HTTPException(status_code=400, detail="Se requiere stop_loss_price o stop_loss_pct para fixed_risk")

            stop = req.stop_loss_price
            if stop is None and req.stop_loss_pct is not None:
                stop = req.entry_price * (1 - req.stop_loss_pct)

            result = sizer.calculate_fixed_risk(
                entry_price=req.entry_price,
                stop_loss_price=stop,
                risk_pct=req.risk_pct,
            )

        elif req.method == "kelly":
            if any(v is None for v in [req.wins, req.losses, req.avg_win, req.avg_loss]):
                raise HTTPException(status_code=400, detail="Se requieren wins, losses, avg_win, avg_loss para kelly")
            result = sizer.calculate_kelly(
                wins=req.wins,
                losses=req.losses,
                avg_win=req.avg_win,
                avg_loss=req.avg_loss,
            )

        elif req.method == "volatility":
            if req.asset_volatility is None or req.benchmark_volatility is None:
                raise HTTPException(status_code=400, detail="Se requiere asset_volatility y benchmark_volatility")
            result = sizer.calculate_volatility_adjusted(
                asset_volatility=req.asset_volatility,
                benchmark_volatility=req.benchmark_volatility,
                base_size_value=req.account_balance * req.risk_pct * 10,
            )

        elif req.method == "atr":
            if req.atr is None:
                raise HTTPException(status_code=400, detail="Se requiere atr para método atr")
            result = sizer.calculate_atr_position(
                atr=req.atr,
                entry_price=req.entry_price,
                risk_pct=req.risk_pct,
                multiplier=req.atr_multiplier,
            )

        else:
            raise HTTPException(status_code=400, detail=f"Método desconocido: {req.method}")

        return {"status": "ok", "method": req.method, "result": result.__dict__ if hasattr(result, '__dict__') else result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/var")
async def get_var(
    portfolio_value: float = Query(default=100_000, description="Valor del portafolio"),
    ticker: Optional[str] = Query(None, description="Ticker para usar datos de OHLCV"),
):
    """
    Calcula VaR paramétrico, histórico y CVaR.
    Si se proporciona ticker, lee datos de la DB.
    """
    try:
        if ticker:
            conn = _get_db()
            rows = conn.execute(
                "SELECT close FROM precios_ohlcv WHERE simbolo = ? ORDER BY timestamp ASC",
                (ticker.upper(),)
            ).fetchall()
            conn.close()

            if len(rows) < 2:
                raise HTTPException(status_code=404, detail=f"Datos insuficientes para {ticker}")

            prices = [r["close"] for r in rows]
            returns = returns_from_prices(prices)

            if len(returns) < 2:
                raise HTTPException(status_code=404, detail="Retornos insuficientes")

            var_summary = calculate_var_summary(returns, portfolio_value)
        else:
            # Demo con datos sintéticos
            import random
            random.seed(42)
            demo_returns = [random.gauss(0.0005, 0.02) for _ in range(252)]
            var_summary = calculate_var_summary(demo_returns, portfolio_value)

        return var_summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drawdown")
async def get_drawdown(
    ticker: Optional[str] = Query(None, description="Ticker para calcular drawdown"),
):
    """Calcula el drawdown de la equity o de un ticker específico."""
    try:
        if ticker:
            import pandas as pd
            conn = _get_db()
            rows = conn.execute(
                "SELECT close, timestamp FROM precios_ohlcv WHERE simbolo = ? ORDER BY timestamp ASC",
                (ticker.upper(),)
            ).fetchall()
            conn.close()

            if not rows:
                raise HTTPException(status_code=404, detail=f"No hay datos para {ticker}")

            prices = pd.Series([r["close"] for r in rows])
            # Calcular equity como retorno acumulado normalizado
            returns = prices.pct_change().dropna()
            cum_returns = (1 + returns).cumprod() * 100
            equity_curve = cum_returns.tolist()
        else:
            # Demo
            import random
            random.seed(42)
            equity = 100
            equity_curve = []
            for _ in range(252):
                equity *= 1 + random.gauss(0.0003, 0.015)
                equity_curve.append(equity)

        dd_info = calculate_max_drawdown(equity_curve)
        current_dd = current_drawdown(equity_curve[-1], max(equity_curve[:-1]) if len(equity_curve) > 1 else equity_curve[0])

        return {
            "max_drawdown": dd_info,
            "current_drawdown_pct": current_dd,
            "drawdown_alert": drawdown_alert(current_dd),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correlation")
async def calculate_corr(req: CorrelationRequest):
    """Calcula la matriz de correlación entre activos."""
    try:
        if len(req.assets) < 2:
            raise HTTPException(status_code=400, detail="Se necesitan al menos 2 activos")

        corr_matrix = calculate_correlation_matrix(req.assets)
        alerts = correlation_alert(corr_matrix)

        # Si hay valores numéricos, calcular diversificación
        weights = {}
        n = len(req.assets)
        for ticker in req.assets:
            weights[ticker] = round(1.0 / n, 4)

        cov_matrix = {}
        for t1 in req.assets:
            cov_matrix[t1] = {}
            for t2 in req.assets:
                if t1 == t2:
                    returns = req.assets[t1]
                    var = sum((r - sum(returns)/len(returns))**2 for r in returns) / max(len(returns)-1, 1)
                    cov_matrix[t1][t2] = var
                else:
                    cov_matrix[t1][t2] = corr_matrix.get(t1, {}).get(t2, 0) * 0.01  # placeholder

        div_ratio = diversification_ratio(weights, cov_matrix)
        concentration = max_concentration_risk(weights)

        return {
            "correlation_matrix": corr_matrix,
            "alerts": alerts,
            "diversification_ratio": div_ratio,
            "concentration_risk": concentration,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Estado del monitor ─────────────────────────────────────

_drawdown_monitor = DrawdownMonitor()


@router.get("/monitor")
async def get_monitor_status():
    """Estado del drawdown monitor."""
    return {
        "peak_value": _drawdown_monitor.peak_value,
        "current_value": _drawdown_monitor.current_value,
        "max_allowed_dd": _drawdown_monitor.max_allowed_dd,
        "in_alert": _drawdown_monitor.in_alert,
    }


@router.post("/monitor/update")
async def update_monitor(value: float = Query(..., description="Valor actual de equity")):
    """Actualiza el monitor de drawdown."""
    result = _drawdown_monitor.update(value)
    return result