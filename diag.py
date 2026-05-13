#!/usr/bin/env python3
"""Diagnóstico de timestamps y ejecución individual de tests."""
import sys, os, sqlite3
sys.path.insert(0, '/root/pegaton_invest_intelligence')
sys.path.insert(0, '/root/pegaton_invest_intelligence/backend')
os.chdir('/root/pegaton_invest_intelligence')

# 1. Check actual timestamps in DB
db = '/root/pegaton_invest_intelligence/data/pegaton.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT timestamp FROM precios_ohlcv WHERE simbolo='SPY' LIMIT 5")
for row in c.fetchall():
    print(f"TIMESTAMP RAW: [{row[0]}] type={type(row[0]).__name__}")

c.execute("SELECT COUNT(*) FROM precios_ohlcv WHERE simbolo='SPY'")
print(f"\nTotal SPY rows: {c.fetchone()[0]}")
conn.close()

# 2. Test import and run of technical_score
print("\n--- Testing technical_score('SPY') ---")
try:
    from backend.app.core.technical import technical_score
    r = technical_score('SPY')
    print(f"  technical_score(SPY) = {r['technical_score']}")
    print(f"  factors = {len(r['factors'])}")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# 3. Test signal endpoint manually
print("\n--- Testing signal endpoint manually ---")
try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from backend.app.api.v1.endpoints.signal import router as signal_router
    app = FastAPI(title="Pegaton API Test")
    app.include_router(signal_router, prefix="/api/v1")
    client = TestClient(app)

    r = client.get("/api/v1/signal")
    print(f"  GET /signal: status={r.status_code}")
    print(f"  Response: {r.json()}")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\n--- Done ---")