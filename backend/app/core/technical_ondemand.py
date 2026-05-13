"""On-demand technical analysis for any symbol via Twelve Data API.
SDD Nivel 2: Parameters defined in pegaton_config.py — Spec #3.
Reuses scoring functions from technical.py.
"""
import os, requests, numpy as np, pandas as pd
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('TWELVEDATA_API_KEY')

from backend.app.core.technical import (
    compute_rsi_score, rsi as compute_rsi, macd as compute_macd, sma_position
)
from backend.app.core.pegaton_config import (
    TECHNICAL_WEIGHTS, MACD_BULLISH_SCORE, MACD_BEARISH_SCORE,
    SMA_ABOVE_SCORE, SMA_BELOW_SCORE, FACTOR_ALCISTA, FACTOR_BAJISTA,
)


def fetch_ohlcv(symbol: str, days: int = 200) -> pd.DataFrame:
    """Fetch OHLCV data from Twelve Data for any symbol."""
    url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize={days}&apikey={API_KEY}'
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
        if data.get('status') == 'error':
            return pd.DataFrame()
        values = data.get('values', [])
        if not values:
            return pd.DataFrame()
        rows = []
        for v in reversed(values):
            rows.append({
                'timestamp': v['datetime'],
                'close': float(v['close']),
                'open': float(v['open']),
                'high': float(v['high']),
                'low': float(v['low']),
                'volume': float(v.get('volume', 0) or 0),
            })
        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def _factor_direction(score: float) -> str:
    if score >= FACTOR_ALCISTA:
        return 'alcista'
    if score <= FACTOR_BAJISTA:
        return 'bajista'
    return 'neutral'


def ondemand_technical_score(symbol: str) -> dict:
    """Compute technical score by fetching data on-demand from Twelve Data."""
    df = fetch_ohlcv(symbol, 200)
    if df.empty:
        return {'technical_score': 50, 'details': {'error': f'Could not fetch data for {symbol}'}}

    close = df['close']
    rsi_val = float(compute_rsi(close, 14))
    rsi_score = compute_rsi_score(rsi_val)

    macd_data = compute_macd(close)
    macd_score = MACD_BULLISH_SCORE if macd_data['bullish'] else MACD_BEARISH_SCORE

    sma50 = sma_position(close, 50)
    sma200 = sma_position(close, 200)
    sma50_score = SMA_ABOVE_SCORE if sma50['above'] else SMA_BELOW_SCORE
    sma200_score = SMA_ABOVE_SCORE if sma200['above'] else SMA_BELOW_SCORE

    w = TECHNICAL_WEIGHTS
    final = (
        w['RSI(14)'] * rsi_score +
        w['MACD'] * macd_score +
        w['SMA50'] * sma50_score +
        w['SMA200'] * sma200_score
    )

    tech_factors = [
        {'name': 'RSI(14)',  'score': round(float(rsi_score), 1),  'weight': w['RSI(14)'],  'contribution': round(float(rsi_score * w['RSI(14)']), 2),  'direction': _factor_direction(rsi_score)},
        {'name': 'MACD',     'score': round(float(macd_score), 1), 'weight': w['MACD'],     'contribution': round(float(macd_score * w['MACD']), 2),     'direction': _factor_direction(macd_score)},
        {'name': 'SMA50',    'score': round(float(sma50_score), 1),'weight': w['SMA50'],    'contribution': round(float(sma50_score * w['SMA50']), 2),    'direction': _factor_direction(sma50_score)},
        {'name': 'SMA200',   'score': round(float(sma200_score), 1),'weight': w['SMA200'],  'contribution': round(float(sma200_score * w['SMA200']), 2),  'direction': _factor_direction(sma200_score)},
    ]

    return {
        'technical_score': round(float(final), 1),
        'factors': tech_factors,
        'details': {
            'rsi': round(rsi_val, 1),
            'rsi_score': round(float(rsi_score), 1),
            'macd_bullish': macd_data['bullish'],
            'macd_histogram': round(float(macd_data['histogram']), 4),
            'macd_score': round(float(macd_score), 1),
            'sma50_above': sma50['above'],
            'sma50_distance': round(float(sma50['distance_pct']), 2),
            'sma50_score': round(float(sma50_score), 1),
            'sma200_above': sma200['above'],
            'sma200_distance': round(float(sma200['distance_pct']), 2),
            'sma200_score': round(float(sma200_score), 1),
            'last_close': float(close.iloc[-1]),
        }
    }
