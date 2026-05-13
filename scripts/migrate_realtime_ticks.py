"""
Migración para la tabla realtime_ticks.
Ejecutar: python scripts/migrate_realtime_ticks.py
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.core.pegaton_config import get_db_path


def migrate():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
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

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='realtime_ticks'")
    exists = cursor.fetchone()
    conn.close()

    if exists:
        print(f"✅ Tabla realtime_ticks creada/verificada en {db_path}")
    else:
        print("❌ Error: tabla no encontrada después de migración")
        sys.exit(1)


if __name__ == "__main__":
    migrate()
    print("Migración de realtime_ticks completada.")