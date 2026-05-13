"""
WebSocket Manager — Gestiona conexiones a fuentes externas de datos en tiempo real.
P0-01: Real-time Data Feed | EP-FR-001
"""
import asyncio
import json
import logging
import time
import random
from datetime import datetime, timezone
from typing import Optional, Set, Dict, List, Callable

import websockets

from backend.app.core.realtime.handler import MessageHandler

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Gestiona conexiones WebSocket a fuentes de datos financieros.
    - Conexión a múltiples fuentes (Yahoo Finance, Finnhub)
    - Reconexión automática con exponential backoff
    - Suscripción/desuscripción dinámica de tickers
    """

    def __init__(
        self,
        sources: Optional[Dict[str, dict]] = None,
        on_message: Optional[Callable] = None,
        max_buffer: int = 10_000,
    ):
        self.sources = sources or {
            "finnhub": {
                "url": "wss://ws.finnhub.io",
                "type": "finnhub",
            },
        }
        self.on_message = on_message
        self.max_buffer = max_buffer
        self.handler = MessageHandler()

        # Estado
        self._connections: Dict[str, dict] = {}
        self._subscribed_tickers: Set[str] = set()
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._reconnect_attempts: Dict[str, int] = {}

        # Backoff config
        self._backoff_base = 1.0
        self._backoff_max = 60.0
        self._backoff_jitter = 0.1

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def connected_sources(self) -> List[str]:
        return [
            name for name, conn in self._connections.items()
            if conn.get("websocket") and not conn["websocket"].closed
        ]

    def subscribe(self, ticker: str) -> bool:
        """Añade un ticker a la lista de suscripción."""
        self._subscribed_tickers.add(ticker.upper())
        logger.info(f"Suscrito a {ticker}")
        return True

    def unsubscribe(self, ticker: str) -> bool:
        """Elimina un ticker de la lista de suscripción."""
        self._subscribed_tickers.discard(ticker.upper())
        logger.info(f"Eliminada suscripción a {ticker}")
        return True

    def get_subscribed_tickers(self) -> Set[str]:
        return self._subscribed_tickers.copy()

    async def connect(self, source_name: str = "all") -> bool:
        """Conecta a una o todas las fuentes WebSocket."""
        if source_name == "all":
            for name in self.sources:
                await self._connect_source(name)
        elif source_name in self.sources:
            await self._connect_source(source_name)
        else:
            logger.warning(f"Fuente desconocida: {source_name}")
            return False
        return True

    async def _connect_source(self, source_name: str) -> bool:
        """Conecta a una fuente específica."""
        source = self.sources[source_name]
        url = source["url"]
        source_type = source["type"]

        try:
            websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connections[source_name] = {
                "websocket": websocket,
                "type": source_type,
                "connected_at": datetime.now(timezone.utc),
                "last_message": None,
            }
            self._reconnect_attempts[source_name] = 0
            logger.info(f"Conectado a {source_name} ({source_type})")

            # Iniciar tarea de escucha
            self._tasks[source_name] = asyncio.create_task(
                self._listen(source_name, websocket)
            )
            return True

        except Exception as e:
            logger.error(f"Error conectando a {source_name}: {e}")
            self._schedule_reconnect(source_name)
            return False

    async def _listen(self, source_name: str, websocket) -> None:
        """Escucha mensajes de una fuente WebSocket."""
        try:
            async for message in websocket:
                if not self._running:
                    break
                await self._process_message(source_name, message)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Conexión cerrada con {source_name}: {e}")
        except Exception as e:
            logger.error(f"Error en escucha de {source_name}: {e}")
        finally:
            if self._running:
                self._schedule_reconnect(source_name)

    async def _process_message(self, source_name: str, raw_message: str) -> None:
        """Procesa un mensaje crudo y lo normaliza."""
        try:
            data = json.loads(raw_message)
            source_type = self._connections[source_name]["type"]
            normalized = self.handler.normalize(data, source_type)

            if normalized and self.on_message:
                await self.on_message(normalized)

            # Actualizar último mensaje
            self._connections[source_name]["last_message"] = datetime.now(timezone.utc)

        except json.JSONDecodeError:
            logger.debug(f"Mensaje no JSON de {source_name}: {raw_message[:100]}")
        except Exception as e:
            logger.error(f"Error procesando mensaje de {source_name}: {e}")

    def _schedule_reconnect(self, source_name: str) -> None:
        """Programa reconexión con exponential backoff."""
        attempts = self._reconnect_attempts.get(source_name, 0)
        delay = min(
            self._backoff_base * (2 ** attempts) + random.uniform(0, self._backoff_jitter),
            self._backoff_max,
        )
        self._reconnect_attempts[source_name] = attempts + 1
        logger.info(f"Reconexión a {source_name} en {delay:.1f}s (intento {attempts + 1})")

        async def _reconnect():
            await asyncio.sleep(delay)
            if self._running:
                await self._connect_source(source_name)

        self._tasks[f"{source_name}_reconnect"] = asyncio.create_task(_reconnect())

    async def disconnect(self, source_name: str = "all") -> None:
        """Desconecta de una o todas las fuentes."""
        if source_name == "all":
            for name in list(self._connections.keys()):
                await self._disconnect_source(name)
        elif source_name in self._connections:
            await self._disconnect_source(source_name)

    async def _disconnect_source(self, source_name: str) -> None:
        """Desconecta de una fuente específica."""
        conn = self._connections.get(source_name)
        if conn and conn.get("websocket"):
            try:
                await conn["websocket"].close()
            except Exception:
                pass
        if source_name in self._tasks:
            self._tasks[source_name].cancel()
        self._connections.pop(source_name, None)
        logger.info(f"Desconectado de {source_name}")

    async def start(self) -> None:
        """Inicia el manager y todas las conexiones."""
        self._running = True
        self._reconnect_attempts.clear()
        logger.info("WebSocketManager iniciado")
        await self.connect("all")

    async def stop(self) -> None:
        """Detiene todas las conexiones y tareas."""
        self._running = False
        # Cancelar todas las tareas
        for task in self._tasks.values():
            task.cancel()
        await self.disconnect("all")
        self._tasks.clear()
        logger.info("WebSocketManager detenido")