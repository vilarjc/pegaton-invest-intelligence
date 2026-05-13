#!/usr/bin/env python3
import sqlite3
harness_db = '/root/pegaton_invest_intelligence/harness.db'
conn = sqlite3.connect(harness_db)
c = conn.cursor()

# Show ALL in_progress tasks
c.execute("SELECT id, code, epic_id, title, status, spec_id FROM tasks WHERE status='in_progress' ORDER BY code")
rows = c.fetchall()
print("IN-PROGRESS TASKS:")
for r in rows:
    print(f"  {r[1]:<14} epic={r[2]} spec={r[4] or 'N/A':>3} | {r[3]}")

# Show done tasks recent
c.execute("SELECT id, code, title, status FROM tasks WHERE status='done' ORDER BY updated_at DESC LIMIT 10")
rows = c.fetchall()
print(f"\nDONE TASKS (last 10):")
for r in rows:
    print(f"  {r[1]:<14} | {r[2]}")

# Check specs status
c.execute("SELECT id, task_id, title, status FROM specs ORDER BY id DESC LIMIT 15")
rows = c.fetchall()
print(f"\nSPECS (last 15):")
for r in rows:
    print(f"  spec#{r[0]} task={r[1]} | {r[3]:<10} | {r[2][:60]}")

conn.close()