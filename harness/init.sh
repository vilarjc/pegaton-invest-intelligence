#!/bin/bash
# ============================================================================
# HARNESS INIT — Entry point verification script (see Harness Engineering)
# ============================================================================
# Run this at the start of every agent session to verify the environment.
# Exit code: 0 = OK, 1 = warnings, 2 = errors
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   HARNESS — Initializing Session     ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Ensure we're in the right place
if [ ! -f "harness/harness_db.py" ]; then
    echo "ERROR: harness/harness_db.py not found at $PROJECT_ROOT"
    exit 2
fi

# Activate venv if available
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Run verification
python harness/db_verify.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "❌ Environment checks failed. Cannot proceed."
    exit 2
fi

echo "✅ Harness session ready."
exit $EXIT_CODE
