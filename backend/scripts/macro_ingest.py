#!/usr/bin/env python3
"""Script CLI: ingesta de indicadores macroeconómicos desde FRED/yfinance.
HU-PROG-1 / Subtarea 6.1 — Sin dependencias de LLM."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.app.core.macro import get_macro_data
from backend.app.core.pegaton_config import MACRO_SCORING

def main():
    print("🔄 Ingesta Macro — PEGATON Invest Intelligence")
    data = get_macro_data()
    if data.empty:
        print("⚠️  No se obtuvieron datos")
        return 1
    indicators = data['indicator'].unique()
    print(f"✅ {len(indicators)} indicadores cargados: {list(indicators)}")
    print(f"   Fechas: {data['date'].min()} → {data['date'].max()}")
    print(f"   Registros totales: {len(data)}")
    return 0

if __name__ == '__main__':
    sys.exit(main())