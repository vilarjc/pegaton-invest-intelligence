#!/usr/bin/env python3
import sys, os, sqlite3
sys.path.insert(0, '/root/pegaton_invest_intelligence')
sys.path.insert(0, '/root/pegaton_invest_intelligence/backend')
os.chdir('/root/pegaton_invest_intelligence')

results = {"ok": 0, "fail": 0, "errors": []}
def check(name, cond, detail=""):
    if cond:
        results["ok"] += 1
        print(f"  ✅ {name}")
    else:
        results["fail"] += 1
        msg = f"  ❌ {name} — {detail}"
        print(msg)
        results["errors"].append(msg)

from backend.app.core.pegaton_config import MACRO_SCORING, MACRO_WEIGHTS, TECHNICAL_WEIGHTS, MACRO_WEIGHT, TECHNICAL_WEIGHT, ACTIONS, FACTOR_ALCISTA, FACTOR_BAJISTA
print("=== MACRO CONFIG ===")
check("≥5 indicadores macro", len(MACRO_SCORING) >= 5, f"={len(MACRO_SCORING)}")
check("Pesos macro suman 1.0", abs(sum(MACRO_WEIGHTS.values()) - 1.0) < 0.0001)
check("Pesos tech suman 1.0", abs(sum(TECHNICAL_WEIGHTS.values()) - 1.0) < 0.0001)
check("Blend = 1.0", abs(MACRO_WEIGHT + TECHNICAL_WEIGHT - 1.0) < 0.0001)
check("≥3 indicadores tech", len(TECHNICAL_WEIGHTS) >= 3)
check("5 rangos ACTIONS", len(ACTIONS) == 5)
check("FACTORS 55/45", FACTOR_ALCISTA == 55 and FACTOR_BAJISTA == 45)

conn = sqlite3.connect('/root/pegaton_invest_intelligence/data/pegaton.db')
c = conn.cursor()
c.execute("SELECT COUNT(DISTINCT indicator) FROM macro_indicators")
check("8 indicadores macro en DB", c.fetchone()[0] == 8)
c.execute("SELECT COUNT(*) FROM precios_ohlcv WHERE simbolo='SPY'")
check("≥200 rows SPY", c.fetchone()[0] >= 200)
conn.close()

from backend.app.core.macro import macro_score
r = macro_score()
print(f"  macro_score={r['macro_score']:.1f}")
check("macro_score dict", isinstance(r, dict))
check("0-100", 0 <= r['macro_score'] <= 100)
check("8 factores", len(r.get('factors',[])) == 8)

from backend.app.core.technical import technical_score
t = technical_score('SPY')
print(f"  tech_score={t['technical_score']:.1f}")
check("tech 0-100", 0 <= t['technical_score'] <= 100)
check("4 factores", len(t.get('factors',[])) == 4)

from backend.app.core.score import pegaton_score
p = pegaton_score('SPY')
print(f"  pegaton_score={p['pegaton_score']:.1f}, action={p['action']}")
check("pegaton 0-100", 0 <= p['pegaton_score'] <= 100)
check("action válida", p['action'] in ['FUERTE_COMPRA','COMPRA','MANTENER','VENTA','FUERTE_VENTA'])
check("factors.macro", 'macro' in p.get('factors',{}))
check("factors.tech", 'technical' in p.get('factors',{}))
check("details.macro", 'macro' in p.get('details',{}))
check("details.tech", 'technical' in p.get('details',{}))

for f in ['backend/app/core/macro.py','backend/app/core/technical.py','backend/app/core/score.py',
          'backend/app/core/pegaton_config.py','backend/app/api/v1/endpoints/signal.py',
          'backend/app/main.py','frontend/widgets/news-sentimiento.html','docs/architecture.md']:
    check(f"EXISTS {f}", os.path.isfile(f'/root/pegaton_invest_intelligence/{f}'))

with open('/root/pegaton_invest_intelligence/backend/app/main.py') as fh:
    mc = fh.read()
check("signal_router en main.py", "signal_router" in mc and "from backend.app.api.v1.endpoints.signal" in mc)

print(f"\n{'='*60}")
print(f"RESULTADO: {results['ok']} OK, {results['fail']} FAIL")
if results["errors"]:
    for e in results["errors"]: print(f"  {e}")
else:
    print("  ✅ TODAS LAS VALIDACIONES PASARON")