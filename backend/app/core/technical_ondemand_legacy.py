"""Technical analysis indicators calculated from OHLCV data.
SDD Nivel 2: Parameters defined in pegaton_config.py — Spec #3.
"""
import pandas as pd
import numpy as np
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pegaton.db')

from backend.app.core.pegaton_config import (
    TECHNICAL_WEIGHTS,
    RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_BULLISH_SCORE, MACD_BEARISH_SCORE,
    SMA_ABOVE_SCORE, SMA_BELOW_SCORE,
    FACTOR_ALCISTA, FACTOR_BAJISTA,
)


def get_price_data(symbol: str, days: int = 200) -> pd.DataFrame:
    """Fetch OHLCV data from SQLite for a given symbol."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """SELECT timestamp, open, high, low, close, volume
           FROM precios_ohlcv
           WHERE simbolo = ?
           ORDER BY timestamp ASC""",
        conn, params=(symbol,)
    )
    conn.close()
    if df.empty:
        return df
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', dayfirst=False)
    df.set_index('timestamp', inplace=True)
    return df


def rsi(series: pd.Series, period: int = 14) -> float:
    """Calculate RSI for the last value."""
    if len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gains = delta.where(delta > 0, 0)
    losses = (-delta.where(delta < 0, 0))
    avg_gain = float(gains.rolling(window=period).mean().iloc[-1])
    avg_loss = float(losses.rolling(window=period).mean().iloc[-1])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def macd(series: pd.Series) -> dict:
    """Calculate MACD line, signal line, and histogram."""
    if len(series) < 26:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'bullish': True}
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1]),
        'bullish': bool(float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]))
    }


def sma_position(series: pd.Series, period: int) -> dict:
    """Calculate if current price is above/below SMA and the distance %."""
    if len(series) < period:
        return {'above': True, 'distance_pct': 0.0}
    sma = float(series.rolling(window=period).mean().iloc[-1])
    current = float(series.iloc[-1])
    distance = float(((current - sma) / sma) * 100)
    return {'above': bool(current > sma), 'distance_pct': distance}


def _factor_direction(score: float) -> str:
    if score >= FACTOR_ALCISTA:
        return 'alcista'
    if score <= FACTOR_BAJISTA:
        return 'bajista'
    return 'neutral'


def compute_rsi_score(rsi_val: float) -> float:
    """Convert RSI value to 0-100 score."""
    if rsi_val <= RSI_OVERSOLD:
        return 100 - (rsi_val / RSI_OVERSOLD) * 20  # 100 → 80
    elif rsi_val >= RSI_OVERBOUGHT:
        return (100 - rsi_val) / (100 - RSI_OVERBOUGHT) * 20  # 20 → 0
    else:
        return 80 - (rsi_val - RSI_OVERSOLD) / (RSI_OVERBOUGHT - RSI_OVERSOLD) * 60  # 80 → 20


def technical_score(symbol: str) -> dict:
    """Compute combined technical score (0-100) for a symbol."""
    df = get_price_data(symbol, days=200)
    if df.empty:
        return {'technical_score': 50, 'factors': [], 'details': {'error': 'No data'}}

    close = df['close']
    rsi_val = float(rsi(close, 14))
    rsi_score = compute_rsi_score(rsi_val)

    macd_data = macd(close)
    macd_score = MACD_BULLISH_SCORE if macd_data['bullish'] else MACD_BEARISH_SCORE

    sma50 = sma_position(close, 50)
    sma200 = sma_position(close, 200)
    sma50_score = SMA_ABOVE_SCORE if sma50['above'] else SMA_BELOW_SCORE
    sma200_score = SMA_ABOVE_SCORE if sma200['above'] else SMA_BELOW_SCORE

    # Weights from config (Spec B)
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
            'last_close': float(close.iloc[-1]) if not close.empty else None,
        }
    }
