#!/usr/bin/env python3
"""
Track AI model usage. Call this at the end of any session/task to register costs.
Usage: python track_task.py <project> <model> <tokens_in> <tokens_out> <description>
"""
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scripts.budget_tracker import BudgetTracker

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: track_task.py <project> <model> <tokens_in> <tokens_out> [description]")
        sys.exit(1)
    project = sys.argv[1]
    model = sys.argv[2]
    tokens_in = int(sys.argv[3])
    tokens_out = int(sys.argv[4])
    desc = ' '.join(sys.argv[5:]) if len(sys.argv) > 5 else ''

    bt = BudgetTracker()
    cost = bt.register_task(project, model, tokens_in, tokens_out, desc)
    summary = bt.get_project_summary(project)
    print(f"✅ Registered: {model} - {tokens_in:,} IN / {tokens_out:,} OUT = ${cost:.6f}")
    print(f"💰 Project '{project}' total spent: ${summary['spent']:.4f}")
    print(f"💰 DeepSeek balance: ${summary['saldo']:.2f} remaining")
