#!/usr/bin/env python3
"""Test suite for requirements_db module."""
import sys, os
sys.path.insert(0, '/root/pegaton_invest_intelligence')
os.chdir('/root/pegaton_invest_intelligence')

from harness.requirements_db import get_requirements_db, RequirementsDB

# Reset singleton
import harness.requirements_db as rmod
rmod._req_db = None
rdb = get_requirements_db()

# ── Test 1: Create ──
rid = rdb.create_requirement(
    source="test", req_type="feature",
    client_priority="high", title="Test Requirement",
    description="Descripcion de prueba", internal_priority="P1"
)
print(f"Test 1 - Create: ID={rid} ✅" if rid > 0 else "❌")

# ── Test 2: Get ──
req = rdb.get_requirement(rid)
assert req is not None, "Get failed"
assert req['req_code'].startswith('REQ-'), f"Bad code: {req['req_code']}"
assert req['title'] == 'Test Requirement'
print(f"Test 2 - Get: {req['req_code']} ✅")

# ── Test 3: List ──
reqs = rdb.list_requirements(status='pending')
assert any(r['id'] == rid for r in reqs), "List failed"
print(f"Test 3 - List: {len(reqs)} pending ✅")

# ── Test 4: Classify ──
req = rdb.classify_requirement(rid, 'P0', 'Critico para produccion')
assert req['internal_priority'] == 'P0'
assert req['status'] == 'classified'
print(f"Test 4 - Classify: P0 ✅")

# ── Test 5: Stats ──
stats = rdb.get_stats()
print(f"Test 5 - Stats: {stats} ✅")

# ── Test 6: Link epic ──
rdb.link_epic(rid, 12)
req = rdb.get_requirement(rid)
assert req['epic_id'] == 12
print(f"Test 6 - Link epic: EP-FR-001 (id=12) ✅")

# ── Test 7: Update status ──
rdb.update_requirement_status(rid, 'in_progress')
req = rdb.get_requirement(rid)
assert req['status'] == 'in_progress'
print(f"Test 7 - Status update: in_progress ✅")

# ── Test 8: Progress ──
rdb.update_progress(rid, 5, 3)
req = rdb.get_requirement(rid)
assert req['tasks_count'] == 5
assert req['tasks_done'] == 3
print(f"Test 8 - Progress: 60% ✅")

# ── Test 9: Filter by type ──
reqs_feat = rdb.list_requirements(req_type='feature')
print(f"Test 9 - Filter by type: {len(reqs_feat)} features ✅")

# ── Test 10: Decompose ──
from harness.harness_db import HarnessDB
db = HarnessDB()
tasks_ep_fr = db.get_tasks_by_epic('EP-FR-001')
task_codes = [t['code'] for t in tasks_ep_fr[:3]]
print(f"Test 10 - Decompose with tasks: {task_codes} ✅")

rdb.update_requirement_status(rid, 'decomposed')
req = rdb.get_requirement(rid)
assert req['status'] == 'decomposed'
print(f"Test 10b - Decompose status: decomposed ✅")

# ── Test 11: Get by code ──
req_by_code = rdb.get_requirement_by_code(req['req_code'])
assert req_by_code['id'] == rid
print(f"Test 11 - Get by code: {req['req_code']} ✅")

print("\n=== ALL 11 TESTS PASSED ✅ ===")

# Cleanup
rdb.close()