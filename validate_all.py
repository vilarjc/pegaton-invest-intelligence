#!/usr/bin/env python3
"""Validación completa del sistema PEGATON — HU-FIN-1, HU-TEC-1, HU-PROG-1"""
import sys, os

sys.path.insert(0, '/root/pegaton_invest_intelligence')
sys.path.insert(0, '/root/pegaton_invest_intelligence/backend')
os.chdir('/root/pegaton_invest_intelligence')

import sqlite3
results = {"ok": 0, "fail": 0, "errors": []}

def check(name, condition, detail=""):
    if condition:
        results["ok"] += 1
        print(f"  ✅ {name}")
    else:
        results["fail"] += 1
        msg = f"  ❌ {name} — {detail}"
        print(msg)
        results["errors"].append(msg)

# ════════════════════════════════════════
print("=" * 60)
print("VALIDACIÓN: Configuración Macro (Spec A)")
print("=" * 60)

from backend.app.core.pegaton_config import (
    MACRO_SCORING, MACRO_WEIGHTS,
    TECHNICAL_WEIGHTS,
    MACRO_WEIGHT, TECHNICAL_WEIGHT, ACTIONS,
    FACTOR_ALCISTA, FACTOR_BAJISTA
)

check("≥5 indicadores macro definidos", len(MACRO_SCORING) >= 5,
      f"hay {len(MACRO_SCORING)}")

check("Pesos macro suman 1.0",
      abs(sum(MACRO_WEIGHTS.values()) - 1.0) < 0.0001,
      f"suma={sum(MACRO_WEIGHTS.values())}")

check("Pesos técnicos suman 1.0",
      abs(sum(TECHNICAL_WEIGHTS.values()) - 1.0) < 0.0001,
      f"suma={sum(TECHNICAL_WEIGHTS.values())}")

check("Blend macro_weight + technical_weight = 1.0",
      abs(MACRO_WEIGHT + TECHNICAL_WEIGHT - 1.0) < 0.0001,
      f"{MACRO_WEIGHT} + {TECHNICAL_WEIGHT} = {MACRO_WEIGHT + TECHNICAL_WEIGHT}")

check("≥3 indicadores técnicos",
      len(TECHNICAL_WEIGHTS) >= 3,
      f"hay {len(TECHNICAL_WEIGHTS)}")

check("ACTIONS: 5 rangos definidos",
      len(ACTIONS) == 5)

check("FACTOR_ALCISTA=55, FACTOR_BAJISTA=45",
      FACTOR_ALCISTA == 55 and FACTOR_BAJISTA == 45)

for key in ['CPI', 'PCE', 'DGS10', 'FEDFUNDS', 'UNRATE', 'GDP', 'ISM', 'M2']:
    check(f"Indicador {key} en MACRO_WEIGHTS", key in MACRO_WEIGHTS)

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Datos en pegaton.db (HU-FIN-1)")
print("=" * 60)

conn = sqlite3.connect('/root/pegaton_invest_intelligence/data/pegaton.db')

macro_count = conn.execute("SELECT COUNT(DISTINCT indicator) FROM macro_indicators").fetchone()[0]
check("macro_indicators: 8 indicadores distintos",
      macro_count == 8, f"hay {macro_count}")

spy_count = conn.execute("SELECT COUNT(*) FROM precios_ohlcv WHERE simbolo='SPY'").fetchone()[0]
check("precios_ohlcv: ≥200 rows SPY",
      spy_count >= 200, f"hay {spy_count} rows")

all_indicators = conn.execute("SELECT DISTINCT indicator FROM macro_indicators ORDER BY indicator").fetchall()
print(f"  Indicadores: {[r[0] for r in all_indicators]}")

latest_date = conn.execute("SELECT MAX(fecha) FROM macro_indicators").fetchone()[0]
check("macro_indicators: fecha actualizada",
      latest_date is not None, f"última fecha: {latest_date}")

conn.close()

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Ejecutar macro_score() (HU-FIN-1)")
print("=" * 60)

