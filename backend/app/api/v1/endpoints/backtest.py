"""
Backtest API — Endpoints para ejecutar y consultar backtests.
P0-02: Backtesting Engine | EP-FR-001

Endpoints:
  POST /api/v1/backtest/run    — ejecutar backtest
  GET  /api/v1/backtest/{id}   — resultado
  GET  /api/v1/backtest/{id}/equity_curve — curva de equity
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import sqlite3
import json
from uuid import uuid4

from backend.app.core.backtester.engine import BacktestEngine, BacktestResult
from backend.app.core.backtester.strategy import list_strategies, get_strategy
from backend.app.core.pegaton_config import get_db_path

router = APIRouter(prefix="/backtest", tags=["backtest"])


# ── Request models ──────────────────────────────────────────

class BacktestRunRequest(BaseModel):
    strategy: str
    ticker: str
    start_date: str
    end_date: str
    params: Optional[Dict[str, Any]] = None
    mode: str = "vectorized"
    capital: Optional[float] = None


class BacktestListResponse(BaseModel):
    backtests: List[Dict[str, Any]]
    count: int


# ── Helpers ─────────────────────────────────────────────────

def _get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def _store_result(result: BacktestResult):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO backtest_results
            (id, strategy_name, ticker, start_date, end_date,
             metrics, equity_curve, monte_carlo_results, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.backtest_id,
        result.strategy_name,
        result.ticker,
        result.start_date,
        result.end_date,
        json.dumps(result.metrics),
        json.dumps(result.equity_curve),
        json.dumps(result.monte_carlo),
        result.status,
    ))
    conn.commit()
    conn.close()
    return result.backtest_id


def _load_result(bt_id: str) -> BacktestResult:
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM backtest_results WHERE id = ?", (bt_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return BacktestResult(
        backtest_id=row["id"],
        strategy_name=row["strategy_name"],
        ticker=row["ticker"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        metrics=json.loads(row["metrics"] or "{}"),
        equity_curve=json.loads(row["equity_curve"] or "[]"),
        monte_carlo=json.loads(row["monte_carlo_results"] or "{}"),
        status=row["status"],
    )


# ── Migración automática ───────────────────────────────────

def _ensure_tables():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id TEXT PRIMARY KEY,
            strategy_name TEXT NOT NULL,
            ticker TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            metrics JSON NOT NULL DEFAULT '{}',
            equity_curve JSON,
            monte_carlo_results JSON,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


# ── Lifecycle hook ──────────────────────────────────────────

@router.on_event("startup")
async def startup():
    _ensure_tables()


# ── Endpoints ───────────────────────────────────────────────

@router.post("/run")
async def run_backtest(req: BacktestRunRequest):
    """Ejecuta un backtest con la estrategia y datos solicitados."""
    try:
        engine = BacktestEngine()
        # Cargar datos de OHLCV desde DB
        import pandas as pd
        conn = _get_db()
        cursor = conn.execute(
            "SELECT * FROM precios_ohlcv WHERE simbolo = ? ORDER BY timestamp ASC",
            (req.ticker.upper(),)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No hay datos OHLCV para {req.ticker}")

        df = pd.DataFrame([dict(r) for r in rows])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        result = engine.run(
            strategy_name=req.strategy,
            data=df,
            start_date=req.start_date,
            end_date=req.end_date,
            params=req.params,
            mode=req.mode,
            capital=req.capital,
        )

        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error)

        _store_result(result)

        return {
            "backtest_id": result.backtest_id,
            "status": "completed",
            "metrics": result.metrics,
            "trades_count": len(result.trades),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{bt_id}")
async def get_backtest(bt_id: str):
    """Obtiene el resultado de un backtest por ID."""
    result = _load_result(bt_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Backtest {bt_id} no encontrado")
    return {
        "backtest_id": result.backtest_id,
        "strategy": result.strategy_name,
        "ticker": result.ticker,
        "dates": {"start": result.start_date, "end": result.end_date},
        "metrics": result.metrics,
        "trades_count": len(result.trades),
        "monte_carlo": result.monte_carlo,
    }


@router.get("/result/{bt_id}/equity_curve")
async def get_equity_curve(bt_id: str):
    """Obtiene la curva de equity de un backtest."""
    result = _load_result(bt_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Backtest {bt_id} no encontrado")
    return {
        "backtest_id": result.backtest_id,
        "points": result.equity_curve,
    }


@router.get("/strategies")
async def list_backtest_strategies():
    """Lista todas las estrategias disponibles."""
    return {"strategies": list_strategies()}