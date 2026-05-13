"""
Volume Indicators — Pegaton Invest Intelligence
Category: volume (7 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('volume', 'obv')
class OBV(TechnicalIndicator):
    """On Balance Volume."""
    name = "OBV"
    category = "volume"
    requires_periods = 2

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        df['obv'] = obv
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'obv' not in df.columns:
            self.calculate(df)
        obv = df['obv'].iloc[-1]
        prev = df['obv'].iloc[-5] if len(df) >= 5 else obv
        if obv > prev:
            return 65.0
        elif obv < prev:
            return 35.0
        return 50.0


@register_indicator('volume', 'vwap')
class VWAP(TechnicalIndicator):
    """Volume Weighted Average Price."""
    name = "VWAP"
    category = "volume"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        typical = (high + low + close) / 3
        cum_tp_vol = (typical * volume).cumsum()
        cum_vol = volume.cumsum()
        df['vwap'] = cum_tp_vol / (cum_vol + 1e-10)
        df['vwap'] = df['vwap'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'vwap' not in df.columns:
            self.calculate(df)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        vwap = df['vwap'].iloc[-1]
        if close > vwap:
            return 65.0
        elif close < vwap:
            return 35.0
        return 50.0


@register_indicator('volume', 'ad')
class AccumulationDistribution(TechnicalIndicator):
    """Accumulation/Distribution Line."""
    name = "A/D"
    category = "volume"
    requires_periods = 2

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
        mfv = mfm * volume
        df['ad'] = mfv.cumsum()
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'ad' not in df.columns:
            self.calculate(df)
        ad = df['ad'].iloc[-1]
        prev = df['ad'].iloc[-5] if len(df) >= 5 else ad
        return 65.0 if ad > prev else 35.0 if ad < prev else 50.0


@register_indicator('volume', 'volume_sma')
class VolumeSMA(TechnicalIndicator):
    """Volume Simple Moving Average."""
    name = "Volume SMA"
    category = "volume"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        df['vol_sma'] = volume.rolling(window=period).mean()
        df['vol_sma'] = df['vol_sma'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        period = params.get('period', 20)
        if 'vol_sma' not in df.columns:
            self.calculate(df, period=period)
        vol = df['volume'].iloc[-1] if 'volume' in df.columns else 1
        vsma = df['vol_sma'].iloc[-1]
        ratio = vol / vsma if vsma > 0 else 1
        if ratio > 2:
            return 70.0  # volumen inusualmente alto
        elif ratio < 0.5:
            return 30.0
        return 50.0


@register_indicator('volume', 'pvt')
class PriceVolumeTrend(TechnicalIndicator):
    """Price Volume Trend."""
    name = "PVT"
    category = "volume"
    requires_periods = 2

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        pct_change = close.pct_change()
        df['pvt'] = (pct_change * volume).cumsum()
        df['pvt'] = df['pvt'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'pvt' not in df.columns:
            self.calculate(df)
        pvt = df['pvt'].iloc[-1]
        prev = df['pvt'].iloc[-5] if len(df) >= 5 else pvt
        return 65.0 if pvt > prev else 35.0 if pvt < prev else 50.0


@register_indicator('volume', 'force_index')
class ForceIndex(TechnicalIndicator):
    """Force Index."""
    name = "Force Index"
    category = "volume"
    requires_periods = 13

    def calculate(self, df: pd.DataFrame, period: int = 13) -> pd.DataFrame:
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        fi = close.diff() * volume
        df['force_index'] = fi.ewm(span=period).mean()
        df['force_index'] = df['force_index'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'force_index' not in df.columns:
            self.calculate(df)
        fi = df['force_index'].iloc[-1]
        return normalize_score(fi, df['force_index'].quantile(0.05), df['force_index'].quantile(0.95))


@register_indicator('volume', 'elders_force')
class EldersForce(TechnicalIndicator):
    """Elder's Force Index."""
    name = "Elder's Force"
    category = "volume"
    requires_periods = 13

    def calculate(self, df: pd.DataFrame, period: int = 13) -> pd.DataFrame:
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        ema = close.ewm(span=period).mean()
        df['elders_force'] = (close - ema.shift(1)) * volume
        df['elders_force'] = df['elders_force'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'elders_force' not in df.columns:
            self.calculate(df)
        ef = df['elders_force'].iloc[-1]
        return 65.0 if ef > 0 else 35.0 if ef < 0 else 50.0