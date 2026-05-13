#!/usr/bin/env python3
"""Test unitarios para TechEngine (technical.py)
Spec ref: docs/architecture.md Sección 3.2, 9.2"""
import pytest
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def make_price_series(close_prices):
    """Helper para crear una Serie de pandas con índices de fecha."""
    dates = pd.date_range(start="2025-01-01", periods=len(close_prices), freq="D")
    return pd.Series(close_prices, index=dates, dtype=float)


class TestRSI:
    """Tests para rsi()"""

    def test_rsi_calculation_with_gains(self):
        """SPEC: test_rsi_calculation — serie con solo ganancias"""
        from backend.app.core.technical import rsi
        gains = [100 + i * 2 for i in range(30)]
        series = make_price_series(gains)
        result = rsi(series, 14)
        assert isinstance(result, float)
        assert 80 < result <= 100  # Fuertemente alcista

    def test_rsi_calculation_with_losses(self):
        """SPEC: test_rsi_calculation — serie con solo pérdidas"""
        from backend.app.core.technical import rsi
        losses = [100 - i * 2 for i in range(30)]
        series = make_price_series(losses)
        result = rsi(series, 14)
        assert isinstance(result, float)
        assert 0 <= result < 20  # Fuertemente bajista

    def test_rsi_neutral(self):
        """SPEC: test_rsi_calculation — serie alternada (neutral)"""
        from backend.app.core.technical import rsi
        alt = [100, 101, 100, 101, 100, 101] * 10
        series = make_price_series(alt)
        result = rsi(series, 14)
        assert isinstance(result, float)
        assert 40 <= result <= 60

    def test_rsi_insufficient_data(self):
        """SPEC: test_rsi_insufficient_data — menos datos que el periodo"""
        from backend.app.core.technical import rsi
        short_series = make_price_series([100, 101, 102])
        result = rsi(short_series, 14)
        assert result == 50.0

    def test_rsi_produces_float(self):
        """SPEC: test_rsi_returns_float"""
        from backend.app.core.technical import rsi
        series = make_price_series([100 + (i % 5) for i in range(50)])
        result = rsi(series, 14)
        assert isinstance(result, float)


class TestRSIScore:
    """Tests para compute_rsi_score()"""

    def test_compute_rsi_score_oversold(self):
        """SPEC: test_compute_rsi_score_boundaries — RSI en sobreventa (score alto)"""
        from backend.app.core.technical import compute_rsi_score
        score = compute_rsi_score(25.0)
        assert score > 80

    def test_compute_rsi_score_overbought(self):
        """SPEC: test_compute_rsi_score_boundaries — RSI en sobrecompra (score bajo)"""
        from backend.app.core.technical import compute_rsi_score
        score = compute_rsi_score(75.0)
        assert score < 30

    def test_compute_rsi_score_neutral(self):
        """SPEC: test_compute_rsi_score_boundaries — RSI neutral"""
        from backend.app.core.technical import compute_rsi_score
        score = compute_rsi_score(50.0)
        assert 35 <= score <= 55

    def test_compute_rsi_score_extreme_low(self):
        """SPEC: test_rsi_score_extreme_low"""
        from backend.app.core.technical import compute_rsi_score
        score = compute_rsi_score(0.0)
        assert 95 <= score <= 100

    def test_compute_rsi_score_extreme_high(self):
        """SPEC: test_rsi_score_extreme_high"""
        from backend.app.core.technical import compute_rsi_score
        score = compute_rsi_score(100.0)
        assert 0 <= score <= 5


class TestMACD:
    """Tests para macd()"""

    def test_macd_bullish(self):
        """SPEC: test_macd_bullish_bearish — tendencia alcista"""
        from backend.app.core.technical import macd
        series = make_price_series([100 + i for i in range(50)])
        result = macd(series)
        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert "bullish" in result

    def test_macd_bearish(self):
        """SPEC: test_macd_bullish_bearish — tendencia bajista"""
        from backend.app.core.technical import macd
        series = make_price_series([100 - i for i in range(50)])
        result = macd(series)
        assert isinstance(result, dict)

    def test_macd_insufficient_data(self):
        """SPEC: test_macd_insufficient_data"""
        from backend.app.core.technical import macd
        short_series = make_price_series([100, 101, 102])
        result = macd(short_series)
        assert result["macd"] == 0
        assert result["signal"] == 0
        assert result["histogram"] == 0
        assert result["bullish"] is True

    def test_macd_returns_dict(self):
        """SPEC: test_macd_returns_correct_schema"""
        from backend.app.core.technical import macd
        series = make_price_series([100 + (i % 3) * 0.5 for i in range(50)])
        result = macd(series)
        assert isinstance(result, dict)
        assert all(k in result for k in ["macd", "signal", "histogram", "bullish"])


