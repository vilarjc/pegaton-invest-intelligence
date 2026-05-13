#!/usr/bin/env python3
"""
Provider Model & Price Checker
Verifica diariamente nombres de modelos, precios y disponibilidad
en DeepSeek, OpenRouter, Groq y Gemini. Sin LLM. Solo curl + parsing.

Uso: python3 backend/scripts/provider_check.py [--alert]
  --alert: enviar alerta si hay cambios detectados
"""

import json, os, sys, re, subprocess, time
from datetime import datetime, timezone
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load credentials from .env
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")
SNAPSHOT_FILE = os.path.join(DATA_DIR, "model_snapshot.json")
CHANGE_LOG_FILE = os.path.join(DATA_DIR, "model_changes.log")
LOG_FILE = "/tmp/provider_check.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def curl(url, timeout=15, post_data=None, content_type=None):
    try:
        cmd = ["curl", "-sL", "--max-time", str(timeout)]
        if post_data:
            cmd.extend(["-X", "POST", "-d", post_data])
            if content_type:
                cmd.extend(["-H", f"Content-Type: {content_type}"])
        cmd.append(url)
        r = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout+5
        )
        return r.stdout, r.returncode
    except Exception as e:
        return "", -1

def parse_deepseek_pricing(html):
    """Extract prices from DeepSeek pricing page HTML."""
    result = {"source": "https://api-docs.deepseek.com/quick_start/pricing", "fetched_at": datetime.now(timezone.utc).isoformat()}
    
    # Extract flash prices from the HTML table
    flash = {}
    
    # Cache hit: look for $0.0028
    m = re.search(r'\$0\.0028', html)
    if m:
        flash["input_cache_hit"] = 0.0028
    
    # Cache miss: look for $0.14
    m = re.search(r'1M INPUT TOKENS \(CACHE MISS\)[^<]*</td><td>\$([0-9.]+)', html, re.DOTALL)
    if m:
        flash["input_cache_miss"] = float(m.group(1))
    
    m = re.search(r'1M OUTPUT TOKENS[^<]*</td><td>\$([0-9.]+)', html, re.DOTALL)
    if m:
        flash["output"] = float(m.group(1))
    
    m = re.search(r'1M INPUT TOKENS \(CACHE HIT\)[^<]*</td><td>\$([0-9.]+)', html, re.DOTALL)
    if m:
        flash["input_cache_hit"] = float(m.group(1))
    
    # Context length
    m = re.search(r'CONTEXT LENGTH[^<]*</td><td[^>]*>([0-9.KM]+)', html)
    if m:
        flash["context_length"] = m.group(1).strip()
    
    # Pro discount info
    pro = {}
    m = re.search(r'75%.*?discount.*?extended until ([^<]*)', html, re.IGNORECASE)
    if m:
        pro["discount_note"] = f"75% off extended until {m.group(1).strip()}"
    
    m = re.search(r'V4.pro[^<]*?</td><td>\$([0-9.]+)', html, re.DOTALL)
    if m:
        pro["input_cache_miss"] = float(m.group(1))
    
    # Deprecation note
    m = re.search(r'will be discontinued in three months[^)]*\)', html)
    deprecation = m.group(0) if m else "Not found"
    
    result["deepseek-v4-flash"] = flash
    result["deepseek-v4-pro"] = pro if pro else {"note": "Not parsed - check manually"}
    result["deprecation_note"] = deprecation
    return result

def fetch_openrouter_models():
    """Get free models from OpenRouter."""
    data, rc = curl("https://openrouter.ai/api/v1/models")
    if rc != 0 or not data:
        return {"error": f"HTTP status {rc}"}
    
    try:
        models = json.loads(data)
    except json.JSONDecodeError:
        # Try to find JSON in response
        m = re.search(r'(\{.*\})', data, re.DOTALL)
        if m:
            try:
                models = json.loads(m.group(1))
            except:
                return {"error": "JSON parse failed"}
        else:
            return {"error": "JSON parse failed"}
    
    free_models = []
    all_models = []
    
    if isinstance(models, dict) and "data" in models:
        for m in models["data"]:
            pricing = m.get("pricing", {})
            prompt_price = float(pricing.get("prompt", 1))
            completion_price = float(pricing.get("completion", 1))
            is_free = prompt_price == 0 and completion_price == 0
            entry = {
                "id": m.get("id"),
                "name": m.get("name", m.get("id")),
                "free": is_free,
                "pricing": pricing,
                "context_length": m.get("context_length"),
            }
            all_models.append(entry)
            if is_free:
                free_models.append(entry)
    
    return {
        "source": "https://openrouter.ai/api/v1/models",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(all_models),
        "free_models_count": len(free_models),
        "free_models": [m["id"] for m in free_models],
        "all_model_ids": [m["id"] for m in all_models],
    }

