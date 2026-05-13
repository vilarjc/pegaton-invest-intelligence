#!/usr/bin/env python3
"""
Download Fear & Greed data — pure Python, NO LLM.
Reads VIX (yfinance), macro (FRED if available), RSS sentiment.
Saves to harness.db fear_greed_snapshots table.
Runs autonomously via crontab.
"""
import json, os, sys, time
from datetime import datetime

PROJECT_DIR = "/root/pegaton_invest_intelligence"
sys.path.insert(0, PROJECT_DIR)

DB_PATH = os.path.join(PROJECT_DIR, "harness.db")

# ── DB helpers ──

def init_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS fear_greed_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        score INTEGER NOT NULL,
        action TEXT NOT NULL DEFAULT 'Neutral',
        vix_value REAL,
        vix_score REAL,
        macro_score REAL,
        macro_details TEXT,
        sent_score REAL,
        sent_details TEXT,
        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def save_snapshot(data):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    factores = data.get("factores", {})
    vix_info = factores.get("vix") or {}
    macro_info = factores.get("macro") or {}
    sent_info = factores.get("sentimiento") or {}
    
    conn.execute("""INSERT INTO fear_greed_snapshots 
        (score, action, vix_value, vix_score, macro_score, macro_details, sent_score, sent_details, full_response)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            data.get("score", 50),
            data.get("action", "Neutral"),
            vix_info.get("value"),
            vix_info.get("score"),
            macro_info.get("score"),
            json.dumps(macro_info.get("detalles", {})) if macro_info.get("detalles") else None,
            sent_info.get("score"),
            json.dumps(sent_info.get("detalles", {})) if sent_info.get("detalles") else None,
            json.dumps(data, default=str),
        )
    )
    conn.commit()
    conn.close()
    print(f"✅ Saved: score={data.get('score')}, action={data.get('action')}, vix={vix_info.get('value')}")

# ── Data collection ──

def get_vix():
    """VIX from Yahoo Finance"""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return None, None
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        return current, current - prev
    except Exception as e:
        print(f"  ⚠ VIX error: {e}")
        return None, None

def get_macro():
    """Macro indicators from FRED (optional, needs FRED_API_KEY)"""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return {}
    results = {}
    series = {
        "CPIAUCSL": "IPC",
        "UNRATE": "Desempleo",
        "FEDFUNDS": "Tasa Fed",
    }
    for sid, name in series.items():
        try:
            import requests
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": sid, "api_key": api_key, "file_type": "json",
                        "sort_order": "desc", "limit": 3},
                timeout=10
            )
            if r.ok:
                data = r.json()
                obs = data.get("observations", [])
                if obs:
                    val = float(obs[0]["value"])
                    prev_val = float(obs[1]["value"]) if len(obs) > 1 else val
                    results[name] = {"value": val, "change": val - prev_val}
        except Exception as e:
            print(f"  ⚠ {name} error: {e}")
    return results

def rss_sentiment():
    """Basic RSS sentiment from financial news headers"""
    try:
        import requests
        from xml.etree import ElementTree
        
        feeds = [
            "https://feeds.content.dowjones.io/public/rss/mw_topstories",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        ]
        
        positive_words = {"sube", "gana", "recupera", "crece", "alza", "rally", "optimismo", "acuerdo",
                         "estable", "crecimiento", "empleo", "inversión", "dividendo", "beneficio",
                         "gains", "rally", "bullish", "recovery", "growth", "record", "positive"}
        negative_words = {"cae", "pierde", "desploma", "tensión", "guerra", "tarifas", "inflación",
                         "recesión", "crisis", "miedo", "incertidumbre", "desempleo", "baja",
                         "declines", "losses", "bearish", "recession", "crash", "fear", "uncertainty"}
        
        pos, neg = 0, 0
        seen = set()
        
        for feed_url in feeds:
            try:
                r = requests.get(feed_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                if not r.ok: continue
                root = ElementTree.fromstring(r.content)
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    if not title or title in seen: continue
                    seen.add(title)
                    title_lower = title.lower()
                    for w in positive_words:
                        if w in title_lower: pos += 1
                    for w in negative_words:
                        if w in title_lower: neg += 1
            except Exception as e:
                print(f"  ⚠ RSS error ({feed_url[:30]}...): {e}")
                continue
        
        total = pos + neg
        if total == 0:
            return 50, pos, neg
        return int((pos / total) * 100), pos, neg
    except Exception as e:
        print(f"  ⚠ RSS error: {e}")
        return 50, 0, 0

def compute():
    """Compute fear & greed composite score"""
    factors = {}
    
    # VIX → score (VIX < 12 = greed ~90, VIX > 30 = fear ~10)
    vix_val, vix_change = get_vix()
    if vix_val:
        vix_score = max(0, min(100, int(100 - (vix_val - 10) * 4)))
        factors["VIX"] = {"score": vix_score, "value": vix_val, "change": vix_change}
        print(f"  VIX: {vix_val:.1f} → score {vix_score}")
    
    # Macro
    macro = get_macro()
    macro_scores = []
    for name, data in macro.items():
        val = data["value"]
        if name == "IPC":
            s = max(0, min(100, int(100 - abs(val - 2) * 15)))
        elif name == "Desempleo":
            s = max(0, min(100, int(100 - abs(val - 4) * 20)))
        elif name == "Tasa Fed":
            s = max(0, min(100, int(60 - val * 3)))
        else:
            s = 50
        macro_scores.append(s)
        factors[name] = {"score": s, "value": val, "change": data["change"]}
        print(f"  {name}: {val} → score {s}")
    
    # Sentiment
    sent_score, pos, neg = rss_sentiment()
    factors["Noticias"] = {"score": sent_score, "articles_pos": pos, "articles_neg": neg}
    print(f"  Noticias: {pos}↑ {neg}↓ → score {sent_score}")
    
    # Composite
    scores = [f["score"] for f in factors.values()]
    total = sum(scores) / len(scores) if scores else 50
    score_val = int(total)
    
    if score_val <= 25: action = "Miedo extremo"
    elif score_val <= 45: action = "Miedo"
    elif score_val <= 55: action = "Neutral"
    elif score_val <= 75: action = "Codicia"
    else: action = "Codicia extrema"
    
    emoji_map = {"Miedo extremo": "🔴", "Miedo": "🟠", "Neutral": "⚪", "Codicia": "🟢", "Codicia extrema": "🔵"}
    
    result = {
        "score": score_val,
        "action": action,
        "action_emoji": emoji_map.get(action, "⚪"),
        "timestamp": datetime.now().isoformat(),
        "cacheado": True,
        "factores": {
            "vix": {"value": vix_val, "score": round(vix_score, 1), "peso": "40%"} if vix_val else None,
            "macro": {"score": round(sum(macro_scores)/len(macro_scores), 1), "peso": "35%", "detalles": {
                k: {"value": v["value"], "score": s} for k, v, s in zip(macro.keys(), macro.values(), macro_scores)
            }} if macro_scores else None,
            "sentimiento": {"score": float(sent_score), "peso": "25%", "detalles": {
                "total_articles": pos + neg,
                "total_positive": pos,
                "total_negative": neg,
                "positive": pos,
                "negative": neg,
                "sentiment_pct": float(sent_score),
                "feeds": {"articles_total": pos + neg, "positive": pos, "negative": neg}
            }}
        }
    }
    return result

# ── Main ──

def main():
    print(f"📥 Fear & Greed downloader — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   PID: {os.getpid()}")
    
    init_db()
    data = compute()
    save_snapshot(data)
    print(f"\n📊 Score: {data['score']}/100 — {data['action_emoji']} {data['action']}")

if __name__ == "__main__":
    main()
