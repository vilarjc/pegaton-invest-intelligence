#!/usr/bin/env python3
"""Health check server — sin LLM, solo curl + restart si falla."""
import subprocess, os, sys, time
from datetime import datetime

SERVER_DIR = "/root/pegaton_invest_intelligence"
LOG_FILE = "/tmp/pegaton_health.log"
HEALTH_URL = "http://localhost:8000/health"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    log("=== Health Check ===")

    # 1. Check if server responds
    rc, out, err = run(f"curl -s --max-time 5 {HEALTH_URL}")
    
    if rc == 0 and '"status":"ok"' in out:
        log("✅ Server healthy")
        return 0

    if rc == 0:
        log(f"⚠️ Server responded but unexpected: {out[:200]}")
    else:
        log(f"❌ Server unreachable: curl exit={rc}, err={err[:200]}")
    
    # 2. Try to restart
    log("🔄 Attempting restart...")
    restart_cmd = (
        f"cd {SERVER_DIR} && source venv/bin/activate && "
        f"nohup python backend/app/main.py > /tmp/pegaton_server.log 2>&1 &"
    )
    rc2, out2, err2 = run(restart_cmd)
    time.sleep(3)
    
    # 3. Verify restart
    rc3, out3, _ = run(f"curl -s --max-time 5 {HEALTH_URL}")
    if rc3 == 0:
        log("✅ Server restarted successfully")
    else:
        log(f"❌ Server restart FAILED: {err2[:200]}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
