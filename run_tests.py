#!/usr/bin/env python3
"""Wrapper para ejecutar tests unitarios desde el directorio raíz."""
import sys, os, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Ejecutar pytest
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short', '-x'],
    capture_output=True, text=True, cwd=os.getcwd()
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:])
sys.exit(result.returncode)