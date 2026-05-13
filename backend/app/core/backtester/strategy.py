"""
Strategy Interface — Define el contrato para todas las estrategias de backtesting.
P0-02: Backtesting Engine | EP-FR-001
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd


class Strategy(ABC):
    """
    Clase base abstracta para estrategias de backtesting.
    Cada estrategia debe implementar initialize() y generate_signals().
    """

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        self._initialized = False

    @abstractmethod
    def initialize(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> None:
        """Inicializa la estrategia con datos históricos y parámetros."""
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Genera señales de trading sobre los datos.
        Debe añadir columna 'signal': 1 (compra), -1 (venta), 0 (neutral).
        """
        pass

    def is_initialized(self) -> bool:
        return self._initialized


class MACrossoverStrategy(Strategy):
    """
    Estrategia de cruce de medias móviles.
    Señal de compra cuando SMA rápida > SMA lenta.
    Señal de venta cuando SMA rápida < SMA lenta.
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("MACrossover")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def initialize(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> None:
        if params:
            self.fast_period = params.get("fast_period", self.fast_period)
            self.slow_period = params.get("slow_period", self.slow_period)
        self._initialized = True

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["sma_fast"] = df["close"].rolling(window=self.fast_period).mean()
        df["sma_slow"] = df["close"].rolling(window=self.slow_period).mean()
        df["signal"] = 0
        df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
        df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1
        return df


class RSIReversalStrategy(Strategy):
    """
    Estrategia de reversión RSI.
    Compra cuando RSI < oversold (default 30).
    Vende cuando RSI > overbought (default 70).
    """

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        super().__init__("RSIReversal")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def initialize(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> None:
        if params:
            self.period = params.get("period", self.period)
            self.oversold = params.get("oversold", self.oversold)
            self.overbought = params.get("overbought", self.overbought)
        self._initialized = True

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        delta = df["close"].diff()
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        avg_gain = gains.rolling(window=self.period).mean()
        avg_loss = losses.rolling(window=self.period).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan")).fillna(1)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["signal"] = 0
        df.loc[df["rsi"] < self.oversold, "signal"] = 1
        df.loc[df["rsi"] > self.overbought, "signal"] = -1
        return df


class BollingerBandsStrategy(Strategy):
    """
    Estrategia de Bandas de Bollinger.
    Compra cuando precio toca la banda inferior.
    Vende cuando precio toca la banda superior.
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("BollingerBands")
        self.period = period
        self.std_dev = std_dev

    def initialize(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> None:
        if params:
            self.period = params.get("period", self.period)
            self.std_dev = params.get("std_dev", self.std_dev)
        self._initialized = True

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["sma"] = df["close"].rolling(window=self.period).mean()
        df["std"] = df["close"].rolling(window=self.period).std()
        df["upper"] = df["sma"] + (df["std"] * self.std_dev)
        df["lower"] = df["sma"] - (df["std"] * self.std_dev)
        df["signal"] = 0
        df.loc[df["close"] <= df["lower"], "signal"] = 1
        df.loc[df["close"] >= df["upper"], "signal"] = -1
        return df


STRATEGY_REGISTRY: Dict[str, Strategy] = {
    "MACross": MACrossoverStrategy(),
    "RSIReversal": RSIReversalStrategy(),
    "BollingerBands": BollingerBandsStrategy(),
}


def get_strategy(name: str) -> Strategy:
    """Obtiene una estrategia del registro por nombre."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Estrategia desconocida: {name}. Disponibles: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]


def list_strategies() -> List[Dict[str, Any]]:
    """Lista todas las estrategias registradas."""
    return [{"name": name, "type": type(s).__name__} for name, s in STRATEGY_REGISTRY.items()]