#!/usr/bin/env python3
"""Migration script: creates pegaton.db with all required tables."""
import sqlite3
import os, random

DB_PATH = "/root/pegaton_invest_intelligence/data/pegaton.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Precios OHLCV ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS precios_ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        simbolo TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        UNIQUE(simbolo, timestamp)
    )
""")

# ── Indicadores macro ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS indicadores_macro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        valor REAL,
        cambio_pct REAL DEFAULT 0,
        direccion TEXT DEFAULT 'neutral',
        fecha TEXT,
        score REAL DEFAULT 50
    )
""")

# ── Indicadores técnicos ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS indicadores_tecnicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        simbolo TEXT NOT NULL,
        indicador TEXT NOT NULL,
        valor REAL,
        direccion TEXT DEFAULT 'neutral',
        score REAL DEFAULT 50,
        fecha TEXT,
        UNIQUE(simbolo, indicador, fecha)
    )
""")

# ── Realtime ticks ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS realtime_ticks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        simbolo TEXT NOT NULL,
        tipo TEXT DEFAULT 'trade',
        precio REAL,
        cantidad REAL,
        timestamp TEXT NOT NULL,
        fecha_ms INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    )
""")

# ── Backtest results ──
cursor.execute("""
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

# ── Alert rules ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_rules (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        conditions_json TEXT NOT NULL DEFAULT '[]',
        actions_json TEXT NOT NULL DEFAULT '[]',
        cooldown_minutes INTEGER DEFAULT 60,
        last_triggered TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
""")

# ── Alert history ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT NOT NULL,
        triggered_at TEXT NOT NULL,
        condition_met TEXT NOT NULL,
        actual_value REAL,
        message TEXT,
        channel TEXT,
        sent INTEGER DEFAULT 0,
        FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
    )
""")

# ── Positions ──
cursor.execute("""
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

# ── Risk metrics ──
cursor.execute("""
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

# ── Risk alerts ──
cursor.execute("""
    CREATE TABLE IF NOT EXISTS risk_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT DEFAULT 'warning',
        triggered_at TEXT DEFAULT (datetime('now')),
        dismissed INTEGER DEFAULT 0
    )
""")

# ── Índices separados ──
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_sym ON precios_ohlcv(simbolo, timestamp DESC)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_ts ON precios_ohlcv(timestamp DESC)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_rt_symbol ON realtime_ticks(simbolo)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_rt_time ON realtime_ticks(timestamp DESC)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_hist_rule ON alert_history(rule_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_hist_time ON alert_history(triggered_at DESC)")

# ── Insertar datos macro base ──
macro_indicators = [
    ("SPX", "S&P 500", 5263.17, -0.15, 50.0),
    ("DJI", "Dow Jones", 39127.80, 0.07, 55.0),
    ("IXIC", "Nasdaq 100", 16667.86, -0.52, 48.0),
    ("VIX", "Volatility Index", 25.21, 1.68, 45.0),
    ("DXY", "Dollar Index", 104.76, -0.11, 52.0),
    ("US10Y", "10Y Treasury", 4.28, 0.06, 50.0),
    ("US2Y", "2Y Treasury", 4.61, -0.10, 48.0),
    ("T10Y2Y", "2Y-10Y Spread", -0.33, 0.0, 50.0),
]

cursor.execute("SELECT COUNT(*) FROM indicadores_macro")
if cursor.fetchone()[0] == 0:
    for name, full_name, value, change, score in macro_indicators:
        cursor.execute(
            "INSERT INTO indicadores_macro (nombre, valor, cambio_pct, direccion, score) VALUES (?, ?, ?, 'neutral', ?)",
            (full_name, value, change, score),
        )

# ── Insertar precios OHLCV ejemplo ──
cursor.execute("SELECT COUNT(*) FROM precios_ohlcv")
if cursor.fetchone()[0] == 0:
    random.seed(42)
    base_price = 500
    for i in range(100):
        ts = f"2025-04-{5+i:02d} 23:00:00" if i < 26 else f"2025-05-{(i-25):02d} 23:00:00"
        open_p = base_price
        close_p = base_price + random.gauss(0, 5)
        high_p = max(open_p, close_p) + abs(random.gauss(0, 2))
        low_p = min(open_p, close_p) - abs(random.gauss(0, 2))
        vol = random.uniform(5000000, 15000000)
        cursor.execute(
            "INSERT INTO precios_ohlcv (simbolo, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("SPX", ts, round(open_p, 2), round(high_p, 2), round(low_p, 2), round(close_p, 2), round(vol, 0)),
        )
        base_price = close_p

conn.commit()
conn.close()

print(f"✅ pegaton.db creada en {DB_PATH}")

# Verificar
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print(f"Tablas creadas ({len(tables)}):")
for t in tables:
    count = cursor.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"  {t[0]}: {count} filas")
conn.close()