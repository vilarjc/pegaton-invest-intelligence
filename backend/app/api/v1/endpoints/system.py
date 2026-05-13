"""System health, processes, and budget endpoints for the command center."""
from fastapi import APIRouter
import os, json, subprocess, psutil

router = APIRouter()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
BUDGET_PATH = os.path.join(PROJECT_ROOT, 'data', 'budget_tracker.json')

@router.get("/health")
async def system_health():
    """Returns server metrics: CPU, RAM, disk, uptime."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime_seconds = int(psutil.boot_time())
        return {
            "status": "healthy",
            "cpu": {"percent": cpu, "cores": psutil.cpu_count()},
            "ram": {"total_gb": round(ram.total / 1e9, 1), "used_gb": round(ram.used / 1e9, 1), "percent": ram.percent},
            "disk": {"total_gb": round(disk.total / 1e9, 1), "used_gb": round(disk.used / 1e9, 1), "percent": disk.percent},
            "uptime_seconds": uptime_seconds,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/services")
async def service_status():
    """Checks if key services are running."""
    result = {
        "api_server": {"running": True, "port": 8000},
        "database": {"path": os.path.join(PROJECT_ROOT, 'data', 'pegaton.db'), "exists": os.path.exists(os.path.join(PROJECT_ROOT, 'data', 'pegaton.db'))},
    }
    # Check if cron jobs are defined (via hermes)
    jobs_path = os.path.expanduser('~/.hermes/cron/jobs.json')
    if os.path.exists(jobs_path):
        try:
            with open(jobs_path) as f:
                jobs = json.load(f)
            result["cron_jobs"] = {"count": len(jobs), "jobs": [{"name": j.get('name','unnamed'), "schedule": j.get('schedule',''), "enabled": j.get('enabled',False)} for j in jobs[:10]]}
        except:
            result["cron_jobs"] = {"count": 0}
    else:
        result["cron_jobs"] = {"count": 0}
    return result

@router.get("/budget")
async def budget_status():
    """Returns budget data from DeepSeek real-time balance + local history."""
    import requests
    ds_key = os.getenv('DEEPSEEK_API_KEY', '')
    if not ds_key:
        return {'error': 'DEEPSEEK_API_KEY not configured'}
    try:
        resp = requests.get(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {ds_key}"},
            timeout=10
        )
        balance_data = resp.json() if resp.status_code == 200 else {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        balance_data = {"error": str(e)}
    
    # Read balance history
    hist_path = os.path.join(PROJECT_ROOT, 'data', 'balance_history.json')
    history = []
    if os.path.exists(hist_path):
        try:
            with open(hist_path) as f:
                history = json.load(f)
        except: pass
    
    # Read local budget tracker
    tracker = {}
    if os.path.exists(BUDGET_PATH):
        try:
            with open(BUDGET_PATH) as f:
                tracker = json.load(f)
        except: pass
    
    # Calculate spending
    total_balance = 0.0
    if balance_data.get("is_available"):
        for info in balance_data.get("balance_infos", []):
            if info.get("currency") == "USD":
                total_balance = float(info["total_balance"])
    
    topped_up = 0.0
    if balance_data.get("is_available"):
        for info in balance_data.get("balance_infos", []):
            if info.get("currency") == "USD":
                topped_up = float(info["topped_up_balance"])
    
    spent = round(topped_up - total_balance, 2) if topped_up > 0 else 0
    
    return {
        "live_balance": total_balance,
        "topped_up": topped_up,
        "spent": max(0, spent),
        "currency": "USD",
        "balance_history": history[-30:] if history else [],
        "tracker": tracker,
    }

@router.get("/database-stats")
async def database_stats():
    """Returns database table row counts."""
    import sqlite3
    db_path = os.path.join(PROJECT_ROOT, 'data', 'pegaton.db')
    if not os.path.exists(db_path):
        return {"error": "Database not found"}
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    tables = ['macro_indicators', 'precios_ohlcv']
    stats = {}
    for table in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            # Different tables have different date column names
            date_col = 'date' if table == 'macro_indicators' else 'timestamp'
            c.execute(f"SELECT MAX({date_col}) FROM {table}")
            max_date = c.fetchone()[0]
            stats[table] = {"rows": count, "latest_date": max_date}
        except:
            stats[table] = {"rows": 0, "latest_date": None}
    conn.close()
    return stats
