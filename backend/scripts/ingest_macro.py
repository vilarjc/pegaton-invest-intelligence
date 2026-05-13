#!/usr/bin/env python3
"""
Ingesta de datos macroeconómicos en harness.db.
Se ejecuta vía cron job de Hermes.
Lee de la API inversor-ia y persiste en DB para histórico.
"""
import json, os, sys, sqlite3
from datetime import datetime
from urllib.request import Request, urlopen

DB_PATH = "/root/pegaton_invest_intelligence/harness.db"
API_URL = "http://100.64.64.58:18081/api/macro/history"

def init_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TIMESTAMP,
            vix REAL,
            dxy REAL,
            sp500 REAL,
            gold_price REAL,
            oil_price REAL,
            pmi_manufacturing REAL,
            pmi_services REAL,
            inflation REAL,
            fed_rate TEXT,
            unemployment REAL,
            yield_2y REAL,
            yield_10y REAL,
            gdp TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_macro_captured 
        ON macro_snapshots(captured_at DESC)
    """)
    conn.commit()
    conn.close()

def parse_float(val):
    if val is None: return None
    if isinstance(val, (int, float)): return float(val)
    try: return float(str(val).replace("%","").replace("$","").replace(",","").strip())
    except: return None

def ingest():
    init_table()
    
    req = Request(API_URL, headers={"User-Agent": "Hermes-Ingestor"})
    with urlopen(req, timeout=15) as resp:
        raw = json.loads(resp.read().decode())
    
    items = raw.get("data", []) if isinstance(raw, dict) else raw
    if not items:
        print("No data from API")
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for item in items:
        captured = item.get("captured_at")
        if not captured: continue
        
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM macro_snapshots WHERE captured_at = ?", (captured,)
        ).fetchone()
        if existing: continue
        
        conn.execute("""
            INSERT INTO macro_snapshots 
            (captured_at, vix, dxy, sp500, gold_price, oil_price,
             pmi_manufacturing, pmi_services, inflation, fed_rate,
             unemployment, yield_2y, yield_10y, gdp, summary)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            captured,
            parse_float(item.get("vix")),
            parse_float(item.get("dxy")),
            parse_float(item.get("sp500")),
            parse_float(item.get("gold_price")),
            parse_float(item.get("oil_price")),
            parse_float(item.get("pmi_manufacturing")),
            parse_float(item.get("pmi_services")),
            parse_float(item.get("inflation")),
            str(item.get("fed_rate", "")),
            parse_float(item.get("unemployment")),
            parse_float(item.get("yield_2y")),
            parse_float(item.get("yield_10y")),
            str(item.get("gdp", "")),
            str(item.get("summary", "")),
        ))
        inserted += 1
    
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM macro_snapshots").fetchone()[0]
    conn.close()
    
    print(f"Inserted: {inserted} records | Total in DB: {total}")
    return inserted

if __name__ == "__main__":
    count = ingest()
    print(f"✅ Ingesta macro completada: {count} registros nuevos")
