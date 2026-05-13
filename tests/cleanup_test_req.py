#!/usr/bin/env python3
"""Cleanup residual test data."""
import sys, os
sys.path.insert(0, '/root/pegaton_invest_intelligence')
os.chdir('/root/pegaton_invest_intelligence')

import sqlite3

DB = '/root/pegaton_invest_intelligence/harness.db'
conn = sqlite3.connect(DB)
cur = conn.execute("SELECT COUNT(*) FROM requirements WHERE source='test'")
n = cur.fetchone()[0]
print(f"Hay {n} registros de test source")

if n > 0:
    conn.execute("DELETE FROM requirements WHERE source='test'")
    conn.commit()
    print(f"Limpiados {n} registros de test source ✅")
else:
    print("No hay datos de test para limpiar ✅")

conn.close()
print("Done!")