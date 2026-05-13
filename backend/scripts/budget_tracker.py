#!/usr/bin/env python3
"""
Budget Tracker v2 — Precios reales de DeepSeek.
Seguimiento de tokens IN/OUT, costos por modelo, límites por proyecto.
"""

import json, os, math
from datetime import datetime, date, timedelta

TRACKER_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'budget_tracker.json')

# Precios REALES de DeepSeek (por millón de tokens)
MODEL_PRICING = {
    'deepseek-v4-flash':  {'input': 0.14,  'output': 0.28},
    'deepseek-v4-flash':      {'input': 0.28,  'output': 0.42},
    'deepseek-v4-pro':    {'input': 0.435, 'output': 0.87},
    'deepseek-v4-pro':  {'input': 0.55,  'output': 2.19},
}

class BudgetTracker:
    def __init__(self, path=TRACKER_PATH):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    return json.load(f)
            except: pass
        today = date.today()
        return {
            'recarga_total': 5.0,  # $5 recargados en Abril
            'projects': {
                'pegaton': {
                    'name': 'PEGATON INVEST INTELLIGENCE',
                    'budget_limit': 3.0,     # Límite para este proyecto
                    'alert_threshold': 0.8,   # Alerta al 80%
                    'spent': 0.0,
                    'tasks': [],
                }
            },
            'budgets': {
                'daily': {'limit': 1.0, 'spent': 0.0, 'date': str(today)},
                'weekly': {'limit': 3.0, 'spent': 0.0, 'week_start': str(today)},
                'monthly': {'limit': 5.0, 'spent': 0.0, 'month': str(today)[:7]},
            },
            'created': str(date.today()),
        }

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def _calc_cost(self, model, tokens_in, tokens_out):
        """Calculate cost based on real DeepSeek pricing per million tokens."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING['deepseek-v4-flash'])
        cost_in = (tokens_in / 1_000_000) * pricing['input']
        cost_out = (tokens_out / 1_000_000) * pricing['output']
        return round(cost_in + cost_out, 6)

    def register_task(self, project, model, tokens_in, tokens_out, description=''):
        """Register a task with actual token counts. Calculates cost automatically."""
        cost = self._calc_cost(model, tokens_in, tokens_out)
        today = str(date.today())

        # Add task to project
        proj = self.data['projects'].get(project)
        if proj:
            entry = {
                'date': today,
                'time': datetime.now().strftime('%H:%M'),
                'model': model,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'cost': cost,
                'description': description[:60],
            }
            proj['tasks'].append(entry)
            proj['spent'] = round(proj['spent'] + cost, 4)

            # Update global budgets
            self.data['budgets']['daily']['spent'] = round(self.data['budgets']['daily']['spent'] + cost, 4)
            self.data['budgets']['weekly']['spent'] = round(self.data['budgets']['weekly']['spent'] + cost, 4)
            self.data['budgets']['monthly']['spent'] = round(self.data['budgets']['monthly']['spent'] + cost, 4)

            self._save()
            return cost
        return 0.0

    def get_project_summary(self, project='pegaton'):
        """Get summary matching DeepSeek dashboard format."""
        proj = self.data['projects'].get(project)
        if not proj:
            return {'error': 'Project not found'}

        tasks = proj['tasks']
        recarga = self.data.get('recarga_total', 5.0)
        spent = proj['spent']
        saldo = round(recarga - spent, 2)

        # Aggregate by model
        by_model = {}
        for t in tasks:
            m = t['model']
            if m not in by_model:
                by_model[m] = {'tokens_in': 0, 'tokens_out': 0, 'cost': 0.0, 'count': 0}
            by_model[m]['tokens_in'] += t['tokens_in']
            by_model[m]['tokens_out'] += t['tokens_out']
            by_model[m]['cost'] += t['cost']
            by_model[m]['count'] += 1

        # Per-day aggregation
        by_day = {}
        for t in tasks:
            d = t['date']
            if d not in by_day:
                by_day[d] = {'models': set(), 'cost': 0.0, 'tokens_in': 0, 'tokens_out': 0}
            by_day[d]['models'].add(t['model'])
            by_day[d]['cost'] += t['cost']
            by_day[d]['tokens_in'] += t['tokens_in']
            by_day[d]['tokens_out'] += t['tokens_out']

        # Estimate days remaining
        if spent > 0 and len(tasks) > 0:
            days_active = max((datetime.now() - datetime.fromisoformat(self.data['created'])).days, 1)
            daily_rate = spent / days_active
            days_remaining = int(saldo / daily_rate) if daily_rate > 0 else 0
            projection = recarga / daily_rate if daily_rate > 0 else 0
            projection_pct = round((spent / recarga) * 100, 1) if recarga > 0 else 0
        else:
            days_remaining = 30
            projection = 30
            projection_pct = 0

        # Alert check
        limit = proj.get('budget_limit', 3.0)
        threshold = proj.get('alert_threshold', 0.8)
        alert = spent >= (limit * threshold)

        return {
            'project': project,
            'recarga': recarga,
            'saldo': saldo,
            'spent': spent,
            'budget_limit': limit,
            'alert': alert,
            'days_remaining': days_remaining,
            'projection_days': int(projection),
            'projection_pct': projection_pct,
            'by_model': {m: {
                'tokens_in': d['tokens_in'],
                'tokens_out': d['tokens_out'],
                'cost': round(d['cost'], 3),
                'requests': d['count'],
                'price_in': MODEL_PRICING.get(m, {}).get('input', 0),
                'price_out': MODEL_PRICING.get(m, {}).get('output', 0),
            } for m, d in sorted(by_model.items(), key=lambda x: -x[1]['cost'])},
            'by_day': sorted([{
                'date': d,
                'models': list(v['models']),
                'cost': round(float(v['cost']), 3),
                'tokens_in': v['tokens_in'],
                'tokens_out': v['tokens_out'],
            } for d, v in by_day.items()], key=lambda x: x['date'], reverse=True),
        }

    def get_report(self):
        s = self.get_project_summary()
        if 'error' in s:
            return s['error']
        lines = [f"📊 PEGATON Budget", f"  Saldo: ${s['saldo']:.2f} de ${s['recarga']:.2f} recargados"]
        lines.append(f"  Gastado: ${s['spent']:.2f} · Límite proyecto: ${s['budget_limit']:.2f}")
        if s['alert']:
            lines.append(f"  ⚠️ ALERTA: Has gastado el {(s['spent']/s['budget_limit'])*100:.0f}% del límite!")
        lines.append(f"  Proyección: {s['projection_pct']}% del presupuesto en {s['projection_days']} días")
        for m, d in s['by_model'].items():
            lines.append(f"  {m}: {d['tokens_in']:,} IN · {d['tokens_out']:,} OUT · {d['requests']} reqs · ${d['cost']:.3f}")
        return '\n'.join(lines)


if __name__ == "__main__":
    bt = BudgetTracker()
    print(bt.get_report())
