"""
Trend Indicators — Pegaton Invest Intelligence
Category: trend (10 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('trend', 'sma')
class SMA(TechnicalIndicator):
    """Simple Moving Average."""
    name = "SMA"
    category = "trend"
    requires_periods = 50

    def calculate(self, df: pd.DataFrame, period: int = 50) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        df[f'sma_{period}'] = df[col].rolling(window=period).mean()
        df[f'sma_{period}'] = df[f'sma_{period}'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        period = params.get('period', 50)
        key = f'sma_{period}'
        if key not in df.columns:
            self.calculate(df, period=period)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        sma = df[key].iloc[-1]
        if close > sma:
            return 65.0
        elif close < sma:
            return 35.0
        return 50.0


@register_indicator('trend', 'ema')
class EMA(TechnicalIndicator):
    """Exponential Moving Average."""
    name = "EMA"
    category = "trend"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        df[f'ema_{period}'] = df[col].ewm(span=period).mean()
        df[f'ema_{period}'] = df[f'ema_{period}'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        period = params.get('period', 20)
        key = f'ema_{period}'
        if key not in df.columns:
            self.calculate(df, period=period)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        ema = df[key].iloc[-1]
        if close > ema:
            return 65.0
        elif close < ema:
            return 35.0
        return 50.0


@register_indicator('trend', 'wma')
class WMA(TechnicalIndicator):
    """Weighted Moving Average."""
    name = "WMA"
    category = "trend"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        weights = np.arange(1, period + 1)
        df[f'wma_{period}'] = df[col].rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
        df[f'wma_{period}'] = df[f'wma_{period}'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        period = params.get('period', 20)
        key = f'wma_{period}'
        if key not in df.columns:
            self.calculate(df, period=period)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        wma = df[key].iloc[-1]
        if close > wma:
            return 63.0
        elif close < wma:
            return 37.0
        return 50.0


@register_indicator('trend', 'macd')
class MACD(TechnicalIndicator):
    """MACD — Moving Average Convergence Divergence."""
    name = "MACD"
    category = "trend"
    requires_periods = 26

    def calculate(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        ema_fast = df[col].ewm(span=fast).mean()
        ema_slow = df[col].ewm(span=slow).mean()
        df['macd_line'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd_line'].ewm(span=signal).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']
        for c in ['macd_line', 'macd_signal', 'macd_hist']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'macd_hist' not in df.columns:
            self.calculate(df)
        hist = df['macd_hist'].iloc[-1]
        signal = df['macd_signal'].iloc[-1]
        if hist > 0 and hist > signal:
            return 70.0
        elif hist < 0 and hist < signal:
            return 30.0
        return 50.0


@register_indicator('trend', 'adx')
class ADX(TechnicalIndicator):
    """Average Directional Index."""
    name = "ADX"
    category = "trend"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        plus_dm = high - high.shift(1)
        minus_dm = low.shift(1) - low
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * plus_dm.rolling(window=period).mean() / (atr + 1e-10)
        minus_di = 100 * minus_dm.rolling(window=period).mean() / (atr + 1e-10)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        df['adx'] = dx.rolling(window=period).mean()
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        for c in ['adx', 'plus_di', 'minus_di']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'adx' not in df.columns:
            self.calculate(df, **params)
        adx = df['adx'].iloc[-1]
        plus = df['plus_di'].iloc[-1]
        minus = df['minus_di'].iloc[-1]
        if adx > 25 and plus > minus:
            return 75.0
        elif adx > 25 and minus > plus:
            return 25.0
        return 50.0


@register_indicator('trend', 'ichimoku')
class Ichimoku(TechnicalIndicator):
    """Ichimoku Kinko Hyo."""
    name = "Ichimoku"
    category = "trend"
    requires_periods = 52

    def calculate(self, df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou: int = 52) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        df['ichi_tenkan'] = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
        df['ichi_kijun'] = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
        df['ichi_senkou_a'] = ((df['ichi_tenkan'] + df['ichi_kijun']) / 2).shift(kijun)
        df['ichi_senkou_b'] = ((high.rolling(senkou).max() + low.rolling(senkou).min()) / 2).shift(kijun)
        df['ichi_chikou'] = close.shift(-kijun)
        for c in ['ichi_tenkan', 'ichi_kijun', 'ichi_senkou_a', 'ichi_senkou_b', 'ichi_chikou']:
            df[c] = df[c].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'ichi_senkou_a' not in df.columns:
            self.calculate(df, **params)
        close = df['close'].iloc[-1]
        a = df['ichi_senkou_a'].iloc[-1]
        b = df['ichi_senkou_b'].iloc[-1]
        tenkan = df['ichi_tenkan'].iloc[-1]
        kijun = df['ichi_kijun'].iloc[-1]
        above_cloud = close > max(a, b)
        tenkan_above_kijun = tenkan > kijun
        if above_cloud and tenkan_above_kijun:
            return 80.0
        elif not above_cloud and not tenkan_above_kijun:
            return 20.0
        return 50.0


@register_indicator('trend', 'supertrend')
class Supertrend(TechnicalIndicator):
    """Supertrend."""
    name = "Supertrend"
    category = "trend"
    requires_periods = 10

    def calculate(self, df: pd.DataFrame, period: int = 10, mult: float = 3.0) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        hl2 = (high + low) / 2
        atr = ATR().calculate(df.copy(), period)['atr']
        upper = hl2 + mult * atr
        lower = hl2 - mult * atr
        st = pd.Series(0.0, index=df.index)
        for i in range(1, len(df)):
            if close.iloc[i] > upper.iloc[i-1]:
                st.iloc[i] = lower.iloc[i]
            elif close.iloc[i] < lower.iloc[i-1]:
                st.iloc[i] = upper.iloc[i]
            else:
                prev = st.iloc[i-1] if st.iloc[i-1] != 0 else lower.iloc[i]
                if close.iloc[i] > prev:
                    st.iloc[i] = max(lower.iloc[i], prev)
                else:
                    st.iloc[i] = min(upper.iloc[i], prev)
        df['supertrend'] = st
        df['supertrend_trend'] = np.where(close > st, 1, -1)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'supertrend' not in df.columns:
            self.calculate(df, **params)
        trend = df['supertrend_trend'].iloc[-1]
        return 70.0 if trend == 1 else 30.0


@register_indicator('trend', 'parabolic_sar')
class ParabolicSAR(TechnicalIndicator):
    """Parabolic SAR."""
    name = "Parabolic SAR"
    category = "trend"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        sar = [low.iloc[0]]
        ep = high.iloc[0]
        af = step
        trend = 1
        for i in range(1, len(df)):
            if trend == 1:
                sar.append(sar[-1] + af * (ep - sar[-1]))
                if low.iloc[i] < sar[-1]:
                    trend = -1
                    sar[-1] = ep
                    ep = low.iloc[i]
                    af = step
                else:
                    if high.iloc[i] > ep:
                        ep = high.iloc[i]
                        af = min(af + step, max_step)
            else:
                sar.append(sar[-1] + af * (ep - sar[-1]))
                if high.iloc[i] > sar[-1]:
                    trend = 1
                    sar[-1] = ep
                    ep = high.iloc[i]
                    af = step
                else:
                    if low.iloc[i] < ep:
                        ep = low.iloc[i]
                        af = min(af + step, max_step)
        df['parabolic_sar'] = sar
        df['parabolic_trend'] = np.where(close > sar, 1, -1)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'parabolic_trend' not in df.columns:
            self.calculate(df, **params)
        return 70.0 if df['parabolic_trend'].iloc[-1] == 1 else 30.0


@register_indicator('trend', 'ama')
class AMA(TechnicalIndicator):
    """Adaptive Moving Average (Kaufman)."""
    name = "AMA"
    category = "trend"
    requires_periods = 30

    def calculate(self, df: pd.DataFrame, period: int = 10, fast: int = 2, slow: int = 30) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        direction = df[col].diff(period).abs()
        volatility = df[col].diff().abs().rolling(window=period).sum()
        er = direction / (volatility + 1e-10)
        sc_fast = 2.0 / (fast + 1)
        sc_slow = 2.0 / (slow + 1)
        sc = er * (sc_fast - sc_slow) + sc_slow
        sc = sc ** 2
        ama = pd.Series(0.0, index=df.index)
        ama.iloc[period] = df[col].iloc[period]
        for i in range(period + 1, len(df)):
            ama.iloc[i] = ama.iloc[i-1] + sc.iloc[i] * (df[col].iloc[i] - ama.iloc[i-1])
        df['ama'] = ama
        df['ama'] = df['ama'].bfill().fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'ama' not in df.columns:
            self.calculate(df, **params)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        ama = df['ama'].iloc[-1]
        return 65.0 if close > ama else 35.0


@register_indicator('trend', 'vortex')
class VortexIndicator(TechnicalIndicator):
    """Vortex Indicator."""
    name = "Vortex"
    category = "trend"
    requires_periods = 14

    def calculate(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        vm_plus = high - low.shift(1)
        vm_minus = low - high.shift(1)
        vm_plus = vm_plus.where(vm_plus > 0, 0)
        vm_minus = vm_minus.where(vm_minus > 0, 0)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        vi_plus = vm_plus.rolling(window=period).sum() / (tr.rolling(window=period).sum() + 1e-10)
        vi_minus = vm_minus.rolling(window=period).sum() / (tr.rolling(window=period).sum() + 1e-10)
        df['vortex_plus'] = vi_plus
        df['vortex_minus'] = vi_minus
        df['vortex_diff'] = vi_plus - vi_minus
        for c in ['vortex_plus', 'vortex_minus', 'vortex_diff']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'vortex_diff' not in df.columns:
            self.calculate(df, **params)
        diff = df['vortex_diff'].iloc[-1]
        return normalize_score(diff, -0.5, 0.5)