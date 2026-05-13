#!/usr/bin/python3
"""
Ingest News Sentiment — extracts news from configured RSS sources,
runs sentiment analysis (VADER lexicon), stores results in harness.db.
Designed for 0 LLM token operation via system crontab.
"""
import sys, os, json, yaml, hashlib, logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from harness.harness_db import HarnessDB

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "news_sources.yaml")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    log.warning(f"Config not found at {CONFIG_PATH}, using defaults")
    return {
        "sources": [
            {"name": "Google News", "type": "rss", "weight": 0.30, "enabled": True},
            {"name": "Reuters", "type": "rss", "weight": 0.25, "enabled": True},
            {"name": "CNBC", "type": "rss", "weight": 0.20, "enabled": True},
            {"name": "MarketWatch", "type": "rss", "weight": 0.15, "enabled": True},
            {"name": "Yahoo Finance", "type": "rss", "weight": 0.10, "enabled": True},
        ],
        "sentiment": {"method": "lexicon", "lexicon": "vader", "language": "en"},
        "update": {"max_articles_per_source": 20, "max_age_hours": 72},
        "scoring": {"compound_to_score": {"min": -1.0, "max": 1.0}}
    }

# ── RSS Fetching ──────────────────────────────────────────────────

def fetch_rss(url, max_articles=20):
    """Fetch RSS feed and extract title, description, link, pub_date."""
    import feedparser
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "") or entry.get("description", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", url),
            })
        return articles
    except Exception as e:
        log.error(f"RSS fetch error for {url}: {e}")
        return []

# ── Sentiment Analysis ───────────────────────────────────────────

def vader_sentiment(text):
    """Use VADER sentiment lexicon to compute sentiment score (0-100)."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        compound = analyzer.polarity_scores(text)["compound"]
        # Map compound (-1 to +1) to score (0-100)
        score = int((compound + 1) / 2 * 100)
        return max(0, min(100, score))
    except ImportError:
        log.warning("VADER not installed, falling back to simple keyword scoring")
        return simple_keyword_sentiment(text)

def simple_keyword_sentiment(text):
    """Simple keyword-based sentiment scoring as fallback when VADER is unavailable."""
    text_lower = text.lower()
    positive_words = [
        "bullish", "rally", "surge", "gain", "growth", "positive", "profit",
        "outperform", "upgrade", "boom", "optimistic", "recovery", "breakthrough",
        "record high", "beat expectations", "green"
    ]
    negative_words = [
        "bearish", "crash", "decline", "loss", "recession", "negative", "sell-off",
        "downgrade", "inflation fear", "volatile", "crisis", "plunge", "tumble",
        "miss expectations", "downturn", "bankruptcy", "layoff", "red"
    ]
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 50  # Neutral
    ratio = pos_count / total
    return int(ratio * 100)

# ── Article Deduplication ─────────────────────────────────────────

def article_hash(title, summary):
    """Create a unique hash for deduplication."""
    content = (title[:100] + summary[:100]).encode('utf-8', errors='ignore')
    return hashlib.md5(content).hexdigest()

# ── Main Pipeline ────────────────────────────────────────────────

def run_ingestion():
    config = load_config()
    db = HarnessDB()
    conn = db.connect()
    
    # Ensure news_sentiment table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_hash TEXT UNIQUE,
            title TEXT,
            summary TEXT,
            source TEXT,
            link TEXT,
            published TEXT,
            sentiment_score INTEGER,
            compound_score REAL,
            batch_id TEXT,
            captured_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_hash ON news_sentiment(article_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_batch ON news_sentiment(batch_id)")
    
    batch_id = datetime.now().strftime("%Y%m%d%H%M%S")
    all_articles = []
    total_new = 0
    
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue
        url = source.get("url", "")
        name = source.get("name", url)
        max_art = config.get("update", {}).get("max_articles_per_source", 20)
        
        if source.get("type") == "rss" and url:
            log.info(f"Fetching from {name}...")
            articles = fetch_rss(url, max_art)
            log.info(f"  Got {len(articles)} articles")
            
            for art in articles:
                title = art.get("title", "")
                summary = art.get("summary", "")
                
                # Deduplicate
                h = article_hash(title, summary)
                existing = conn.execute(
                    "SELECT id FROM news_sentiment WHERE article_hash = ?", (h,)
                ).fetchone()
                if existing:
                    continue
                
                # Sentiment analysis
                text_to_analyze = f"{title}. {summary}"
                sentiment_method = config.get("sentiment", {}).get("lexicon", "vader")
                if sentiment_method == "vader":
                    try:
                        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                        analyzer = SentimentIntensityAnalyzer()
                        compound = analyzer.polarity_scores(text_to_analyze)["compound"]
                        score = int((compound + 1) / 2 * 100)
                    except ImportError:
                        compound = 0.0
                        score = simple_keyword_sentiment(text_to_analyze)
                else:
                    compound = 0.0
                    score = simple_keyword_sentiment(text_to_analyze)
                
                score = max(0, min(100, score))
                art["sentiment_score"] = score
                art["compound"] = compound
                art["article_hash"] = h
                all_articles.append(art)
    
    # Batch insert
    for art in all_articles:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO news_sentiment 
                   (article_hash, title, summary, source, link, published, sentiment_score, compound_score, batch_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (art["article_hash"], art["title"], art["summary"][:500],
                 art.get("source", ""), art.get("link", ""), art.get("published", ""),
                 art["sentiment_score"], art.get("compound", 0.0), batch_id)
            )
            total_new += 1
        except Exception as e:
            log.error(f"Error inserting article: {e}")
    
    conn.commit()
    
    # ── Compute aggregated sentiment index ──
    rows = conn.execute(
        """SELECT sentiment_score FROM news_sentiment 
           WHERE captured_at > datetime('now', ?) 
           ORDER BY captured_at DESC""",
        (f"-{config.get('update', {}).get('max_age_hours', 72)} hours",)
    ).fetchall()
    
    if rows:
        scores = [r[0] for r in rows]
        avg_score = sum(scores) / len(scores)
        aggregated = int(avg_score)
        
        # Save aggregated result to a snapshot table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_sentiment_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score INTEGER,
                total_articles INTEGER,
                batch_id TEXT,
                captured_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "INSERT INTO news_sentiment_snapshots (score, total_articles, batch_id) VALUES (?, ?, ?)",
            (aggregated, len(scores), batch_id)
        )
        conn.commit()
        
        # Log to agent_logs
        db.log_activity(
            session_id=f"ingest_news_{batch_id}",
            agent_name="News Sentiment Ingest",
            task_id=None,
            action="ingest",
            summary=f"News sentiment ingestion completed. {total_new} new articles, {len(scores)} total in window. Aggregated score: {aggregated}/100.",
            tokens_used=0,
            status="completed"
        )
        
        log.info(f"Ingestion complete: {total_new} new articles, aggregate score: {aggregated}/100")
    else:
        log.warning("No articles found in this batch")
        aggregated = None
    
    conn.close()
    return {"new_articles": total_new, "aggregate_score": aggregated, "batch_id": batch_id}

if __name__ == "__main__":
    result = run_ingestion()
    print(json.dumps(result, indent=2))
