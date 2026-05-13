"""
Pattern Indicators — Pegaton Invest Intelligence
Category: patterns (8 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('patterns', 'double_top_bottom')
class DoubleTopBottom(TechnicalIndicator):
    """Double Top / Double Bottom."""
    name = "Double Top/Bottom"
    category = "patterns"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        double_top = pd.Series(0.0, index=df.index)
        double_bot = pd.Series(0.0, index=df.index)
        for i in range(lookback, len(df)):
            segment_h = high.iloc[i-lookback:i+1]
            segment_l = low.iloc[i-lookback:i+1]
            max_idx = segment_h.idxmax()
            min_idx = segment_l.idxmin()
            if max_idx < i and max_idx > i - lookback:
                peak2_prev = segment_h.nlargest(2).iloc[-1]
                if peak2_prev / segment_h.max() > 0.95:
                    double_top.iloc[i] = 1.0
            if min_idx < i and min_idx > i - lookback:
                trough2_prev = segment_l.nsmallest(2).iloc[-1]
                if trough2_prev / segment_l.min() < 1.05:
                    double_bot.iloc[i] = 1.0
        df['double_top'] = double_top
        df['double_bottom'] = double_bot
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'double_top' not in df.columns:
            self.calculate(df, **params)
        dt = df['double_top'].iloc[-1]
        db = df['double_bottom'].iloc[-1]
        if db == 1:
            return 75.0
        elif dt == 1:
            return 25.0
        return 50.0


@register_indicator('patterns', 'head_shoulders')
class HeadAndShoulders(TechnicalIndicator):
    """Head and Shoulders."""
    name = "Head & Shoulders"
    category = "patterns"
    requires_periods = 30

    def calculate(self, df: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        hs_bear = pd.Series(0.0, index=df.index)
        hs_inv_bull = pd.Series(0.0, index=df.index)
        for i in range(lookback, len(df)):
            seg = high.iloc[i-lookback:i+1]
            vals = seg.values
            if len(vals) < 5:
                continue
            peaks = []
            for j in range(2, len(vals) - 2):
                if vals[j] > vals[j-1] and vals[j] > vals[j-2] and vals[j] > vals[j+1] and vals[j] > vals[j+2]:
                    peaks.append((i - lookback + j, vals[j]))
            if len(peaks) >= 3:
                p1, p2, p3 = peaks[0], peaks[len(peaks)//2], peaks[-1]
                if p2[1] > p1[1] and p2[1] > p3[1] and abs(p1[1] - p3[1]) / max(p1[1], 1) < 0.05:
                    hs_bear.iloc[i] = 1.0
            lows = []
            low_seg = df['low'].iloc[i-lookback:i+1] if 'low' in df.columns else seg
            lv = low_seg.values
            for j in range(2, len(lv) - 2):
                if lv[j] < lv[j-1] and lv[j] < lv[j-2] and lv[j] < lv[j+1] and lv[j] < lv[j+2]:
                    lows.append((i - lookback + j, lv[j]))
            if len(lows) >= 3:
                p1, p2, p3 = lows[0], lows[len(lows)//2], lows[-1]
                if p2[1] < p1[1] and p2[1] < p3[1] and abs(p1[1] - p3[1]) / max(p1[1], 1) < 0.05:
                    hs_inv_bull.iloc[i] = 1.0
        df['hs_bearish'] = hs_bear
        df['hs_inverse_bullish'] = hs_inv_bull
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'hs_bearish' not in df.columns:
            self.calculate(df, **params)
        if df['hs_inverse_bullish'].iloc[-1]:
            return 75.0
        elif df['hs_bearish'].iloc[-1]:
            return 25.0
        return 50.0


@register_indicator('patterns', 'triangle')
class TrianglePattern(TechnicalIndicator):
    """Triangle Patterns — Symmetrical, Ascending, Descending."""
    name = "Triangle"
    category = "patterns"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        highs = high.iloc[-lookback:].values
        lows = low.iloc[-lookback:].values
        symm = self._is_symmetrical(highs, lows)
        asc = self._is_ascending(highs, lows)
        desc = self._is_descending(highs, lows)
        df['triangle_symmetrical'] = symm
        df['triangle_ascending'] = asc
        df['triangle_descending'] = desc
        return df

    @staticmethod
    def _is_symmetrical(h, l):
        h_range = np.nanmax(h) - np.nanmin(h)
        l_range = np.nanmax(l) - np.nanmin(l)
        return 1.0 if h_range < 0.02 and l_range < 0.02 else 0.0

    @staticmethod
    def _is_ascending(h, l):
        return 1.0 if np.all(np.diff(l) >= -0.001) and h[-1] <= h[0] else 0.0

    @staticmethod
    def _is_descending(h, l):
        return 1.0 if np.all(np.diff(h) <= 0.001) and l[-1] >= l[0] else 0.0

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'triangle_symmetrical' not in df.columns:
            self.calculate(df, **params)
        asc = df['triangle_ascending'].iloc[-1]
        desc = df['triangle_descending'].iloc[-1]
        sym = df['triangle_symmetrical'].iloc[-1]
        if asc == 1:
            return 70.0
        elif desc == 1:
            return 30.0
        elif sym == 1:
            return 55.0
        return 50.0


@register_indicator('patterns', 'flag_pennant')
class FlagPennant(TechnicalIndicator):
    """Flag and Pennant Patterns."""
    name = "Flag/Pennant"
    category = "patterns"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        ret = close.pct_change()
        consec = 0
        flag_bull = pd.Series(0.0, index=df.index)
        flag_bear = pd.Series(0.0, index=df.index)
        vol_threshold = df['volume'].rolling(lookback).mean() if 'volume' in df.columns else pd.Series(1, index=df.index)
        for i in range(lookback, len(df)):
            recent = ret.iloc[i-lookback:i]
            if recent.iloc[0] > 0.05:
                body = abs(recent.values)
                if all(b < 0.02 for b in body[1:]):
                    flag_bull.iloc[i] = 1.0
            elif recent.iloc[0] < -0.05:
                body = abs(recent.values)
                if all(b < 0.02 for b in body[1:]):
                    flag_bear.iloc[i] = 1.0
        df['flag_bullish'] = flag_bull
        df['flag_bearish'] = flag_bear
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'flag_bullish' not in df.columns:
            self.calculate(df, **params)
        fb = df['flag_bullish'].iloc[-1]
        fbe = df['flag_bearish'].iloc[-1]
        if fb == 1:
            return 70.0
        elif fbe == 1:
            return 30.0
        return 50.0


@register_indicator('patterns', 'wedge')
class WedgePattern(TechnicalIndicator):
    """Wedge Patterns — Rising and Falling Wedges."""
    name = "Wedge"
    category = "patterns"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        h = high.iloc[-lookback:].values
        l = low.iloc[-lookback:].values
        rising = self._is_rising_wedge(h, l)
        falling = self._is_falling_wedge(h, l)
        df['wedge_rising'] = rising
        df['wedge_falling'] = falling
        return df

    @staticmethod
    def _is_rising_wedge(h, l):
        h_slope = np.polyfit(range(len(h)), h, 1)[0]
        l_slope = np.polyfit(range(len(l)), l, 1)[0]
        return 1.0 if h_slope > 0 and l_slope > 0 and h_slope > l_slope else 0.0

    @staticmethod
    def _is_falling_wedge(h, l):
        h_slope = np.polyfit(range(len(h)), h, 1)[0]
        l_slope = np.polyfit(range(len(l)), l, 1)[0]
        return 1.0 if h_slope < 0 and l_slope < 0 and l_slope > h_slope else 0.0

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'wedge_rising' not in df.columns:
            self.calculate(df, **params)
        rf = df['wedge_rising'].iloc[-1]
        ff = df['wedge_falling'].iloc[-1]
        if ff == 1:
            return 72.0
        elif rf == 1:
            return 28.0
        return 50.0


@register_indicator('patterns', 'gap')
class GapPattern(TechnicalIndicator):
    """Gap Detection — Breakaway, Runaway, Exhaustion."""
    name = "Gap"
    category = "patterns"
    requires_periods = 5

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        open_p = df['open'] if 'open' in df.columns else df['close']
        gap_up = (open_p - high.shift(1)) / high.shift(1) * 100
        gap_down = (low - open_p.shift(1)) / open_p.shift(1) * 100
        df['gap_up_pct'] = gap_up.fillna(0)
        df['gap_down_pct'] = gap_down.fillna(0)
        df['gap_type'] = 0
        df.loc[gap_up > 1, 'gap_type'] = 1
        df.loc[gap_down > 1, 'gap_type'] = -1
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'gap_type' not in df.columns:
            self.calculate(df)
        gt = df['gap_type'].iloc[-1]
        return 70.0 if gt == 1 else 30.0 if gt == -1 else 50.0


@register_indicator('patterns', 'support_resistance')
class SupportResistance(TechnicalIndicator):
    """Support and Resistance Levels."""
    name = "Support/Resistance"
    category = "patterns"
    requires_periods = 50

    def calculate(self, df: pd.DataFrame, lookback: int = 50) -> pd.DataFrame:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close'] if 'close' in df.columns else df.iloc[:, -1]
        pivot = (high.rolling(lookback).max() + low.rolling(lookback).min() + close) / 3
        s1 = 2 * pivot - high.rolling(lookback).max()
        r1 = 2 * pivot - low.rolling(lookback).min()
        s2 = pivot - (high.rolling(lookback).max() - low.rolling(lookback).min())
        r2 = pivot + (high.rolling(lookback).max() - low.rolling(lookback).min())
        df['pivot'] = pivot
        df['support_1'] = s1
        df['resistance_1'] = r1
        df['support_2'] = s2
        df['resistance_2'] = r2
        for c in ['pivot', 'support_1', 'resistance_1', 'support_2', 'resistance_2']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'pivot' not in df.columns:
            self.calculate(df)
        close = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        r1 = df['resistance_1'].iloc[-1]
        s1 = df['support_1'].iloc[-1]
        proximity = min(abs(close - r1), abs(close - s1))
        if close > r1:
            return 75.0
        elif close < s1:
            return 25.0
        elif proximity / close < 0.01:
            return 55.0
        return 50.0