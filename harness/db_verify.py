#!/usr/bin/env python3
"""
============================================================================
HARNESS VERIFY — Environment Validation (init.sh equivalent)
============================================================================
Run this before ANY agent session starts. It verifies:
  - harness.db exists and has correct schema
  - All required directories exist
  - Python venv is active
  - API keys are present (but doesn't validate them)
  - Previous agent tasks are consistent
  - No files marked "Generated from spec" have been manually modified

Exit code: 0 = all good, 1 = warnings, 2 = critical failures
============================================================================
"""

import os
import sys
import json

# Ensure we can import the harness module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.harness_db import HarnessDB


# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_DIRS = [
    "backend",
    "frontend",
    "harness",
    "obsidian_vault",
    "data",
]
REQUIRED_FILES = [
    "start.sh",
    ".env",
    "requirements.txt",
    "harness/harness_db.py",
    "harness/schema.sql",
]
EXPECTED_TABLES = {"epics", "tasks", "specs", "agent_logs", "artifacts", "sessions", "decisions"}

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")

def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def fail(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def verify() -> int:
    exit_code = 0
    errors = 0
    warnings = 0

    print(f"\n{CYAN}{BOLD}╔══════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║   HARNESS — Environment Verification  ║{RESET}")
    print(f"{CYAN}{BOLD}╚══════════════════════════════════════╝{RESET}\n")

    # 1. Project root exists
    print(f"{BOLD}1. Project Structure{RESET}")
    if not os.path.isdir(PROJECT_ROOT):
        fail(f"Project root not found: {PROJECT_ROOT}")
        errors += 1
    else:
        ok(f"Project root: {PROJECT_ROOT}")
        for d in REQUIRED_DIRS:
            path = os.path.join(PROJECT_ROOT, d)
            if os.path.isdir(path):
                ok(f"Directory exists: {d}/")
            else:
                warn(f"Directory missing: {d}/")
                warnings += 1
        for f in REQUIRED_FILES:
            path = os.path.join(PROJECT_ROOT, f)
            if os.path.isfile(path):
                ok(f"File exists: {f}")
            else:
                fail(f"File missing: {f}")
                errors += 1

    # 2. Database
    print(f"\n{BOLD}2. Database{RESET}")
    db_path = os.path.join(PROJECT_ROOT, "harness.db")
    if not os.path.isfile(db_path):
        fail(f"harness.db not found at {db_path}")
        errors += 1
    else:
        ok(f"harness.db exists ({os.path.getsize(db_path)} bytes)")
        try:
            db = HarnessDB(db_path)
            conn = db.connect()
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            actual_tables = {row[0] for row in cur.fetchall()}
            missing = EXPECTED_TABLES - actual_tables
            extra = actual_tables - EXPECTED_TABLES
            if missing:
                fail(f"Missing tables: {', '.join(sorted(missing))}")
                errors += 1
            else:
                ok(f"All {len(EXPECTED_TABLES)} expected tables present")
            if extra:
                ok(f"Extra tables found: {', '.join(sorted(extra))}")
            db.close()
        except Exception as e:
            fail(f"Database connection failed: {e}")
            errors += 1

    # 3. Python Environment
    print(f"\n{BOLD}3. Python Environment{RESET}")
    venv_path = os.path.join(PROJECT_ROOT, "venv")
    if os.path.isdir(venv_path):
        ok(f"Virtual env found: {venv_path}")
    else:
        warn("No venv/ directory — using system Python")
        warnings += 1

    # Check critical Python packages
    try:
        import fastapi
        ok(f"fastapi: {getattr(fastapi, '__version__', 'unknown')}")
    except ImportError:
        fail("fastapi not installed")
        errors += 1
    try:
        import sqlite3
        ok("sqlite3: available")
    except ImportError:
        fail("sqlite3 not available (critical)")
        errors += 1

    # 4. API Keys
    print(f"\n{BOLD}4. API Keys{RESET}")
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            lines = f.readlines()
        # Build a dict of key -> value from the env file
        env_vars = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip()
        required_keys = ["FRED_API_KEY", "TWELVEDATA_API_KEY", "DEEPSEEK_API_KEY"]
        optional_keys = ["GEMINI_API_KEY"]
        for key in required_keys:
            val = env_vars.get(key, "")
            if val and "poner_aqui" not in val:
                ok(f"{key}: present")
            else:
                warn(f"{key}: missing or placeholder")
                warnings += 1
        for key in optional_keys:
            val = env_vars.get(key, "")
            if val and "poner_aqui" not in val:
                ok(f"{key}: present (optional)")
    else:
        fail(".env file missing")
        errors += 1

    # 5. Artifact Integrity (Generated from spec — do not edit)
    print(f"\n{BOLD}5. Artifact Integrity{RESET}")
    try:
        db = HarnessDB(db_path)
        conn = db.connect()
        cur = conn.execute(
            "SELECT id, file_path FROM artifacts WHERE is_generated_from_spec = 1"
        )
        artifacts = cur.fetchall()
        if artifacts:
            for art in artifacts:
                if db.check_artifact_integrity(art['id']):
                    ok(f"Artifact #{art['id']}: {os.path.basename(art['file_path'])} integrity OK")
                else:
                    # Check if file still exists
                    if os.path.exists(art['file_path']):
                        fail(f"Artifact #{art['id']}: {art['file_path']} was MODIFIED manually!")
                        errors += 1
                    else:
                        fail(f"Artifact #{art['id']}: {art['file_path']} MISSING!")
                        errors += 1
        else:
            ok("No generated artifacts to verify (yet)")
        db.close()
    except Exception as e:
        warn(f"Could not verify artifacts: {e}")

    # 6. Task Consistency Check
    print(f"\n{BOLD}6. Task Consistency{RESET}")
    try:
        db = HarnessDB(db_path)
        summary = db.get_project_summary()
        print(f"  Tasks: {summary['tasks']['total']} total "
              f"({summary['tasks']['pending']} pending, "
              f"{summary['tasks']['in_progress']} in_progress, "
              f"{summary['tasks']['done']} done, "
              f"{summary['tasks']['blocked']} blocked)")

        # Check for stalled in_progress tasks
        conn = db.connect()
        cur = conn.execute(
            "SELECT code, title, assignee, updated_at FROM tasks "
            "WHERE status = 'in_progress'"
        )
        stalled = cur.fetchall()
        if stalled:
            for t in stalled:
                warn(f"Task '{t['code']}' still in_progress (assignee: {t['assignee']}, "
                     f"updated: {t['updated_at']})")
                warnings += 1
        db.close()
    except Exception as e:
        warn(f"Could not check task consistency: {e}")

    # Summary
    print(f"\n{'='*50}")
    if errors == 0 and warnings == 0:
        print(f"  {GREEN}{BOLD}VERDICT: Everything OK. Ready to work.{RESET}")
    elif errors == 0 and warnings > 0:
        print(f"  {YELLOW}{BOLD}VERDICT: {warnings} warning(s). Can proceed but review suggestions.{RESET}")
        exit_code = 1
    else:
        print(f"  {RED}{BOLD}VERDICT: {errors} error(s), {warnings} warning(s). Fix before proceeding.{RESET}")
        exit_code = 2
    print(f"{'='*50}\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(verify())
