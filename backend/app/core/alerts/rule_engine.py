"""
Alert Rules Engine — Evalúa reglas de alertas contra datos del mercado.
P0-03: Alert System | EP-FR-001
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class Operator(Enum):
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"


class ConditionType(Enum):
    THRESHOLD = "threshold"
    CROSSOVER = "crossover"
    FEAR_GREED = "fear_greed"
    VOLUME_SPIKE = "volume_spike"
    PRICE_LEVEL = "price_level"
    MACRO_CHANGE = "macro_change"


class ActionType(Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class Rule:
    """Representa una regla de alerta configurable."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        enabled: bool = True,
        conditions: Optional[List[Dict]] = None,
        actions: Optional[List[Dict]] = None,
        cooldown_minutes: int = 60,
        last_triggered: Optional[str] = None,
    ):
        self.id = rule_id
        self.name = name
        self.enabled = enabled
        self.conditions = conditions or []
        self.actions = actions or []
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = last_triggered

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "actions": self.actions,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            rule_id=data["id"],
            name=data["name"],
            enabled=data.get("enabled", True),
            conditions=data.get("conditions", []),
            actions=data.get("actions", []),
            cooldown_minutes=data.get("cooldown_minutes", 60),
            last_triggered=data.get("last_triggered"),
        )

    @property
    def is_in_cooldown(self) -> bool:
        """Verifica si la regla está en período de cooldown."""
        if not self.last_triggered:
            return False
        last_ts = datetime.fromisoformat(self.last_triggered)
        elapsed = datetime.now(timezone.utc) - last_ts
        return elapsed < timedelta(minutes=self.cooldown_minutes)


