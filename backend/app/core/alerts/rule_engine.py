"""
Rule Engine — Motor de evaluación de reglas de alertas.
P0-03: Alert System | EP-FR-001
"""
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Rule:
    """Representa una regla de alerta individual."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        enabled: bool = True,
        conditions: Optional[List[Dict]] = None,
        actions: Optional[List[Dict]] = None,
        cooldown_minutes: float = 60.0,
        last_triggered: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.name = name
        self.enabled = enabled
        self.conditions = conditions or []
        self.actions = actions or []
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = last_triggered
        self._last_trigger_ts: float = 0.0
        if last_triggered:
            try:
                dt = datetime.fromisoformat(last_triggered.replace("Z", "+00:00"))
                self._last_trigger_ts = dt.timestamp()
            except (ValueError, AttributeError):
                pass

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "actions": self.actions,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered,
        }


class RuleEngine:
    """
    Motor de evaluación de reglas.
    Almacena reglas y las evalúa contra datos del mercado.
    """

    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._metrics_cache: Dict[str, float] = {}

    def add_rule(self, rule: Rule) -> None:
        self._rules[rule.rule_id] = rule
        logger.debug(f"Regla añadida: {rule.rule_id} ({rule.name})")

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.debug(f"Regla eliminada: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[Rule]:
        return list(self._rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def update_metric(self, key: str, value: float) -> None:
        """Actualiza un métrico que las reglas pueden evaluar."""
        self._metrics_cache[key] = value

    def update_metrics(self, metrics: Dict[str, float]) -> None:
        """Actualiza múltiples métricos."""
        self._metrics_cache.update(metrics)

    def clear_metrics(self) -> None:
        self._metrics_cache.clear()

    def evaluate(self) -> List[Dict[str, Any]]:
        """
        Evalúa todas las reglas habilitadas contra los métricos actuales.

        Returns:
            Lista de dicts con las reglas que se dispararon.
        """
        triggered = []
        now = time.time()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Verificar cooldown
            elapsed = (now - rule._last_trigger_ts) / 60.0
            if elapsed < rule.cooldown_minutes:
                continue

            # Evaluar condiciones
            met_conditions = self._evaluate_conditions(rule.conditions)
            if met_conditions:
                rule.last_triggered = datetime.now(timezone.utc).isoformat()
                rule._last_trigger_ts = now
                triggered.append({
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "conditions_met": met_conditions,
                    "actions": rule.actions,
                })
                logger.info(f"⚠️ Regla disparada: {rule.name} ({rule.rule_id})")

        return triggered

    def _evaluate_conditions(self, conditions: List[Dict]) -> List[str]:
        """
        Evalúa una lista de condiciones contra los métricos cacheados.

        Cada condición es un dict con:
          - metric: str (clave en _metrics_cache)
          - operator: str ('>', '>=', '<', '<=', '==', '!=', 'in', 'not_in')
          - value: referencia para comparar (escalar o lista)

        Returns:
            Lista de strings describiendo las condiciones cumplidas.
        """
        met = []
        for cond in conditions:
            metric_name = cond.get("metric")
            operator = cond.get("operator")
            threshold = cond.get("value")

            if metric_name not in self._metrics_cache:
                continue

            actual = self._metrics_cache[metric_name]

            if self._compare(actual, operator, threshold):
                met.append(
                    f"{metric_name} {operator} {threshold} (actual: {actual})"
                )

        return met

    @staticmethod
    def _compare(actual: float, operator: str, threshold) -> bool:
        """Compara un valor actual contra un umbral con el operador dado."""
        ops = {
            ">": lambda a, t: a > t,
            ">=": lambda a, t: a >= t,
            "<": lambda a, t: a < t,
            "<=": lambda a, t: a <= t,
            "==": lambda a, t: a == t,
            "!=": lambda a, t: a != t,
            "in": lambda a, t: a in t if isinstance(t, (list, tuple, set)) else False,
            "not_in": lambda a, t: a not in t if isinstance(t, (list, tuple, set)) else True,
        }
        comparator = ops.get(operator)
        if comparator is None:
            logger.warning(f"Operador desconocido: {operator}")
            return False
        return comparator(actual, threshold)

    def evaluate_single(self, rule_id: str, metrics: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Evalúa una regla específica con métricos proporcionados (sin usar cache).

        Args:
            rule_id: ID de la regla a evaluar
            metrics: Dict de métricos para esta evaluación

        Returns:
            Dict con resultado si se disparó, None si no
        """
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            return None

        met_conditions = []
        for cond in rule.conditions:
            metric_name = cond.get("metric")
            operator = cond.get("operator")
            threshold = cond.get("value")

            if metric_name in metrics:
                if self._compare(metrics[metric_name], operator, threshold):
                    met_conditions.append(
                        f"{metric_name} {operator} {threshold} (actual: {metrics[metric_name]})"
                    )

        if met_conditions:
            return {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "conditions_met": met_conditions,
                "actions": rule.actions,
            }
        return None

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def enabled_count(self) -> int:
        return sum(1 for r in self._rules.values() if r.enabled)

    def summary(self) -> dict:
        return {
            "total_rules": self.rule_count,
            "enabled_rules": self.enabled_count,
            "metrics_cached": len(self._metrics_cache),
            "rules": [r.to_dict() for r in self._rules.values()],
        }