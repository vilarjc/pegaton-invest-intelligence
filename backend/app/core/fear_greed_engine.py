"""
Fear & Greed Engine — Equipo A
Calculates a Fear & Greed composite score (0-100) from:
- VIX (40%): via yfinance ^VIX
- Macro (35%): FRED data (UNRATE, CPIAUCSL, GDPPOT)
- RSS Sentiment (25%): Reuters/CNBC keyword analysis

Cache: in-memory with 1-hour TTL
"""

import os
import time
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf
import feedparser

logger = logging.getLogger(__name__)

# Actions
ACTIONS = [
    (0, 24, "Miedo Extremo", "🔴"),
    (25, 44, "Miedo", "🟠"),
    (45, 54, "Neutral", "🟡"),
    (55, 74, "Ganancia", "🟢"),
    (75, 100, "Euforia Extrema", "🟣"),
]

# RSS Sentiment Keywords
POSITIVE_KEYWORDS = [
    "rally", "bullish", "growth", "surge", "recovery",
    "gain", "optimism", "upgrade", "strong",
]
NEGATIVE_KEYWORDS = [
    "crash", "bearish", "recession", "plunge", "fear",
    "selloff", "decline", "inflation", "warning", "volatility",
]

# RSS Feed URLs
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.marketwatch.com/marketwatch/topstories",
]

# Cache
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 3600  # 1 hour in seconds


def _get_action(score: int) -> dict:
    """Map score (0-100) to action label and emoji."""
    for lo, hi, label, emoji in ACTIONS:
        if lo <= score <= hi:
            return {"label": label, "emoji": emoji}
    return {"label": "Neutral", "emoji": "🟡"}


