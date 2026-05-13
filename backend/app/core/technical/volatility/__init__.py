"""
Volatility Indicators — Pegaton Invest Intelligence
Category: volatility (8 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('volatility', 'bollinger')
class BollingerBands(TechnicalIndicator):
    """Bollinger Bands."""
    name = "Bollinger Bands"
    category = "volatility"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        sma = df[col].rolling(window=period).mean()
        std = df[col].rolling(window=period).std()
        df['bb_upper'] = sma + std_dev * std
        df['bb_lower'] = sma - std_dev * std
        df['bb_middle'] = sma
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma * 100
        df['bb_pctb'] = (df[col] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10) * 100
        for c in ['bb_upper', 'bb_lower', 'bb_middle', 'bb_width', 'bb_pctb']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'bb_pctb' not in df.columns:
            self.calculate(df, **params)
        pctb = df['bb_pctb'].iloc[-1]
        if pctb < 5:
            return 80.0  # cerca de lower band → posible rebote
        elif pctb > 95:
            return 20.0
        return 50.0


@register_indicator('volatility', 'atr')
class ATR(TechnicalIndicator):
    """Average True Range."""
    name = "ATR"
    category = "volatility"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=period).mean()
        df['atr'] = df['atr'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'atr' not in df.columns:
            self.calculate(df, **params)
        atr = df['atr'].iloc[-1]
        prev = df['atr'].iloc[-5] if len(df) >= 5 else atr
        if prev > 0 and atr / prev > 1.5:
            return 30.0  # volatilidad creciente
        return 50.0


@register_indicator('volatility', 'keltner')
class KeltnerChannels(TechnicalIndicator):
    """Keltner Channels."""
    name = "Keltner Channels"
    category = "volatility"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20, mult: float = 2.0) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        atr = ATR().calculate(df.copy(), period)['atr']
        ema = close.ewm(span=period).mean()
        df['kc_upper'] = ema + mult * atr
        df['kc_lower'] = ema - mult * atr
        df['kc_middle'] = ema
        for c in ['kc_upper', 'kc_lower', 'kc_middle']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'kc_upper' not in df.columns:
            self.calculate(df, **params)
        close = df['close'].iloc[-1]
        upper = df['kc_upper'].iloc[-1]
        lower = df['kc_lower'].iloc[-1]
        if close > upper:
            return 25.0
        elif close < lower:
            return 75.0
        return 50.0


@register_indicator('volatility', 'donchian')
class DonchianChannels(TechnicalIndicator):
    """Donchian Channels."""
    name = "Donchian Channels"
    category = "volatility"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        df['dc_upper'] = high.rolling(window=period).max()
        df['dc_lower'] = low.rolling(window=period).min()
        df['dc_middle'] = (df['dc_upper'] + df['dc_lower']) / 2
        for c in ['dc_upper', 'dc_lower', 'dc_middle']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'dc_upper' not in df.columns:
            self.calculate(df, **params)
        close = df['close'].iloc[-1]
        upper = df['dc_upper'].iloc[-1]
        lower = df['dc_lower'].iloc[-1]
        if close >= upper:
            return 80.0  # breakout alcista
        elif close <= lower:
            return 20.0
        return 50.0


@register_indicator('volatility', 'std_dev')
class StandardDeviation(TechnicalIndicator):
    """Standard Deviation."""
    name = "Standard Deviation"
    category = "volatility"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        df['std_dev'] = df[col].rolling(window=period).std()
        df['std_dev'] = df['std_dev'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'std_dev' not in df.columns:
            self.calculate(df, **params)
        return 50.0  # informativo, no direccional


@register_indicator('volatility', 'hist_vol')
class HistoricalVolatility(TechnicalIndicator):
    """Historical Volatility."""
    name = "Historical Volatility"
    category = "volatility"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        log_ret = np.log(df[col] / df[col].shift(1))
        df['hist_vol'] = log_ret.rolling(window=period).std() * np.sqrt(252) * 100
        df['hist_vol'] = df['hist_vol'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'hist_vol' not in df.columns:
            self.calculate(df, **params)
        vol = df['hist_vol'].iloc[-1]
        if vol > 50:
            return 30.0
        elif vol < 20:
            return 70.0
        return 50.0


@register_indicator('volatility', 'chaikin_vol')
class ChaikinVolatility(TechnicalIndicator):
    """Chaikin Volatility."""
    name = "Chaikin Volatility"
    category = "volatility"
    requires_periods = 10

    def calculate(self, df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        hl_range = high - low
        ema_range = hl_range.ewm(span=period).mean()
        df['chaikin_vol'] = (ema_range - ema_range.shift(period)) / ema_range.shift(period) * 100
        df['chaikin_vol'] = df['chaikin_vol'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'chaikin_vol' not in df.columns:
            self.calculate(df, **params)
        return 50.0


@register_indicator('volatility', 'natr')
class NATR(TechnicalIndicator):
    """Normalized Average True Range."""
    name = "NATR"
    category = "volatility"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        df['natr'] = atr / close * 100
        df['natr'] = df['natr'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'natr' not in df.columns:
            self.calculate(df, **params)
        return 50.0