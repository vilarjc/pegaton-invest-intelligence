#!/usr/bin/env python3
"""Fear & Greed Index — Endpoint + Datos VIX/Macro/RSS"""
import json, os, re, time
from datetime import datetime, timedelta
from pathlib import Path

CACHE_FILE = "/tmp/fear_greed_cache.json"
CACHE_TTL = 3600  # 1 hora

def get_vix():
    """VIX from Yahoo Finance via yfinance"""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return None, None
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        return current, current - prev
    except:
        return None, None

def get_macro():
    """Macro indicators from FRED"""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return {}
    
    results = {}
    series = {
        "CPIAUCSL": "IPC",
        "UNRATE": "Desempleo",
        "FEDFUNDS": "Tasa Fed",
        "PPIACO": "IPP"
    }
    
    for sid, name in series.items():
        try:
            import requests
            r = requests.get(
                f"https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": sid, "api_key": api_key, "file_type": "json", "sort_order": "desc", "limit": 3},
                timeout=10
            )
            if r.ok:
                data = r.json()
                obs = data.get("observations", [])
                if obs:
                    val = float(obs[0]["value"])
                    prev_val = float(obs[1]["value"]) if len(obs) > 1 else val
                    results[name] = {"value": val, "change": val - prev_val}
        except:
            pass
    return results

def rss_sentiment():
    """Basic RSS sentiment from financial news headers"""
    try:
        import requests
        from xml.etree import ElementTree
        
        feeds = [
            "https://feeds.content.dowjones.io/public/rss/mw_topstories",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"
        ]
        
        positive_words = {"sube", "gana", "recupera", "crece", "alza", "rally", "optimismo", "acuerdo",
                         "estable", "crecimiento", "empleo", "inversión", "dividendo", "beneficio"}
        negative_words = {"cae", "pierde", "desploma", "tensión", "guerra", "tarifas", "inflación",
                         "recesión", "crisis", "miedo", "incertidumbre", "desempleo", "baja"}
        
        pos = 0
        neg = 0
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
            except:
                continue
        
        total = pos + neg
        if total == 0:
            return 50, pos, neg
        return int((pos / total) * 100), pos, neg
    except:
        return 50, 0, 0

def compute_fear_greed():
    """Compute 0-100 Fear & Greed index with factor breakdown"""
    factors = {}
    
    # VIX
    vix_val, vix_change = get_vix()
    if vix_val:
        # VIX < 12 = greed (score ~90), VIX > 30 = fear (score ~10)
        vix_score = max(0, min(100, int(100 - (vix_val - 10) * 4)))
        factors["VIX"] = {"score": vix_score, "value": vix_val, "change": vix_change,
                          "label": f"VIX {vix_val:.1f}"}
    
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
        factors[name] = {"score": s, "value": val, "change": data["change"],
                         "label": f"{name} {val:.1f}"}
    
    # Sentiment
    sent_score, pos, neg = rss_sentiment()
    factors["Noticias"] = {"score": sent_score, "value": f"{sent_score}%", "change": None,
                           "label": f"Sentimiento {pos}↑ {neg}↓"}
    
    # Composite score
    scores = [f["score"] for f in factors.values()]
    if scores:
        total = sum(scores) / len(scores)
    else:
        total = 50
    
    # Action based on score
    score_val = int(total)
    if score_val <= 25:
        action = "Miedo extremo"
    elif score_val <= 45:
        action = "Miedo"
    elif score_val <= 55:
        action = "Neutral"
    elif score_val <= 75:
        action = "Codicia"
    else:
        action = "Codicia extrema"
    
    emoji_map = {"Miedo extremo": "🟠", "Miedo": "🟡", "Neutral": "⚪", "Codicia": "🟢", "Codicia extrema": "🔵"}
    
    return {
        "score": score_val,
        "action": action,
        "action_emoji": emoji_map.get(action, "⚪"),
        "timestamp": datetime.now().isoformat(),
        "factores": {
            "vix": {"value": vix_val, "score": round(vix_score, 1), "peso": "40%%"} if vix_val else None,
            "macro": {"score": round(sum(macro_scores)/len(macro_scores), 1), "peso": "35%%", "detalles": {
                k: {"value": v["value"], "score": s} for k, v, s in zip(macro.keys(), macro.values(), macro_scores)
            }} if macro else None,
            "sentimiento": {"score": float(sent_score), "peso": "25%%", "detalles": {
                "feeds": {"count": {"articles": pos + neg, "positive": pos, "negative": neg}}
            }}
        },
        "cacheado": True
    }

def get_cached():
    """Cache results for CACHE_TTL seconds"""
    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < CACHE_TTL:
            with open(CACHE_FILE) as f:
                return json.load(f)
    
    data = compute_fear_greed()
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return data

if __name__ == "__main__":
    result = get_cached()
    print(json.dumps(result, indent=2, default=str))
