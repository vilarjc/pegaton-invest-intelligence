"""
DB Writer — Escribe ticks en SQLite con batching.
P0-01: Real-time Data Feed | EP-FR-001

- Batch insert cada 100ms o 50 mensajes (lo primero que ocurra)
- TTL: 30 días rolling window
- Buffer máximo: 10,000 ticks en RAM
"""
import asyncio
import logging
import time
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from backend.app.core.pegaton_config import get_db_path

logger = logging.getLogger(__name__)


class DBWriter:
    """Escribe ticks en la base de datos con batching y TTL automático."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        batch_interval: float = 0.1,  # 100ms
        batch_size: int = 50,
        ttl_days: int = 30,
        max_buffer: int = 10_000,
    ):
        self.db_path = db_path or get_db_path()
        self.batch_interval = batch_interval
        self.batch_size = batch_size
        self.ttl_days = ttl_days
        self.max_buffer = max_buffer

        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._last_flush = time.monotonic()
        self._total_inserted = 0

    async def start(self) -> None:
        """Inicia el writer y el flush periódico."""
        self._running = True
        self._ensure_table()
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("DBWriter iniciado")

    async def stop(self) -> None:
        """Detiene el writer y hace flush final."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        await self.flush()
        logger.info(f"DBWriter detenido. Total insertados: {self._total_inserted}")

    async def write_tick(self, tick: Dict[str, Any]) -> bool:
        """Añade un tick al buffer."""
        async with self._lock:
            if len(self._buffer) >= self.max_buffer:
                logger.warning("Buffer lleno, descartando tick más viejo")
                self._buffer.pop(0)

            self._buffer.append({
                "ticker": tick.get("ticker", ""),
                "timestamp": tick.get("timestamp", ""),
                "price": tick.get("price"),
                "volume": tick.get("volume"),
                "bid": tick.get("bid"),
                "ask": tick.get("ask"),
                "source": tick.get("source", ""),
            })

        # Flush si alcanza el tamaño de batch
        if len(self._buffer) >= self.batch_size:
            await self.flush()
            return True
        return False

    async def write_batch(self, ticks: List[Dict[str, Any]]) -> int:
        """Escribe un lote de ticks."""
        count = 0
        async with self._lock:
            for tick in ticks:
                if len(self._buffer) >= self.max_buffer:
                    logger.warning("Buffer lleno, pausando escritura")
                    break
                self._buffer.append({
                    "ticker": tick.get("ticker", ""),
                    "timestamp": tick.get("timestamp", ""),
                    "price": tick.get("price"),
                    "volume": tick.get("volume"),
                    "bid": tick.get("bid"),
                    "ask": tick.get("ask"),
                    "source": tick.get("source", ""),
                })
                count += 1

        if len(self._buffer) >= self.batch_size:
            await self.flush()

        return count

    async def flush(self) -> int:
        """Escribe el buffer a la DB y lo limpia."""
        async with self._lock:
            if not self._buffer:
                return 0
            batch = self._buffer.copy()
            self._buffer.clear()

        inserted = self._insert_batch(batch)
        self._total_inserted += inserted
        self._last_flush = time.monotonic()

        # Limpiar datos viejos
        self._purge_old()

        return inserted

    async def _periodic_flush(self) -> None:
        """Flush periódico basado en intervalo de tiempo."""
        try:
            while self._running:
                await asyncio.sleep(self.batch_interval)
                if self._buffer and (time.monotonic() - self._last_flush) >= self.batch_interval:
                    await self.flush()
        except asyncio.CancelledError:
            pass

    def _insert_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Inserta un batch en la DB usando conexión sincrónica (ejecutado en thread)."""
        if not batch:
            return 0

        loop = asyncio.new_event_loop()
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.executemany(
                """
                INSERT INTO realtime_ticks (ticker, timestamp, price, volume, bid, ask, source)
                VALUES (:ticker, :timestamp, :price, :volume, :bid, :ask, :source)
                """,
                batch,
            )
            conn.commit()
            inserted = cursor.rowcount
            conn.close()
            return inserted
        except sqlite3.Error as e:
            logger.error(f"Error insertando batch en DB: {e}")
            return 0
        finally:
            loop.close()

    def _ensure_table(self) -> None:
        """Crea la tabla si no existe."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS realtime_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                source TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rt_ticker_ts
            ON realtime_ticks(ticker, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rt_source
            ON realtime_ticks(source)
        """)
        conn.commit()
        conn.close()
        logger.info("Tabla realtime_ticks verificada/creada")

    def _purge_old(self) -> None:
        """Elimina datos más viejos que el TTL."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=self.ttl_days)).isoformat()
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM realtime_ticks WHERE timestamp < ?", (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted > 0:
                logger.info(f"Purge: {deleted} ticks viejos eliminados")
        except sqlite3.Error as e:
            logger.error(f"Error en purge: {e}")

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    @property
    def total_inserted(self) -> int:
        return self._total_inserted