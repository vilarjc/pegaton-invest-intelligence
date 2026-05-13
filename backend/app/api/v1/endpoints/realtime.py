"""
Realtime API — WebSocket data feed endpoints.
P0-01: Real-time Data Feed | EP-FR-001

Endpoints:
  GET  /api/v1/realtime/{ticker}         — último tick disponible
  GET  /api/v1/realtime/{ticker}/history — últimos N ticks (default 100, max 1000)
  WS   /ws/ticker/{ticker}               — stream WebSocket al cliente
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
import sqlite3
import json
import logging

from backend.app.core.realtime.db_writer import DBWriter
from backend.app.core.realtime.ws_manager import WebSocketManager
from backend.app.core.realtime.handler import MessageHandler
from backend.app.core.pegaton_config import get_db_path

router = APIRouter(prefix="/realtime", tags=["realtime"])

logger = logging.getLogger(__name__)

# Shared instances (singleton pattern for the app lifecycle)
_ws_manager: Optional[WebSocketManager] = None
_db_writer: Optional[DBWriter] = None
_message_handler: Optional[MessageHandler] = None
_active_ws_connections: List[WebSocket] = []


def _get_db_writer() -> DBWriter:
    global _db_writer
    if _db_writer is None:
        _db_writer = DBWriter(db_path=get_db_path())
    return _db_writer


def _get_ws_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager(
            on_message=_on_tick_received,
        )
    return _ws_manager


def _get_handler() -> MessageHandler:
    global _message_handler
    if _message_handler is None:
        _message_handler = MessageHandler()
    return _message_handler


async def _on_tick_received(tick: Dict):
    """Callback cuando se recibe un tick normalizado."""
    writer = _get_db_writer()
    await writer.write_tick(tick)

    # Forward a todos los clientes WebSocket suscritos
    disconnected = []
    for ws in _active_ws_connections:
        try:
            await ws.send_json({
                "ticker": tick.get("ticker"),
                "price": tick.get("price"),
                "volume": tick.get("volume"),
                "bid": tick.get("bid"),
                "ask": tick.get("ask"),
                "timestamp": tick.get("timestamp"),
                "source": tick.get("source"),
            })
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _active_ws_connections.remove(ws)


@router.on_event("startup")
async def startup_event():
    """Inicia el WebSocketManager y DBWriter al levantar la app."""
    writer = _get_db_writer()
    await writer.start()

    manager = _get_ws_manager()
    # Suscribir tickers por defecto (se pueden agregar vía API)
    manager.subscribe("AAPL")
    manager.subscribe("MSFT")
    manager.subscribe("GOOGL")
    manager.subscribe("TSLA")
    await manager.start()
    logger.info("Realtime service iniciado")


@router.on_event("shutdown")
async def shutdown_event():
    """Detiene servicios al apagar la app."""
    manager = _get_ws_manager()
    await manager.stop()

    writer = _get_db_writer()
    await writer.stop()
    logger.info("Realtime service detenido")


# ── REST Endpoints ──────────────────────────────────────────────

@router.get("/{ticker}")
async def get_last_tick(
    ticker: str,
    hours: int = Query(default=24, description="Horas de lookback para 404"),
):
    """
    GET /api/v1/realtime/{ticker}
    Retorna el último tick disponible para el ticker.
    404 si no hay datos en las últimas `hours` horas.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    lookback = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    cursor.execute(
        """
        SELECT ticker, timestamp, price, volume, bid, ask, source, created_at
        FROM realtime_ticks
        WHERE ticker = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (ticker.upper(), lookback),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos para {ticker} en las últimas {hours}h",
        )

    return dict(row)


@router.get("/{ticker}/history")
async def get_tick_history(
    ticker: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Número de ticks (1-1000)"),
    from_ts: Optional[str] = Query(None, description="Timestamp ISO inicio"),
    to_ts: Optional[str] = Query(None, description="Timestamp ISO fin"),
):
    """
    GET /api/v1/realtime/{ticker}/history
    Retorna los últimos N ticks o rango de tiempo.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT ticker, timestamp, price, volume, bid, ask, source, created_at
        FROM realtime_ticks
        WHERE ticker = ?
    """
    params: list = [ticker.upper()]

    if from_ts:
        query += " AND timestamp >= ?"
        params.append(from_ts)
    if to_ts:
        query += " AND timestamp <= ?"
        params.append(to_ts)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    ticks = [dict(row) for row in rows]
    # Revertir para orden cronológico
    ticks.reverse()

    return {
        "ticker": ticker.upper(),
        "count": len(ticks),
        "ticks": ticks,
    }


@router.get("/status")
async def get_realtime_status():
    """Estado del servicio WebSocket."""
    manager = _get_ws_manager()
    return {
        "running": manager.is_running,
        "connected_sources": manager.connected_sources,
        "subscribed_tickers": list(manager.get_subscribed_tickers()),
        "buffer_size": _get_db_writer().buffer_size,
    }


# ── WebSocket Endpoint ─────────────────────────────────────────

@router.websocket("/ws/ticker/{ticker}")
async def websocket_ticker(websocket: WebSocket, ticker: str):
    """
    WS /ws/ticker/{ticker}
    Stream WebSocket con ticks en tiempo real para un ticker.
    """
    await websocket.accept()
    _active_ws_connections.append(websocket)
    logger.info(f"Cliente WS conectado para {ticker.upper()}")

    # Subscribir al ticker
    manager = _get_ws_manager()
    manager.subscribe(ticker.upper())

    try:
        while True:
            # Mantener conexión viva; los ticks se envían via _on_tick_received
            data = await websocket.receive_text()
            # Se permiten comandos simples del cliente
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_json({"action": "pong"})
                elif msg.get("action") == "subscribe":
                    manager.subscribe(msg["ticker"])
                    await websocket.send_json({"action": "subscribed", "ticker": msg["ticker"]})
                elif msg.get("action") == "unsubscribe":
                    manager.unsubscribe(msg["ticker"])
                    await websocket.send_json({"action": "unsubscribed", "ticker": msg["ticker"]})
            except (json.JSONDecodeError, KeyError):
                pass  # Ignorar mensajes no JSON (keepalive)
    except WebSocketDisconnect:
        _active_ws_connections.remove(websocket)
        logger.info(f"Cliente WS desconectado para {ticker.upper()}")
    except Exception as e:
        logger.error(f"Error en WebSocket para {ticker}: {e}")
        if websocket in _active_ws_connections:
            _active_ws_connections.remove(websocket)