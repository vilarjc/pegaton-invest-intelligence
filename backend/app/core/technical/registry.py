"""
Technical Indicators Base — Pegaton Invest Intelligence
SDD Nivel 2 — P0-05: Indicadores Técnicos Avanzados (50+)
"""
import numpy as np
import pandas as pd
from typing import Optional, Dict, List

__all__ = ['TechnicalIndicator', 'IndicatorRegistry']


class TechnicalIndicator:
    """Interfaz base para todos los indicadores técnicos."""
    name: str = "base"
    category: str = "base"
    requires_periods: int = 14

    def calculate(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        raise NotImplementedError

    def score(self, df: pd.DataFrame, **params) -> float:
        """Retorna score de señalización (0-100)."""
        raise NotImplementedError


class IndicatorRegistry:
    """Catálogo auto-registrable de indicadores técnicos."""

    def __init__(self):
        self._indicators: Dict[str, Dict] = {}

    def register(self, category: str, name: str, cls):
        self._indicators[f"{category}.{name}"] = {
            'category': category,
            'name': name,
            'class': cls,
            'requires_periods': getattr(cls, 'requires_periods', 14),
        }

    def get(self, key: str):
        return self._indicators.get(key)

    def list_all(self, category: Optional[str] = None) -> List[Dict]:
        if category:
            return [v for v in self._indicators.values() if v['category'] == category]
        return list(self._indicators.values())

    def categories(self) -> List[str]:
        return sorted(set(v['category'] for v in self._indicators.values()))

    def count(self, category: Optional[str] = None) -> int:
        if category:
            return len([v for v in self._indicators.values() if v['category'] == category])
        return len(self._indicators)


# Global singleton registry
_registry = IndicatorRegistry()

def register_indicator(category: str, name: str):
    """Decorator para registrar indicadores automáticamente."""
    def decorator(cls):
        _registry.register(category, name, cls)
        return cls
    return decorator

def get_registry() -> IndicatorRegistry:
    return _registry