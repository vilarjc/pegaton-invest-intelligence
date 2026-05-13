#!/usr/bin/env python3
"""Script CLI: combina señal macro + técnica en señal PEGATON final.
HU-PROG-1 / Subtarea 6.5 — Sin dependencias de LLM."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from backend.app.core.score import pegaton_score, all_scores

def main():
    import argparse
    parser = argparse.ArgumentParser(description='PEGATON Signal Combiner')
    parser.add_argument('--symbol', '-s', default='SPY', help='Símbolo a evaluar')
    parser.add_argument('--all', '-a', action='store_true', help='Todos los símbolos')
    parser.add_argument('--json', '-j', action='store_true', help='Salida JSON')
    args = parser.parse_args()

    if args.all:
        scores = all_scores()
    else:
        scores = {args.symbol: pegaton_score(args.symbol)}

    if args.json:
        print(json.dumps(scores, indent=2, default=str))
    else:
        for sym, data in scores.items():
            print(f"\n{'='*50}")
            print(f"  {sym} — PEGATON Score")
            print(f"{'='*50}")
            print(f"  Score : {data['pegaton_score']:.1f}/100")
            print(f"  Acción: {data['action']}")
            print(f"  Macro : {data['macro_score']:.1f} | Técnico: {data['technical_score']:.1f}")
            factors = data.get('factors', {})
            summary = factors.get('summary', {})
            print(f"  Alcistas: {summary.get('factores_alcistas', 0)} | Bajistas: {summary.get('factores_bajistas', 0)}")
            dom = summary.get('factor_dominante', {})
            if dom:
                print(f"  Dominante: {dom.get('name')} ({dom.get('direction')}, {dom.get('contribution'):.1f})")
    return 0

if __name__ == '__main__':
    sys.exit(main())