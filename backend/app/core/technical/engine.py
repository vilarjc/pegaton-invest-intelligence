"""
Technical Engine — Pegaton Invest Intelligence
Unified engine that runs all 50+ indicators and produces composite scores.
SDD Nivel 2 — P0-05
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from backend.app.core.technical.registry import get_registry, TechnicalIndicator
from backend.app.core.technical.scoring import composite_score


class TechnicalEngine:
    """
    Motor principal de análisis técnico.
    Ejecuta todos los indicadores registrados y genera scores compuestos.
    """

    def __init__(self):
        self.registry = get_registry()
        self._instance_cache: Dict[str, TechnicalIndicator] = {}
        self._last_run: Optional[datetime] = None
        self._last_results: Dict[str, Any] = {}

    def _get_or_create(self, category: str, name: str) -> TechnicalIndicator:
        key = f"{category}.{name}"
        if key not in self._instance_cache:
            entry = self.registry.get(key)
            if entry:
                self._instance_cache[key] = entry['class']()
        return self._instance_cache.get(key)

    def run_all(self, df: pd.DataFrame, min_periods: int = 20) -> Dict[str, Any]:
        """
        Ejecuta todos los indicadores registrados sobre el DataFrame.

        Args:
            df: DataFrame con columnas OHLCV (open, high, low, close, volume)
            min_periods: mínimo de filas requeridas para ejecutar

        Returns:
            {
                'composite': {...},
                'indicators': {category: {name: result}},
                'summary': {...},
                'metadata': {...}
            }
        """
        if len(df) < min_periods:
            return {
                'error': f'Mínimo {min_periods} períodos requeridos, recibidos {len(df)}',
                'composite': {'composite': 50.0, 'dominant_signal': 'neutral'},
                'indicators': {},
                'summary': {}
            }

        # Ensure float columns
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').ffill().fillna(0)

        indicator_results = {}
        categories = self.registry.categories()

        for category in categories:
            indicators = self.registry.list_all(category)
            for ind_info in indicators:
                key = f"{category}.{ind_info['name']}"
                try:
                    instance = self._get_or_create(category, ind_info['name'])
                    if instance and len(df) >= instance.requires_periods:
                        # Calculate
                        df_copy = df.copy()
                        df_with_ind = instance.calculate(df_copy)

                        # Score
                        score = instance.score(df_with_ind)

                        # Extract signal value
                        signal = self._extract_signal(df_with_ind, instance)

                        indicator_results[key] = {
                            'score': score,
                            'signal': signal,
                            'category': category,
                            'name': ind_info['name'],
                        }
                except Exception as e:
                    indicator_results[key] = {
                        'score': 50.0,
                        'signal': 0.0,
                        'category': category,
                        'name': ind_info['name'],
                        'error': str(e),
                    }

        # Composite scoring
        composite = composite_score(indicator_results)

        # Store results
        self._last_run = datetime.utcnow()
        self._last_results = {
            'composite': composite,
            'indicators': indicator_results,
            'summary': self._build_summary(composite, indicator_results),
            'metadata': {
                'timestamp': self._last_run.isoformat(),
                'total_indicators': len(indicator_results),
                'data_points': len(df),
                'categories': len(categories),
            }
        }

        return self._last_results

    def _extract_signal(self, df: pd.DataFrame, instance: TechnicalIndicator) -> float:
        """Extrae valor de señal normalizada del DataFrame."""
        last_val = df.iloc[-1]
        name = instance.name.lower().replace(' ', '_').replace('%', 'pct')

        # Buscar columnas relacionadas
        for col in df.columns:
            if name in col.lower():
                val = last_val.get(col, 0)
                if isinstance(val, (int, float, np.floating, np.integer)):
                    # Normalizar a rango -1 a 1
                    if 'rsi' in col or 'stoch' in col or 'mfi' in col:
                        return (val - 50) / 50  # 0-100 → -1 to 1
                    elif 'pctb' in col or 'pct' in col:
                        return (val - 50) / 50
                    elif 'hist' in col or 'vol' in col:
                        return 0.0  # informativos
                    else:
                        norm = abs(val)
                        if norm > 100:
                            norm = 100
                        return max(-1.0, min(1.0, val / (norm + 1e-10)))

        return 0.0

    def _build_summary(self, composite: Dict, indicators: Dict) -> Dict:
        """Construye resumen ejecutivo."""
        bull_count = sum(1 for i in indicators.values() if i['score'] > 55)
        bear_count = sum(1 for i in indicators.values() if i['score'] < 45)
        neutral_count = len(indicators) - bull_count - bear_count

        cat_scores = composite.get('by_category', {})
        strongest_cat = max(cat_scores.items(), key=lambda x: x[1]) if cat_scores else ('N/A', 50)
        weakest_cat = min(cat_scores.items(), key=lambda x: x[1]) if cat_scores else ('N/A', 50)

        return {
            'total_indicators': len(indicators),
            'bullish_signals': bull_count,
            'bearish_signals': bear_count,
            'neutral_signals': neutral_count,
            'strongest_category': {'name': strongest_cat[0], 'score': strongest_cat[1]},
            'weakest_category': {'name': weakest_cat[0], 'score': weakest_cat[1]},
            'confidence': self._calculate_confidence(composite, bull_count, bear_count, len(indicators)),
        }

    def _calculate_confidence(self, composite: Dict, bull: int, bear: int, total: int) -> str:
        """Calcula nivel de confianza en la señal."""
        dev = abs(composite['composite'] - 50)
        consensus = max(bull, bear) / total if total > 0 else 0
        if dev > 25 and consensus > 0.6:
            return 'high'
        elif dev > 15 and consensus > 0.5:
            return 'medium'
        return 'low'

    def run_category(self, df: pd.DataFrame, category: str) -> Dict[str, Any]:
        """Ejecuta solo una categoría de indicadores."""
        indicators = self.registry.list_all(category)
        results = {}
        for ind_info in indicators:
            key = ind_info['name']
            try:
                instance = self._get_or_create(category, ind_info['name'])
                if instance and len(df) >= instance.requires_periods:
                    df_copy = df.copy()
                    df_with_ind = instance.calculate(df_copy)
                    score = instance.score(df_with_ind)
                    results[key] = {'score': score, 'category': category}
            except Exception as e:
                results[key] = {'score': 50.0, 'error': str(e)}
        return results

    def get_categories(self) -> List[str]:
        return self.registry.categories()

    def get_indicator_count(self) -> Dict[str, int]:
        return {cat: self.registry.count(cat) for cat in self.registry.categories()}

    def get_last_results(self) -> Optional[Dict[str, Any]]:
        return self._last_results


# Global singleton
_engine = TechnicalEngine()


def get_engine() -> TechnicalEngine:
    return _engine