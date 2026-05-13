#!/usr/bin/env python3
"""Script CLI: ingesta de datos OHLCV de precios (SPY, EUR/USD, BTC/USD).
HU-PROG-1 / Subtarea 6.3 — Sin dependencias de LLM."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.app.core.technical import get_price_data

SYMBOLS = ['SPY', 'EUR/USD', 'BTC/USD']

def main():
    print("🔄 Ingesta Precios OHLCV — PEGATON Invest Intelligence")
    for sym in SYMBOLS:
        try:
            df = get_price_data(sym, days=200)
            if df.empty:
                print(f"  ⚠️  {sym}: sin datos")
                continue
            print(f"  ✅ {sym}: {len(df)} registros ({df.index.min().date()} → {df.index.max().date()})")
        except Exception as e:
            print(f"  ❌ {sym}: {e}")
    return 0

if __name__ == '__main__':
    sys.exit(main())