class RuleEngine:
    """
    Motor de evaluación de reglas.
    Evalúa condiciones AND/OR contra datos del mercado.
    """

    def __init__(self):
        self.rules: Dict[str, Rule] = {}

    def add_rule(self, rule: Rule) -> None:
        """Registra una regla."""
        self.rules[rule.id] = rule
        logger.info(f"Regla añadida: {rule.name} ({rule.id})")

    def remove_rule(self, rule_id: str) -> bool:
        """Elimina una regla por ID."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Regla eliminada: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self.rules.get(rule_id)

    def get_all_rules(self) -> List[Rule]:
        return list(self.rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def evaluate(
        self,
        rule_id: str,
        indicators: Dict[str, Any],
        ticker: str = "",
    ) -> tuple[bool, str]:
        """
        Evalúa una regla contra los indicadores proporcionados.

        Args:
            rule_id: ID de la regla a evaluar
            indicators: Diccionario con valores de indicadores y datos de mercado
            ticker: Símbolo del activo (opcional)

        Returns:
            (triggered: bool, condition_met: str)
        """
        rule = self.rules.get(rule_id)
        if not rule:
            return False, "rule_not_found"

        if not rule.enabled:
            return False, "disabled"

        if rule.is_in_cooldown:
            return False, "cooldown"

        # Evaluar condiciones (AND para todas las condiciones de la regla)
        met_conditions = []
        all_must_match = True

        for condition in rule.conditions:
            result, detail = self._evaluate_condition(condition, indicators, ticker)
            if result and condition.get("field"):
                met_conditions.append(f"{condition['field']} {condition.get('operator')} {condition.get('value')}")
            all_must_match = all_must_match and result

        if all_must_match and met_conditions:
            return True, "; ".join(met_conditions)

        return False, "conditions_not_met"

    def _evaluate_condition(
        self,
        condition: Dict,
        indicators: Dict[str, Any],
        ticker: str,
    ) -> tuple[bool, str]:
        """Evalúa una condición individual."""
        cond_type = condition.get("type", "threshold")
        field = condition.get("field", "")
        operator = condition.get("operator", "")
        value = condition.get("value")
        lookback = condition.get("lookback", 0)

        try:
            if cond_type == "threshold":
                return self._check_threshold(indicators, field, operator, value)

            elif cond_type == "crossover":
                return self._check_crossover(indicators, field, value, lookback)

            elif cond_type == "fear_greed":
                return self._check_fear_greed(indicators, operator, value)

            elif cond_type == "volume_spike":
                return self._check_volume_spike(indicators, field, value)

            elif cond_type == "price_level":
                return self._check_price_level(indicators, field, operator, value)

            elif cond_type == "macro_change":
                return self._check_macro_change(indicators, field, operator, value)

            else:
                logger.warning(f"Tipo de condición desconocido: {cond_type}")
                return False, "unknown_type"

        except Exception as e:
            logger.error(f"Error evaluando condición: {e}")
            return False, f"error: {e}"

    @staticmethod
    def _check_threshold(
        indicators: Dict[str, Any],
        field: str,
        operator: str,
        threshold: float,
    ) -> tuple[bool, str]:
        """Evalúa condición de umbral simple."""
        actual = indicators.get(field)
        if actual is None:
            return False, f"campo {field} no disponible"

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
        }

        check = ops.get(operator)
        if check is None:
            return False, f"operador desconocido: {operator}"

        result = check(actual, threshold)
        return result, f"{field}={actual:.2f} {operator} {threshold}"

    @staticmethod
    def _check_crossover(
        indicators: Dict[str, Any],
        field_a: str,
        field_b: str,
        lookback: int,
    ) -> tuple[bool, str]:
        """Evalúa cruce entre dos indicadores."""
        series_a = indicators.get(f"{field_a}_series")
        series_b = indicators.get(f"{field_b}_series")

        if series_a is None or series_b is None:
            return False, f"series {field_a}/{field_b} no disponibles"

        if len(series_a) < 2 or len(series_b) < 2:
            return False, "series demasiado cortas"

        # Cruce: último valor de A cruza por encima de B
        prev_a, prev_b = series_a[-2], series_b[-2]
        curr_a, curr_b = series_a[-1], series_b[-1]

        crossed = prev_a <= prev_b and curr_a > curr_b
        return crossed, f"{field_a} cruzó por encima de {field_b}"

    @staticmethod
    def _check_fear_greed(
        indicators: Dict[str, Any],
        operator: str,
        threshold: float,
    ) -> tuple[bool, str]:
        """Evalúa umbral de Fear & Greed."""
        fg_value = indicators.get("fear_greed_index")
        if fg_value is None:
            return False, "fear_greed_index no disponible"

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }

        check = ops.get(operator)
        if check is None:
            return False, f"operador desconocido: {operator}"

        result = check(fg_value, threshold)
        return result, f"F&G={fg_value} {operator} {threshold}"

    @staticmethod
    def _check_volume_spike(
        indicators: Dict[str, Any],
        field: str,
        multiplier: float,
    ) -> tuple[bool, str]:
        """Evalúa si el volumen es un pico (múltiplo de la media)."""
        current_vol = indicators.get(f"{field}_current")
        avg_vol = indicators.get(f"{field}_avg")

        if current_vol is None or avg_vol is None:
            return False, "datos de volumen no disponibles"

        if avg_vol == 0:
            return False, "volumen medio = 0"

        ratio = current_vol / avg_vol
        return ratio >= multiplier, f"vol_ratio={ratio:.2f}x >= {multiplier}x"

    @staticmethod
    def _check_price_level(
        indicators: Dict[str, Any],
        field: str,
        operator: str,
        level: float,
    ) -> tuple[bool, str]:
        """Evalúa si el precio cruza un nivel específico."""
        price = indicators.get(field)
        if price is None:
            return False, f"precio ({field}) no disponible"

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }

        check = ops.get(operator)
        if check is None:
            return False, f"operador desconocido: {operator}"

        result = check(price, level)
        return result, f"price={price:.2f} {operator} {level}"

    @staticmethod
    def _check_macro_change(
        indicators: Dict[str, Any],
        field: str,
        operator: str,
        threshold: float,
    ) -> tuple[bool, str]:
        """Evalúa cambio en indicador macro."""
        value = indicators.get(field)
        if value is None:
            return False, f"indicador macro {field} no disponible"

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }

        check = ops.get(operator)
        if check is None:
            return False, f"operador desconocido: {operator}"

        result = check(value, threshold)
        return result, f"{field}={value} {operator} {threshold}"