"""Threshold-based alerting for Mjolnir.

When a metric breaches a rule the AlertManager records an alert --
like thunder following the lightning strike of Thor's hammer.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from mjolnir.core import Metric, MetricCollector


# ---------------------------------------------------------------------------
# Enums & value objects
# ---------------------------------------------------------------------------

class Condition(Enum):
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Declarative rule that fires when a metric breaches a threshold.

    Attributes:
        metric:    Name of the metric to watch.
        condition: Comparison operator.
        threshold: Numeric boundary.
        severity:  Importance level of the resulting alert.
        message:   Optional human-readable description.
        rule_id:   Unique identifier (auto-generated).
    """
    metric: str
    condition: Condition
    threshold: float
    severity: Severity = Severity.WARNING
    message: str = ""
    rule_id: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = f"rule-{uuid.uuid4().hex[:8]}"

    def evaluate(self, value: float) -> bool:
        """Return ``True`` if *value* breaches this rule."""
        if self.condition == Condition.GT:
            return value > self.threshold
        if self.condition == Condition.LT:
            return value < self.threshold
        if self.condition == Condition.EQ:
            return value == self.threshold
        if self.condition == Condition.GTE:
            return value >= self.threshold
        if self.condition == Condition.LTE:
            return value <= self.threshold
        return False


@dataclass
class Alert:
    """An alert that was fired by a rule evaluation."""
    rule_id: str
    metric_name: str
    metric_value: float
    severity: Severity
    message: str
    fired_at: float = 0.0
    alert_id: str = ""

    def __post_init__(self) -> None:
        if self.fired_at == 0.0:
            self.fired_at = time.time()
        if not self.alert_id:
            self.alert_id = f"alert-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "metric": self.metric_name,
            "value": self.metric_value,
            "severity": self.severity.value,
            "message": self.message,
            "fired_at": self.fired_at,
        }


# ---------------------------------------------------------------------------
# AlertHistory
# ---------------------------------------------------------------------------

class AlertHistory:
    """Append-only ledger of fired alerts."""

    def __init__(self, max_size: int = 5000) -> None:
        self._alerts: List[Alert] = []
        self._max_size = max_size

    def add(self, alert: Alert) -> None:
        self._alerts.append(alert)
        if len(self._alerts) > self._max_size:
            self._alerts[:] = self._alerts[-self._max_size:]

    @property
    def alerts(self) -> List[Alert]:
        return list(self._alerts)

    def by_severity(self, severity: Severity) -> List[Alert]:
        return [a for a in self._alerts if a.severity == severity]

    def by_metric(self, metric_name: str) -> List[Alert]:
        return [a for a in self._alerts if a.metric_name == metric_name]

    @property
    def count(self) -> int:
        return len(self._alerts)

    def clear(self) -> None:
        self._alerts.clear()


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

class AlertManager:
    """Evaluates :class:`AlertRule` instances against a collector.

    Call :meth:`check` to evaluate all rules against the latest metric
    values and fire alerts for any breaches.
    """

    def __init__(self, collector: MetricCollector) -> None:
        self.collector = collector
        self._rules: Dict[str, AlertRule] = {}
        self.history = AlertHistory()
        self._callbacks: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def list_rules(self) -> List[AlertRule]:
        return list(self._rules.values())

    def on_alert(self, callback: Callable[[Alert], None]) -> None:
        self._callbacks.append(callback)

    def check(self) -> List[Alert]:
        """Evaluate every rule against the latest metric values.

        Returns the list of newly-fired alerts (if any).
        """
        fired: List[Alert] = []
        for rule in self._rules.values():
            latest = self.collector.latest(rule.metric)
            if latest is None:
                continue
            if rule.evaluate(latest.value):
                alert = Alert(
                    rule_id=rule.rule_id,
                    metric_name=rule.metric,
                    metric_value=latest.value,
                    severity=rule.severity,
                    message=rule.message or f"{rule.metric} {rule.condition.value} {rule.threshold}",
                )
                fired.append(alert)
                self.history.add(alert)
                for cb in self._callbacks:
                    cb(alert)
        return fired
