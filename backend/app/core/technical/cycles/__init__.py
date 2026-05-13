"""
Cycle Indicators — Pegaton Invest Intelligence
Category: cycles (7 indicators)
"""
import numpy as np
import pandas as pd
from backend.app.core.technical.registry import (
    TechnicalIndicator, register_indicator
)


@register_indicator('cycles', 'hilbert')
class HilbertTransform(TechnicalIndicator):
    """Hilbert Transform — Instantaneous Trendline."""
    name = "Hilbert Transform"
    category = "cycles"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        price = df[col].values
        n = len(price)
        detrender = np.zeros(n)
        q1 = np.zeros(n)
        i1 = np.zeros(n)
        jI = np.zeros(n)
        jQ = np.zeros(n)

        for i in range(period, n):
            detrender[i] = 0.0962 * price[i] + 0.5769 * price[i-2] - 0.5769 * price[i-4] - 0.0962 * price[i-6]
        for i in range(3, n):
            q1[i] = 0.0962 * detrender[i] + 0.5769 * detrender[i-2] - 0.5769 * detrender[i-4] - 0.0962 * detrender[i-6]
            i1[i] = detrender[i-3]

        ji = np.zeros(n)
        jq = np.zeros(n)
        for i in range(3, n):
            ji[i] = 0.0962 * i1[i] + 0.5769 * i1[i-2] - 0.5769 * i1[i-4] - 0.0962 * i1[i-6]
            jq[i] = 0.0962 * q1[i] + 0.5769 * q1[i-2] - 0.5769 * q1[i-4] - 0.0962 * q1[i-6]

        phasor_angle = np.degrees(np.arctan2(q1, i1 + 1e-10))
        phasor_amp = np.sqrt(i1**2 + q1**2)
        dc_period = np.zeros(n)
        smooth_period = np.zeros(n)

        for i in range(3, n):
            dc_period[i] = 0.0
            for j in range(5, 31):
                if phasor_angle[i] > phasor_angle[i-j]:
                    dc_period[i] += 1
            dc_period[i] = dc_period[i] * 2 * np.pi / 30.0
            smooth_period[i] = 0.33 * dc_period[i] + 0.67 * smooth_period[i-1]
            if smooth_period[i] < 6:
                smooth_period[i] = 6
            elif smooth_period[i] > 50:
                smooth_period[i] = 50

        df['hilbert_inphase'] = i1
        df['hilbert_quadrature'] = q1
        df['hilbert_phasor'] = phasor_angle
        df['hilbert_dcperiod'] = smooth_period
        for c in ['hilbert_inphase', 'hilbert_quadrature', 'hilbert_phasor', 'hilbert_dcperiod']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'hilbert_dcperiod' not in df.columns:
            self.calculate(df)
        period = df['hilbert_dcperiod'].iloc[-1]
        if period < 10:
            return 70.0
        elif period > 30:
            return 30.0
        return 50.0


@register_indicator('cycles', 'dominant_cycle')
class DominantCycle(TechnicalIndicator):
    """Dominant Cycle Length using Autocorrelation."""
    name = "Dominant Cycle"
    category = "cycles"
    requires_periods = 30

    def calculate(self, df: pd.DataFrame, max_lag: int = 30) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        signal = df[col].values - df[col].rolling(window=5).mean().bfill().values
        n = len(signal)
        autocorr = np.zeros((n, max_lag))
        for lag in range(1, max_lag + 1):
            if lag < n:
                c = np.corrcoef(signal[:-lag], signal[lag:])[0, 1] if lag < len(signal) else 0
                autocorr[lag:, lag-1] = c if not np.isnan(c) else 0
        dominant = np.zeros(n)
        for i in range(max_lag, n):
            row = autocorr[i]
            peaks = []
            for j in range(2, max_lag - 1):
                if row[j] > row[j-1] and row[j] > row[j+1] and row[j] > 0.3:
                    peaks.append((j + 1, row[j]))
            if peaks:
                dominant[i] = max(peaks, key=lambda x: x[1])[0]
            else:
                dominant[i] = dominant[i-1] if i > 0 else 20
        df['dominant_cycle'] = dominant
        df['dominant_cycle'] = df['dominant_cycle'].bfill().fillna(20)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'dominant_cycle' not in df.columns:
            self.calculate(df)
        cycle = df['dominant_cycle'].iloc[-1]
        return normalize_score(cycle, 5, 40)


@register_indicator('cycles', 'sine_wave')
class SineWave(TechnicalIndicator):
    """MESA Sine Wave."""
    name = "Sine Wave"
    category = "cycles"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        price = df[col].values
        n = len(price)
        smooth = np.zeros(n)
        cycle = np.zeros(n)
        for i in range(period, n):
            smooth[i] = (4 * price[i] + 3 * price[i-1] + 2 * price[i-2] + price[i-3]) / 10
        for i in range(2, n):
            re = 0
            im = 0
            for j in range(period):
                if i - j >= 0:
                    re += np.sin(360 * j / period) * smooth[i-j]
                    im += np.cos(360 * j / period) * smooth[i-j]
            cycle[i] = np.arctan2(im, re + 1e-10)
        df['sine_wave'] = np.sin(cycle)
        df['sine_wave_lead'] = np.sin(cycle + np.pi/4)
        for c in ['sine_wave', 'sine_wave_lead']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'sine_wave' not in df.columns:
            self.calculate(df)
        sw = df['sine_wave'].iloc[-1]
        return normalize_score(sw, -1, 1)