def _linear_map(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Linearly map a value from one range to another, clamping."""
    if value <= in_min:
        return out_max
    if value >= in_max:
        return out_min
    ratio = (value - in_min) / (in_max - in_min)
    return out_max - ratio * (out_max - out_min)


# --- VIX Component ---

def _fetch_vix() -> tuple[Optional[float], Optional[float]]:
    """
    Fetch VIX from yfinance.
    Returns: (vix_value, score_0_100)
    Score: VIX < 12 -> 100 (Euforia), VIX > 40 -> 0 (Miedo Extremo)
    """
    try:
        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="1d")
        if hist.empty:
            logger.warning("VIX: No data from yfinance")
            return None, None
        vix = float(hist["Close"].iloc[-1])
        score = _linear_map(vix, 12, 40, 100, 0)
        return vix, round(score, 1)
    except Exception as e:
        logger.error(f"VIX fetch error: {e}")
        return None, None


# --- Macro Component (FRED) ---

FRED_API_KEY = os.getenv("FRED_API_KEY", "6998c5546e26a1868b104ff07a3b5a77")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def _fred_fetch_value(series_id: str) -> Optional[float]:
    """Fetch the latest observation value for a FRED series."""
    url = (
        f"{FRED_BASE}?series_id={series_id}"
        f"&api_key={FRED_API_KEY}"
        f"&file_type=json"
        f"&sort_order=desc"
        f"&limit=2"
    )
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        obs = data.get("observations", [])
        if not obs:
            logger.warning(f"FRED {series_id}: no observations")
            return None
        val = obs[0].get("value")
        if val in (None, ".", ""):
            return None
        return float(val)
    except Exception as e:
        logger.error(f"FRED fetch {series_id} error: {e}")
        return None


def _score_unemployment(unrate: float) -> float:
    """UNRATE scoring: <4%=90, 4-5%=70, >6%=30"""
    if unrate < 4:
        return 90
    elif unrate < 5:
        return 70
    elif unrate < 6:
        return 50
    else:
        return 30


def _score_inflation(cpi_yoy: float) -> float:
    """CPIAUCSL YoY scoring: <3%=85, 3-5%=60, >6%=20"""
    if cpi_yoy < 3:
        return 85
    elif cpi_yoy < 5:
        return 60
    elif cpi_yoy < 6:
        return 40
    else:
        return 20


def _score_gdp_output_gap(unrate: float) -> float:
    """
    GDP output gap proxy using unemployment (Okun's law proxy).
    Lower unemployment -> positive output gap -> higher score
    """
    if unrate < 4:
        return 80
    elif unrate < 5:
        return 60
    elif unrate < 6:
        return 40
    else:
        return 20


def _fetch_macro() -> tuple[Optional[float], dict]:
    """
    Fetch all 3 FRED series and compute macro score (0-100).
    Returns: (composite_score, details_dict)
    """
    unrate = _fred_fetch_value("UNRATE")
    cpiaucsl = _fred_fetch_value("CPIAUCSL")
    # For CPIAUCSL we need YoY change, so fetch 2 observations
    # The function already fetches limit=2

    # Also fetch GDPPOT (real potential GDP)
    gdppot = _fred_fetch_value("GDPPOT")

    details = {}

    # Unemployment score
    if unrate is not None:
        unrate_score = _score_unemployment(unrate)
        details["unemployment"] = {"value": unrate, "score": unrate_score}
    else:
        unrate_score = 50
        details["unemployment"] = {"value": None, "score": 50}

    # Inflation CPI YoY
    if cpiaucsl is not None:
        # Try to get the previous value for YoY calculation
        try:
            url = (
                f"{FRED_BASE}?series_id=CPIAUCSL"
                f"&api_key={FRED_API_KEY}"
                f"&file_type=json"
                f"&sort_order=desc"
                f"&limit=13"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            obs = data.get("observations", [])
            if len(obs) >= 13:
                latest = float(obs[0]["value"])
                year_ago = float(obs[12]["value"])
                cpi_yoy = ((latest - year_ago) / year_ago) * 100
            else:
                cpi_yoy = cpiaucsl  # fallback
        except Exception:
            cpi_yoy = cpiaucsl
        cpi_score = _score_inflation(abs(cpi_yoy))
        details["inflation"] = {"value": cpi_yoy, "score": cpi_score}
    else:
        cpi_score = 50
        details["inflation"] = {"value": None, "score": 50}

    # GDP output gap
    if unrate is not None:
        gdp_score = _score_gdp_output_gap(unrate)
        details["output_gap"] = {"value": unrate, "score": gdp_score}
    else:
        gdp_score = 50
        details["output_gap"] = {"value": None, "score": 50}

    # Composite macro score (simple average of 3 components)
    macro_score = round((unrate_score + cpi_score + gdp_score) / 3, 1)
    return macro_score, details


# --- RSS Sentiment Component ---

def _fetch_rss_sentiment() -> tuple[Optional[float], dict]:
    """
    Fetch RSS feeds from Reuters/CNBC, count positive/negative keywords.
    Returns: (sentiment_score_0_100, details_dict)
    """
    total_pos = 0
    total_neg = 0
    total_articles = 0
    details = {"feeds": {}}

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            articles = []
            for entry in feed.entries[:20]:
                title = (entry.get("title", "") or "")
                summary = (entry.get("summary", "") or "")
                content = f"{title} {summary}".lower()
                articles.append(content)

            pos_count = sum(1 for a in articles for kw in POSITIVE_KEYWORDS if kw in a)
            neg_count = sum(1 for a in articles for kw in NEGATIVE_KEYWORDS if kw in a)

            total_pos += pos_count
            total_neg += neg_count
            total_articles += len(articles)

            source_name = url.split("//")[1].split("/")[0]
            details["feeds"][source_name] = {
                "articles": len(articles),
                "positive": pos_count,
                "negative": neg_count,
            }
        except Exception as e:
            logger.warning(f"RSS feed error for {url}: {e}")

    if total_articles == 0:
        logger.warning("RSS: No articles fetched")
        return None, details

    # Sentiment score: 0-100 where more positive = higher
    # Normalize: if all positive -> 100, all negative -> 0
    total_keywords = total_pos + total_neg
    if total_keywords == 0:
        sentiment = 50.0  # neutral
    else:
        sentiment = (total_pos / total_keywords) * 100

    details["total_articles"] = total_articles
    details["total_positive"] = total_pos
    details["total_negative"] = total_neg
    details["sentiment_pct"] = round(sentiment, 1)

    return round(sentiment, 1), details


# --- Main Engine ---

class FearGreedEngine:
    """Fear & Greed composite indicator engine."""

    def get_score(self, force_refresh: bool = False) -> dict:
        """
        Compute the Fear & Greed score.

        Args:
            force_refresh: If True, bypass cache.

        Returns:
            dict with score, action, action_emoji, timestamp, factores, cacheado
        """
        now = time.time()
        cached = True

        if force_refresh or _cache["data"] is None or (now - _cache["timestamp"]) > CACHE_TTL:
            cached = False
            logger.info("Computing Fear & Greed score (cache miss)")

            # 1. VIX Component (40%)
            vix_value, vix_score = _fetch_vix()
            if vix_score is None:
                vix_score = 50.0  # fallback neutral
                vix_value = None

            # 2. Macro Component (35%)
            macro_score, macro_details = _fetch_macro()

            # 3. RSS Sentiment Component (25%)
            sentiment_score, sentiment_details = _fetch_rss_sentiment()
            if sentiment_score is None:
                sentiment_score = 50.0  # fallback neutral

            # Composite score
            final_score = (
                vix_score * 0.40
                + macro_score * 0.35
                + sentiment_score * 0.25
            )
            final_score = round(max(0, min(100, final_score)))

            action_info = _get_action(final_score)

            _cache["data"] = {
                "score": final_score,
                "action": action_info["label"],
                "action_emoji": action_info["emoji"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "factores": {
                    "vix": {
                        "value": vix_value,
                        "score": vix_score,
                        "peso": "40%",
                    },
                    "macro": {
                        "score": macro_score,
                        "peso": "35%",
                        "detalles": macro_details,
                    },
                    "sentimiento": {
                        "score": sentiment_score,
                        "peso": "25%",
                        "detalles": sentiment_details,
                    },
                },
                "cacheado": False,
            }
            _cache["timestamp"] = now

        result = dict(_cache["data"])
        result["cacheado"] = cached
        return result

    def clear_cache(self):
        """Clear the in-memory cache."""
        _cache["data"] = None
        _cache["timestamp"] = 0