class TestSMAPosition:
    """Tests para sma_position()"""

    def test_sma_above(self):
        """SPEC: test_sma50_above — precio > SMA"""
        from backend.app.core.technical import sma_position
        series = make_price_series([100 + i for i in range(60)])
        result = sma_position(series, 50)
        assert isinstance(result, dict)
        assert "above" in result
        assert "distance_pct" in result

    def test_sma_below(self):
        """SPEC: test_sma200_below — precio < SMA"""
        from backend.app.core.technical import sma_position
        series = make_price_series([100 - i for i in range(60)])
        result = sma_position(series, 50)
        assert isinstance(result, dict)

    def test_sma_insufficient_data(self):
        """SPEC: test_sma_insufficient_data"""
        from backend.app.core.technical import sma_position
        short_series = make_price_series([100, 101, 102])
        result = sma_position(short_series, 50)
        assert result["above"] is True
        assert result["distance_pct"] == 0.0

    def test_sma_returns_dict(self):
        """SPEC: test_sma_returns_correct_schema"""
        from backend.app.core.technical import sma_position
        series = make_price_series([100 + (i % 5) for i in range(100)])
        result = sma_position(series, 50)
        assert isinstance(result, dict)
        assert "above" in result
        assert "distance_pct" in result


class TestTechnicalScore:
    """Tests para technical_score()"""

    def test_technical_score_returns_valid_schema(self):
        """SPEC: test_technical_score_returns_valid_schema"""
        import sqlite3, tempfile, random
        from backend.app.core import technical as tech_mod

        fd, db_path = tempfile.mkstemp(suffix=".db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE precios_ohlcv (
            timestamp TEXT, simbolo TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        )""")

        random.seed(42)
        price = 400.0
        base_date = "2025-06-01"
        for i in range(250):
            open_p = price
            close_p = price + random.uniform(-3, 3)
            high_p = max(open_p, close_p) + random.uniform(0, 1)
            low_p = min(open_p, close_p) - random.uniform(0, 1)
            vol = random.uniform(1000000, 5000000)
            # Fecha válida con incremento diario
            from datetime import datetime, timedelta
            dt = datetime(2025, 6, 1) + timedelta(days=i)
            ts = dt.strftime("%Y-%m-%d")
            conn.execute(
                "INSERT INTO precios_ohlcv VALUES (?, 'SPY', ?, ?, ?, ?, ?)",
                (ts, open_p, high_p, low_p, close_p, vol),
            )
            price = close_p
        conn.commit()
        conn.close()

        original = tech_mod.DB_PATH
        tech_mod.DB_PATH = db_path

        result = tech_mod.technical_score("SPY")

        assert "technical_score" in result
        assert isinstance(result["technical_score"], (int, float))
        assert 0 <= result["technical_score"] <= 100
        assert "factors" in result
        assert len(result["factors"]) >= 45
        assert "details" in result

        tech_mod.DB_PATH = original
        os.close(fd)
        os.unlink(db_path)

    def test_technical_score_empty_data(self):
        """SPEC: test_technical_score_with_empty_data"""
        import sqlite3, tempfile
        from backend.app.core import technical as tech_mod

        fd, db_path = tempfile.mkstemp(suffix=".db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE precios_ohlcv (
            timestamp TEXT, simbolo TEXT,
            open REAL, high REAL, low REAL, close REAL, volume REAL
        )""")
        conn.commit()
        conn.close()

        original = tech_mod.DB_PATH
        tech_mod.DB_PATH = db_path

        result = tech_mod.technical_score("UNKNOWN")

        assert result["technical_score"] == 50
        assert "factors" in result
        assert len(result["factors"]) == 0

        tech_mod.DB_PATH = original
        os.close(fd)
        os.unlink(db_path)

    def test_technical_weights_sum_one(self):
        """SPEC: test_technical_weights_sum_1"""
        from backend.app.core.pegaton_config import TECHNICAL_WEIGHTS
        total = sum(TECHNICAL_WEIGHTS.values())
        assert abs(total - 1.0) < 0.0001

    def test_technical_factors_have_direction(self):
        """SPEC: test_technical_factors_have_direction"""
        from backend.app.core.technical import _factor_direction
        assert _factor_direction(60) == "alcista"
        assert _factor_direction(40) == "bajista"
        assert _factor_direction(50) == "neutral"
        assert _factor_direction(55) == "alcista"
        assert _factor_direction(45) == "bajista"