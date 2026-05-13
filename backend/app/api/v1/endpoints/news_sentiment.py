"""
News Sentiment API Endpoint — /api/v1/news-sentiment
Extiende el endpoint con datos completos para el widget del inversor.
SDD Nivel 2: spec definida en PROMPT_PROGRAMADOR_NEWS_SENTIMIENTO.md
"""
import re, os, sys
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from harness.harness_db import HarnessDB

router = APIRouter()

# ── Stopwords ──────────────────────────────────────────────────────
STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "must","can","shall","not","no","nor","so","if","then","than","that",
    "this","these","those","it","its","they","them","their","what","which",
    "who","whom","how","when","where","why","all","each","every","both",
    "few","more","most","other","some","such","only","own","same","too",
    "very","just","because","as","until","while","during","before","after",
    "above","below","between","through","about","into","over","under",
    "again","further","once","here","there","up","out","off","also",
    "new","now","many","much","one","two","three","still","even","down",
    "back","get","got","like","need","want","year","years","time","today",
    "week","month","day","days","said","nbsp","href","src","img","alt","title","class","style","div","span",
    "says","reported","according","based","including","includes","included",
}

_html_re = re.compile(r"<[^>]+>")
_url_re = re.compile(r"https?://\S+")

def _strip_html(text):
    """Remove HTML tags, URLs, and decode entities."""
    if not text:
        return ""
    text = _url_re.sub(" ", text)
    text = _html_re.sub(" ", text)
    for entity, char in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),
                         ("&gt;",">"),("&quot;",'"'),("&#39;","'")]:
        text = text.replace(entity, char)
    return text

# Nombres canónicos — matchea el título real del feed en la DB
_SOURCE_MAP = {
    "Google News": "Google News",
    "Reuters": "Reuters",
    "CNBC": "CNBC",
    "MarketWatch": "MarketWatch",
    "X/Twitter": "X/Twitter",
    "Business - Latest": "Google News",
    "US Top News": "Reuters",
    "Top Stories": "MarketWatch",
}

def _clean_source(src):
    """Normaliza nombre de fuente desde DB."""
    s = (src or "").strip()
    # Buscar coincidencia parcial
    for key, name in _SOURCE_MAP.items():
        if key.lower() in s.lower():
            return name
    # Fallback: tomar primera palabra significativa
    parts = s.split(" - ")
    if parts:
        return parts[0].strip() or s
    return s


def analyze_articles(conn, hours=72):
    """Analiza artículos recientes y extrae sources, keywords, distribution."""
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    rows = conn.execute("""
        SELECT source, title, summary, sentiment_score
        FROM news_sentiment
        WHERE captured_at > ?
        ORDER BY captured_at DESC
    """, (cutoff,)).fetchall()

    if not rows:
        return None

    total = len(rows)
    sources = Counter()
    all_words = Counter()
    fear = neutral = greed = 0

    for row in rows:
        src = _clean_source(row["source"])
        sources[src] += 1

        title_clean = _strip_html(row["title"] or "")
        summary_clean = _strip_html(row["summary"] or "")
        text = f"{title_clean} {summary_clean}".lower()
        # Solo palabras alfabéticas de 4+ chars
        words = re.findall(r"[a-záéíóúñ]{4,}", text)
        words = [w for w in words if w not in STOPWORDS]
        all_words.update(words)

        score = row["sentiment_score"] or 50
        if score < 40:
            fear += 1
        elif score > 60:
            greed += 1
        else:
            neutral += 1

    sources_dict = dict(sources.most_common(10))
    keywords = [{"word": w, "count": c} for w, c in all_words.most_common(10)]

    return {
        "sources": sources_dict,
        "top_keywords": keywords,
        "distribution": {"fear": fear, "neutral": neutral, "greed": greed},
        "total_articles": total,
    }


@router.get("/news-sentiment")
async def get_news_sentiment(force_refresh: bool = Query(False, alias="force")):
    """
    Retorna el índice de sentimiento de noticias con desglose completo.
    """
    db = HarnessDB()
    conn = db.connect()

    try:
        latest_snap = conn.execute(
            "SELECT * FROM news_sentiment_snapshots ORDER BY captured_at DESC LIMIT 1"
        ).fetchone()

        needs_ingest = force_refresh or latest_snap is None
        if not needs_ingest:
            snap_time = datetime.fromisoformat(latest_snap["captured_at"])
            if (datetime.now() - snap_time).total_seconds() > 4 * 3600:
                needs_ingest = True

        if needs_ingest:
            from backend.scripts.ingest_news_sentiment import run_ingestion
            run_ingestion()
            conn = db.connect()

        latest = conn.execute(
            "SELECT * FROM news_sentiment_snapshots ORDER BY captured_at DESC LIMIT 1"
        ).fetchone()

        if latest is None:
            return {
                "score": 50, "delta": 0, "delta_pct": "0%",
                "alert": None, "total_articles": 0, "sources": {},
                "top_keywords": [],
                "distribution": {"fear": 0, "neutral": 0, "greed": 0},
                "timestamp": datetime.now().isoformat(),
                "status": "no_data"
            }

        score = latest["score"] or 50

        prev = conn.execute(
            "SELECT * FROM news_sentiment_snapshots ORDER BY captured_at DESC LIMIT 1 OFFSET 1"
        ).fetchone()

        if prev and prev["score"] is not None:
            delta = score - prev["score"]
            delta_pct = f"{int((delta / prev['score']) * 100):+d}%" if prev["score"] != 0 else f"{delta:+d}%"
        else:
            delta = 0
            delta_pct = "0%"

        alert = None
        if score < 20:
            alert = "EXTREME_FEAR"
        elif score > 80:
            alert = "EXTREME_GREED"

        analysis = analyze_articles(conn)

        return {
            "score": score,
            "delta": delta,
            "delta_pct": delta_pct,
            "alert": alert,
            "total_articles": analysis["total_articles"] if analysis else 0,
            "sources": analysis["sources"] if analysis else {},
            "top_keywords": analysis["top_keywords"] if analysis else [],
            "distribution": analysis["distribution"] if analysis else {"fear": 0, "neutral": 0, "greed": 0},
            "timestamp": latest["captured_at"] or datetime.now().isoformat(),
            "status": "ready"
        }
    finally:
        conn.close()