@register_indicator('cycles', 'trend_cycle')
class TrendCycle(TechnicalIndicator):
    """Trend-Cycle Decomposition."""
    name = "Trend Cycle"
    category = "cycles"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        close = df[col]
        cycle = np.zeros(len(close))
        for i in range(period, len(close)):
            segment = close.iloc[i-period+1:i+1].values
            cycle[i] = segment[-1] - segment.mean()
        trend = close - cycle
        df['trend_cycle_component'] = cycle
        df['trend_cycle_trend'] = trend
        df['trend_cycle_oscillator'] = cycle / (trend.abs() + 1e-10)
        for c in ['trend_cycle_component', 'trend_cycle_trend', 'trend_cycle_oscillator']:
            df[c] = df[c].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'trend_cycle_oscillator' not in df.columns:
            self.calculate(df)
        osc = df['trend_cycle_oscillator'].iloc[-1]
        return normalize_score(osc, -0.1, 0.1)


@register_indicator('cycles', 'mama')
class MAMA(TechnicalIndicator):
    """MESA Adaptive Moving Average."""
    name = "MAMA"
    category = "cycles"
    requires_periods = 30

    def calculate(self, df: pd.DataFrame, fast: float = 0.5, slow: float = 0.05) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        price = df[col].values
        n = len(price)
        mama = np.zeros(n)
        fama = np.zeros(n)
        mama[0] = price[0]
        fama[0] = price[0]
        for i in range(1, n):
            smooth = (4 * price[i] + 3 * price[i-1] + 2 * price[max(0,i-2)] + price[max(0,i-3)]) / 10
            detrender = (0.0962 * smooth + 0.5769 * 0 - 0.5769 * 0 - 0.0962 * 0)
            q1 = (0.0962 * detrender + 0.5769 * 0 - 0.5769 * 0 - 0.0962 * 0)
            i1 = detrender
            ji = (0.0962 * i1 + 0.5769 * 0 - 0.5769 * 0 - 0.0962 * 0)
            jq = (0.0962 * q1 + 0.5769 * 0 - 0.5769 * 0 - 0.0962 * 0)
            i2 = i1 - jq
            q2 = q1 + ji
            re = i2 * i2 + q2 * q2
            im = i2 * q1 - q2 * i1
            if im != 0 and re != 0:
                period = 2 * np.pi / np.arctan(im / re)
            else:
                period = 0
            if period < 6:
                period = 6
            elif period > 50:
                period = 50
            alpha = fast / period
            mama[i] = alpha * price[i] + (1 - alpha) * mama[i-1]
            fama[i] = (slow / 2) * mama[i] + (1 - slow / 2) * fama[i-1]
        df['mama'] = mama
        df['fama'] = fama
        df['mama_fama_diff'] = mama - fama
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'mama' not in df.columns:
            self.calculate(df)
        diff = df['mama_fama_diff'].iloc[-1]
        return normalize_score(diff, df['mama_fama_diff'].quantile(0.05), df['mama_fama_diff'].quantile(0.95))


@register_indicator('cycles', 'fama')
class FAMA(MAMA):
    """Following Adaptive Moving Average (FAMA)."""
    name = "FAMA"
    category = "cycles"
    requires_periods = 30

    def calculate(self, df: pd.DataFrame, fast: float = 0.5, slow: float = 0.05) -> pd.DataFrame:
        if 'mama' not in df.columns:
            super().calculate(df, fast, slow)
        df['fama'] = df['fama']
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'fama' not in df.columns:
            MAMA().calculate(df)
        price = df['close'].iloc[-1] if 'close' in df.columns else df.iloc[-1, -1]
        fama = df['fama'].iloc[-1]
        return 65.0 if price > fama else 35.0


@register_indicator('cycles', 'roofing_filter')
class RoofingFilter(TechnicalIndicator):
    """Roofing Filter."""
    name = "Roofing Filter"
    category = "cycles"
    requires_periods = 20

    def calculate(self, df: pd.DataFrame, hp_period: int = 10, lp_period: int = 48) -> pd.DataFrame:
        col = 'close' if 'close' in df.columns else df.columns[-1]
        close = df[col]
        alpha1 = (np.cos(0.07 * 2 * np.pi / hp_period) + np.sin(0.07 * 2 * np.pi / hp_period) - 1) / np.cos(0.07 * 2 * np.pi / hp_period) if hp_period > 0 else 0.1
        hp = pd.Series(0.0, index=df.index)
        for i in range(1, len(close)):
            hp.iloc[i] = 0.5 * (1 + alpha1) * (close.iloc[i] - close.iloc[i-1]) + alpha1 * hp.iloc[i-1]
        alpha2 = (np.cos(0.15 * 2 * np.pi / lp_period) + np.sin(0.15 * 2 * np.pi / lp_period) - 1) / np.cos(0.15 * 2 * np.pi / lp_period) if lp_period > 0 else 0.04
        filt = pd.Series(0.0, index=df.index)
        for i in range(1, len(hp)):
            filt.iloc[i] = 0.5 * (1 + alpha2) * (hp.iloc[i] + hp.iloc[i-1]) + alpha2 * filt.iloc[i-1]
        df['roofing_filter'] = filt
        df['roofing_filter'] = df['roofing_filter'].fillna(0)
        return df

    def score(self, df: pd.DataFrame, **params) -> float:
        if 'roofing_filter' not in df.columns:
            self.calculate(df)
        f = df['roofing_filter'].iloc[-1]
        prev = df['roofing_filter'].iloc[-3] if len(df) >= 3 else f
        if f > prev and f > 0:
            return 70.0
        elif f < prev and f < 0:
            return 30.0
        return 50.0