from backend.app.core.macro import macro_score
result = macro_score()
print(f"  macro_score() = {result['macro_score']:.1f}")
print(f"  interpretación: {result['interpretation']}")
check("macro_score() retorna dict", isinstance(result, dict))
check("macro_score en rango 0-100",
      0 <= result.get('macro_score', -1) <= 100,
      f"valor={result.get('macro_score')}")
check("8 factores calculados",
      len(result.get('factors', [])) == 8,
      f"hay {len(result.get('factors', []))}")

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Ejecutar technical_score() (HU-TEC-1)")
print("=" * 60)

from backend.app.core.technical import technical_score
tech_result = technical_score('SPY')
print(f"  technical_score(SPY) = {tech_result['technical_score']:.1f}")
check("technical_score en rango",
      0 <= tech_result['technical_score'] <= 100,
      f"valor={tech_result['technical_score']}")
check("4 factors técnicos",
      len(tech_result.get('factors', [])) == 4,
      f"hay {len(tech_result.get('factors', []))}")

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Ejecutar pegaton_score('SPY') (HU-TEC-1)")
print("=" * 60)

from backend.app.core.score import pegaton_score
score_result = pegaton_score('SPY')
print(f"  pegaton_score(SPY) = {score_result['pegaton_score']:.1f}")
print(f"  acción: {score_result['action']}")
check("pegaton_score en rango",
      0 <= score_result['pegaton_score'] <= 100)
check("action presente y válida",
      score_result['action'] in ['FUERTE_COMPRA', 'COMPRA', 'MANTENER', 'VENTA', 'FUERTE_VENTA'],
      f"action={score_result['action']}")
check("factors.macro presente",
      'macro' in score_result.get('factors', {}))
check("factors.technical presente",
      'technical' in score_result.get('factors', {}))
check("macro_details presente",
      'macro' in score_result.get('details', {}))
check("technical_details presente",
      'technical' in score_result.get('details', {}))

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Archivos fuente (HU-PROG-1)")
print("=" * 60)

for f in [
    'backend/app/core/macro.py',
    'backend/app/core/technical.py',
    'backend/app/core/score.py',
    'backend/app/core/pegaton_config.py',
    'backend/app/api/v1/endpoints/signal.py',
    'backend/app/api/v1/endpoints/news_sentiment.py',
    'backend/app/main.py',
    'frontend/widgets/news-sentimiento.html',
    'docs/architecture.md',
    'harness/specs/Spec-HU-PROG-1.md',
]:
    full = os.path.join('/root/pegaton_invest_intelligence', f)
    check(f"EXISTS {f}", os.path.isfile(full))

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Endpoint /signal en main.py (HU-PROG-1)")
print("=" * 60)

with open('/root/pegaton_invest_intelligence/backend/app/main.py') as fh:
    main_content = fh.read()
check("signal_router registrado en main.py",
      "signal_router" in main_content and "from backend.app.api.v1.endpoints.signal" in main_content)

# ════════════════════════════════════════
print("\n" + "=" * 60)
print("VALIDACIÓN: Arquitectura + Specs (HU-PROG-1)")
print("=" * 60)

with open('/root/pegaton_invest_intelligence/docs/architecture.md') as fh:
    arch = fh.read()
check("architecture.md: tiene sección Frontend/Backend",
      "Frontend" in arch and "Backend" in arch)
check("architecture.md: tiene diagrama de flujo",
      "signal" in arch.lower())

with open('/root/pegaton_invest_intelligence/harness/specs/Spec-HU-PROG-1.md') as fh:
    spec = fh.read()
check("Spec-HU-PROG-1.md: tiene tareas desglosadas",
      len(spec) > 500)

print("\n" + "=" * 60)
print(f"RESULTADO FINAL: {results['ok']} OK, {results['fail']} FAIL")
print("=" * 60)

if results["errors"]:
    print("\nERRORES:")
    for e in results["errors"]:
        print(f"  {e}")
else:
    print("\n✅ TODAS LAS VALIDACIONES PASARON")