"""
Monte Carlo Simulator — Genera escenarios de retornos aleatorios.
P0-02: Backtesting Engine | EP-FR-001
"""
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Simula múltiples escenarios de retornos basándose en la distribución
    histórica de retornos de una estrategia.
    """

    def __init__(self, n_scenarios: int = 1000, seed: int = 42):
        self.n_scenarios = n_scenarios
        self.seed = seed
        np.random.seed(seed)

    def simulate(
        self,
        returns: List[float],
        n_scenarios: Optional[int] = None,
        horizon: int = 252,
    ) -> Dict[str, Any]:
        """
        Simula escenarios de retornos futuros.

        Args:
            returns: Lista de retornos porcentuales (ej: [0.01, -0.005, ...])
            n_scenarios: Número de escenarios (default 1000)
            horizon: Horizonte en días (default 252 = 1 año)

        Returns:
            Diccionario con percentiles, probabilidad de ruina y estadísticas
        """
        n_scenarios = n_scenarios or self.n_scenarios

        if not returns or len(returns) < 2:
            return {
                "error": "Se necesitan al menos 2 retornos históricos",
                "n_scenarios": n_scenarios,
                "horizon": horizon,
            }

        returns_arr = np.array(returns, dtype=np.float64)

        # Calcular estadísticos de la distribución
        mean_return = np.mean(returns_arr)
        std_return = np.std(returns_arr, ddof=1)

        # Generar escenarios: retornos acumulados sobre horizonte
        # Cada escenario: suma de retornos diarios aleatorios
        daily_returns_matrix = np.random.normal(
            loc=mean_return,
            scale=std_return,
            size=(n_scenarios, horizon),
        )

        # Retorno acumulado por escenario
        cumulative_returns = np.sum(daily_returns_matrix, axis=1)
        final_values = (1 + cumulative_returns) * 100  # Base 100

        # Percentiles
        percentiles = {
            "p5": float(np.percentile(final_values, 5)),
            "p10": float(np.percentile(final_values, 10)),
            "p25": float(np.percentile(final_values, 25)),
            "p50": float(np.percentile(final_values, 50)),  # Mediana
            "p75": float(np.percentile(final_values, 75)),
            "p90": float(np.percentile(final_values, 90)),
            "p95": float(np.percentile(final_values, 95)),
        }

        # Probabilidad de ruina (valor final < 90% del inicial)
        ruin_threshold = 90.0
        ruin_count = int(np.sum(final_values < ruin_threshold))
        ruin_probability = ruin_count / n_scenarios

        # Probabilidad de pérdida
        loss_count = int(np.sum(final_values < 100.0))
        loss_probability = loss_count / n_scenarios

        # Probabilidad de duplicar (valor final > 120% del inicial)
        double_count = int(np.sum(final_values > 120.0))
        double_probability = double_count / n_scenarios

        # Estadísticas de la distribución de retornos diarios
        daily_stats = {
            "mean": float(mean_return),
            "std": float(std_return),
            "skewness": float(self._skewness(returns_arr)),
            "kurtosis": float(self._kurtosis(returns_arr)),
            "min": float(np.min(returns_arr)),
            "max": float(np.max(returns_arr)),
        }

        # Estadísticas de escenarios
        scenario_stats = {
            "mean_final": float(np.mean(final_values)),
            "std_final": float(np.std(final_values)),
            "min_final": float(np.min(final_values)),
            "max_final": float(np.max(final_values)),
        }

        return {
            "n_scenarios": n_scenarios,
            "horizon_days": horizon,
            "ruin_probability": round(ruin_probability, 4),
            "loss_probability": round(loss_probability, 4),
            "double_probability": round(double_probability, 4),
            "percentiles": {k: round(v, 4) for k, v in percentiles.items()},
            "daily_stats": {k: round(v, 6) for k, v in daily_stats.items()},
            "scenario_stats": {k: round(v, 4) for k, v in scenario_stats.items()},
            "raw_final_values": final_values.tolist()[:100],  # Primeros 100 para visualización
        }

    @staticmethod
    def _skewness(arr: np.ndarray) -> float:
        """Calcula asimetría (skewness) de un array."""
        n = len(arr)
        if n < 3:
            return 0.0
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(((arr - mean) / std) ** 3))

    @staticmethod
    def _kurtosis(arr: np.ndarray) -> float:
        """Calcula curtosis de un array (exceso de curtosis)."""
        n = len(arr)
        if n < 4:
            return 0.0
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std == 0:
            return 0.0
        kurt = np.mean(((arr - mean) / std) ** 4)
        return float(kurt - 3.0)  # Exceso de curtosis