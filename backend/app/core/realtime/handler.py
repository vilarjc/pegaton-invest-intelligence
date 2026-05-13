"""
Message Handler — Parsea y normaliza mensajes de fuentes WebSocket.
P0-01: Real-time Data Feed | EP-FR-001

Schema de salida unificado:
{
    "ticker": "AAPL",
    "timestamp": "2026-05-13T20:30:00.000Z",
    "price": 189.42,
    "volume": 15234,
    "bid": 189.40,
    "ask": 189.44,
    "source": "yahoo|finnhub|polygon"
}
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Parsea mensajes crudos de distintas fuentes WS y los normaliza
    al schema unificado de Pegaton.
    """

    def normalize(self, data: Any, source_type: str) -> Optional[Dict[str, Any]]:
        """Normaliza un mensaje crudo al schema unificado."""
        try:
            if source_type == "finnhub":
                return self._parse_finnhub(data)
            elif source_type == "yahoo":
                return self._parse_yahoo(data)
            elif source_type == "polygon":
                return self._parse_polygon(data)
            else:
                logger.warning(f"Tipo de fuente desconocido: {source_type}")
                return None
        except Exception as e:
            logger.error(f"Error normalizando mensaje: {e}")
            return None

    def _parse_finnhub(self, data: dict) -> Optional[Dict[str, Any]]:
        """
        Parsea mensajes de Finnhub WebSocket.
        Formato: {"data": [{"s": "AAPL", "p": 189.42, "v": 15234, "t": 1684000000, ...}], "type": "trade"}
        """
        if not isinstance(data, dict):
            return None

        data_type = data.get("type", "")

        # Tipo 'trade' — datos de trades en tiempo real
        if data_type == "trade":
            trades = data.get("data", [])
            if not trades:
                return None
            # Retornar el último trade como representación del tick actual
            t = trades[-1]
            return {
                "ticker": t.get("s", ""),
                "timestamp": self._ts_to_iso(t.get("t", 0)),
                "price": t.get("p"),
                "volume": t.get("v"),
                "bid": t.get("bp"),
                "ask": t.get("ap"),
                "source": "finnhub",
            }

        # Tipo 'quote' — datos de libro de órdenes
        elif data_type == "quote":
            d = data.get("data", {})
            if not d:
                return None
            return {
                "ticker": d.get("s", ""),
                "timestamp": self._ts_to_iso(d.get("t", 0)),
                "price": d.get("p"),
                "volume": d.get("v"),
                "bid": d.get("bp"),
                "ask": d.get("ap"),
                "source": "finnhub",
            }

        return None

    def _parse_yahoo(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Parsea mensajes de Yahoo Finance WebSocket.
        Yahoo envía cadenas con formato: quoteDataEvents~{"symbol":"AAPL","price":...}
        """
        try:
            if isinstance(data, str):
                # Limpiar prefijo de Yahoo
                if "~" in data:
                    data = data.split("~", 1)[1]
                data = json.loads(data)

            if isinstance(data, list):
                # Yahoo a veces envía arrays
                if not data:
                    return None
                data = data[0]

            if not isinstance(data, dict):
                return None

            return {
                "ticker": data.get("symbol", data.get("s", "")),
                "timestamp": self._ts_to_iso(data.get("timestamp", data.get("t", 0))),
                "price": data.get("price", data.get("p")),
                "volume": data.get("volume", data.get("v")),
                "bid": data.get("bid"),
                "ask": data.get("ask"),
                "source": "yahoo",
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _parse_polygon(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Parsea mensajes de Polygon.io WebSocket.
        """
        try:
            if isinstance(data, str):
                data = json.loads(data)

            if not isinstance(data, dict):
                return None

            ev = data.get("ev", "")

            # Trade event
            if ev == "T":
                return {
                    "ticker": data.get("sym", ""),
                    "timestamp": self._ts_to_iso(data.get("t", 0)),
                    "price": data.get("p"),
                    "volume": data.get("s"),
                    "bid": data.get("bp"),
                    "ask": data.get("ap"),
                    "source": "polygon",
                }

            # Quote event
            elif ev == "Q":
                return {
                    "ticker": data.get("sym", ""),
                    "timestamp": self._ts_to_iso(data.get("t", 0)),
                    "price": data.get("p"),
                    "volume": data.get("s"),
                    "bid": data.get("bidPrice"),
                    "ask": data.get("askPrice"),
                    "source": "polygon",
                }

            return None
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    @staticmethod
    def _ts_to_iso(ts) -> str:
        """Convierte timestamp a ISO 8601 string."""
        if ts is None or ts == 0:
            return datetime.now(timezone.utc).isoformat()
        # Puede venir en ms o segundos
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return datetime.now(timezone.utc).isoformat()

    def batch_normalize(self, messages: List[Any], source_type: str) -> List[Dict[str, Any]]:
        """Normaliza un lote de mensajes."""
        results = []
        for msg in messages:
            normalized = self.normalize(msg, source_type)
            if normalized:
                results.append(normalized)
        return results