def fetch_groq_models():
    """Get models from Groq."""
    key = os.environ.get("GROQ_API_KEY", "")
    headers = []
    if key:
        headers = ["-H", f"Authorization: Bearer {key}"]
    
    cmd = ["curl", "-sL", "--max-time", "15"] + headers + ["https://api.groq.com/openai/v1/models"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        data, rc = r.stdout, r.returncode
    except Exception as e:
        return {"error": str(e)}
    
    if rc != 0 or not data:
        return {"error": f"HTTP status {rc}"}
    
    try:
        result = json.loads(data)
    except:
        return {"error": "JSON parse failed"}
    
    models = []
    for m in result.get("data", []):
        models.append({
            "id": m.get("id"),
            "owned_by": m.get("owned_by"),
            "created": m.get("created"),
        })
    
    return {
        "source": "https://api.groq.com/openai/v1/models",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_models": len(models),
        "models": models,
    }

def check_gemini_free_tier():
    """Check which Gemini models are actually usable for chat (free tier).
    Model metadata endpoint returns 200 even if chat completions give 429."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return {"error": "No GEMINI_API_KEY"}
    
    models_to_check = [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-pro",
    ]
    
    results = {}
    for model in models_to_check:
        # Test actual chat completion (lightweight)
        chat_data, chat_rc = curl(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            timeout=10,
            post_data='{"contents":[{"parts":[{"text":"Say OK, one word only"}]}]}',
            content_type="application/json"
        )
        
        if chat_rc == 0 and chat_data:
            try:
                info = json.loads(chat_data)
                if "candidates" in info:
                    results[model] = {
                        "available": True,
                        "status": "OK",
                        "chat_works": True,
                    }
                elif "error" in info:
                    err_msg = info["error"].get("message", str(info))
                    results[model] = {
                        "available": True,
                        "status": f"Chat blocked: {err_msg[:100]}",
                        "chat_works": False,
                    }
                else:
                    results[model] = {"available": True, "status": "unexpected response", "chat_works": False}
            except:
                results[model] = {"available": True, "status": "unparseable", "chat_works": False}
        elif chat_rc == 429:
            results[model] = {"available": False, "status": "429 Rate Limited (free tier blocked)"}
        else:
            results[model] = {"available": False, "status": f"HTTP {chat_rc}"}
    
    return {
        "source": "Gemini API (chat test)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "models": results,
    }

def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE) as f:
                return json.load(f)
        except:
            return None
    return None

def save_snapshot(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def log_changes(changes):
    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CHANGE_LOG_FILE, "a") as f:
        f.write(f"\n{'='*60}\n[{ts}] PROVIDER CHANGES DETECTED\n{'='*60}\n")
        for change in changes:
            f.write(f"• {change}\n")

def compare_snapshots(old, new):
    changes = []
    
    # Compare DeepSeek pricing
    old_ds = old.get("deepseek", {})
    new_ds = new.get("deepseek", {})
    for key in new_ds:
        if key in ("source", "fetched_at", "deprecation_note"):
            continue
        old_model = old_ds.get(key, {})
        new_model = new_ds.get(key, {})
        # Normalize: remove fetched_at from nested dicts too
        if isinstance(old_model, dict):
            old_model = {k: v for k, v in old_model.items() if k not in ("source", "fetched_at")}
        if isinstance(new_model, dict):
            new_model = {k: v for k, v in new_model.items() if k not in ("source", "fetched_at")}
        if old_model != new_model:
            changes.append(f"DeepSeek {key}: {json.dumps(old_model)} → {json.dumps(new_model)}")
    
    # Compare OpenRouter free models
    old_or_free = set(old.get("openrouter", {}).get("free_models", []))
    new_or_free = set(new.get("openrouter", {}).get("free_models", []))
    added = new_or_free - old_or_free
    removed = old_or_free - new_or_free
    if added:
        changes.append(f"OpenRouter nuevos gratuitos: {', '.join(sorted(added))}")
    if removed:
        changes.append(f"OpenRouter ya no gratuitos: {', '.join(sorted(removed))}")
    
    old_or_count = old.get("openrouter", {}).get("total_models", 0)
    new_or_count = new.get("openrouter", {}).get("total_models", 0)
    if old_or_count and old_or_count != new_or_count:
        changes.append(f"OpenRouter total models: {old_or_count} → {new_or_count}")
    
    # Compare Groq models
    old_groq_ids = set(m["id"] for m in old.get("groq", {}).get("models", []))
    new_groq_ids = set(m["id"] for m in new.get("groq", {}).get("models", []))
    added_g = new_groq_ids - old_groq_ids
    removed_g = old_groq_ids - new_groq_ids
    if added_g:
        changes.append(f"Groq nuevos: {', '.join(sorted(added_g))}")
    if removed_g:
        changes.append(f"Groq eliminados: {', '.join(sorted(removed_g))}")
    
    # Compare Gemini availability
    old_gem = old.get("gemini", {}).get("models", {})
    new_gem = new.get("gemini", {}).get("models", {})
    for model, info in new_gem.items():
        old_info = old_gem.get(model, {})
        if old_info.get("available") != info.get("available"):
            changes.append(f"Gemini {model}: {'disponible' if info.get('available') else 'NO disponible'} (antes: {'disponible' if old_info.get('available') else 'NO disponible'})")
    
    return changes

def main():
    alert_mode = "--alert" in sys.argv
    log("=== Provider Check Start ===")
    
    snapshot = {"fetched_at": datetime.now(timezone.utc).isoformat()}
    
    # 1. DeepSeek pricing
    log("🔍 Checking DeepSeek pricing...")
    html, rc = curl("https://api-docs.deepseek.com/quick_start/pricing")
    if rc == 0:
        ds = parse_deepseek_pricing(html)
        snapshot["deepseek"] = ds
        flash = ds.get("deepseek-v4-flash", {})
        if flash.get("input_cache_hit"):
            log(f"  ✅ V4 Flash: cache hit=${flash['input_cache_hit']}/M, miss=${flash.get('input_cache_miss', '?')}/M, out=${flash.get('output', '?')}/M")
        else:
            log(f"  ⚠️ V4 Flash: parsing incomplete: {flash}")
    else:
        snapshot["deepseek"] = {"error": f"HTTP {rc}"}
        log(f"  ❌ DeepSeek pricing page: HTTP {rc}")
    
    # Check changelog for announcements
    changelog, rc2 = curl("https://api-docs.deepseek.com/updates")
    if rc2 == 0:
        # Extract latest update date
        dates = re.findall(r'Date:\s*(\d{4}-\d{2}-\d{2})', changelog)
        if dates:
            snapshot["deepseek_latest_update"] = dates[0]
            log(f"  📅 Latest DeepSeek update: {dates[0]}")
    
    # 2. OpenRouter models
    log("🔍 Checking OpenRouter models...")
    or_data = fetch_openrouter_models()
    snapshot["openrouter"] = or_data
    if "error" not in or_data:
        log(f"  ✅ {or_data['total_models']} models, {or_data['free_models_count']} free")
        log(f"  Free: {', '.join(or_data['free_models'][:5])}{'...' if len(or_data['free_models'])>5 else ''}")
    else:
        log(f"  ❌ OpenRouter: {or_data['error']}")
    
    # 3. Groq models
    log("🔍 Checking Groq models...")
    groq_data = fetch_groq_models()
    snapshot["groq"] = groq_data
    if "error" not in groq_data:
        log(f"  ✅ {groq_data['total_models']} models: {', '.join(m['id'] for m in groq_data['models'])}")
    else:
        log(f"  ❌ Groq: {groq_data['error']}")
    
    # 4. Gemini availability
    log("🔍 Checking Gemini free tier models...")
    gem_data = check_gemini_free_tier()
    snapshot["gemini"] = gem_data
    if "error" not in gem_data:
        for model, info in gem_data["models"].items():
            status = "✅" if info.get("available") else "❌"
            log(f"  {status} {model}: {info.get('status', '?')}")
    else:
        log(f"  ❌ Gemini: {gem_data['error']}")
    
    # 5. Compare with previous snapshot
    old = load_snapshot()
    if old:
        changes = compare_snapshots(old, snapshot)
        if changes:
            log(f"\n⚠️  {len(changes)} CHANGE(S) DETECTED:")
            for c in changes:
                log(f"  • {c}")
            log_changes(changes)
            if alert_mode:
                # Write alert file for cron delivery
                alert_file = "/tmp/provider_change_alert.txt"
                with open(alert_file, "w") as f:
                    f.write(f"Provider changes detected ({datetime.now().strftime('%Y-%m-%d %H:%M')}):\n")
                    for c in changes:
                        f.write(f"  • {c}\n")
                log(f"  📝 Alert written to {alert_file}")
        else:
            log("\n✅ No changes detected")
    else:
        log("\n📝 First snapshot saved (no comparison yet)")
    
    # 6. Save new snapshot
    save_snapshot(snapshot)
    log(f"💾 Snapshot saved ({len(json.dumps(snapshot))} bytes)")
    log("=== Provider Check Complete ===")

if __name__ == "__main__":
    main()
