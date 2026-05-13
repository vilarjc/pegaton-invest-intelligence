"""
Momentum Indicators — Pegaton Invest Intelligence
Category: momentum (10 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('momentum', 'rsi')
class RSI(TechnicalIndicator):
    """Relative Strength Index."""
    name = "RSI"
    category = "momentum"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        delta = df[col].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        for i in range(period, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'rsi' not in df.columns:
            self.calculate(df, **params)
        last = df['rsi'].iloc[-1]
        if last < 30:
            return 80.0  # sobreventa → alcista
        elif last > 70:
            return 20.0  # sobrecompra → bajista
        elif last < 40:
            return 60.0
        elif last > 60:
            return 40.0
        return 50.0


@register_indicator('momentum', 'stoch_rsi')
class StochasticRSI(TechnicalIndicator):
    """Stochastic RSI."""
    name = "StochRSI"
    category = "momentum"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
        if 'rsi' not in df.columns:
            rsi_ind = RSI()
            df = rsi_ind.calculate(df, period)
        rsi = df['rsi']
        stoch_rsi = (rsi - rsi.rolling(window=period).min()) / (rsi.rolling(window=period).max() - rsi.rolling(window=period).min() + 1e-10)
        df['stoch_rsi_k'] = stoch_rsi.rolling(window=smooth_k).mean() * 100
        df['stoch_rsi_d'] = df['stoch_rsi_k'].rolling(window=smooth_d).mean()
        df['stoch_rsi_k'] = df['stoch_rsi_k'].fillna(50)
        df['stoch_rsi_d'] = df['stoch_rsi_d'].fillna(50)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'stoch_rsi_k' not in df.columns:
            self.calculate(df, **params)
        k = df['stoch_rsi_k'].iloc[-1]
        d = df['stoch_rsi_d'].iloc[-1]
        if k < 20 and k > d:
            return 75.0
        elif k > 80 and k < d:
            return 25.0
        return 50.0


@register_indicator('momentum', 'williams')
class WilliamsR(TechnicalIndicator):
    """Williams %R."""
    name = "Williams %R"
    category = "momentum"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        hh = high.rolling(window=period).max()
        ll = low.rolling(window=period).min()
        df['williams_r'] = -100 * (hh - close) / (hh - ll + 1e-10)
        df['williams_r'] = df['williams_r'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'williams_r' not in df.columns:
            self.calculate(df, **params)
        last = df['williams_r'].iloc[-1]
        if last < -80:
            return 75.0
        elif last > -20:
            return 25.0
        return 50.0


@register_indicator('momentum', 'cci')
class CCI(TechnicalIndicator):
    """Commodity Channel Index."""
    name = "CCI"
    category = "momentum"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        tp = (high + low + close) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        df['cci'] = (tp - sma) / (0.015 * mad + 1e-10)
        df['cci'] = df['cci'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'cci' not in df.columns:
            self.calculate(df, **params)
        last = df['cci'].iloc[-1]
        if last < -100:
            return 70.0
        elif last > 100:
            return 30.0
        return 50.0


@register_indicator('momentum', 'roc')
class ROC(TechnicalIndicator):
    """Rate of Change."""
    name = "ROC"
    category = "momentum"
    requires_periods = 12

    def calculate(self, df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        df['roc'] = df[col].pct_change(periods=period) * 100
        df['roc'] = df['roc'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'roc' not in df.columns:
            self.calculate(df, **params)
        last = df['roc'].iloc[-1]
        return normalize_score(last, -10, 10)


@register_indicator('momentum', 'mfi')
class MFI(TechnicalIndicator):
    """Money Flow Index."""
    name = "MFI"
    category = "momentum"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
        typical = (high + low + close) / 3
        money_flow = typical * volume
        positive = money_flow.where(typical > typical.shift(1), 0)
        negative = money_flow.where(typical < typical.shift(1), 0)
        pos_sum = positive.rolling(window=period).sum()
        neg_sum = negative.rolling(window=period).sum()
        rs = pos_sum / neg_sum.replace(0, np.nan)
        df['mfi'] = 100 - (100 / (1 + rs))
        df['mfi'] = df['mfi'].fillna(50)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'mfi' not in df.columns:
            self.calculate(df, **params)
        last = df['mfi'].iloc[-1]
        if last < 20:
            return 75.0
        elif last > 80:
            return 25.0
        return 50.0


@register_indicator('momentum', 'ppo')
class PPO(TechnicalIndicator):
    """Percentage Price Oscillator."""
    name = "PPO"
    category = "momentum"
    requires_periods = 26

    def calculate(self, df: pd.DataFrame, fast: int = 12, slow: int = 26) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        ema_fast = df[col].ewm(span=fast).mean()
        ema_slow = df[col].ewm(span=slow).mean()
        df['ppo'] = (ema_fast - ema_slow) / ema_slow * 100
        df['ppo_signal'] = df['ppo'].ewm(span=9).mean()
        df['ppo_hist'] = df['ppo'] - df['ppo_signal']
        df['ppo'] = df['ppo'].fillna(0)
        df['ppo_signal'] = df['ppo_signal'].fillna(0)
        df['ppo_hist'] = df['ppo_hist'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'ppo_hist' not in df.columns:
            self.calculate(df, **params)
        hist = df['ppo_hist'].iloc[-1]
        return normalize_score(hist, -2, 2)


@register_indicator('momentum', 'tsi')
class TSI(TechnicalIndicator):
    """True Strength Index."""
    name = "TSI"
    category = "momentum"
    requires_periods = 25

    def calculate(self, df: pd.DataFrame, r: int = 25, s: int = 13) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        mom = df[col].diff()
        abs_mom = mom.abs()
        ema1 = mom.ewm(span=r).mean()
        ema2 = ema1.ewm(span=s).mean()
        abs_ema1 = abs_mom.ewm(span=r).mean()
        abs_ema2 = abs_ema1.ewm(span=s).mean()
        df['tsi'] = (ema2 / abs_ema2) * 100
        df['tsi'] = df['tsi'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'tsi' not in df.columns:
            self.calculate(df, **params)
        last = df['tsi'].iloc[-1]
        return normalize_score(last, -25, 25)


@register_indicator('momentum', 'uo')
class UltimateOscillator(TechnicalIndicator):
    """Ultimate Oscillator."""
    name = "UO"
    category = "momentum"
    requires_periods = 28

    def calculate(self, df: pd.DataFrame, p1: int = 7, p2: int = 14, p3: int = 28) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        bp = close - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        tr = pd.concat([high, close.shift(1)], axis=1).max(axis=1) - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        avg1 = bp.rolling(p1).sum() / tr.rolling(p1).sum()
        avg2 = bp.rolling(p2).sum() / tr.rolling(p2).sum()
        avg3 = bp.rolling(p3).sum() / tr.rolling(p3).sum()
        df['uo'] = 100 * (4 * avg1 + 2 * avg2 + avg3) / 7
        df['uo'] = df['uo'].fillna(50)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'uo' not in df.columns:
            self.calculate(df, **params)
        last = df['uo'].iloc[-1]
        if last < 30:
            return 70.0
        elif last > 70:
            return 30.0
        return 50.0


@register_indicator('momentum', 'ao')
class AwesomeOscillator(TechnicalIndicator):
    """Awesome Oscillator."""
    name = "AO"
    category = "momentum"
    requires_periods = 34

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        mp = (high + low) / 2
        df['ao'] = mp.rolling(5).mean() - mp.rolling(34).mean()
        df['ao'] = df['ao'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'ao' not in df.columns:
            self.calculate(df)
        last = df['ao'].iloc[-1]
        prev = df['ao'].iloc[-2] if len(df) > 1 else 0
        if last > 0 and last > prev:
            return 65.0
        elif last < 0 and last < prev:
            return 35.0
        return 50.0